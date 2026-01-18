import pytest

from app.ai.evaluator.code_runner import run_code_tests


def test_python_runner_works_without_resource_module_dependency():
    code = "print('ok')"
    res = run_code_tests(code=code, language="python", test_cases=[{"input": "", "expected_output": "ok"}])
    assert res["passed"] == 1
    assert res["failed"] == 0


def test_comparison_mode_normalized():
    code = "print('a   b')"
    res = run_code_tests(
        code=code,
        language="python",
        test_cases=[{"input": "", "expected_output": "a b", "comparison_mode": "normalized"}],
    )
    assert res["passed"] == 1
    assert res["failed"] == 0


def test_output_limit_exceeded_fails():
    code = "print('x' * 50000)"
    res = run_code_tests(
        code=code,
        language="python",
        test_cases=[{"input": "", "expected_output": ""}],
        max_output_kb=1,
    )
    assert res["failed"] == 1
    assert any("Output limit exceeded" in (e or "") for e in res.get("errors") or [])


@pytest.mark.parametrize(
    "bad_code",
    [
        "import os\nprint('x')",
        "print(eval('2+2'))",
    ],
)
def test_security_mode_block_rejects_unsafe_code(bad_code: str):
    res = run_code_tests(
        code=bad_code,
        language="python",
        test_cases=[{"input": "", "expected_output": "x"}],
        security_mode="block",
    )
    assert res["errors"] == ["Blocked by security policy"]
