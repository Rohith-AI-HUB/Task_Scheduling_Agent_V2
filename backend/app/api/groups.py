from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database.collections import get_collection
from app.models.group import GroupCreateRequest, GroupListResponse, GroupResponse
from app.services.group_service import (
    generate_groups_for_task,
    get_student_group_for_task,
    list_groups_for_task,
    serialize_group,
)
from app.utils.dependencies import get_current_student, get_current_teacher, get_current_user

router = APIRouter()


def _join_submissions_by_group_id(groups: list[dict], submissions: list[dict]) -> list[GroupResponse]:
    by_group_id: dict[ObjectId, dict] = {}
    for s in submissions:
        gid = s.get("group_id")
        if isinstance(gid, ObjectId):
            by_group_id[gid] = s

    results: list[GroupResponse] = []
    for g in groups:
        submission = by_group_id.get(g["_id"])
        results.append(GroupResponse(**serialize_group(g, submission=submission)))
    return results


@router.post("", response_model=GroupListResponse, status_code=status.HTTP_201_CREATED)
async def create_groups_for_task(
    request: GroupCreateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    group_set, groups, has_submissions = await generate_groups_for_task(
        task_id=request.task_id,
        teacher_uid=current_teacher["uid"],
        regenerate=request.regenerate,
    )
    return GroupListResponse(
        task_id=str(group_set["task_id"]),
        group_set_id=str(group_set["_id"]),
        group_settings=group_set.get("group_settings"),
        problem_statements=list(group_set.get("problem_statements") or []),
        has_submissions=has_submissions,
        groups=[GroupResponse(**serialize_group(g)) for g in groups],
    )


@router.get("", response_model=GroupListResponse)
async def list_groups(
    task_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    group_set, groups, has_submissions = await list_groups_for_task(task_id=task_id, user=current_user)
    if not group_set:
        return GroupListResponse(task_id=task_id, has_submissions=has_submissions, groups=[])

    group_ids = [g["_id"] for g in groups if g.get("_id")]
    submissions: list[dict] = []
    if current_user.get("role") == "teacher" and group_ids:
        submissions_collection = get_collection("submissions")
        submissions = await submissions_collection.find(
            {"task_id": group_set["task_id"], "group_id": {"$in": group_ids}}
        ).to_list(length=None)

    serialized = _join_submissions_by_group_id(groups, submissions) if submissions else [GroupResponse(**serialize_group(g)) for g in groups]
    return GroupListResponse(
        task_id=str(group_set["task_id"]),
        group_set_id=str(group_set["_id"]),
        group_settings=group_set.get("group_settings"),
        problem_statements=list(group_set.get("problem_statements") or []),
        has_submissions=has_submissions,
        groups=serialized,
    )


@router.get("/me", response_model=GroupResponse)
async def get_my_group(
    task_id: str = Query(...),
    current_student: dict = Depends(get_current_student),
):
    group = await get_student_group_for_task(task_id=task_id, student_uid=current_student["uid"])
    return GroupResponse(**serialize_group(group))


@router.get("/health")
async def health():
    return {"status": "ok", "service": "groups"}
