"""
Intent classifier for routing requests to appropriate models.

Rule-based classification (no LLM overhead) to determine whether to use
8B (simple/medium tasks) or Scout (complex tasks).
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class IntentComplexity(str, Enum):
    """Complexity levels for intent classification."""

    SIMPLE = "simple"  # Route to 8B
    MEDIUM = "medium"  # Route to 8B
    COMPLEX = "complex"  # Route to Scout


class IntentType(str, Enum):
    """Types of intents in the system."""

    TEST_CASE_GENERATION = "test_case_generation"
    GRADE_FEEDBACK = "grade_feedback"
    DEADLINE_SUGGESTION = "deadline_suggestion"
    STATEMENT_ANALYSIS = "statement_analysis"
    HINT_GENERATION = "hint_generation"
    GRADE_INSIGHTS = "grade_insights"
    GENERAL = "general"


class IntentClassifier:
    """
    Rule-based classifier to determine request complexity.

    Based on GroqAPI.md guidelines:
    - 8B handles 80% of traffic (simple & medium)
    - Scout handles ≤15% (complex only)
    """

    @staticmethod
    def classify(
        *,
        intent_type: IntentType,
        prompt_length: Optional[int] = None,
        context: Optional[dict] = None,
    ) -> IntentComplexity:
        """
        Classify intent complexity based on type and context.

        Args:
            intent_type: The type of request
            prompt_length: Length of prompt in characters
            context: Additional context (e.g., num_test_cases, submission_count)

        Returns:
            IntentComplexity level
        """
        context = context or {}

        # Test case generation
        if intent_type == IntentType.TEST_CASE_GENERATION:
            num_cases = context.get("num_cases", 5)
            if num_cases <= 3:
                return IntentComplexity.SIMPLE
            elif num_cases <= 10:
                return IntentComplexity.MEDIUM
            else:
                return IntentComplexity.COMPLEX

        # Grade feedback
        elif intent_type == IntentType.GRADE_FEEDBACK:
            code_length = context.get("code_length", 0)
            has_complex_errors = context.get("has_complex_errors", False)

            if has_complex_errors or code_length > 3000:
                return IntentComplexity.COMPLEX
            elif code_length > 1000:
                return IntentComplexity.MEDIUM
            else:
                return IntentComplexity.SIMPLE

        # Deadline suggestion (always complex - needs reasoning)
        elif intent_type == IntentType.DEADLINE_SUGGESTION:
            return IntentComplexity.COMPLEX

        # Statement analysis
        elif intent_type == IntentType.STATEMENT_ANALYSIS:
            statement_length = context.get("statement_length", 0)
            if statement_length > 2000:
                return IntentComplexity.COMPLEX
            else:
                return IntentComplexity.MEDIUM

        # Hint generation
        elif intent_type == IntentType.HINT_GENERATION:
            hint_level = context.get("hint_level", 1)
            if hint_level >= 3:
                return IntentComplexity.MEDIUM
            else:
                return IntentComplexity.SIMPLE

        # Grade insights (always complex - analytics)
        elif intent_type == IntentType.GRADE_INSIGHTS:
            submission_count = context.get("submission_count", 0)
            if submission_count > 50:
                return IntentComplexity.COMPLEX
            else:
                return IntentComplexity.MEDIUM

        # General/unknown
        else:
            # Fallback to prompt length
            if prompt_length and prompt_length > 1000:
                return IntentComplexity.COMPLEX
            else:
                return IntentComplexity.SIMPLE

    @staticmethod
    def should_use_scout(complexity: IntentComplexity) -> bool:
        """
        Determine if Scout model should be used.

        Args:
            complexity: The classified complexity level

        Returns:
            True if Scout should be used, False for 8B
        """
        return complexity == IntentComplexity.COMPLEX

    @staticmethod
    def estimate_tokens(prompt: str, max_completion_tokens: int = 1024) -> int:
        """
        Estimate total tokens (prompt + completion).

        Rule of thumb: ~4 characters per token

        Args:
            prompt: Input prompt text
            max_completion_tokens: Expected completion tokens

        Returns:
            Estimated total tokens
        """
        prompt_tokens = len(prompt) // 4
        return prompt_tokens + max_completion_tokens
