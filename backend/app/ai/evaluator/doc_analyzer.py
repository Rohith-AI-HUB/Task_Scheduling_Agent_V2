from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


def calculate_readability(text: str) -> dict[str, float]:
    """
    Calculate readability metrics (Flesch Reading Ease and Grade Level).
    Returns scores between 0-100 (higher = easier to read).
    """
    if not text or not text.strip():
        return {"flesch_reading_ease": 0.0, "flesch_kincaid_grade": 0.0}

    # Count sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    num_sentences = max(len(sentences), 1)

    # Count words
    words = re.findall(r'\b\w+\b', text)
    num_words = max(len(words), 1)

    # Count syllables (approximation)
    def count_syllables(word: str) -> int:
        word = word.lower()
        vowels = "aeiouy"
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent 'e'
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        return max(syllable_count, 1)

    total_syllables = sum(count_syllables(w) for w in words)

    # Flesch Reading Ease: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
    words_per_sentence = num_words / num_sentences
    syllables_per_word = total_syllables / num_words

    flesch_reading_ease = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    flesch_reading_ease = max(0.0, min(100.0, flesch_reading_ease))

    # Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    flesch_kincaid_grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
    flesch_kincaid_grade = max(0.0, flesch_kincaid_grade)

    return {
        "flesch_reading_ease": round(flesch_reading_ease, 2),
        "flesch_kincaid_grade": round(flesch_kincaid_grade, 2),
    }


def check_basic_plagiarism(text: str, reference_texts: list[str] | None = None) -> dict[str, Any]:
    """
    Basic plagiarism detection using sequence matching.
    Returns similarity percentage with reference texts.
    """
    if not reference_texts or not text.strip():
        return {
            "plagiarism_detected": False,
            "max_similarity": 0.0,
            "similar_sources": [],
        }

    text_lower = text.lower()
    similarities = []

    for idx, ref in enumerate(reference_texts):
        if not ref or not ref.strip():
            continue

        ref_lower = ref.lower()
        similarity = SequenceMatcher(None, text_lower, ref_lower).ratio()

        if similarity > 0.3:  # Threshold for suspicion
            similarities.append({
                "source_index": idx,
                "similarity": round(similarity * 100, 2),
            })

    max_similarity = max((s["similarity"] for s in similarities), default=0.0)
    plagiarism_detected = max_similarity > 70.0  # 70% similarity threshold

    return {
        "plagiarism_detected": plagiarism_detected,
        "max_similarity": round(max_similarity, 2),
        "similar_sources": sorted(similarities, key=lambda x: x["similarity"], reverse=True)[:3],
    }


def analyze_structure(text: str) -> dict[str, Any]:
    """
    Analyze document structure quality.
    Checks for paragraphs, headings, formatting, etc.
    """
    if not text or not text.strip():
        return {"structure_quality": 0.0, "has_paragraphs": False, "paragraph_count": 0}

    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)

    # Check for headings (lines that start with # or are all caps)
    lines = text.split('\n')
    potential_headings = 0
    for line in lines:
        line = line.strip()
        if line.startswith('#') or (line.isupper() and len(line.split()) <= 10 and len(line) > 0):
            potential_headings += 1

    # Calculate structure quality score (0-100)
    quality_score = 0.0

    # Has multiple paragraphs
    if paragraph_count >= 2:
        quality_score += 30
    elif paragraph_count == 1:
        quality_score += 10

    # Has headings/sections
    if potential_headings >= 3:
        quality_score += 30
    elif potential_headings >= 1:
        quality_score += 15

    # Paragraph length consistency (not too short, not too long)
    if paragraphs:
        avg_para_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
        if 30 <= avg_para_length <= 150:
            quality_score += 20
        elif 15 <= avg_para_length <= 200:
            quality_score += 10

    # Has proper spacing
    if '\n\n' in text:
        quality_score += 20

    quality_score = min(100.0, quality_score)

    return {
        "structure_quality": round(quality_score, 2),
        "has_paragraphs": paragraph_count > 1,
        "paragraph_count": paragraph_count,
        "heading_count": potential_headings,
        "avg_paragraph_words": round(sum(len(p.split()) for p in paragraphs) / max(len(paragraphs), 1), 2),
    }


def analyze_text(
    *,
    text: str,
    keywords: list[str] | None = None,
    min_words: int = 0,
    reference_texts: list[str] | None = None,
    enable_readability: bool = True,
    enable_plagiarism: bool = False,
    enable_structure: bool = True,
) -> dict[str, Any]:
    """
    Comprehensive text analysis with multiple metrics.

    Args:
        text: The text to analyze
        keywords: List of keywords to search for
        min_words: Minimum expected word count
        reference_texts: Reference texts for plagiarism detection
        enable_readability: Calculate readability metrics
        enable_plagiarism: Check for plagiarism
        enable_structure: Analyze document structure

    Returns:
        Dictionary with analysis results including:
        - word_count
        - keywords_found
        - readability_score (if enabled)
        - plagiarism_detected (if enabled)
        - structure_quality (if enabled)
    """

    text = text or ""

    # Basic word count and keyword matching
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    keyword_list = [k.strip() for k in (keywords or []) if isinstance(k, str) and k.strip()]
    lower_text = text.lower()
    found_keywords = []

    for keyword in keyword_list:
        # Support multi-word keywords
        if keyword.lower() in lower_text:
            found_keywords.append(keyword)

    result = {
        "word_count": word_count,
        "keywords_found": found_keywords,
        "keyword_match_ratio": round(len(found_keywords) / max(len(keyword_list), 1) * 100, 2),
        "meets_min_words": word_count >= min_words,
    }

    # Readability analysis
    if enable_readability:
        readability = calculate_readability(text)
        result["readability_score"] = readability.get("flesch_reading_ease", 0.0)
        result["grade_level"] = readability.get("flesch_kincaid_grade", 0.0)

    # Plagiarism check
    if enable_plagiarism and reference_texts:
        plagiarism = check_basic_plagiarism(text, reference_texts)
        result["plagiarism_detected"] = plagiarism.get("plagiarism_detected", False)
        result["max_similarity"] = plagiarism.get("max_similarity", 0.0)
        result["similar_sources"] = plagiarism.get("similar_sources", [])

    # Structure analysis
    if enable_structure:
        structure = analyze_structure(text)
        result["structure_quality"] = structure.get("structure_quality", 0.0)
        result["paragraph_count"] = structure.get("paragraph_count", 0)
        result["has_paragraphs"] = structure.get("has_paragraphs", False)

    return result


def extract_text_from_pdf(path: str | Path) -> str:
    """Extract text content from a PDF file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF file not found: {p}")

    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception as e:
            raise RuntimeError("PDF extraction library not installed (pypdf or PyPDF2 required)") from e

    try:
        reader = PdfReader(str(p))
        chunks: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)

        return "\n\n".join(chunks)
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}") from e
