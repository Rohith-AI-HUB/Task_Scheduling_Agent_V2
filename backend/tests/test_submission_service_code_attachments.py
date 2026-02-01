from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from bson import ObjectId


class _FakeCollection:
    def __init__(self, docs: list[dict] | None = None):
        self._docs = list(docs or [])

    def _match(self, doc: dict, query: dict) -> bool:
        for k, v in query.items():
            if doc.get(k) != v:
                return False
        return True

    async def find_one(self, query: dict, sort=None):
        for d in self._docs:
            if self._match(d, query):
                return d
        return None

    async def update_one(self, query: dict, update: dict):
        for d in self._docs:
            if not self._match(d, query):
                continue
            if "$set" in update:
                for k, v in update["$set"].items():
                    if "." in k:
                        keys = k.split(".")
                        cur = d
                        for part in keys[:-1]:
                            nxt = cur.get(part)
                            if not isinstance(nxt, dict):
                                nxt = {}
                                cur[part] = nxt
                            cur = nxt
                        cur[keys[-1]] = v
                    else:
                        d[k] = v
            if "$push" in update:
                for k, v in update["$push"].items():
                    if isinstance(v, dict) and "$each" in v:
                        d.setdefault(k, [])
                        d[k].extend(v["$each"])
                    else:
                        d.setdefault(k, [])
                        d[k].append(v)
            if "$pull" in update:
                for k, cond in update["$pull"].items():
                    if not isinstance(d.get(k), list) or not isinstance(cond, dict):
                        continue
                    key = next(iter(cond.keys()), None)
                    value = cond.get(key) if key else None
                    d[k] = [row for row in d[k] if not (isinstance(row, dict) and row.get(key) == value)]
            return


@pytest.mark.asyncio
async def test_evaluate_submission_uses_code_attachment(monkeypatch, tmp_path: Path):
    from app.services import submission_service

    submission_id = ObjectId()
    task_id = ObjectId()

    code_path = tmp_path / "solution.py"
    code_path.write_text("print('from_attachment')\n", encoding="utf-8")

    submissions = _FakeCollection(
        [
            {
                "_id": submission_id,
                "task_id": task_id,
                "subject_id": ObjectId(),
                "student_uid": "s1",
                "group_id": None,
                "content": "print('from_content')\n",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "attachments": [
                    {
                        "id": "a1",
                        "filename": "solution.py",
                        "content_type": "text/x-python",
                        "size": code_path.stat().st_size,
                        "uploaded_at": datetime.utcnow(),
                        "path": str(code_path),
                    }
                ],
                "evaluation": {"status": "pending"},
            }
        ]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": task_id,
                "subject_id": ObjectId(),
                "title": "T",
                "description": "D",
                "points": 10,
                "evaluation_config": {"code": {"language": "python"}, "document": {}},
            }
        ]
    )

    def fake_get_collection(name: str):
        if name == "submissions":
            return submissions
        if name == "tasks":
            return tasks
        raise AssertionError(f"Unexpected collection: {name}")

    captured: dict[str, object] = {}

    def fake_run_code_tests(*, code: str, language: str, **kwargs):
        captured["code"] = code
        captured["language"] = language
        return {
            "passed": 1,
            "failed": 0,
            "total_points": 1,
            "earned_points": 1,
            "errors": [],
            "warnings": [],
            "test_results": [],
        }

    async def fake_analyze_text_with_groq(**kwargs):
        return {"word_count": 0, "keywords_found": [], "keyword_match_ratio": 0, "meets_min_words": True}

    def fake_build_ai_feedback(**kwargs):
        return "ok"

    class _FakeGroq:
        def is_available(self):
            return False

    monkeypatch.setattr(submission_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(submission_service, "run_code_tests", fake_run_code_tests)
    monkeypatch.setattr(submission_service, "analyze_text_with_groq", fake_analyze_text_with_groq)
    monkeypatch.setattr(submission_service, "build_ai_feedback", fake_build_ai_feedback)
    monkeypatch.setattr(submission_service, "GroqService", _FakeGroq)

    await submission_service.evaluate_submission(submission_id=submission_id)

    assert captured.get("language") == "python"
    assert "from_attachment" in str(captured.get("code") or "")


@pytest.mark.asyncio
async def test_evaluate_submission_runs_with_empty_code_config(monkeypatch, tmp_path: Path):
    from app.services import submission_service

    submission_id = ObjectId()
    task_id = ObjectId()

    code_path = tmp_path / "solution.py"
    code_path.write_text("print('from_attachment')\n", encoding="utf-8")

    submissions = _FakeCollection(
        [
            {
                "_id": submission_id,
                "task_id": task_id,
                "subject_id": ObjectId(),
                "student_uid": "s1",
                "group_id": None,
                "content": "",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "attachments": [
                    {
                        "id": "a1",
                        "filename": "solution.py",
                        "content_type": "text/x-python",
                        "size": code_path.stat().st_size,
                        "uploaded_at": datetime.utcnow(),
                        "path": str(code_path),
                    }
                ],
                "evaluation": {"status": "pending"},
            }
        ]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": task_id,
                "subject_id": ObjectId(),
                "title": "T",
                "description": "D",
                "points": 10,
                "evaluation_config": {"code": {}, "document": {}},
            }
        ]
    )

    def fake_get_collection(name: str):
        if name == "submissions":
            return submissions
        if name == "tasks":
            return tasks
        raise AssertionError(f"Unexpected collection: {name}")

    captured: dict[str, object] = {}

    def fake_run_code_tests(*, code: str, language: str, **kwargs):
        captured["code"] = code
        captured["language"] = language
        return {
            "passed": 1,
            "failed": 0,
            "total_points": 1,
            "earned_points": 1,
            "errors": [],
            "warnings": [],
            "test_results": [],
        }

    async def fake_analyze_text_with_groq(**kwargs):
        return {"word_count": 0, "keywords_found": [], "keyword_match_ratio": 0, "meets_min_words": True}

    def fake_build_ai_feedback(**kwargs):
        return "ok"

    class _FakeGroq:
        def is_available(self):
            return False

    monkeypatch.setattr(submission_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(submission_service, "run_code_tests", fake_run_code_tests)
    monkeypatch.setattr(submission_service, "analyze_text_with_groq", fake_analyze_text_with_groq)
    monkeypatch.setattr(submission_service, "build_ai_feedback", fake_build_ai_feedback)
    monkeypatch.setattr(submission_service, "GroqService", _FakeGroq)

    await submission_service.evaluate_submission(submission_id=submission_id)

    assert captured.get("language") == "python"
    assert "from_attachment" in str(captured.get("code") or "")


@pytest.mark.asyncio
async def test_evaluate_submission_uses_ipynb_code_attachment(monkeypatch, tmp_path: Path):
    from app.services import submission_service

    submission_id = ObjectId()
    task_id = ObjectId()

    nb_path = tmp_path / "solution.ipynb"
    nb_path.write_text(
        """{
  "cells": [
    {"cell_type": "markdown", "source": ["# Title\\n"]},
    {"cell_type": "code", "source": ["print('ipynb')\\n", "x = 1\\n"]},
    {"cell_type": "code", "source": "print('second')\\n"}
  ]
}""",
        encoding="utf-8",
    )

    submissions = _FakeCollection(
        [
            {
                "_id": submission_id,
                "task_id": task_id,
                "subject_id": ObjectId(),
                "student_uid": "s1",
                "group_id": None,
                "content": "print('from_content')\n",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "attachments": [
                    {
                        "id": "a1",
                        "filename": "solution.ipynb",
                        "content_type": "application/x-ipynb+json",
                        "size": nb_path.stat().st_size,
                        "uploaded_at": datetime.utcnow(),
                        "path": str(nb_path),
                    }
                ],
                "evaluation": {"status": "pending"},
            }
        ]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": task_id,
                "subject_id": ObjectId(),
                "title": "T",
                "description": "D",
                "points": 10,
                "evaluation_config": {"code": {"language": "python"}, "document": {}},
            }
        ]
    )

    def fake_get_collection(name: str):
        if name == "submissions":
            return submissions
        if name == "tasks":
            return tasks
        raise AssertionError(f"Unexpected collection: {name}")

    captured: dict[str, object] = {}

    def fake_run_code_tests(*, code: str, language: str, **kwargs):
        captured["code"] = code
        captured["language"] = language
        return {
            "passed": 1,
            "failed": 0,
            "total_points": 1,
            "earned_points": 1,
            "errors": [],
            "warnings": [],
            "test_results": [],
        }

    async def fake_analyze_text_with_groq(**kwargs):
        return {"word_count": 0, "keywords_found": [], "keyword_match_ratio": 0, "meets_min_words": True}

    def fake_build_ai_feedback(**kwargs):
        return "ok"

    class _FakeGroq:
        def is_available(self):
            return False

    monkeypatch.setattr(submission_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(submission_service, "run_code_tests", fake_run_code_tests)
    monkeypatch.setattr(submission_service, "analyze_text_with_groq", fake_analyze_text_with_groq)
    monkeypatch.setattr(submission_service, "build_ai_feedback", fake_build_ai_feedback)
    monkeypatch.setattr(submission_service, "GroqService", _FakeGroq)

    await submission_service.evaluate_submission(submission_id=submission_id)

    assert captured.get("language") == "python"
    payload = str(captured.get("code") or "")
    assert "ipynb" in payload
    assert "second" in payload


@pytest.mark.asyncio
async def test_evaluate_submission_infers_code_from_ipynb_without_code_config(monkeypatch, tmp_path: Path):
    from app.services import submission_service

    submission_id = ObjectId()
    task_id = ObjectId()

    nb_path = tmp_path / "oop.ipynb"
    nb_path.write_text(
        """{
  "cells": [
    {"cell_type": "code", "source": ["print('hello')\\n"]}
  ]
}""",
        encoding="utf-8",
    )

    submissions = _FakeCollection(
        [
            {
                "_id": submission_id,
                "task_id": task_id,
                "subject_id": ObjectId(),
                "student_uid": "s1",
                "group_id": None,
                "content": "",
                "submitted_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "attachments": [
                    {
                        "id": "a1",
                        "filename": "oop.ipynb",
                        "content_type": "application/x-ipynb+json",
                        "size": nb_path.stat().st_size,
                        "uploaded_at": datetime.utcnow(),
                        "path": str(nb_path),
                    }
                ],
                "evaluation": {"status": "pending"},
            }
        ]
    )
    tasks = _FakeCollection(
        [
            {
                "_id": task_id,
                "subject_id": ObjectId(),
                "title": "T",
                "description": "D",
                "points": 10,
                "evaluation_config": {"document": {}},
            }
        ]
    )

    def fake_get_collection(name: str):
        if name == "submissions":
            return submissions
        if name == "tasks":
            return tasks
        raise AssertionError(f"Unexpected collection: {name}")

    captured: dict[str, object] = {}

    def fake_run_code_tests(*, code: str, language: str, **kwargs):
        captured["code"] = code
        captured["language"] = language
        return {
            "passed": 1,
            "failed": 0,
            "total_points": 1,
            "earned_points": 1,
            "errors": [],
            "warnings": [],
            "test_results": [],
        }

    async def fake_analyze_text_with_groq(**kwargs):
        return {"word_count": 0, "keywords_found": [], "keyword_match_ratio": 0, "meets_min_words": True}

    def fake_build_ai_feedback(**kwargs):
        return "ok"

    class _FakeGroq:
        def is_available(self):
            return False

    monkeypatch.setattr(submission_service, "get_collection", fake_get_collection)
    monkeypatch.setattr(submission_service, "run_code_tests", fake_run_code_tests)
    monkeypatch.setattr(submission_service, "analyze_text_with_groq", fake_analyze_text_with_groq)
    monkeypatch.setattr(submission_service, "build_ai_feedback", fake_build_ai_feedback)
    monkeypatch.setattr(submission_service, "GroqService", _FakeGroq)

    await submission_service.evaluate_submission(submission_id=submission_id)

    assert captured.get("language") == "python"
    assert "hello" in str(captured.get("code") or "")
