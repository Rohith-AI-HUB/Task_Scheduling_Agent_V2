from __future__ import annotations

from typing import Any


def build_ai_feedback(*, code_results: dict[str, Any], document_metrics: dict[str, Any], ai_score: int | None) -> str:
    parts: list[str] = []
    if ai_score is not None:
        parts.append(f"AI Score: {ai_score}/100")

    passed = int(code_results.get("passed") or 0)
    failed = int(code_results.get("failed") or 0)
    if passed or failed:
        parts.append(f"Code tests: {passed} passed, {failed} failed")
        errs = code_results.get("errors") or []
        if isinstance(errs, list) and errs:
            parts.append(f"Errors: {str(errs[0])[:300]}")

    word_count = int(document_metrics.get("word_count") or 0)
    keywords_found = document_metrics.get("keywords_found") or []
    parts.append(f"Word count: {word_count}")
    if isinstance(keywords_found, list) and keywords_found:
        parts.append("Keywords found: " + ", ".join([str(k) for k in keywords_found[:20]]))

    return "\n".join(parts).strip()
