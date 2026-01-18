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


async def evaluate_submission(*, submission_id: ObjectId) -> None:
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

        code_results = {"passed": 0, "failed": 0, "errors": []}
        if code_cfg:
            language = str(code_cfg.get("language") or "python").lower()
            timeout_ms = int(code_cfg.get("timeout_ms") or 2000)
            test_cases = code_cfg.get("test_cases")
            test_cases_list = test_cases if isinstance(test_cases, list) else None
            code_results = run_code_tests(
                code=str(submission.get("content") or ""),
                language=language if language in {"python", "javascript", "java"} else "python",
                test_cases=test_cases_list,
                timeout_ms=timeout_ms,
            )

        keywords = doc_cfg.get("keywords")
        keywords_list = keywords if isinstance(keywords, list) else []

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
                    text = (text + "\n" + extracted).strip()
            except Exception:
                continue

        document_metrics = analyze_text(text=text, keywords=keywords_list)

        ai_score = _compute_ai_score(
            code_results=code_results,
            document_metrics=document_metrics,
            code_cfg=code_cfg,
            doc_cfg=doc_cfg,
        )
        ai_feedback = build_ai_feedback(
            code_results=code_results, document_metrics=document_metrics, ai_score=ai_score
        )

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
        now = datetime.utcnow()
        await submissions_collection.update_one(
            {"_id": submission_id},
            {
                "$set": {
                    "evaluation.status": "failed",
                    "evaluation.last_error": f"{type(e).__name__}: {str(e)[:1500]}",
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
    code_weight = 0.0
    doc_weight = 0.0
    if code_cfg:
        code_weight = 0.7
    if doc_cfg:
        doc_weight = 0.3
    if code_weight == 0.0 and doc_weight == 0.0:
        doc_weight = 1.0

    passed = int(code_results.get("passed") or 0)
    failed = int(code_results.get("failed") or 0)
    total = passed + failed
    errors = code_results.get("errors") or []

    if total > 0:
        code_score = int(round((passed / max(1, total)) * 100))
    elif code_cfg and not errors:
        code_score = 100
    elif code_cfg:
        code_score = 0
    else:
        code_score = 0

    word_count = int(document_metrics.get("word_count") or 0)
    min_words = doc_cfg.get("min_words")
    if isinstance(min_words, int) and min_words > 0:
        doc_score = int(round(min(1.0, word_count / min_words) * 100))
    else:
        doc_score = 100 if word_count > 0 else 0

    combined = (code_score * code_weight) + (doc_score * doc_weight)
    return int(max(0, min(100, round(combined))))
