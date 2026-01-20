"""
Model router with quota-aware intelligent routing.

Implements the full architecture from GroqAPI.md:
Request → Prompt Guard → Intent Classifier → Model Router → Output Guard
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.ai.groq_client.cache import get_groq_cache
from app.ai.groq_client.client import GroqClient, get_groq_client
from app.ai.groq_client.guards import get_output_guard, get_prompt_guard
from app.ai.groq_client.intent import IntentClassifier, IntentComplexity, IntentType
from app.ai.groq_client.quota_tracker import get_quota_tracker
from app.config import settings

logger = logging.getLogger(__name__)


class ModelRouter:
    """
    Quota-aware model router implementing the full guard → classify → route → validate pipeline.
    """

    def __init__(self):
        self.client = get_groq_client()
        self.quota_tracker = get_quota_tracker()
        self.cache = get_groq_cache()
        self.prompt_guard = get_prompt_guard()
        self.output_guard = get_output_guard()
        self.classifier = IntentClassifier()
        self.routing_enabled = settings.groq_enable_routing

    async def complete(
        self,
        *,
        prompt: str,
        intent_type: IntentType = IntentType.GENERAL,
        context: Optional[dict] = None,
        system_message: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        json_mode: bool = False,
        force_model: Optional[str] = None,
        skip_cache: bool = False,
    ) -> dict[str, Any]:
        """
        Execute full routing pipeline with guards and caching.

        Args:
            prompt: User input prompt
            intent_type: Type of request for classification
            context: Additional context for routing decisions
            system_message: Optional system message
            max_tokens: Maximum completion tokens
            temperature: Sampling temperature
            json_mode: Whether to request JSON output
            force_model: Force specific model (bypasses routing)
            skip_cache: Skip cache lookup/storage

        Returns:
            Dict with response, model_used, cached, complexity, etc.
        """
        context = context or {}

        # ============================================================
        # STEP 1: PROMPT GUARD
        # ============================================================
        guard_result = await self.prompt_guard.check_prompt(prompt)
        if not guard_result.safe:
            logger.warning(f"Prompt blocked by guard: {guard_result.reason}")
            return {
                "success": False,
                "error": f"Prompt safety check failed: {guard_result.reason}",
                "blocked_by": "prompt_guard",
            }

        # ============================================================
        # STEP 2: CACHE LOOKUP
        # ============================================================
        cache_params = {
            "system_message": system_message,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "json_mode": json_mode,
        }

        if not skip_cache:
            # Determine model for cache key (either forced or estimated)
            cache_model = force_model or GroqClient.MODEL_8B
            cached_response = await self.cache.get(prompt=prompt, model=cache_model, params=cache_params)

            if cached_response:
                logger.info(f"Returning cached response for {intent_type}")
                return {
                    "success": True,
                    "response": cached_response,
                    "model_used": cache_model,
                    "cached": True,
                    "complexity": "cached",
                }

        # ============================================================
        # STEP 3: INTENT CLASSIFICATION & MODEL SELECTION
        # ============================================================
        if force_model:
            selected_model = force_model
            complexity = IntentComplexity.COMPLEX if "scout" in force_model.lower() else IntentComplexity.SIMPLE
            logger.info(f"Using forced model: {selected_model}")
        elif not self.routing_enabled:
            # Routing disabled, default to 8B
            selected_model = GroqClient.MODEL_8B
            complexity = IntentComplexity.MEDIUM
            logger.info("Routing disabled, using 8B model")
        else:
            # Classify intent
            prompt_length = len(prompt)
            complexity = self.classifier.classify(
                intent_type=intent_type,
                prompt_length=prompt_length,
                context=context,
            )

            # Route based on complexity
            if self.classifier.should_use_scout(complexity):
                selected_model = GroqClient.MODEL_SCOUT
            else:
                selected_model = GroqClient.MODEL_8B

            logger.info(f"Intent: {intent_type}, Complexity: {complexity}, Routed to: {selected_model}")

        # ============================================================
        # STEP 4: QUOTA CHECK
        # ============================================================
        estimated_tokens = self.classifier.estimate_tokens(prompt, max_tokens)
        quota_available, quota_reason = await self.quota_tracker.check_quota_available(
            model=selected_model,
            estimated_tokens=estimated_tokens,
        )

        if not quota_available:
            logger.warning(f"Quota exceeded for {selected_model}: {quota_reason}")

            # Fallback strategy
            if selected_model == GroqClient.MODEL_SCOUT:
                logger.info("Falling back from Scout to 8B due to quota")
                selected_model = GroqClient.MODEL_8B

                # Re-check 8B quota
                quota_available, quota_reason = await self.quota_tracker.check_quota_available(
                    model=selected_model,
                    estimated_tokens=estimated_tokens,
                )

                if not quota_available:
                    return {
                        "success": False,
                        "error": f"All models quota exceeded: {quota_reason}",
                        "quota_exceeded": True,
                    }
            else:
                return {
                    "success": False,
                    "error": f"Quota exceeded: {quota_reason}",
                    "quota_exceeded": True,
                }

        # ============================================================
        # STEP 5: API CALL
        # ============================================================
        try:
            response = await self.client.complete(
                prompt=prompt,
                model=selected_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system_message=system_message,
                json_mode=json_mode,
            )

            # Track quota usage
            # Note: Actual tokens from API would be more accurate, but estimated is sufficient
            await self.quota_tracker.track_request(model=selected_model, tokens=estimated_tokens)

        except Exception as e:
            logger.error(f"API call failed: {str(e)[:200]}")
            return {
                "success": False,
                "error": f"API call failed: {str(e)}",
                "model_attempted": selected_model,
            }

        # ============================================================
        # STEP 6: OUTPUT GUARD
        # ============================================================
        expected_format = "json" if json_mode else "text"
        output_result = await self.output_guard.validate_output(
            response,
            expected_format=expected_format,
        )

        if not output_result.safe:
            logger.warning(f"Output blocked by guard: {output_result.reason}")
            return {
                "success": False,
                "error": f"Output validation failed: {output_result.reason}",
                "blocked_by": "output_guard",
                "raw_response": response[:500],  # Include snippet for debugging
            }

        # ============================================================
        # STEP 7: CACHE STORAGE
        # ============================================================
        if not skip_cache:
            await self.cache.set(
                prompt=prompt,
                model=selected_model,
                response=response,
                params=cache_params,
            )

        # ============================================================
        # RETURN SUCCESS
        # ============================================================
        return {
            "success": True,
            "response": response,
            "model_used": selected_model,
            "cached": False,
            "complexity": complexity.value,
            "intent_type": intent_type.value,
            "estimated_tokens": estimated_tokens,
            "warnings": output_result.details.get("warning") if output_result.details else None,
        }

    async def complete_with_retry(
        self,
        *,
        prompt: str,
        intent_type: IntentType = IntentType.GENERAL,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute with automatic Scout → 8B fallback on quota issues.

        Args:
            prompt: User input
            intent_type: Intent type
            **kwargs: Additional arguments for complete()

        Returns:
            Response dict
        """
        result = await self.complete(prompt=prompt, intent_type=intent_type, **kwargs)

        # If Scout quota exceeded, retry with 8B
        if not result["success"] and result.get("quota_exceeded"):
            model_attempted = result.get("model_attempted")
            if model_attempted == GroqClient.MODEL_SCOUT:
                logger.info("Retrying with 8B after Scout quota exceeded")
                return await self.complete(
                    prompt=prompt,
                    intent_type=intent_type,
                    force_model=GroqClient.MODEL_8B,
                    **kwargs,
                )

        return result

    async def get_routing_stats(self) -> dict[str, Any]:
        """
        Get statistics about routing and quota usage.

        Returns:
            Dict with routing stats
        """
        quota_stats = await self.quota_tracker.get_all_quotas()
        cache_stats = await self.cache.get_stats()

        return {
            "routing_enabled": self.routing_enabled,
            "quotas": quota_stats,
            "cache": cache_stats,
        }


# Global singleton
_model_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Get or create the global ModelRouter instance."""
    global _model_router
    if _model_router is None:
        _model_router = ModelRouter()
    return _model_router
