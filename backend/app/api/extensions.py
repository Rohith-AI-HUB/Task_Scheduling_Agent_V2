"""
Extension Request API
Handles deadline extension requests from students with AI analysis
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.database.connection import get_db
from app.models.extension import (
    ExtensionRequestCreate,
    ExtensionRequestResponse,
    ExtensionRequestList,
    ExtensionReviewRequest,
    ExtensionReviewResponse,
    ExtensionStats
)
from app.services.extension_service import ExtensionService
from app.services.groq_service import groq_service
from app.utils.dependencies import get_current_user

router = APIRouter()


def get_extension_service():
    """Dependency to get extension service"""
    return ExtensionService(get_db())


@router.post("", response_model=ExtensionRequestResponse, status_code=201)
async def create_extension_request(
    request_data: ExtensionRequestCreate,
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    Create a new extension request (Student only)

    Generates AI workload analysis to help teachers make informed decisions
    """
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can request extensions")

    try:
        extension = await service.create_extension_request(
            student_uid=current_user["uid"],
            request_data=request_data,
            groq_service=groq_service
        )
        return extension
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create extension request: {str(e)}")


@router.get("", response_model=ExtensionRequestList)
async def list_extension_requests(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    List extension requests

    - Students: See their own requests
    - Teachers: See requests for their subjects
    """
    if current_user["role"] == "student":
        # Students see only their own requests
        extensions = await service.get_extension_requests(
            student_uid=current_user["uid"],
            status=status,
            limit=limit
        )
    elif current_user["role"] == "teacher":
        # Teachers see requests for their subjects
        extensions = await service.get_extension_requests(
            teacher_uid=current_user["uid"],
            status=status,
            limit=limit
        )
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Count by status
    pending_count = sum(1 for ext in extensions if ext.status == "pending")
    approved_count = sum(1 for ext in extensions if ext.status == "approved")
    denied_count = sum(1 for ext in extensions if ext.status == "denied")

    return ExtensionRequestList(
        items=extensions,
        total=len(extensions),
        pending_count=pending_count,
        approved_count=approved_count,
        denied_count=denied_count
    )


@router.get("/stats", response_model=ExtensionStats)
async def get_extension_stats(
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    Get extension request statistics (Teacher only)
    """
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can view statistics")

    stats = await service.get_extension_stats(teacher_uid=current_user["uid"])
    return stats


@router.get("/{extension_id}", response_model=ExtensionRequestResponse)
async def get_extension_request(
    extension_id: str,
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    Get a specific extension request by ID
    """
    extension = await service.get_extension_by_id(extension_id)
    if not extension:
        raise HTTPException(status_code=404, detail="Extension request not found")

    # Verify access
    if current_user["role"] == "student":
        if extension.student_uid != current_user["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to view this extension")
    elif current_user["role"] == "teacher":
        # Verify teacher owns the subject (checked in service layer, but double-check)
        db = get_db()
        task = await db.tasks.find_one({"_id": extension.task_id})
        subject = await db.subjects.find_one({"_id": task["subject_id"]}) if task else None
        if not subject or subject["teacher_uid"] != current_user["uid"]:
            raise HTTPException(status_code=403, detail="Not authorized to view this extension")

    return extension


@router.patch("/{extension_id}/approve", response_model=ExtensionReviewResponse)
async def approve_extension_request(
    extension_id: str,
    review_data: ExtensionReviewRequest,
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    Approve an extension request (Teacher only)

    Updates the task deadline to the approved deadline
    """
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can approve extensions")

    try:
        extension = await service.approve_extension(
            extension_id=extension_id,
            teacher_uid=current_user["uid"],
            response=review_data.response,
            approved_deadline=review_data.approved_deadline
        )

        return ExtensionReviewResponse(
            success=True,
            message="Extension request approved successfully",
            extension=extension
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve extension: {str(e)}")


@router.patch("/{extension_id}/deny", response_model=ExtensionReviewResponse)
async def deny_extension_request(
    extension_id: str,
    review_data: ExtensionReviewRequest,
    current_user: dict = Depends(get_current_user),
    service: ExtensionService = Depends(get_extension_service)
):
    """
    Deny an extension request (Teacher only)

    Task deadline remains unchanged
    """
    if current_user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Only teachers can deny extensions")

    try:
        extension = await service.deny_extension(
            extension_id=extension_id,
            teacher_uid=current_user["uid"],
            response=review_data.response
        )

        return ExtensionReviewResponse(
            success=True,
            message="Extension request denied",
            extension=extension
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deny extension: {str(e)}")


@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "extensions"}
