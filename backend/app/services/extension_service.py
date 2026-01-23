"""
Extension Service
Manages deadline extension requests with AI workload analysis
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.extension import (
    ExtensionRequestCreate,
    ExtensionRequestResponse,
    ExtensionAIAnalysis,
    WorkloadSnapshot,
    ExtensionStats
)

logger = logging.getLogger(__name__)


class ExtensionService:
    """Service for managing extension requests"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.extensions
        self.tasks_collection = db.tasks
        self.submissions_collection = db.submissions
        self.subjects_collection = db.subjects
        self.users_collection = db.users

    async def get_workload_snapshot(self, student_uid: str) -> WorkloadSnapshot:
        """
        Get current workload snapshot for a student
        """
        now = datetime.utcnow()
        next_week = now + timedelta(days=7)

        # Get all tasks for student (through enrollments)
        enrollments = await self.db.enrollments.find({"student_uid": student_uid}).to_list(None)
        subject_ids = [e["subject_id"] for e in enrollments]

        # Get all tasks from enrolled subjects
        all_tasks = await self.tasks_collection.find({
            "subject_id": {"$in": subject_ids}
        }).to_list(None)

        # Get all submissions from this student
        submissions = await self.submissions_collection.find({
            "student_uid": student_uid
        }).to_list(None)

        submitted_task_ids = {str(s["task_id"]) for s in submissions}

        # Calculate metrics
        pending_tasks = []
        overdue_tasks = []
        upcoming_deadlines = []
        total_points = 0

        for task in all_tasks:
            task_id = str(task["_id"])
            if task_id in submitted_task_ids:
                continue  # Skip submitted tasks

            deadline = task.get("deadline")
            if not deadline:
                continue

            points = task.get("points", 0)
            total_points += points

            task_info = {
                "task_id": task_id,
                "title": task.get("title", ""),
                "deadline": deadline.isoformat() if isinstance(deadline, datetime) else str(deadline),
                "points": points
            }

            if deadline < now:
                overdue_tasks.append(task_info)
            elif deadline <= next_week:
                upcoming_deadlines.append(task_info)

            pending_tasks.append(task_info)

        # Calculate recent submission activity
        recent_submissions = await self.submissions_collection.count_documents({
            "student_uid": student_uid,
            "submitted_at": {"$gte": now - timedelta(days=7)}
        })

        # Calculate average submission time (how early/late they submit)
        avg_submission_time = None
        submission_times = []
        for sub in submissions:
            if sub.get("submitted_at") and sub.get("task_id"):
                task = await self.tasks_collection.find_one({"_id": sub["task_id"]})
                if task and task.get("deadline"):
                    time_diff = (task["deadline"] - sub["submitted_at"]).total_seconds() / 3600  # hours
                    submission_times.append(time_diff)

        if submission_times:
            avg_submission_time = sum(submission_times) / len(submission_times)

        return WorkloadSnapshot(
            pending_tasks=len(pending_tasks),
            overdue_tasks=len(overdue_tasks),
            upcoming_deadlines=upcoming_deadlines[:10],  # Limit to 10
            recent_submissions=recent_submissions,
            average_submission_time=avg_submission_time,
            current_subjects=len(subject_ids),
            total_points_at_stake=total_points
        )

    async def create_extension_request(
        self,
        student_uid: str,
        request_data: ExtensionRequestCreate,
        groq_service=None
    ) -> ExtensionRequestResponse:
        """
        Create a new extension request with AI analysis
        """
        # Get task details
        task = await self.tasks_collection.find_one({"_id": ObjectId(request_data.task_id)})
        if not task:
            raise ValueError("Task not found")

        current_deadline = task.get("deadline")
        if not current_deadline:
            raise ValueError("Task has no deadline")

        # Verify student is enrolled in the subject
        enrollment = await self.db.enrollments.find_one({
            "student_uid": student_uid,
            "subject_id": task["subject_id"]
        })
        if not enrollment:
            raise ValueError("Student not enrolled in this subject")

        # Check if extension already requested for this task
        existing = await self.collection.find_one({
            "student_uid": student_uid,
            "task_id": request_data.task_id,
            "status": "pending"
        })
        if existing:
            raise ValueError("Extension request already pending for this task")

        # Calculate extension days
        # Handle timezone awareness to avoid "can't subtract offset-naive and offset-aware datetimes"
        req_deadline = request_data.requested_deadline
        curr_deadline = current_deadline

        if req_deadline.tzinfo is None:
            req_deadline = req_deadline.replace(tzinfo=timezone.utc)
        
        if curr_deadline.tzinfo is None:
            curr_deadline = curr_deadline.replace(tzinfo=timezone.utc)

        extension_days = (req_deadline - curr_deadline).days

        if extension_days <= 0:
            raise ValueError("Requested deadline must be after current deadline")

        # Get workload snapshot
        workload = await self.get_workload_snapshot(student_uid)

        # Generate AI analysis
        ai_analysis = None
        if groq_service:
            try:
                ai_analysis = await self._generate_ai_analysis(
                    task=task,
                    workload=workload,
                    extension_days=extension_days,
                    reason=request_data.reason,
                    groq_service=groq_service
                )
            except Exception as e:
                logger.error(f"Failed to generate AI analysis: {e}")
                # Continue without AI analysis

        # Create extension request
        now = datetime.utcnow()
        extension_doc = {
            "student_uid": student_uid,
            "task_id": request_data.task_id,
            "subject_id": str(task["subject_id"]),
            "current_deadline": current_deadline,
            "requested_deadline": request_data.requested_deadline,
            "extension_days": extension_days,
            "reason": request_data.reason,
            "status": "pending",
            "ai_analysis": ai_analysis.dict() if ai_analysis else None,
            "teacher_response": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": now,
            "updated_at": now
        }

        result = await self.collection.insert_one(extension_doc)
        extension_doc["_id"] = result.inserted_id

        return await self._build_extension_response(extension_doc)

    async def _generate_ai_analysis(
        self,
        task: dict,
        workload: WorkloadSnapshot,
        extension_days: int,
        reason: str,
        groq_service
    ) -> ExtensionAIAnalysis:
        """
        Generate AI workload analysis using Groq
        """
        # Prepare data for Groq
        preprocessed_data = {
            "task_info": {
                "title": task.get("title", ""),
                "points": task.get("points", 0),
                "deadline": task.get("deadline").isoformat() if task.get("deadline") else None,
                "type": task.get("type", "unknown")
            },
            "extension_request": {
                "days": extension_days,
                "reason": reason[:500]  # Truncate reason
            },
            "workload": {
                "pending_tasks": workload.pending_tasks,
                "overdue_tasks": workload.overdue_tasks,
                "upcoming_count": len(workload.upcoming_deadlines),
                "recent_submissions": workload.recent_submissions,
                "avg_submission_time": workload.average_submission_time,
                "total_points": workload.total_points_at_stake
            }
        }

        # Call Groq service
        analysis_result = await groq_service.analyze_extension_request(preprocessed_data)

        return analysis_result

    async def get_extension_requests(
        self,
        student_uid: Optional[str] = None,
        teacher_uid: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ExtensionRequestResponse]:
        """
        Get extension requests filtered by criteria
        """
        query = {}

        if student_uid:
            query["student_uid"] = student_uid

        if teacher_uid:
            # Get subjects taught by this teacher
            subjects = await self.subjects_collection.find({"teacher_uid": teacher_uid}).to_list(None)
            subject_ids = [str(s["_id"]) for s in subjects]
            query["subject_id"] = {"$in": subject_ids}

        if status:
            query["status"] = status

        extensions = await self.collection.find(query).sort("created_at", -1).limit(limit).to_list(None)

        results = []
        for ext in extensions:
            results.append(await self._build_extension_response(ext))

        return results

    async def get_extension_by_id(self, extension_id: str) -> Optional[ExtensionRequestResponse]:
        """Get a specific extension request by ID"""
        extension = await self.collection.find_one({"_id": ObjectId(extension_id)})
        if not extension:
            return None

        return await self._build_extension_response(extension)

    async def approve_extension(
        self,
        extension_id: str,
        teacher_uid: str,
        response: Optional[str] = None,
        approved_deadline: Optional[datetime] = None
    ) -> ExtensionRequestResponse:
        """
        Approve an extension request and update task deadline
        """
        extension = await self.collection.find_one({"_id": ObjectId(extension_id)})
        if not extension:
            raise ValueError("Extension request not found")

        if extension["status"] != "pending":
            raise ValueError("Extension request is not pending")

        # Verify teacher owns the subject
        task = await self.tasks_collection.find_one({"_id": ObjectId(extension["task_id"])})
        subject = await self.subjects_collection.find_one({"_id": task["subject_id"]})
        if subject["teacher_uid"] != teacher_uid:
            raise ValueError("Not authorized to review this extension")

        # Determine final deadline
        final_deadline = approved_deadline or extension["requested_deadline"]

        # Update extension request
        now = datetime.utcnow()
        await self.collection.update_one(
            {"_id": ObjectId(extension_id)},
            {
                "$set": {
                    "status": "approved",
                    "teacher_response": response,
                    "reviewed_by": teacher_uid,
                    "reviewed_at": now,
                    "approved_deadline": final_deadline,
                    "updated_at": now
                }
            }
        )

        # Update task deadline
        await self.tasks_collection.update_one(
            {"_id": ObjectId(extension["task_id"])},
            {"$set": {"deadline": final_deadline}}
        )

        # Get updated extension
        updated = await self.collection.find_one({"_id": ObjectId(extension_id)})
        return await self._build_extension_response(updated)

    async def deny_extension(
        self,
        extension_id: str,
        teacher_uid: str,
        response: Optional[str] = None
    ) -> ExtensionRequestResponse:
        """
        Deny an extension request
        """
        extension = await self.collection.find_one({"_id": ObjectId(extension_id)})
        if not extension:
            raise ValueError("Extension request not found")

        if extension["status"] != "pending":
            raise ValueError("Extension request is not pending")

        # Verify teacher owns the subject
        task = await self.tasks_collection.find_one({"_id": ObjectId(extension["task_id"])})
        subject = await self.subjects_collection.find_one({"_id": task["subject_id"]})
        if subject["teacher_uid"] != teacher_uid:
            raise ValueError("Not authorized to review this extension")

        # Update extension request
        now = datetime.utcnow()
        await self.collection.update_one(
            {"_id": ObjectId(extension_id)},
            {
                "$set": {
                    "status": "denied",
                    "teacher_response": response,
                    "reviewed_by": teacher_uid,
                    "reviewed_at": now,
                    "updated_at": now
                }
            }
        )

        # Get updated extension
        updated = await self.collection.find_one({"_id": ObjectId(extension_id)})
        return await self._build_extension_response(updated)

    async def get_extension_stats(self, teacher_uid: Optional[str] = None) -> ExtensionStats:
        """Get extension request statistics"""
        query = {}

        if teacher_uid:
            subjects = await self.subjects_collection.find({"teacher_uid": teacher_uid}).to_list(None)
            subject_ids = [str(s["_id"]) for s in subjects]
            query["subject_id"] = {"$in": subject_ids}

        total = await self.collection.count_documents(query)

        pending = await self.collection.count_documents({**query, "status": "pending"})
        approved = await self.collection.count_documents({**query, "status": "approved"})
        denied = await self.collection.count_documents({**query, "status": "denied"})

        approval_rate = (approved / total * 100) if total > 0 else 0.0

        # Calculate average extension days for approved requests
        approved_extensions = await self.collection.find({
            **query,
            "status": "approved"
        }).to_list(None)

        avg_days = 0.0
        if approved_extensions:
            total_days = sum(ext.get("extension_days", 0) for ext in approved_extensions)
            avg_days = total_days / len(approved_extensions)

        return ExtensionStats(
            total_requests=total,
            pending_requests=pending,
            approved_requests=approved,
            denied_requests=denied,
            approval_rate=round(approval_rate, 1),
            average_extension_days=round(avg_days, 1)
        )

    async def _build_extension_response(self, extension_doc: dict) -> ExtensionRequestResponse:
        """Build extension response with enriched data"""
        # Get task details
        task = await self.tasks_collection.find_one({"_id": ObjectId(extension_doc["task_id"])})
        task_title = task.get("title", "Unknown Task") if task else "Unknown Task"

        # Get subject details
        subject = None
        if task:
            subject = await self.subjects_collection.find_one({"_id": task["subject_id"]})

        subject_name = subject.get("name", "Unknown Subject") if subject else "Unknown Subject"

        # Get student details
        user = await self.users_collection.find_one({"uid": extension_doc["student_uid"]})
        student_name = user.get("display_name") or user.get("email") if user else None

        # Parse AI analysis
        ai_analysis = None
        if extension_doc.get("ai_analysis"):
            ai_analysis = ExtensionAIAnalysis(**extension_doc["ai_analysis"])

        return ExtensionRequestResponse(
            id=str(extension_doc["_id"]),
            student_uid=extension_doc["student_uid"],
            student_name=student_name,
            task_id=extension_doc["task_id"],
            task_title=task_title,
            subject_id=extension_doc.get("subject_id"),
            subject_name=subject_name,
            current_deadline=extension_doc["current_deadline"],
            requested_deadline=extension_doc["requested_deadline"],
            extension_days=extension_doc["extension_days"],
            reason=extension_doc["reason"],
            status=extension_doc["status"],
            ai_analysis=ai_analysis,
            teacher_response=extension_doc.get("teacher_response"),
            reviewed_by=extension_doc.get("reviewed_by"),
            created_at=extension_doc["created_at"],
            updated_at=extension_doc["updated_at"],
            reviewed_at=extension_doc.get("reviewed_at")
        )
