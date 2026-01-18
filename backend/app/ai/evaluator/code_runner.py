from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal


Language = Literal["python", "javascript", "java"]


def _check_code_quality(code: str, language: Language) -> list[str]:
    """Basic code quality checks without external linters."""
    warnings = []

    if language == "python":
        if len(code) > 50000:
            warnings.append("Code is very long (>50K chars)")
        if code.count("import os") > 0 or code.count("import subprocess") > 0:
            warnings.append("Warning: Potentially unsafe imports detected")
        if code.count("eval(") > 0 or code.count("exec(") > 0:
            warnings.append("Warning: Dynamic code execution detected")
        lines = code.split("\n")
        if len(lines) > 1000:
            warnings.append(f"Code has {len(lines)} lines (consider breaking into functions)")

    return warnings


def _normalize_output(text: str, normalize_whitespace: bool = True) -> str:
    """Normalize output for comparison."""
    text = text.strip()
    if normalize_whitespace:
        text = " ".join(text.split())
    return text


def _compare_output(actual: str, expected: str, comparison_mode: str = "exact") -> tuple[bool, str | None]:
    """
    Compare outputs with different comparison modes.
    Returns (matches, error_message).
    """
    if comparison_mode == "exact":
        if actual == expected:
            return True, None
        return False, f"Expected {expected!r}, got {actual!r}"

    elif comparison_mode == "normalized":
        actual_norm = _normalize_output(actual)
        expected_norm = _normalize_output(expected)
        if actual_norm == expected_norm:
            return True, None
        return False, f"Expected {expected_norm!r}, got {actual_norm!r}"

    elif comparison_mode == "regex":
        try:
            if re.fullmatch(expected, actual):
                return True, None
            return False, f"Output {actual!r} doesn't match pattern {expected!r}"
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"

    elif comparison_mode == "contains":
        if expected in actual:
            return True, None
        return False, f"Expected output to contain {expected!r}, got {actual!r}"

    else:
        return False, f"Unknown comparison mode: {comparison_mode}"


def _run_python_code(
    code: str,
    program_path: Path,
    stdin_text: str | None,
    timeout_ms: int,
    memory_limit_mb: int = 256,
) -> subprocess.CompletedProcess[str]:
    """Run Python code with resource restrictions."""

    program_path.write_text(code, encoding="utf-8")

    # Create a wrapper script that sets resource limits
    wrapper = f"""
import resource
import sys

# Set memory limit (soft and hard limit in bytes)
try:
    memory_bytes = {memory_limit_mb} * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
except Exception:
    pass

# Set CPU time limit (soft and hard limit in seconds)
try:
    cpu_seconds = max(1, {timeout_ms} // 1000)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
except Exception:
    pass

# Execute the student code
with open(r"{program_path}", "r", encoding="utf-8") as f:
    exec(f.read())
"""

    wrapper_path = program_path.parent / "_wrapper.py"
    wrapper_path.write_text(wrapper, encoding="utf-8")

    cmd = [sys.executable, "-I", "-u", str(wrapper_path)]

    try:
        return subprocess.run(
            cmd,
            input=stdin_text,
            text=True,
            capture_output=True,
            cwd=str(program_path.parent),
            timeout=max(0.1, timeout_ms / 1000.0),
        )
    except subprocess.TimeoutExpired as e:
        raise e


def _run_javascript_code(
    code: str,
    program_path: Path,
    stdin_text: str | None,
    timeout_ms: int,
) -> subprocess.CompletedProcess[str]:
    """Run JavaScript code using Node.js."""

    program_path.write_text(code, encoding="utf-8")

    # Try to find node executable
    node_cmd = "node"

    cmd = [node_cmd, str(program_path)]

    return subprocess.run(
        cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        cwd=str(program_path.parent),
        timeout=max(0.1, timeout_ms / 1000.0),
    )


def _run_java_code(
    code: str,
    program_path: Path,
    stdin_text: str | None,
    timeout_ms: int,
) -> subprocess.CompletedProcess[str]:
    """Run Java code."""

    class_name = "Main"
    match = re.search(r'public\s+class\s+(\w+)', code)
    if match:
        class_name = match.group(1)

    java_file = program_path.parent / f"{class_name}.java"
    java_file.write_text(code, encoding="utf-8")

    # Compile
    compile_cmd = ["javac", str(java_file)]
    compile_result = subprocess.run(
        compile_cmd,
        capture_output=True,
        text=True,
        cwd=str(program_path.parent),
        timeout=30,
    )

    if compile_result.returncode != 0:
        raise RuntimeError(f"Compilation failed: {compile_result.stderr}")

    # Run
    run_cmd = ["java", "-cp", str(program_path.parent), class_name]

    return subprocess.run(
        run_cmd,
        input=stdin_text,
        text=True,
        capture_output=True,
        cwd=str(program_path.parent),
        timeout=max(0.1, timeout_ms / 1000.0),
    )


def run_code_tests(
    *,
    code: str,
    language: Language,
    test_cases: list[dict[str, Any]] | None = None,
    timeout_ms: int = 2000,
    memory_limit_mb: int = 256,
    enable_quality_checks: bool = True,
) -> dict[str, Any]:
    """
    Run code tests with enhanced security and features.

    Args:
        code: Source code to test
        language: Programming language
        test_cases: List of test cases with structure:
            {
                "input": str,
                "expected_output": str,
                "timeout_ms": int (optional),
                "comparison_mode": str (optional: "exact", "normalized", "regex", "contains"),
                "points": int (optional, for weighted scoring),
                "description": str (optional)
            }
        timeout_ms: Default timeout in milliseconds
        memory_limit_mb: Memory limit in megabytes (Python only)
        enable_quality_checks: Whether to run code quality checks

    Returns:
        {
            "passed": int,
            "failed": int,
            "total_points": int,
            "earned_points": int,
            "errors": list[str],
            "warnings": list[str],
            "test_results": list[dict] (detailed per-test results)
        }
    """

    # Quality checks
    warnings = []
    if enable_quality_checks:
        warnings = _check_code_quality(code, language)

    cases = list(test_cases or [])
    passed = 0
    failed = 0
    errors: list[str] = []
    test_results = []
    total_points = 0
    earned_points = 0

    with tempfile.TemporaryDirectory(prefix="tsa_eval_") as tmp:
        root = Path(tmp)

        # Set file extension based on language
        extensions = {"python": ".py", "javascript": ".js", "java": ".java"}
        program_path = root / f"main{extensions.get(language, '.txt')}"

        # If no test cases, just run once
        if not cases:
            try:
                if language == "python":
                    res = _run_python_code(code, program_path, None, timeout_ms, memory_limit_mb)
                elif language == "javascript":
                    res = _run_javascript_code(code, program_path, None, timeout_ms)
                elif language == "java":
                    res = _run_java_code(code, program_path, None, timeout_ms)
                else:
                    return {
                        "passed": 0,
                        "failed": 0,
                        "total_points": 0,
                        "earned_points": 0,
                        "errors": [f"Language not supported: {language}"],
                        "warnings": warnings,
                        "test_results": [],
                    }
            except subprocess.TimeoutExpired:
                return {
                    "passed": 0,
                    "failed": 1,
                    "total_points": 1,
                    "earned_points": 0,
                    "errors": ["Execution timeout"],
                    "warnings": warnings,
                    "test_results": [{"status": "timeout", "error": "Execution timeout"}],
                }
            except Exception as e:
                return {
                    "passed": 0,
                    "failed": 1,
                    "total_points": 1,
                    "earned_points": 0,
                    "errors": [str(e)[:500]],
                    "warnings": warnings,
                    "test_results": [{"status": "error", "error": str(e)[:500]}],
                }

            if res.returncode == 0:
                return {
                    "passed": 1,
                    "failed": 0,
                    "total_points": 1,
                    "earned_points": 1,
                    "errors": [],
                    "warnings": warnings,
                    "test_results": [{"status": "passed", "output": res.stdout}],
                }

            msg = (res.stderr or res.stdout or "").strip()
            return {
                "passed": 0,
                "failed": 1,
                "total_points": 1,
                "earned_points": 0,
                "errors": [msg or "Runtime error"],
                "warnings": warnings,
                "test_results": [{"status": "failed", "error": msg or "Runtime error"}],
            }

        # Run test cases
        for i, case in enumerate(cases, start=1):
            stdin_text = str(case.get("input") or "")
            expected = str(case.get("expected_output") or "")
            timeout_override = case.get("timeout_ms")
            comparison_mode = case.get("comparison_mode", "exact")
            points = case.get("points", 1)
            description = case.get("description", f"Test case {i}")

            total_points += points

            if isinstance(timeout_override, int) and timeout_override > 0:
                timeout_used = timeout_override
            else:
                timeout_used = timeout_ms

            test_result = {
                "case_number": i,
                "description": description,
                "points": points,
            }

            try:
                if language == "python":
                    out_res = _run_python_code(code, program_path, stdin_text, timeout_used, memory_limit_mb)
                elif language == "javascript":
                    out_res = _run_javascript_code(code, program_path, stdin_text, timeout_used)
                elif language == "java":
                    out_res = _run_java_code(code, program_path, stdin_text, timeout_used)
                else:
                    raise ValueError(f"Unsupported language: {language}")

            except subprocess.TimeoutExpired:
                failed += 1
                error_msg = f"Case {i} ({description}): Timeout after {timeout_used}ms"
                errors.append(error_msg)
                test_result["status"] = "timeout"
                test_result["error"] = f"Timeout after {timeout_used}ms"
                test_results.append(test_result)
                continue
            except Exception as e:
                failed += 1
                error_msg = f"Case {i} ({description}): {str(e)[:500]}"
                errors.append(error_msg)
                test_result["status"] = "error"
                test_result["error"] = str(e)[:500]
                test_results.append(test_result)
                continue

            if out_res.returncode != 0:
                failed += 1
                msg = (out_res.stderr or out_res.stdout or "").strip()
                error_msg = f"Case {i} ({description}): {msg[:500] if msg else 'Runtime error'}"
                errors.append(error_msg)
                test_result["status"] = "runtime_error"
                test_result["error"] = msg[:500] if msg else "Runtime error"
                test_result["stderr"] = out_res.stderr[:500] if out_res.stderr else None
                test_results.append(test_result)
                continue

            actual = (out_res.stdout or "").strip()
            matches, error_msg = _compare_output(actual, expected, comparison_mode)

            if matches:
                passed += 1
                earned_points += points
                test_result["status"] = "passed"
                test_result["output"] = actual[:500]
            else:
                failed += 1
                errors.append(f"Case {i} ({description}): {error_msg}"[:500])
                test_result["status"] = "failed"
                test_result["error"] = error_msg
                test_result["expected"] = expected[:500]
                test_result["actual"] = actual[:500]

            test_results.append(test_result)

    return {
        "passed": passed,
        "failed": failed,
        "total_points": total_points,
        "earned_points": earned_points,
        "errors": errors,
        "warnings": warnings,
        "test_results": test_results,
    }
