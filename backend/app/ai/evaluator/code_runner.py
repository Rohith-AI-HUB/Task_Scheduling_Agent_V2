from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal


Language = Literal["python", "javascript", "java"]


def run_code_tests(
    *,
    code: str,
    language: Language,
    test_cases: list[dict[str, Any]] | None = None,
    timeout_ms: int = 2000,
) -> dict[str, Any]:
    if language != "python":
        return {"passed": 0, "failed": 0, "errors": [f"Language not supported: {language}"]}

    cases = list(test_cases or [])
    passed = 0
    failed = 0
    errors: list[str] = []

    with tempfile.TemporaryDirectory(prefix="tsa_eval_") as tmp:
        root = Path(tmp)
        program_path = root / "main.py"
        program_path.write_text(code or "", encoding="utf-8")

        def _run_one(
            stdin_text: str | None, *, timeout_used_ms: int
        ) -> subprocess.CompletedProcess[str]:
            cmd = [sys.executable, "-I", str(program_path)]
            return subprocess.run(
                cmd,
                input=stdin_text,
                text=True,
                capture_output=True,
                cwd=str(root),
                timeout=max(0.1, timeout_used_ms / 1000.0),
            )

        if not cases:
            try:
                res = _run_one(None, timeout_used_ms=timeout_ms)
            except subprocess.TimeoutExpired:
                return {"passed": 0, "failed": 1, "errors": ["Timeout"]}
            if res.returncode == 0:
                return {"passed": 1, "failed": 0, "errors": []}
            msg = (res.stderr or res.stdout or "").strip()
            return {"passed": 0, "failed": 1, "errors": [msg or "Runtime error"]}

        for i, case in enumerate(cases, start=1):
            stdin_text = str(case.get("input") or "")
            expected = str(case.get("expected_output") or "")
            timeout_override = case.get("timeout_ms")
            if isinstance(timeout_override, int) and timeout_override > 0:
                timeout_used = timeout_override
            else:
                timeout_used = timeout_ms

            try:
                out_res = _run_one(stdin_text, timeout_used_ms=timeout_used)
            except subprocess.TimeoutExpired:
                failed += 1
                errors.append(f"Case {i}: Timeout")
                continue

            if out_res.returncode != 0:
                failed += 1
                msg = (out_res.stderr or out_res.stdout or "").strip()
                errors.append(f"Case {i}: {msg[:400] if msg else 'Runtime error'}")
                continue

            actual = (out_res.stdout or "").strip()
            if actual == expected.strip():
                passed += 1
            else:
                failed += 1
                errors.append(
                    f"Case {i}: Expected {expected.strip()!r}, got {actual!r}"[:400]
                )

    return {"passed": passed, "failed": failed, "errors": errors}
