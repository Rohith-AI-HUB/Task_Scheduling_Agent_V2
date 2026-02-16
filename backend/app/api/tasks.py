from datetime import datetime
from functools import lru_cache
from functools import partial
from pathlib import Path
from uuid import uuid4

import anyio
import boto3
from botocore.exceptions import ClientError
import logging
from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.database.collections import get_collection
from app.config import settings
from app.models.task import (
    TaskCreateRequest,
    TaskEvaluationsSummaryResponse,
    TaskResponse,
    TaskUpdateRequest,
)
from app.utils.dependencies import get_current_teacher, get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

_CODE_EXTENSIONS = {".py", ".ipynb", ".js", ".java", ".c", ".cpp", ".txt"}
_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".zip", ".pptx", ".ppt", ".doc", ".docx", *_CODE_EXTENSIONS}
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/zip",
    "application/x-zip-compressed",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "application/javascript",
    "text/javascript",
    "application/octet-stream",
    "application/x-ipynb+json",
}


def _serialize_task(doc: dict) -> TaskResponse:
    attachments = []
    for att in doc.get("attachments") or []:
        if isinstance(att, dict):
            uploaded_at = att.get("uploaded_at") or doc.get("created_at") or datetime.utcnow()
            attachments.append(
                {
                    "id": str(att.get("id") or ""),
                    "filename": att.get("filename") or "attachment",
                    "content_type": att.get("content_type"),
                    "size": att.get("size"),
                    "uploaded_at": uploaded_at,
                }
            )
    return TaskResponse(
        id=str(doc["_id"]),
        subject_id=str(doc["subject_id"]),
        title=doc["title"],
        description=doc.get("description"),
        deadline=doc.get("deadline"),
        points=doc.get("points"),
        task_type=doc.get("task_type"),
        type=doc.get("type", "individual"),
        problem_statements=list(doc.get("problem_statements") or []),
        group_settings=doc.get("group_settings"),
        evaluation_config=doc.get("evaluation_config"),
        attachments=attachments,
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


async def _find_task_or_404(task_id: str) -> dict:
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    tasks_collection = get_collection("tasks")
    task = await tasks_collection.find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _ensure_teacher_owns_subject(teacher_uid: str, subject_oid: ObjectId) -> dict:
    subjects_collection = get_collection("subjects")
    subject = await subjects_collection.find_one({"_id": subject_oid})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if subject.get("teacher_uid") != teacher_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return subject


async def _ensure_student_enrolled(student_uid: str, subject_oid: ObjectId) -> None:
    enrollments_collection = get_collection("enrollments")
    enrollment = await enrollments_collection.find_one(
        {"subject_id": subject_oid, "student_uid": student_uid}
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _uploads_root() -> Path:
    root = Path(settings.uploads_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    value = (name or "").strip()
    base = Path(value).name
    if not base or base in {".", ".."}:
        return "file"
    cleaned = base.replace("\x00", "").replace(":", "_").replace("/", "_").replace("\\", "_")
    if not cleaned or cleaned in {".", ".."}:
        return "file"
    return cleaned


def _safe_upload_path(root: Path, filename: str, attachment_id: str) -> tuple[str, Path]:
    safe_name = _safe_filename(filename)
    dest = root / f"{attachment_id}_{safe_name}"
    root_resolved = root.resolve()
    dest_resolved = dest.resolve()
    if root_resolved not in dest_resolved.parents and dest_resolved != root_resolved:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file name")
    return safe_name, dest


def _validate_file(file: UploadFile) -> None:
    filename = _safe_filename(file.filename or "")
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")
    if file.content_type:
        ct = str(file.content_type).lower()
        if ext in _CODE_EXTENSIONS:
            if not (ct.startswith("text/") or ct in {"application/octet-stream", "application/javascript"}):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")
        else:
            if ct not in _ALLOWED_CONTENT_TYPES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")


async def _save_upload(file: UploadFile, dest_path: Path) -> int:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with dest_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_bytes:
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
            out.write(chunk)
    return size


def _s3_enabled() -> bool:
    return bool(
        settings.s3_bucket
        and settings.s3_access_key_id
        and settings.s3_secret_access_key
    )


@lru_cache(maxsize=1)
def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        region_name=settings.s3_region or None,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )


def _s3_key(task_id: str, attachment_id: str, filename: str) -> str:
    safe_name = _safe_filename(filename)
    return f"tasks/{task_id}/{attachment_id}_{safe_name}"


def _file_size_sync(file: UploadFile) -> int:
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    return int(size)


async def _get_file_size(file: UploadFile) -> int:
    return await anyio.to_thread.run_sync(_file_size_sync, file)


async def _upload_to_s3(file: UploadFile, key: str) -> None:
    client = _s3_client()
    await anyio.to_thread.run_sync(file.file.seek, 0)

    def _do_upload():
        extra = {"ContentType": file.content_type} if file.content_type else None
        if extra:
            client.upload_fileobj(file.file, settings.s3_bucket, key, ExtraArgs=extra)
        else:
            client.upload_fileobj(file.file, settings.s3_bucket, key)

    await anyio.to_thread.run_sync(_do_upload)


def _presigned_get_url(key: str) -> str:
    client = _s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=settings.s3_presign_expires_seconds,
    )


async def _get_s3_object(key: str) -> dict:
    client = _s3_client()
    return await anyio.to_thread.run_sync(
        partial(client.get_object, Bucket=settings.s3_bucket, Key=key)
    )


async def _delete_s3_object(key: str) -> None:
    client = _s3_client()
    await anyio.to_thread.run_sync(
        partial(client.delete_object, Bucket=settings.s3_bucket, Key=key)
    )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    if not ObjectId.is_valid(request.subject_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")

    subject_oid = ObjectId(request.subject_id)
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    now = datetime.utcnow()
    normalized_problem_statements = [
        s.strip() for s in (request.problem_statements or []) if isinstance(s, str) and s.strip()
    ]
    task_doc = {
        "subject_id": subject_oid,
        "title": request.title.strip(),
        "description": request.description.strip() if request.description else None,
        "deadline": request.deadline,
        "points": request.points,
        "task_type": request.task_type.strip() if request.task_type else None,
        "type": request.type,
        "problem_statements": normalized_problem_statements if request.type == "group" else [],
        "group_settings": request.group_settings.model_dump() if request.type == "group" and request.group_settings else None,
        "evaluation_config": request.evaluation_config.model_dump() if request.evaluation_config else None,
        "attachments": [],
        "created_at": now,
        "updated_at": now,
    }
    if request.type == "group" and not request.group_settings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_settings is required for group tasks",
        )

    tasks_collection = get_collection("tasks")
    result = await tasks_collection.insert_one(task_doc)
    created = await tasks_collection.find_one({"_id": result.inserted_id})
    return _serialize_task(created)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    subject_id: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    tasks_collection = get_collection("tasks")
    subjects_collection = get_collection("subjects")

    if subject_id is not None:
        if not ObjectId.is_valid(subject_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")
        subject_oid = ObjectId(subject_id)

        if current_user.get("role") == "teacher":
            await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
        else:
            await _ensure_student_enrolled(current_user["uid"], subject_oid)

        tasks = await (
            tasks_collection.find({"subject_id": subject_oid})
            .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
            .to_list(length=None)
        )
        return [_serialize_task(t) for t in tasks]

    if current_user.get("role") == "teacher":
        subjects = await subjects_collection.find({"teacher_uid": current_user["uid"]}).to_list(
            length=None
        )
        subject_oids = [s["_id"] for s in subjects if s.get("_id")]
        if not subject_oids:
            return []
        tasks = await (
            tasks_collection.find({"subject_id": {"$in": subject_oids}})
            .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
            .to_list(length=None)
        )
        return [_serialize_task(t) for t in tasks]

    enrollments_collection = get_collection("enrollments")
    enrollments = await enrollments_collection.find({"student_uid": current_user["uid"]}).to_list(
        length=None
    )
    subject_oids = [e["subject_id"] for e in enrollments if e.get("subject_id")]
    if not subject_oids:
        return []
    tasks = await (
        tasks_collection.find({"subject_id": {"$in": subject_oids}})
        .sort([("deadline", 1), ("updated_at", -1), ("_id", -1)])
        .to_list(length=None)
    )
    return [_serialize_task(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]

    if current_user.get("role") == "teacher":
        await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
        return _serialize_task(task)

    await _ensure_student_enrolled(current_user["uid"], subject_oid)
    return _serialize_task(task)


@router.post("/{task_id}/attachments", response_model=TaskResponse)
async def upload_task_attachments(
    task_id: str,
    files: list[UploadFile] = File(...),
    current_teacher: dict = Depends(get_current_teacher),
):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    attachments_to_add: list[dict] = []
    saved_paths: list[Path] = []
    now = datetime.utcnow()
    root = _uploads_root() / "tasks" / str(task["_id"])

    try:
        for file in files:
            _validate_file(file)
            attachment_id = str(uuid4())
            filename = _safe_filename(file.filename or "file")
            if _s3_enabled():
                size = await _get_file_size(file)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
                key = _s3_key(str(task["_id"]), attachment_id, filename)
                await _upload_to_s3(file, key)
                attachments_to_add.append(
                    {
                        "id": attachment_id,
                        "filename": filename,
                        "content_type": file.content_type or "application/octet-stream",
                        "size": size,
                        "uploaded_at": now,
                        "storage": "s3",
                        "key": key,
                        "bucket": settings.s3_bucket,
                    }
                )
            else:
                filename, dest = _safe_upload_path(root, filename, attachment_id)
                size = await _save_upload(file, dest)
                saved_paths.append(dest)
                attachments_to_add.append(
                    {
                        "id": attachment_id,
                        "filename": filename,
                        "content_type": file.content_type or "application/octet-stream",
                        "size": size,
                        "uploaded_at": now,
                        "storage": "local",
                        "path": str(dest),
                    }
                )
    except HTTPException:
        for p in saved_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        raise

    tasks_collection = get_collection("tasks")
    await tasks_collection.update_one(
        {"_id": task["_id"]},
        {"$push": {"attachments": {"$each": attachments_to_add}}, "$set": {"updated_at": now}},
    )
    updated = await tasks_collection.find_one({"_id": task["_id"]})
    return _serialize_task(updated)


@router.get("/{task_id}/attachments/{attachment_id}")
async def download_task_attachment(
    task_id: str,
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    if current_user.get("role") == "teacher":
        await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
    else:
        await _ensure_student_enrolled(current_user["uid"], subject_oid)

    attachment = None
    for a in task.get("attachments") or []:
        if isinstance(a, dict) and a.get("id") == attachment_id:
            attachment = a
            break
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if attachment.get("storage") == "s3":
        key = attachment.get("key")
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
        try:
            obj = await _get_s3_object(key)
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code") or "")
            logger.error("S3 get_object failed: code=%s bucket=%s key=%s", code, settings.s3_bucket, key)
            if code in {"NoSuchKey", "NotFound"}:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
            if code in {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attachment access denied")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Attachment download failed")
        except Exception:
            logger.exception("S3 get_object failed: bucket=%s key=%s", settings.s3_bucket, key)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Attachment download failed")

        filename = _safe_filename(attachment.get("filename") or "attachment")
        content_type = obj.get("ContentType") or attachment.get("content_type") or "application/octet-stream"
        body = obj.get("Body")
        if body is None:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Attachment download failed")
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(body, media_type=content_type, headers=headers)

    path = attachment.get("path")
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    return FileResponse(
        path=str(file_path),
        media_type=attachment.get("content_type") or "application/octet-stream",
        filename=attachment.get("filename") or "attachment",
    )


@router.delete("/{task_id}/attachments/{attachment_id}", response_model=TaskResponse)
async def delete_task_attachment(
    task_id: str,
    attachment_id: str,
    current_teacher: dict = Depends(get_current_teacher),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    target = None
    for a in task.get("attachments") or []:
        if isinstance(a, dict) and a.get("id") == attachment_id:
            target = a
            break
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    if target.get("storage") == "s3":
        key = target.get("key")
        if key:
            await _delete_s3_object(key)
    else:
        path = target.get("path")
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    tasks_collection = get_collection("tasks")
    now = datetime.utcnow()
    await tasks_collection.update_one(
        {"_id": task["_id"]},
        {"$pull": {"attachments": {"id": attachment_id}}, "$set": {"updated_at": now}},
    )
    updated = await tasks_collection.find_one({"_id": task["_id"]})
    return _serialize_task(updated)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    request: TaskUpdateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    update: dict = {"updated_at": datetime.utcnow()}
    fields_set = request.model_fields_set
    if "title" in fields_set:
        update["title"] = request.title.strip()
    if "description" in fields_set:
        update["description"] = request.description.strip() if request.description else None
    if "deadline" in fields_set:
        update["deadline"] = request.deadline
    if "points" in fields_set:
        update["points"] = request.points
    if "task_type" in fields_set:
        update["task_type"] = request.task_type.strip() if request.task_type else None
    if "type" in fields_set:
        update["type"] = request.type
        if request.type != "group":
            update["problem_statements"] = []
            update["group_settings"] = None
    if "problem_statements" in fields_set:
        update["problem_statements"] = [
            s.strip()
            for s in (request.problem_statements or [])
            if isinstance(s, str) and s.strip()
        ]
    if "group_settings" in fields_set:
        update["group_settings"] = request.group_settings.model_dump() if request.group_settings else None
    if "evaluation_config" in fields_set:
        update["evaluation_config"] = (
            request.evaluation_config.model_dump() if request.evaluation_config else None
        )

    tasks_collection = get_collection("tasks")
    await tasks_collection.update_one({"_id": task["_id"]}, {"$set": update})
    updated = await tasks_collection.find_one({"_id": task["_id"]})
    return _serialize_task(updated)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, current_teacher: dict = Depends(get_current_teacher)):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    tasks_collection = get_collection("tasks")
    await tasks_collection.delete_one({"_id": task["_id"]})


@router.get("/{task_id}/evaluations/summary", response_model=TaskEvaluationsSummaryResponse)
async def get_evaluations_summary(
    task_id: str,
    current_teacher: dict = Depends(get_current_teacher),
):
    task = await _find_task_or_404(task_id)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    pipeline = [
        {"$match": {"task_id": task["_id"]}},
        {
            "$project": {
                "status": {"$ifNull": ["$evaluation.status", "pending"]},
                "ai_score": "$evaluation.ai_score",
            }
        },
        {
            "$facet": {
                "counts": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
                "summary": [{"$group": {"_id": None, "total": {"$sum": 1}, "avg": {"$avg": "$ai_score"}}}],
            }
        },
    ]

    agg = await submissions_collection.aggregate(pipeline).to_list(length=1)
    doc = agg[0] if agg else {}
    counts = doc.get("counts") if isinstance(doc.get("counts"), list) else []
    summary = doc.get("summary") if isinstance(doc.get("summary"), list) else []
    summary_doc = summary[0] if summary else {}

    status_counts: dict[str, int] = {}
    for row in counts:
        if not isinstance(row, dict):
            continue
        key = str(row.get("_id") or "pending")
        status_counts[key] = int(row.get("count") or 0)

    total = int(summary_doc.get("total") or sum(status_counts.values()))
    avg = summary_doc.get("avg")
    average_ai_score = float(avg) if isinstance(avg, (int, float)) else None
    return TaskEvaluationsSummaryResponse(
        task_id=task_id,
        total_submissions=total,
        status_counts=status_counts,
        average_ai_score=average_ai_score,
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tasks"}
