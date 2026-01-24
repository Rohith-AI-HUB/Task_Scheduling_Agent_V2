from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument

from app.config import settings
from app.database.collections import get_collection
from app.models.submission import (
    MalpracticeEvent,
    QuizAnswer,
    QuizAttemptMetrics,
    QuizGenerateRequest,
    QuizSubmitRequest,
    SubmissionEvaluation,
    SubmissionResponse,
)
from app.models.task import QuizQuestion
from app.services.groq_service import groq_service
from app.utils.dependencies import get_current_student, get_current_teacher

router = APIRouter()


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


def _serialize_submission(doc: dict) -> SubmissionResponse:
    """Helper to serialize submission document"""
    raw_attachments = doc.get("attachments") or []
    from app.models.submission import SubmissionAttachmentResponse

    attachments = []
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
        evaluation=SubmissionEvaluation.model_validate(doc.get("evaluation")) if doc.get("evaluation") else None,
    )


@router.post("/generate", response_model=list[QuizQuestion])
async def generate_quiz_questions(
    request: QuizGenerateRequest,
    current_teacher: dict = Depends(get_current_teacher),
):
    """
    Generate quiz questions from document content using Groq AI.
    Teachers only.
    """
    try:
        questions = await groq_service.generate_quiz_questions(
            user_uid=current_teacher["uid"],
            document_content=request.document_content,
            topic=request.topic,
            num_questions=request.num_questions
        )

        if not questions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate questions. Please try again."
            )

        # Convert to QuizQuestion model
        quiz_questions = []
        for q in questions:
            quiz_questions.append(
                QuizQuestion(
                    question=q.get("question", ""),
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", 0),
                    explanation=q.get("explanation"),
                    difficulty=q.get("difficulty", "medium"),
                    points=1  # Default 1 point per question
                )
            )

        return quiz_questions

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating quiz questions: {str(e)}"
        )


@router.post("/start", response_model=dict)
async def start_quiz_attempt(
    task_id: str,
    current_student: dict = Depends(get_current_student),
):
    """
    Start a quiz attempt. Returns quiz questions (without correct answers).
    Checks for existing attempts and lockouts.
    """
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")

    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_student_enrolled(current_student["uid"], subject_oid)

    # Check if task is a quiz
    eval_config = task.get("evaluation_config") or {}
    quiz_config = eval_config.get("quiz")
    if not quiz_config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This task is not a quiz")

    # Check for existing submission
    submissions_collection = get_collection("submissions")
    existing = await submissions_collection.find_one({
        "task_id": task_oid,
        "student_uid": current_student["uid"],
        "group_id": None
    })

    # Check if locked out
    if existing:
        evaluation = existing.get("evaluation")
        if evaluation:
            quiz_metrics = evaluation.get("quiz_metrics")
            if quiz_metrics and quiz_metrics.get("locked_out"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are locked out of this quiz due to malpractice detection"
                )

            # Check if already completed
            if evaluation.get("status") == "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already completed this quiz"
                )

    # Return quiz questions without correct answers
    questions = quiz_config.get("questions", [])
    safe_questions = []
    for idx, q in enumerate(questions):
        safe_questions.append({
            "index": idx,
            "question": q.get("question"),
            "options": q.get("options"),
            "points": q.get("points", 1)
        })

    # Create or update submission to mark quiz as started
    now = datetime.utcnow()
    quiz_metrics = QuizAttemptMetrics(
        total_questions=len(questions),
        time_started=now,
        malpractice_detected=False,
        locked_out=False
    )

    evaluation = SubmissionEvaluation(
        status="running",
        quiz_metrics=quiz_metrics,
        evaluated_at=now
    )

    if existing:
        # Update existing submission
        await submissions_collection.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "evaluation": evaluation.model_dump(),
                    "updated_at": now
                }
            }
        )
        submission_id = str(existing["_id"])
    else:
        # Create new submission
        doc = {
            "task_id": task_oid,
            "subject_id": subject_oid,
            "student_uid": current_student["uid"],
            "content": "",
            "submitted_at": now,
            "created_at": now,
            "updated_at": now,
            "score": None,
            "feedback": None,
            "attachments": [],
            "group_id": None,
            "evaluation": evaluation.model_dump()
        }
        result = await submissions_collection.insert_one(doc)
        submission_id = str(result.inserted_id)

    return {
        "submission_id": submission_id,
        "questions": safe_questions,
        "time_limit_minutes": quiz_config.get("time_limit_minutes", 30),
        "shuffle_questions": quiz_config.get("shuffle_questions", True),
        "shuffle_options": quiz_config.get("shuffle_options", True),
        "enable_fullscreen": quiz_config.get("enable_fullscreen", True),
        "enable_anti_cheating": quiz_config.get("enable_anti_cheating", True)
    }


@router.post("/submit", response_model=SubmissionResponse)
async def submit_quiz(
    request: QuizSubmitRequest,
    current_student: dict = Depends(get_current_student),
):
    """
    Submit quiz answers and calculate score.
    Handles malpractice detection and lockouts.
    """
    if not ObjectId.is_valid(request.task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")

    task_oid = ObjectId(request.task_id)
    task = await _find_task_or_404(task_oid)
    subject_oid = task["subject_id"]
    await _ensure_student_enrolled(current_student["uid"], subject_oid)

    # Get quiz config
    eval_config = task.get("evaluation_config") or {}
    quiz_config = eval_config.get("quiz")
    if not quiz_config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This task is not a quiz")

    questions = quiz_config.get("questions", [])

    # Find existing submission
    submissions_collection = get_collection("submissions")
    existing = await submissions_collection.find_one({
        "task_id": task_oid,
        "student_uid": current_student["uid"],
        "group_id": None
    })

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found. Please start the quiz first."
        )

    # Check if already locked out
    evaluation = existing.get("evaluation") or {}
    quiz_metrics = evaluation.get("quiz_metrics") or {}
    if quiz_metrics.get("locked_out"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are locked out of this quiz"
        )

    # Validate answers length
    if len(request.answers) != len(questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {len(questions)} answers, got {len(request.answers)}"
        )

    # Grade the quiz
    quiz_answers = []
    correct_count = 0
    total_points = 0
    earned_points = 0

    for idx, (answer, question) in enumerate(zip(request.answers, questions)):
        is_correct = answer == question.get("correct_answer", 0)
        points = question.get("points", 1)
        total_points += points

        quiz_answers.append(
            QuizAnswer(
                question_index=idx,
                selected_option=answer,
                is_correct=is_correct,
                points_earned=points if is_correct else 0
            )
        )

        if is_correct:
            correct_count += 1
            earned_points += points

    # Calculate score percentage
    score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0

    # Check for malpractice
    malpractice_detected = len(request.malpractice_events) > 0
    locked_out = malpractice_detected  # Lock out if any malpractice

    # Create quiz metrics
    now = datetime.utcnow()
    time_started = quiz_metrics.get("time_started") or now
    time_taken = request.time_taken_seconds

    final_quiz_metrics = QuizAttemptMetrics(
        answers=quiz_answers,
        total_questions=len(questions),
        correct_answers=correct_count,
        total_points=total_points,
        earned_points=earned_points,
        score_percentage=round(score_percentage, 2),
        time_started=time_started,
        time_submitted=now,
        time_taken_seconds=time_taken,
        malpractice_events=request.malpractice_events,
        malpractice_detected=malpractice_detected,
        locked_out=locked_out
    )

    # Generate feedback
    feedback_parts = []
    feedback_parts.append(f"Quiz Score: {score_percentage:.1f}%")
    feedback_parts.append(f"Correct Answers: {correct_count}/{len(questions)}")
    feedback_parts.append(f"Points Earned: {earned_points}/{total_points}")

    if malpractice_detected:
        feedback_parts.append("\n⚠️ MALPRACTICE DETECTED:")
        feedback_parts.append(f"Total violations: {len(request.malpractice_events)}")
        for event in request.malpractice_events[:5]:  # Show first 5
            feedback_parts.append(f"  - {event.event_type}: {event.details or 'N/A'}")
        feedback_parts.append("\n❌ You have been locked out of this quiz.")
        feedback_parts.append("Teacher has been notified.")

    # Update submission
    final_evaluation = SubmissionEvaluation(
        status="completed",
        quiz_metrics=final_quiz_metrics,
        ai_score=int(score_percentage),
        ai_feedback="\n".join(feedback_parts),
        evaluated_at=now
    )

    # Set final score (0 if locked out, otherwise percentage)
    final_score = 0.0 if locked_out else score_percentage

    updated = await submissions_collection.find_one_and_update(
        {"_id": existing["_id"]},
        {
            "$set": {
                "evaluation": final_evaluation.model_dump(),
                "score": final_score,
                "feedback": "\n".join(feedback_parts),
                "submitted_at": now,
                "updated_at": now
            }
        },
        return_document=ReturnDocument.AFTER
    )

    # Notify teacher if malpractice detected (you can implement notification system)
    if malpractice_detected:
        # TODO: Send notification to teacher
        pass

    return _serialize_submission(updated)


@router.post("/malpractice", response_model=dict)
async def record_malpractice_event(
    task_id: str,
    event: MalpracticeEvent,
    current_student: dict = Depends(get_current_student),
):
    """
    Record a malpractice event during quiz attempt.
    This can be called from frontend when suspicious activity is detected.
    """
    if not ObjectId.is_valid(task_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task id")

    task_oid = ObjectId(task_id)
    task = await _find_task_or_404(task_oid)
    await _ensure_student_enrolled(current_student["uid"], task["subject_id"])

    submissions_collection = get_collection("submissions")
    existing = await submissions_collection.find_one({
        "task_id": task_oid,
        "student_uid": current_student["uid"],
        "group_id": None
    })

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz attempt not found"
        )

    # Add malpractice event to metrics
    await submissions_collection.update_one(
        {"_id": existing["_id"]},
        {
            "$push": {
                "evaluation.quiz_metrics.malpractice_events": event.model_dump()
            },
            "$set": {
                "evaluation.quiz_metrics.malpractice_detected": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"status": "recorded", "event_type": event.event_type}
