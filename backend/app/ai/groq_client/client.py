"""
Groq API client wrapper with rate limiting, retries, and error handling.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from groq import AsyncGroq, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """
    Async wrapper for Groq API with built-in retry logic and error handling.
    """

    # Model identifiers
    MODEL_8B = "llama-3.1-8b-instant"
    MODEL_SCOUT = "llama-4-scout-17b-16e-instruct"
    MODEL_GUARD_OUTPUT = "llama-guard-4-12b"
    MODEL_GUARD_PROMPT = "llama-prompt-guard-2-86m"

    # Rate limits per model (from GroqAPI.md)
    RATE_LIMITS = {
        MODEL_8B: {"rpm": 30, "rpd": 14400, "tpm": 6000, "tpd": 600000},
        MODEL_SCOUT: {"rpm": 30, "rpd": 1000, "tpm": 30000, "tpd": 3000000},
        MODEL_GUARD_OUTPUT: {"rpm": 30, "rpd": 14400, "tpm": 15000, "tpd": 1500000},
        MODEL_GUARD_PROMPT: {"rpm": 30, "rpd": 14400, "tpm": 15000, "tpd": 1500000},
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key (defaults to settings.groq_api_key)
        """
        self.api_key = api_key or settings.groq_api_key
        if not self.api_key:
            raise ValueError("Groq API key not configured. Set GROQ_API_KEY environment variable.")

        self.client = AsyncGroq(api_key=self.api_key)
        self._request_counts: dict[str, int] = {}

    async def complete(
        self,
        *,
        prompt: str,
        model: str = MODEL_8B,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_message: Optional[str] = None,
        json_mode: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> str:
        """
        Generate completion using Groq API with retry logic.

        Args:
            prompt: The input prompt
            model: Model to use (defaults to 8B)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            system_message: Optional system message
            json_mode: Whether to request JSON output
            retry_count: Number of retries on rate limit
            retry_delay: Initial delay between retries (exponential backoff)

        Returns:
            Generated text response

        Raises:
            ValueError: If model is invalid
            RuntimeError: If API call fails after retries
        """
        if model not in self.RATE_LIMITS:
            raise ValueError(f"Invalid model: {model}. Must be one of {list(self.RATE_LIMITS.keys())}")

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(retry_count):
            try:
                response_format = {"type": "json_object"} if json_mode else None

                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_format=response_format,
                )

                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("Empty response from Groq API")

                # Track successful request
                self._request_counts[model] = self._request_counts.get(model, 0) + 1

                logger.info(
                    f"Groq API success: model={model}, tokens={response.usage.total_tokens if response.usage else 'unknown'}"
                )
                return content.strip()

            except RateLimitError as e:
                if attempt < retry_count - 1:
                    delay = retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit for {model}. Retrying in {delay}s (attempt {attempt + 1}/{retry_count})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Rate limit exceeded for {model} after {retry_count} attempts")
                    raise RuntimeError(f"Rate limit exceeded for {model}: {str(e)}") from e

            except Exception as e:
                if attempt < retry_count - 1:
                    delay = retry_delay * (2**attempt)
                    logger.warning(
                        f"Groq API error: {str(e)[:100]}. Retrying in {delay}s (attempt {attempt + 1}/{retry_count})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Groq API failed after {retry_count} attempts: {str(e)[:200]}")
                    raise RuntimeError(f"Groq API call failed: {str(e)}") from e

        raise RuntimeError(f"Groq API call failed after {retry_count} attempts")

    async def complete_with_fallback(
        self,
        *,
        prompt: str,
        preferred_model: str = MODEL_8B,
        fallback_model: str = MODEL_8B,
        **kwargs: Any,
    ) -> tuple[str, str]:
        """
        Try completing with preferred model, fallback to another if rate limited.

        Args:
            prompt: The input prompt
            preferred_model: First choice model
            fallback_model: Fallback if preferred fails
            **kwargs: Additional arguments for complete()

        Returns:
            Tuple of (response, model_used)
        """
        try:
            response = await self.complete(prompt=prompt, model=preferred_model, **kwargs)
            return response, preferred_model
        except RuntimeError as e:
            if "rate limit" in str(e).lower():
                logger.info(f"Falling back from {preferred_model} to {fallback_model}")
                response = await self.complete(prompt=prompt, model=fallback_model, **kwargs)
                return response, fallback_model
            raise

    def get_request_count(self, model: str) -> int:
        """Get number of requests made to a specific model."""
        return self._request_counts.get(model, 0)

    def reset_counts(self) -> None:
        """Reset request counters (useful for testing)."""
        self._request_counts.clear()


# Global singleton instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """
    Get or create the global Groq client instance.

    Returns:
        GroqClient singleton instance
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
