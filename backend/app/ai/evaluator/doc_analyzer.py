from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def analyze_text(*, text: str, keywords: list[str] | None = None) -> dict[str, Any]:
    words = re.findall(r"\b\w+\b", text or "")
    keyword_list = [k.strip() for k in (keywords or []) if isinstance(k, str) and k.strip()]
    lower = (text or "").lower()
    found = []
    for k in keyword_list:
        if k.lower() in lower:
            found.append(k)
    return {"word_count": len(words), "keywords_found": found}


def extract_text_from_pdf(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception as e:
            raise RuntimeError("PDF extraction library not installed") from e

    reader = PdfReader(str(p))
    chunks: list[str] = []
    for page in reader.pages:
        t = page.extract_text() or ""
        if t:
            chunks.append(t)
    return "\n".join(chunks)
