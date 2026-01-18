from __future__ import annotations

from typing import Any


def _get_score_category(score: int) -> str:
    """Categorize score into performance levels."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 60:
        return "Satisfactory"
    elif score >= 40:
        return "Needs Improvement"
    else:
        return "Unsatisfactory"


def _build_code_feedback(code_results: dict[str, Any]) -> str:
    """Generate detailed code evaluation feedback."""
    sections = []

    passed = int(code_results.get("passed") or 0)
    failed = int(code_results.get("failed") or 0)
    total_points = int(code_results.get("total_points") or 0)
    earned_points = int(code_results.get("earned_points") or 0)
    errors = code_results.get("errors") or []
    warnings = code_results.get("warnings") or []

    # Test results summary
    if passed or failed:
        sections.append("=== CODE EVALUATION ===")

        if total_points > 0:
            sections.append(f"Test Results: {passed}/{passed + failed} tests passed ({earned_points}/{total_points} points)")
        else:
            sections.append(f"Test Results: {passed} passed, {failed} failed")

        # Success rate
        total_tests = passed + failed
        if total_tests > 0:
            success_rate = (passed / total_tests) * 100
            sections.append(f"Success Rate: {success_rate:.1f}%")

    # Code quality warnings
    if warnings:
        sections.append("\nCode Quality Warnings:")
        for i, warning in enumerate(warnings[:5], 1):  # Limit to 5 warnings
            sections.append(f"  {i}. {warning}")
        if len(warnings) > 5:
            sections.append(f"  ... and {len(warnings) - 5} more warnings")

    # Error details
    if errors:
        sections.append("\nErrors Encountered:")
        for i, error in enumerate(errors[:3], 1):  # Limit to 3 errors
            sections.append(f"  {i}. {str(error)[:300]}")
        if len(errors) > 3:
            sections.append(f"  ... and {len(errors) - 3} more errors")

    return "\n".join(sections)


def _build_document_feedback(document_metrics: dict[str, Any]) -> str:
    """Generate detailed document analysis feedback."""
    sections = []

    word_count = int(document_metrics.get("word_count") or 0)
    keywords_found = document_metrics.get("keywords_found") or []
    keyword_ratio = float(document_metrics.get("keyword_match_ratio") or 0)
    readability = float(document_metrics.get("readability_score") or 0)
    grade_level = float(document_metrics.get("grade_level") or 0)
    structure_quality = float(document_metrics.get("structure_quality") or 0)
    paragraph_count = int(document_metrics.get("paragraph_count") or 0)
    plagiarism_detected = bool(document_metrics.get("plagiarism_detected", False))
    max_similarity = float(document_metrics.get("max_similarity") or 0)
    meets_min_words = bool(document_metrics.get("meets_min_words", True))

    sections.append("=== DOCUMENT ANALYSIS ===")

    # Word count
    if word_count > 0:
        status = "✓" if meets_min_words else "✗"
        sections.append(f"Word Count: {word_count} {status}")

    # Keywords
    if keywords_found:
        sections.append(f"\nKeyword Coverage: {keyword_ratio:.1f}%")
        sections.append(f"Keywords Found: {', '.join(str(k) for k in keywords_found[:15])}")
        if len(keywords_found) > 15:
            sections.append(f"  ... and {len(keywords_found) - 15} more")
    else:
        if keyword_ratio == 0:
            sections.append("\nKeyword Coverage: No required keywords found")

    # Readability
    if readability > 0:
        sections.append(f"\nReadability:")
        sections.append(f"  - Flesch Reading Ease: {readability:.1f}/100")
        sections.append(f"  - Grade Level: {grade_level:.1f}")

        if readability >= 60:
            sections.append(f"  - Assessment: Easy to read")
        elif readability >= 50:
            sections.append(f"  - Assessment: Fairly easy to read")
        elif readability >= 30:
            sections.append(f"  - Assessment: Fairly difficult to read")
        else:
            sections.append(f"  - Assessment: Difficult to read")

    # Structure
    if structure_quality > 0:
        sections.append(f"\nStructure Quality: {structure_quality:.1f}/100")
        if paragraph_count > 0:
            sections.append(f"  - Paragraphs: {paragraph_count}")

    # Plagiarism
    if plagiarism_detected:
        sections.append(f"\n⚠️ PLAGIARISM WARNING:")
        sections.append(f"  - Similarity with other submissions: {max_similarity:.1f}%")
        sections.append(f"  - This submission shows significant similarity to other work.")
    elif max_similarity > 30:
        sections.append(f"\nSimilarity Check: {max_similarity:.1f}% match with other submissions")

    return "\n".join(sections)


def build_ai_feedback(
    *,
    code_results: dict[str, Any],
    document_metrics: dict[str, Any],
    ai_score: int | None,
) -> str:
    """
    Generate comprehensive AI feedback combining code and document evaluation.

    Args:
        code_results: Code evaluation results with test cases, errors, warnings
        document_metrics: Document analysis metrics including readability, structure, plagiarism
        ai_score: Overall AI score (0-100)

    Returns:
        Formatted feedback string with detailed evaluation breakdown
    """
    sections = []

    # Overall score header
    if ai_score is not None:
        category = _get_score_category(ai_score)
        sections.append(f"{'='*50}")
        sections.append(f"AI EVALUATION REPORT")
        sections.append(f"{'='*50}")
        sections.append(f"Overall Score: {ai_score}/100 ({category})")
        sections.append(f"{'='*50}\n")

    # Code feedback
    code_feedback = _build_code_feedback(code_results)
    if code_feedback:
        sections.append(code_feedback)
        sections.append("")

    # Document feedback
    document_feedback = _build_document_feedback(document_metrics)
    if document_feedback:
        sections.append(document_feedback)
        sections.append("")

    # Recommendations
    recommendations = []

    # Code recommendations
    if code_results.get("failed", 0) > 0:
        recommendations.append("- Review failed test cases and fix the logic errors")

    if code_results.get("warnings"):
        recommendations.append("- Address code quality warnings to improve maintainability")

    # Document recommendations
    if not document_metrics.get("meets_min_words", True):
        recommendations.append("- Expand your answer to meet the minimum word count requirement")

    keyword_ratio = float(document_metrics.get("keyword_match_ratio") or 0)
    if keyword_ratio < 50:
        recommendations.append("- Include more of the required keywords in your submission")

    readability = float(document_metrics.get("readability_score") or 0)
    if readability > 0 and (readability < 50 or readability > 80):
        if readability < 50:
            recommendations.append("- Simplify sentence structure to improve readability")
        else:
            recommendations.append("- Consider using more varied sentence structures for better clarity")

    structure_quality = float(document_metrics.get("structure_quality") or 0)
    if structure_quality < 50:
        recommendations.append("- Improve document structure with proper paragraphs and sections")

    if document_metrics.get("plagiarism_detected", False):
        recommendations.append("- ⚠️ Rewrite your submission in your own words to avoid plagiarism")

    if recommendations:
        sections.append("=== RECOMMENDATIONS ===")
        sections.extend(recommendations)

    return "\n".join(sections).strip()
