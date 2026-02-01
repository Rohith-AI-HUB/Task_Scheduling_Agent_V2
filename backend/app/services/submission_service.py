from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from bson import ObjectId

from app.ai.evaluator.code_runner import run_code_tests
from app.ai.evaluator.doc_analyzer import analyze_text_with_groq, extract_text_from_pdf
from app.ai.evaluator.report_gen import build_ai_feedback
from app.database.collections import get_collection
from app.models.submission import SubmissionEvaluation
from app.services.groq_service import GroqService


def _normalize_evaluation_config(task: dict) -> dict[str, Any]:
    cfg = task.get("evaluation_config")
    return cfg if isinstance(cfg, dict) else {}


async def queue_evaluation(*, submission_id: ObjectId, force: bool = False) -> dict | None:
    submissions_collection = get_collection("submissions")
    submission = await submissions_collection.find_one({"_id": submission_id})
    if not submission:
        return None

    now = datetime.utcnow()
    existing = submission.get("evaluation") if isinstance(submission.get("evaluation"), dict) else {}
    status = str(existing.get("status") or "").lower()
    if status == "running":
        return submission
    if status == "completed" and not force:
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

    groq_service = GroqService()
    user_uid = str(submission.get("student_uid") or submission.get("user_id") or "")

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
        has_code_cfg = isinstance(cfg.get("code"), dict)
        has_doc_cfg = isinstance(cfg.get("document"), dict)
        code_cfg = cfg.get("code") if has_code_cfg else {}
        doc_cfg = cfg.get("document") if has_doc_cfg else {}
        attachments = submission.get("attachments") or []
        inferred_lang = None
        inferred_ext = None
        inferred_candidates: list[dict[str, Any]] = []
        for a in attachments:
            if not isinstance(a, dict):
                continue
            filename = str(a.get("filename") or "")
            if not filename or not a.get("path"):
                continue
            lower = filename.lower()
            ext = Path(lower).suffix
            if ext not in {".py", ".ipynb", ".js", ".java"}:
                continue
            inferred_candidates.append(a)

        if inferred_candidates:
            inferred_candidates.sort(key=lambda a: int(a.get("size") or 0), reverse=True)
            picked = inferred_candidates[0]
            picked_filename = str(picked.get("filename") or "").lower()
            inferred_ext = Path(picked_filename).suffix
            inferred_lang = {".py": "python", ".ipynb": "python", ".js": "javascript", ".java": "java"}.get(inferred_ext)

        has_effective_code_cfg = has_code_cfg or inferred_lang is not None
        effective_code_cfg = code_cfg if has_code_cfg else ({"language": inferred_lang} if inferred_lang else {})
        code_cfg_for_score = {"weight": effective_code_cfg.get("weight", 0.7), **effective_code_cfg} if has_effective_code_cfg else {}
        doc_cfg_for_score = {"weight": doc_cfg.get("weight", 0.3), **doc_cfg} if has_doc_cfg else {}

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

        code_for_doc = ""
        if has_effective_code_cfg:
            language = str(effective_code_cfg.get("language") or "python").lower()
            timeout_ms = int(effective_code_cfg.get("timeout_ms") or 2000)
            memory_limit_mb = int(effective_code_cfg.get("memory_limit_mb") or 256)
            max_output_kb = int(effective_code_cfg.get("max_output_kb") or 64)
            test_cases = effective_code_cfg.get("test_cases")
            test_cases_list = test_cases if isinstance(test_cases, list) else None
            enable_quality_checks = bool(effective_code_cfg.get("enable_quality_checks", True))
            security_mode = str(effective_code_cfg.get("security_mode") or "warn").lower()

            target_language = language if language in {"python", "javascript", "java"} else "python"
            code = str(submission.get("content") or "")
            code_from_attachment = False
            pre_warnings: list[str] = []

            ext_map = {
                "python": [".py", ".ipynb", ".txt"],
                "javascript": [".js", ".txt"],
                "java": [".java", ".txt"],
            }
            allowed_exts = ext_map.get(target_language, [".py", ".txt"])

            candidates: list[dict[str, Any]] = []
            for a in attachments:
                if not isinstance(a, dict):
                    continue
                filename = str(a.get("filename") or "")
                if not filename:
                    continue
                lower = filename.lower()
                if not any(lower.endswith(ext) for ext in allowed_exts):
                    continue
                if not a.get("path"):
                    continue
                candidates.append(a)

            if candidates:
                candidates.sort(key=lambda a: int(a.get("size") or 0), reverse=True)
                picked = candidates[0]
                picked_path = Path(str(picked.get("path")))
                picked_name = str(picked.get("filename") or "code")
                try:
                    raw = picked_path.read_bytes()
                    max_code_bytes = 250_000
                    if len(raw) > max_code_bytes:
                        raw = raw[:max_code_bytes]
                        pre_warnings.append(f"Code file {picked_name} is large; only first {max_code_bytes} bytes were evaluated")
                    decoded = raw.decode("utf-8", errors="replace")
                    if picked_name.lower().endswith(".ipynb"):
                        try:
                            nb = json.loads(decoded)
                            cells = nb.get("cells") if isinstance(nb, dict) else None
                            if isinstance(cells, list):
                                lines: list[str] = []
                                for c in cells:
                                    if not isinstance(c, dict) or c.get("cell_type") != "code":
                                        continue
                                    src = c.get("source")
                                    if isinstance(src, list):
                                        lines.append("".join([str(x) for x in src]))
                                    elif isinstance(src, str):
                                        lines.append(src)
                                extracted = "\n\n".join([s.strip("\n") for s in lines if str(s).strip()])
                                if extracted.strip():
                                    code = extracted + "\n"
                                else:
                                    code = ""
                                    pre_warnings.append(f"No code cells found in {picked_name}")
                            else:
                                code = ""
                                pre_warnings.append(f"Invalid notebook format in {picked_name}")
                        except Exception as e:
                            code = ""
                            pre_warnings.append(f"Failed to parse notebook {picked_name}: {str(e)[:120]}")
                    else:
                        code = decoded
                    code_from_attachment = True
                except Exception as e:
                    pre_warnings.append(f"Failed to read code attachment {picked_name}: {str(e)[:120]}")

            if code_from_attachment:
                pre_warnings.append("Evaluated code from uploaded attachment")

            code_for_doc = code
            groq_code_analysis = None
            if groq_service.is_available():
                try:
                    groq_code_analysis = await groq_service.grade_code_submission(
                        user_uid=user_uid,
                        code=code,
                        language=target_language,
                        task_title=str(task.get("title") or ""),
                        task_description=str(task.get("description") or ""),
                        role="teacher",
                    )
                except Exception as e:
                    pre_warnings.append(f"Groq code grading failed: {str(e)[:120]}")
                    groq_code_analysis = None

            if isinstance(groq_code_analysis, dict) and groq_code_analysis:
                code_results = {
                    "passed": 0,
                    "failed": 0,
                    "total_points": 0,
                    "earned_points": 0,
                    "errors": [],
                    "warnings": [],
                    "test_results": [],
                    "groq_analysis": groq_code_analysis,
                }
            else:
                code_results = run_code_tests(
                    code=code,
                    language=target_language,
                    test_cases=None,
                    timeout_ms=timeout_ms,
                    memory_limit_mb=memory_limit_mb,
                    max_output_kb=max_output_kb,
                    enable_quality_checks=enable_quality_checks,
                    security_mode="block" if security_mode == "block" else "warn",
                )
            if pre_warnings:
                existing_warnings = code_results.get("warnings")
                if not isinstance(existing_warnings, list):
                    existing_warnings = []
                code_results["warnings"] = [*pre_warnings, *existing_warnings]

        # DOCUMENT ANALYSIS with enhanced features
        keywords = doc_cfg.get("keywords")
        keywords_list = keywords if isinstance(keywords, list) else []
        min_words = int(doc_cfg.get("min_words") or 0)
        enable_readability = bool(doc_cfg.get("enable_readability", True))
        enable_plagiarism = bool(doc_cfg.get("enable_plagiarism", False))
        enable_structure = bool(doc_cfg.get("enable_structure", True))

        text = str(submission.get("content") or "")
        if has_doc_cfg:
            # Collect all text (submission content + PDF attachments)
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
                    code_results.setdefault("warnings", []).append(f"PDF extraction failed for {filename}: {str(e)[:100]}")
                    continue

            if not text.strip() and code_for_doc.strip():
                text = code_for_doc

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

        document_metrics: dict[str, Any] = {}
        if has_doc_cfg:
            document_metrics = await analyze_text_with_groq(
                user_uid=user_uid,
                text=text,
                keywords=keywords_list,
                min_words=min_words,
                task_title=str(task.get("title") or ""),
                task_description=str(task.get("description") or ""),
                reference_texts=reference_texts,
                enable_readability=enable_readability,
                enable_plagiarism=enable_plagiarism,
                enable_structure=enable_structure,
            )

        # COMPUTE AI SCORE with dynamic weighting
        ai_score = _compute_ai_score(
            code_results=code_results,
            document_metrics=document_metrics,
            code_cfg=code_cfg_for_score,
            doc_cfg=doc_cfg_for_score,
        )

        # GENERATE AI FEEDBACK
        ai_feedback = build_ai_feedback(
            code_results=code_results,
            document_metrics=document_metrics,
            ai_score=ai_score,
        )
        total_task_points = task.get("points")
        max_points = float(total_task_points) if isinstance(total_task_points, (int, float)) else None
        ai_points = round((ai_score / 100.0) * max_points, 2) if max_points is not None else None
        if ai_points is not None:
            ai_feedback = (ai_feedback + f"\n\nAI Suggested Marks: {ai_points}/{max_points}").strip()

        if groq_service.is_available() and isinstance(document_metrics, dict):
            groq_analysis = document_metrics.get("groq_analysis")
            if isinstance(groq_analysis, dict):
                quality = groq_analysis.get("quality_assessment")
                structure = groq_analysis.get("structure_feedback")
                improvements = groq_analysis.get("improvements")
                suggested = groq_analysis.get("suggested_score")

                extra_sections: list[str] = []
                if isinstance(quality, str) and quality.strip():
                    extra_sections.append(f"Quality: {quality.strip()}")
                if isinstance(structure, str) and structure.strip():
                    extra_sections.append(f"Structure: {structure.strip()}")
                if isinstance(improvements, list):
                    clean_improvements = [str(x).strip() for x in improvements if str(x).strip()]
                    if clean_improvements:
                        extra_sections.append("Improvements:")
                        extra_sections.extend([f"- {x}" for x in clean_improvements[:8]])
                if suggested is not None:
                    extra_sections.append(f"Suggested Score (Groq): {suggested}")

                if extra_sections:
                    ai_feedback = (ai_feedback + "\n\n" + "\n".join(extra_sections)).strip()

        # Save evaluation results
        now = datetime.utcnow()
        evaluation = SubmissionEvaluation(
            status="completed",
            code_results=code_results,
            document_metrics=document_metrics,
            ai_score=ai_score,
            ai_points=ai_points,
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
        groq_code = code_results.get("groq_analysis")
        if groq_code and isinstance(groq_code, dict):
            suggested = groq_code.get("suggested_score")
            if suggested is not None:
                try:
                    code_score = float(suggested)
                except Exception:
                    code_score = 0.0
        else:
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

    # If Groq analysis is available, use it as the primary source for document score
    groq_analysis = document_metrics.get("groq_analysis")
    if groq_analysis and isinstance(groq_analysis, dict):
        suggested_score = groq_analysis.get("suggested_score")
        if suggested_score is not None:
            doc_score = float(suggested_score)
    elif doc_cfg or not code_cfg:  # Fallback to heuristic scoring
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
