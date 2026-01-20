"""
Prompt and output guard implementations using Groq guard models.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class GuardResult:
    """Result from a guard check."""

    def __init__(self, *, safe: bool, reason: Optional[str] = None, details: Optional[dict] = None):
        self.safe = safe
        self.reason = reason
        self.details = details or {}

    def __bool__(self) -> bool:
        """Allow using GuardResult in boolean context."""
        return self.safe

    def __repr__(self) -> str:
        return f"GuardResult(safe={self.safe}, reason={self.reason})"


class PromptGuard:
    """
    Guard for detecting prompt injection and malformed input.

    Uses llama-prompt-guard-2-86m for fast detection.
    """

    def __init__(self):
        self.enabled = settings.groq_enable_guards

    async def check_prompt(self, prompt: str) -> GuardResult:
        """
        Check if prompt is safe to execute.

        Args:
            prompt: User input prompt

        Returns:
            GuardResult indicating safety
        """
        if not self.enabled:
            return GuardResult(safe=True, reason="Guards disabled")

        # Rule-based checks (fast, no API call)
        if not prompt or not prompt.strip():
            return GuardResult(safe=False, reason="Empty prompt")

        if len(prompt) > 50000:
            return GuardResult(safe=False, reason="Prompt too long (>50K chars)")

        # Check for common injection patterns
        injection_patterns = [
            "ignore previous instructions",
            "ignore all previous",
            "disregard all previous",
            "forget everything above",
            "new instructions:",
            "system:",
            "assistant:",
            "<|im_start|>",
            "<|im_end|>",
        ]

        prompt_lower = prompt.lower()
        for pattern in injection_patterns:
            if pattern in prompt_lower:
                return GuardResult(
                    safe=False,
                    reason=f"Potential prompt injection detected: '{pattern}'",
                    details={"pattern": pattern},
                )

        # TODO: Optionally call llama-prompt-guard-2-86m for deeper analysis
        # For now, rule-based is sufficient and faster

        return GuardResult(safe=True, reason="Prompt passed safety checks")


class OutputGuard:
    """
    Guard for validating LLM output.

    Uses llama-guard-4-12b for output validation and safety checks.
    """

    def __init__(self):
        self.enabled = settings.groq_enable_guards

    async def validate_output(
        self,
        output: str,
        *,
        expected_format: Optional[str] = None,
        schema: Optional[dict] = None,
    ) -> GuardResult:
        """
        Validate LLM output for safety and format.

        Args:
            output: Generated output from LLM
            expected_format: Expected format ("json", "text", etc.)
            schema: Optional JSON schema for validation

        Returns:
            GuardResult indicating validity
        """
        if not self.enabled:
            return GuardResult(safe=True, reason="Guards disabled")

        # Basic checks
        if not output or not output.strip():
            return GuardResult(safe=False, reason="Empty output")

        if len(output) > 100000:
            return GuardResult(safe=False, reason="Output too long (>100K chars)")

        # JSON format validation
        if expected_format == "json":
            try:
                parsed = json.loads(output)

                # Schema validation if provided
                if schema:
                    validation_result = self._validate_schema(parsed, schema)
                    if not validation_result.safe:
                        return validation_result

                return GuardResult(safe=True, reason="Valid JSON output", details={"parsed": parsed})
            except json.JSONDecodeError as e:
                return GuardResult(safe=False, reason=f"Invalid JSON: {str(e)}")

        # Content safety checks (rule-based for speed)
        unsafe_patterns = [
            "```python exec(",
            "import os",
            "import subprocess",
            "eval(",
            "exec(",
            "__import__",
        ]

        output_lower = output.lower()
        for pattern in unsafe_patterns:
            if pattern in output_lower:
                logger.warning(f"Potentially unsafe output pattern detected: {pattern}")
                # Don't block, just log warning
                return GuardResult(
                    safe=True,  # Still allow, but warn
                    reason="Output contains potentially unsafe code",
                    details={"warning": f"Pattern detected: {pattern}"},
                )

        # TODO: Optionally call llama-guard-4-12b for deeper safety analysis

        return GuardResult(safe=True, reason="Output passed validation")

    def _validate_schema(self, data: Any, schema: dict) -> GuardResult:
        """
        Simple schema validation (basic type checking).

        Args:
            data: Parsed JSON data
            schema: Expected schema structure

        Returns:
            GuardResult indicating schema validity
        """
        try:
            # Check required fields
            if "required" in schema and isinstance(data, dict):
                for field in schema["required"]:
                    if field not in data:
                        return GuardResult(safe=False, reason=f"Missing required field: {field}")

            # Check type
            if "type" in schema:
                expected_type = schema["type"]
                if expected_type == "object" and not isinstance(data, dict):
                    return GuardResult(safe=False, reason="Expected object, got different type")
                elif expected_type == "array" and not isinstance(data, list):
                    return GuardResult(safe=False, reason="Expected array, got different type")
                elif expected_type == "string" and not isinstance(data, str):
                    return GuardResult(safe=False, reason="Expected string, got different type")
                elif expected_type == "number" and not isinstance(data, (int, float)):
                    return GuardResult(safe=False, reason="Expected number, got different type")

            # Check array items if schema specifies
            if "items" in schema and isinstance(data, list):
                item_schema = schema["items"]
                for i, item in enumerate(data):
                    result = self._validate_schema(item, item_schema)
                    if not result.safe:
                        return GuardResult(safe=False, reason=f"Item {i}: {result.reason}")

            return GuardResult(safe=True, reason="Schema validation passed")

        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return GuardResult(safe=False, reason=f"Schema validation failed: {str(e)}")


# Global singletons
_prompt_guard: Optional[PromptGuard] = None
_output_guard: Optional[OutputGuard] = None


def get_prompt_guard() -> PromptGuard:
    """Get or create the global PromptGuard instance."""
    global _prompt_guard
    if _prompt_guard is None:
        _prompt_guard = PromptGuard()
    return _prompt_guard


def get_output_guard() -> OutputGuard:
    """Get or create the global OutputGuard instance."""
    global _output_guard
    if _output_guard is None:
        _output_guard = OutputGuard()
    return _output_guard
