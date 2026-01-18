from datetime import datetime
from pathlib import Path
from uuid import uuid4

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.database.collections import get_collection
from app.models.submission import (
    SubmissionAttachmentResponse,
    SubmissionGradeRequest,
    SubmissionResponse,
    SubmissionUpsertRequest,
)
from app.utils.dependencies import get_current_student, get_current_teacher, get_current_user

router = APIRouter()

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".zip"}
_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/zip",
    "application/x-zip-compressed",
}


def _serialize_submission(doc: dict) -> SubmissionResponse:
    raw_attachments = doc.get("attachments") or []
    attachments: list[SubmissionAttachmentResponse] = []
    for a in raw_attachments:
        if not isinstance(a, dict):
            continue
        attachments.append(
            SubmissionAttachmentResponse(
                id=str(a.get("id")),
                filename=str(a.get("filename") or ""),
                content_type=str(a.get("content_type") or "application/octet-stream"),
                size=int(a.get("size") or 0),
                uploaded_at=a.get("uploaded_at") or doc.get("updated_at") or doc.get("created_at"),
            )
        )
    return SubmissionResponse(
        id=str(doc["_id"]),
        task_id=str(doc["task_id"]),
        subject_id=str(doc["subject_id"]),
        student_uid=doc["student_uid"],
        group_id=str(doc["group_id"]) if doc.get("group_id") is not None else None,
        content=doc["content"],
        submitted_at=doc["submitted_at"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
        score=doc.get("score"),
        feedback=doc.get("feedback"),
        attachments=attachments,
    )


async def _find_task_or_404(task_oid: ObjectId) -> dict:
    tasks_collection = get_collection("tasks")
    task = await tasks_collection.find_one({"_id": task_oid})
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def _ensure_teacher_owns_subject(teacher_uid: str, subject_oid: ObjectId) -> None:
    subjects_collection = get_collection("subjects")
    subject = await subjects_collection.find_one({"_id": subject_oid})
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if subject.get("teacher_uid") != teacher_uid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def _ensure_student_enrolled(student_uid: str, subject_oid: ObjectId) -> None:
    enrollments_collection = get_collection("enrollments")
    enrollment = await enrollments_collection.find_one(
        {"subject_id": subject_oid, "student_uid": student_uid}
    )
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


async def _find_submission_or_404(submission_oid: ObjectId) -> dict:
    submissions_collection = get_collection("submissions")
    submission = await submissions_collection.find_one({"_id": submission_oid})
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


def _uploads_root() -> Path:
    root = Path(settings.uploads_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_filename(name: str) -> str:
    value = (name or "").strip()
    base = Path(value).name
    if not base:
        return "file"
    return base.replace("\x00", "")


def _validate_file(file: UploadFile) -> None:
    filename = _safe_filename(file.filename or "")
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed")
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
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


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_200_OK)
async def upsert_submission(
    request: SubmissionUpsertRequest,
    current_student: dict = Depends(get_current_student),
):
    if not ObjectId.is_valid(request.task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")

    task_oid = ObjectId(request.task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_student_enrolled(current_student["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    now = datetime.utcnow()
    doc: dict = {
        "task_id": task_oid,
        "subject_id": subject_oid,
        "student_uid": current_student["uid"],
        "content": request.content,
        "submitted_at": now,
        "updated_at": now,
    }

    task_type = task.get("type", "individual")
    if task_type == "group":
        if not request.group_id or not ObjectId.is_valid(request.group_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_id is required")
        group_oid = ObjectId(request.group_id)
        groups_collection = get_collection("groups")
        group = await groups_collection.find_one(
            {"_id": group_oid, "task_id": task_oid, "member_uids": current_student["uid"]}
        )
        if not group:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        doc["group_id"] = group_oid
        existing = await submissions_collection.find_one({"task_id": task_oid, "group_id": group_oid})
    else:
        existing = await submissions_collection.find_one(
            {"task_id": task_oid, "student_uid": current_student["uid"], "group_id": None}
        )

    if existing:
        await submissions_collection.update_one({"_id": existing["_id"]}, {"$set": doc})
        updated = await submissions_collection.find_one({"_id": existing["_id"]})
        return _serialize_submission(updated)

    doc["created_at"] = now
    doc["score"] = None
    doc["feedback"] = None
    doc["attachments"] = []
    try:
        result = await submissions_collection.insert_one(doc)
    except DuplicateKeyError:
        if task_type == "group":
            existing = await submissions_collection.find_one({"task_id": task_oid, "group_id": doc.get("group_id")})
        else:
            existing = await submissions_collection.find_one(
                {"task_id": task_oid, "student_uid": current_student["uid"], "group_id": None}
            )
        if existing:
            await submissions_collection.update_one({"_id": existing["_id"]}, {"$set": doc})
            updated = await submissions_collection.find_one({"_id": existing["_id"]})
            return _serialize_submission(updated)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submit failed")

    created = await submissions_collection.find_one({"_id": result.inserted_id})
    return _serialize_submission(created)


@router.get("/me", response_model=SubmissionResponse)
async def get_my_submission(
    task_id: str = Query(...),
    current_student: dict = Depends(get_current_student),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_student_enrolled(current_student["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    if task.get("type", "individual") == "group":
        groups_collection = get_collection("groups")
        group = await groups_collection.find_one(
            {"task_id": task_oid, "member_uids": current_student["uid"]}
        )
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        submission = await submissions_collection.find_one(
            {"task_id": task_oid, "group_id": group["_id"]},
            sort=[("submitted_at", -1), ("_id", -1)],
        )
    else:
        submission = await submissions_collection.find_one(
            {"task_id": task_oid, "student_uid": current_student["uid"], "group_id": None},
            sort=[("submitted_at", -1), ("_id", -1)],
        )
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return _serialize_submission(submission)


@router.get("/mine", response_model=list[SubmissionResponse])
async def list_my_submissions(
    subject_id: str = Query(...),
    current_student: dict = Depends(get_current_student),
):
    if not ObjectId.is_valid(subject_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject id")

    subject_oid = ObjectId(subject_id)
    await _ensure_student_enrolled(current_student["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    tasks_collection = get_collection("tasks")
    tasks = await tasks_collection.find({"subject_id": subject_oid}).to_list(length=None)
    group_task_ids = [t["_id"] for t in tasks if t.get("type") == "group" and t.get("_id")]

    submissions: list[dict] = []
    individual_submissions = await (
        submissions_collection.find(
            {"subject_id": subject_oid, "student_uid": current_student["uid"], "group_id": None}
        )
        .sort([("submitted_at", -1), ("_id", -1)])
        .to_list(length=None)
    )
    submissions.extend(individual_submissions)

    if group_task_ids:
        groups_collection = get_collection("groups")
        groups = await groups_collection.find(
            {"task_id": {"$in": group_task_ids}, "member_uids": current_student["uid"]}
        ).to_list(length=None)
        group_ids = [g["_id"] for g in groups if g.get("_id")]
        if group_ids:
            group_submissions = await (
                submissions_collection.find({"subject_id": subject_oid, "group_id": {"$in": group_ids}})
                .sort([("submitted_at", -1), ("_id", -1)])
                .to_list(length=None)
            )
            submissions.extend(group_submissions)

    submissions.sort(key=lambda s: (s.get("submitted_at") or datetime.min), reverse=True)
    return [_serialize_submission(s) for s in submissions]


@router.post("/{submission_id}/attachments", response_model=SubmissionResponse)
async def upload_attachments(
    submission_id: str,
    files: list[UploadFile] = File(...),
    current_student: dict = Depends(get_current_student),
):
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission id")
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")

    submission_oid = ObjectId(submission_id)
    submission = await _find_submission_or_404(submission_oid)

    if submission.get("group_id") is not None:
        groups_collection = get_collection("groups")
        group = await groups_collection.find_one({"_id": submission["group_id"], "member_uids": current_student["uid"]})
        if not group:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    else:
        if submission.get("student_uid") != current_student["uid"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    task = await _find_task_or_404(submission["task_id"])
    await _ensure_student_enrolled(current_student["uid"], task["subject_id"])

    attachments_to_add: list[dict] = []
    saved_paths: list[Path] = []
    now = datetime.utcnow()
    root = _uploads_root() / "submissions" / str(submission_oid)

    try:
        for file in files:
            _validate_file(file)
            attachment_id = str(uuid4())
            filename = _safe_filename(file.filename or "file")
            dest = root / f"{attachment_id}_{filename}"
            size = await _save_upload(file, dest)
            saved_paths.append(dest)
            attachments_to_add.append(
                {
                    "id": attachment_id,
                    "filename": filename,
                    "content_type": file.content_type or "application/octet-stream",
                    "size": size,
                    "uploaded_at": now,
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

    submissions_collection = get_collection("submissions")
    await submissions_collection.update_one(
        {"_id": submission_oid},
        {
            "$push": {"attachments": {"$each": attachments_to_add}},
            "$set": {"updated_at": now},
        },
    )
    updated = await submissions_collection.find_one({"_id": submission_oid})
    return _serialize_submission(updated)


@router.get("/{submission_id}/attachments/{attachment_id}")
async def download_attachment(
    submission_id: str,
    attachment_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission id")

    submission_oid = ObjectId(submission_id)
    submission = await _find_submission_or_404(submission_oid)

    task = await _find_task_or_404(submission["task_id"])
    subject_oid = task["subject_id"]

    if current_user.get("role") == "teacher":
        await _ensure_teacher_owns_subject(current_user["uid"], subject_oid)
    else:
        if submission.get("group_id") is not None:
            groups_collection = get_collection("groups")
            group = await groups_collection.find_one({"_id": submission["group_id"], "member_uids": current_user["uid"]})
            if not group:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        else:
            if submission.get("student_uid") != current_user.get("uid"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        await _ensure_student_enrolled(current_user["uid"], subject_oid)

    attachment = None
    for a in submission.get("attachments") or []:
        if isinstance(a, dict) and a.get("id") == attachment_id:
            attachment = a
            break
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

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


@router.delete("/{submission_id}/attachments/{attachment_id}", response_model=SubmissionResponse)
async def delete_attachment(
    submission_id: str,
    attachment_id: str,
    current_student: dict = Depends(get_current_student),
):
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission id")

    submission_oid = ObjectId(submission_id)
    submission = await _find_submission_or_404(submission_oid)
    if submission.get("group_id") is not None:
        groups_collection = get_collection("groups")
        group = await groups_collection.find_one({"_id": submission["group_id"], "member_uids": current_student["uid"]})
        if not group:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    else:
        if submission.get("student_uid") != current_student["uid"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    target = None
    for a in submission.get("attachments") or []:
        if isinstance(a, dict) and a.get("id") == attachment_id:
            target = a
            break
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    path = target.get("path")
    if path:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    submissions_collection = get_collection("submissions")
    now = datetime.utcnow()
    await submissions_collection.update_one(
        {"_id": submission_oid},
        {"$pull": {"attachments": {"id": attachment_id}}, "$set": {"updated_at": now}},
    )
    updated = await submissions_collection.find_one({"_id": submission_oid})
    return _serialize_submission(updated)


@router.get("", response_model=list[SubmissionResponse])
async def list_submissions(
    task_id: str = Query(...),
    current_teacher: dict = Depends(get_current_teacher),
):
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")
    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    submissions_collection = get_collection("submissions")
    submissions = await (
        submissions_collection.find({"task_id": task_oid})
        .sort([("submitted_at", -1), ("_id", -1)])
        .to_list(length=None)
    )
    return [_serialize_submission(s) for s in submissions]


@router.patch("/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: str,
    request: SubmissionGradeRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    if not ObjectId.is_valid(submission_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission id")

    submissions_collection = get_collection("submissions")
    submission = await submissions_collection.find_one({"_id": ObjectId(submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    subject_oid = submission["subject_id"]
    await _ensure_teacher_owns_subject(current_teacher["uid"], subject_oid)

    update = {"updated_at": datetime.utcnow()}
    if request.score is not None:
        update["score"] = request.score
    if request.feedback is not None:
        update["feedback"] = request.feedback

    await submissions_collection.update_one({"_id": submission["_id"]}, {"$set": update})
    updated = await submissions_collection.find_one({"_id": submission["_id"]})
    return _serialize_submission(updated)


@router.get("/health")
async def health():
    return {"status": "ok", "service": "submissions"}
