from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from bson import ObjectId

from app.ai.evaluator.code_runner import run_code_tests
from app.ai.evaluator.doc_analyzer import analyze_text, extract_text_from_pdf
from app.ai.evaluator.report_gen import build_ai_feedback
from app.database.collections import get_collection
from app.models.submission import SubmissionEvaluation


def _normalize_evaluation_config(task: dict) -> dict[str, Any]:
    cfg = task.get("evaluation_config")
    return cfg if isinstance(cfg, dict) else {}


async def queue_evaluation(*, submission_id: ObjectId) -> dict | None:
    submissions_collection = get_collection("submissions")
    submission = await submissions_collection.find_one({"_id": submission_id})
    if not submission:
        return None

    now = datetime.utcnow()
    existing = submission.get("evaluation") if isinstance(submission.get("evaluation"), dict) else {}
    status = str(existing.get("status") or "").lower()
    if status == "running":
        return submission

    evaluation = SubmissionEvaluation(status="pending").model_dump()
    await submissions_collection.update_one(
        {"_id": submission_id},
        {"$set": {"evaluation": evaluation, "updated_at": now}},
    )
    asyncio.create_task(evaluate_submission(submission_id=submission_id))
    return await submissions_collection.find_one({"_id": submission_id})


async def evaluate_submission(*, submission_id: ObjectId, retry_count: int = 0) -> None:
    """
    Evaluate a submission with enhanced features and error handling.

    Args:
        submission_id: The submission to evaluate
        retry_count: Current retry attempt (max 2 retries)
    """
    MAX_RETRIES = 2
    submissions_collection = get_collection("submissions")
    tasks_collection = get_collection("tasks")

    submission = await submissions_collection.find_one({"_id": submission_id})
    if not submission:
        return

    now = datetime.utcnow()
    await submissions_collection.update_one(
        {"_id": submission_id},
        {"$set": {"evaluation.status": "running", "evaluation.last_error": None, "updated_at": now}},
    )

    try:
        task = await tasks_collection.find_one({"_id": submission.get("task_id")})
        if not task:
            raise RuntimeError("Task not found")

        cfg = _normalize_evaluation_config(task)
        code_cfg = cfg.get("code") if isinstance(cfg.get("code"), dict) else {}
        doc_cfg = cfg.get("document") if isinstance(cfg.get("document"), dict) else {}

        # CODE EVALUATION with enhanced features
        code_results = {
            "passed": 0,
            "failed": 0,
            "total_points": 0,
            "earned_points": 0,
            "errors": [],
            "warnings": [],
            "test_results": [],
        }

        if code_cfg:
            language = str(code_cfg.get("language") or "python").lower()
            timeout_ms = int(code_cfg.get("timeout_ms") or 2000)
            memory_limit_mb = int(code_cfg.get("memory_limit_mb") or 256)
            max_output_kb = int(code_cfg.get("max_output_kb") or 64)
            test_cases = code_cfg.get("test_cases")
            test_cases_list = test_cases if isinstance(test_cases, list) else None
            enable_quality_checks = bool(code_cfg.get("enable_quality_checks", True))
            security_mode = str(code_cfg.get("security_mode") or "warn").lower()

            code_results = run_code_tests(
                code=str(submission.get("content") or ""),
                language=language if language in {"python", "javascript", "java"} else "python",
                test_cases=test_cases_list,
                timeout_ms=timeout_ms,
                memory_limit_mb=memory_limit_mb,
                max_output_kb=max_output_kb,
                enable_quality_checks=enable_quality_checks,
                security_mode="block" if security_mode == "block" else "warn",
            )

        # DOCUMENT ANALYSIS with enhanced features
        keywords = doc_cfg.get("keywords")
        keywords_list = keywords if isinstance(keywords, list) else []
        min_words = int(doc_cfg.get("min_words") or 0)
        enable_readability = bool(doc_cfg.get("enable_readability", True))
        enable_plagiarism = bool(doc_cfg.get("enable_plagiarism", False))
        enable_structure = bool(doc_cfg.get("enable_structure", True))

        # Collect all text (submission content + PDF attachments)
        text = str(submission.get("content") or "")
        for a in submission.get("attachments") or []:
            if not isinstance(a, dict):
                continue
            path = a.get("path")
            filename = str(a.get("filename") or "")
            if not path or not filename.lower().endswith(".pdf"):
                continue
            try:
                extracted = extract_text_from_pdf(Path(path))
                if extracted:
                    text = (text + "\n\n" + extracted).strip()
            except Exception as e:
                # Log PDF extraction errors but don't fail evaluation
                code_results.setdefault("warnings", []).append(f"PDF extraction failed for {filename}: {str(e)[:100]}")
                continue

        # Get reference texts for plagiarism check (other submissions for this task)
        reference_texts = []
        if enable_plagiarism:
            other_submissions = await submissions_collection.find(
                {
                    "task_id": submission.get("task_id"),
                    "_id": {"$ne": submission_id},
                    "content": {"$exists": True, "$ne": ""},
                },
                {"content": 1}
            ).limit(20).to_list(length=20)

            reference_texts = [s.get("content", "") for s in other_submissions if s.get("content")]

        # Analyze document
        document_metrics = analyze_text(
            text=text,
            keywords=keywords_list,
            min_words=min_words,
            reference_texts=reference_texts,
            enable_readability=enable_readability,
            enable_plagiarism=enable_plagiarism,
            enable_structure=enable_structure,
        )

        # COMPUTE AI SCORE with dynamic weighting
        ai_score = _compute_ai_score(
            code_results=code_results,
            document_metrics=document_metrics,
            code_cfg=code_cfg,
            doc_cfg=doc_cfg,
        )

        # GENERATE AI FEEDBACK
        ai_feedback = build_ai_feedback(
            code_results=code_results,
            document_metrics=document_metrics,
            ai_score=ai_score,
        )

        # Save evaluation results
        now = datetime.utcnow()
        evaluation = SubmissionEvaluation(
            status="completed",
            code_results=code_results,
            document_metrics=document_metrics,
            ai_score=ai_score,
            ai_feedback=ai_feedback,
            evaluated_at=now,
            last_error=None,
        ).model_dump()

        await submissions_collection.update_one(
            {"_id": submission_id},
            {"$set": {"evaluation": evaluation, "updated_at": now}},
        )

    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:1500]}"

        # Retry logic for transient errors
        should_retry = (
            retry_count < MAX_RETRIES and
            ("timeout" in str(e).lower() or "connection" in str(e).lower())
        )

        if should_retry:
            # Wait before retrying (exponential backoff)
            await asyncio.sleep(2 ** retry_count)
            await evaluate_submission(submission_id=submission_id, retry_count=retry_count + 1)
            return

        # Mark as failed if no retry or max retries reached
        now = datetime.utcnow()
        await submissions_collection.update_one(
            {"_id": submission_id},
            {
                "$set": {
                    "evaluation.status": "failed",
                    "evaluation.last_error": error_msg + (f" (after {retry_count} retries)" if retry_count > 0 else ""),
                    "updated_at": now,
                }
            },
        )


def _compute_ai_score(
    *,
    code_results: dict[str, Any],
    document_metrics: dict[str, Any],
    code_cfg: dict[str, Any],
    doc_cfg: dict[str, Any],
) -> int:
    """
    Compute AI score with dynamic weighting and partial credit support.

    Scoring components:
    - Code score: Based on test results (with partial credit for weighted tests)
    - Document score: Based on word count, keywords, readability, structure, and plagiarism
    """

    # Get configurable weights (default: 70% code, 30% document)
    code_weight = float(code_cfg.get("weight", 0.7)) if code_cfg else 0.0
    doc_weight = float(doc_cfg.get("weight", 0.3)) if doc_cfg else 0.0

    # Normalize weights
    total_weight = code_weight + doc_weight
    if total_weight == 0.0:
        # If both are zero, default to 100% document
        doc_weight = 1.0
        total_weight = 1.0
    else:
        code_weight = code_weight / total_weight
        doc_weight = doc_weight / total_weight

    # ====================
    # CODE SCORE (0-100)
    # ====================
    code_score = 0.0

    if code_cfg:
        # Use weighted scoring if available (partial credit)
        total_points = int(code_results.get("total_points") or 0)
        earned_points = int(code_results.get("earned_points") or 0)

        if total_points > 0:
            # Weighted test case scoring with partial credit
            code_score = (earned_points / total_points) * 100
        else:
            # Fallback to simple pass/fail ratio
            passed = int(code_results.get("passed") or 0)
            failed = int(code_results.get("failed") or 0)
            total = passed + failed

            if total > 0:
                code_score = (passed / total) * 100
            else:
                # No test cases but code is present
                errors = code_results.get("errors") or []
                code_score = 100.0 if not errors else 0.0

        # Apply quality penalty for warnings (minor deduction)
        warnings = code_results.get("warnings") or []
        if warnings:
            penalty = min(10.0, len(warnings) * 2)  # Max 10% penalty
            code_score = max(0, code_score - penalty)

    # ====================
    # DOCUMENT SCORE (0-100)
    # ====================
    doc_score = 0.0

    if doc_cfg or not code_cfg:  # Evaluate document if config exists OR if no code config
        components = []

        # 1. Word Count (up to 30 points)
        word_count = int(document_metrics.get("word_count") or 0)
        min_words = int(doc_cfg.get("min_words") or 0)

        if min_words > 0:
            word_ratio = min(1.0, word_count / min_words)
            word_score = word_ratio * 30
        else:
            word_score = 30.0 if word_count > 0 else 0.0

        components.append(word_score)

        # 2. Keyword Matching (up to 25 points)
        keyword_ratio = float(document_metrics.get("keyword_match_ratio") or 0)
        keyword_score = (keyword_ratio / 100) * 25
        components.append(keyword_score)

        # 3. Readability (up to 20 points)
        readability = float(document_metrics.get("readability_score") or 0)
        if readability > 0:
            # Flesch Reading Ease: 60-70 is ideal (standard readability)
            if 60 <= readability <= 70:
                readability_score = 20.0
            elif 50 <= readability < 60 or 70 < readability <= 80:
                readability_score = 15.0
            elif 40 <= readability < 50 or 80 < readability <= 90:
                readability_score = 10.0
            else:
                readability_score = 5.0
        else:
            readability_score = 10.0  # Neutral if not calculated

        components.append(readability_score)

        # 4. Structure Quality (up to 15 points)
        structure_quality = float(document_metrics.get("structure_quality") or 0)
        structure_score = (structure_quality / 100) * 15
        components.append(structure_score)

        # 5. Plagiarism Check (up to 10 points - deduction if plagiarized)
        plagiarism_detected = bool(document_metrics.get("plagiarism_detected", False))
        max_similarity = float(document_metrics.get("max_similarity") or 0)

        if plagiarism_detected:
            plagiarism_score = 0.0  # Full deduction if plagiarized
        elif max_similarity > 50:
            plagiarism_score = 5.0  # Partial deduction for high similarity
        elif max_similarity > 30:
            plagiarism_score = 7.5  # Minor deduction for moderate similarity
        else:
            plagiarism_score = 10.0  # No deduction

        components.append(plagiarism_score)

        doc_score = sum(components)

    # ====================
    # COMBINED SCORE
    # ====================
    combined = (code_score * code_weight) + (doc_score * doc_weight)
    return int(max(0, min(100, round(combined))))
