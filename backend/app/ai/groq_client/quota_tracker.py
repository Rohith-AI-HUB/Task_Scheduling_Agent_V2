"""
Quota tracking system for Groq API models.

Tracks RPM (Requests Per Minute), RPD (Requests Per Day),
TPM (Tokens Per Minute), and TPD (Tokens Per Day) for each model.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config import settings
from app.database.collections import get_collection

logger = logging.getLogger(__name__)


class QuotaTracker:
    """
    Track API quota usage per model using Redis (preferred) or MongoDB (fallback).
    """

    def __init__(self, use_redis: bool = True):
        """
        Initialize quota tracker.

        Args:
            use_redis: Whether to use Redis (faster) or MongoDB (fallback)
        """
        self.use_redis = use_redis and redis is not None and settings.redis_url
        self.redis_client: Optional[redis.Redis] = None

        if self.use_redis:
            try:
                self.redis_client = redis.from_url(settings.redis_url, db=settings.redis_db, decode_responses=True)
                logger.info("QuotaTracker using Redis for storage")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Falling back to MongoDB")
                self.use_redis = False

        if not self.use_redis:
            logger.info("QuotaTracker using MongoDB for storage")

    async def track_request(self, *, model: str, tokens: int) -> None:
        """
        Track a single API request.

        Args:
            model: Model identifier
            tokens: Number of tokens used
        """
        now = datetime.utcnow()

        if self.use_redis and self.redis_client:
            await self._track_redis(model=model, tokens=tokens, now=now)
        else:
            await self._track_mongodb(model=model, tokens=tokens, now=now)

    async def _track_redis(self, *, model: str, tokens: int, now: datetime) -> None:
        """Track using Redis with TTL-based expiration."""
        date_str = now.strftime("%Y-%m-%d")
        minute_str = now.strftime("%Y-%m-%d %H:%M")

        # Keys for different metrics
        rpm_key = f"groq:rpm:{model}:{minute_str}"
        rpd_key = f"groq:rpd:{model}:{date_str}"
        tpm_key = f"groq:tpm:{model}:{minute_str}"
        tpd_key = f"groq:tpd:{model}:{date_str}"

        try:
            if self.redis_client:
                # Increment counters
                await self.redis_client.incr(rpm_key)
                await self.redis_client.incr(rpd_key)
                await self.redis_client.incrby(tpm_key, tokens)
                await self.redis_client.incrby(tpd_key, tokens)

                # Set TTL (expire after 2 minutes for per-minute, 25 hours for per-day)
                await self.redis_client.expire(rpm_key, 120)
                await self.redis_client.expire(tpm_key, 120)
                await self.redis_client.expire(rpd_key, 90000)  # 25 hours
                await self.redis_client.expire(tpd_key, 90000)
        except Exception as e:
            logger.error(f"Redis tracking error: {e}")
            # Fallback to MongoDB
            await self._track_mongodb(model=model, tokens=tokens, now=now)

    async def _track_mongodb(self, *, model: str, tokens: int, now: datetime) -> None:
        """Track using MongoDB."""
        try:
            collection = get_collection("groq_quota_tracking")
            date_str = now.strftime("%Y-%m-%d")
            minute_str = now.strftime("%Y-%m-%d %H:%M")

            # Update or insert tracking document
            await collection.update_one(
                {"date": date_str, "model": model},
                {
                    "$inc": {
                        "rpd": 1,
                        "tpd": tokens,
                    },
                    "$set": {
                        "updated_at": now,
                    },
                },
                upsert=True,
            )

            # Track per-minute (separate document with TTL)
            await collection.update_one(
                {"minute": minute_str, "model": model},
                {
                    "$inc": {
                        "rpm": 1,
                        "tpm": tokens,
                    },
                    "$set": {
                        "updated_at": now,
                        "expires_at": now + timedelta(minutes=2),  # TTL
                    },
                },
                upsert=True,
            )
        except Exception as e:
            logger.error(f"MongoDB tracking error: {e}")

    async def get_quota(self, model: str) -> dict:
        """
        Get current quota usage for a model.

        Args:
            model: Model identifier

        Returns:
            Dict with rpm, rpd, tpm, tpd usage
        """
        if self.use_redis and self.redis_client:
            return await self._get_quota_redis(model)
        else:
            return await self._get_quota_mongodb(model)

    async def _get_quota_redis(self, model: str) -> dict:
        """Get quota from Redis."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        minute_str = now.strftime("%Y-%m-%d %H:%M")

        rpm_key = f"groq:rpm:{model}:{minute_str}"
        rpd_key = f"groq:rpd:{model}:{date_str}"
        tpm_key = f"groq:tpm:{model}:{minute_str}"
        tpd_key = f"groq:tpd:{model}:{date_str}"

        try:
            if self.redis_client:
                rpm = await self.redis_client.get(rpm_key)
                rpd = await self.redis_client.get(rpd_key)
                tpm = await self.redis_client.get(tpm_key)
                tpd = await self.redis_client.get(tpd_key)

                return {
                    "rpm": int(rpm) if rpm else 0,
                    "rpd": int(rpd) if rpd else 0,
                    "tpm": int(tpm) if tpm else 0,
                    "tpd": int(tpd) if tpd else 0,
                }
        except Exception as e:
            logger.error(f"Redis quota fetch error: {e}")

        return {"rpm": 0, "rpd": 0, "tpm": 0, "tpd": 0}

    async def _get_quota_mongodb(self, model: str) -> dict:
        """Get quota from MongoDB."""
        try:
            collection = get_collection("groq_quota_tracking")
            from datetime import timezone
            now = datetime.now(timezone.utc)
            date_str = now.strftime("%Y-%m-%d")
            minute_str = now.strftime("%Y-%m-%d %H:%M")

            # Get daily stats
            daily_doc = await collection.find_one({"date": date_str, "model": model})
            # Get minute stats
            minute_doc = await collection.find_one({"minute": minute_str, "model": model})

            return {
                "rpm": int(minute_doc.get("rpm", 0)) if minute_doc else 0,
                "rpd": int(daily_doc.get("rpd", 0)) if daily_doc else 0,
                "tpm": int(minute_doc.get("tpm", 0)) if minute_doc else 0,
                "tpd": int(daily_doc.get("tpd", 0)) if daily_doc else 0,
            }
        except Exception as e:
            logger.error(f"MongoDB quota fetch error: {e}")
            return {"rpm": 0, "rpd": 0, "tpm": 0, "tpd": 0}

    async def check_quota_available(self, model: str, estimated_tokens: int = 1000) -> tuple[bool, Optional[str]]:
        """
        Check if quota is available for a request.

        Args:
            model: Model identifier
            estimated_tokens: Estimated tokens for the request

        Returns:
            Tuple of (available, reason_if_not_available)
        """
        from app.ai.groq_client.client import GroqClient

        quota = await self.get_quota(model)
        limits = GroqClient.RATE_LIMITS.get(model, {})

        # Check RPM
        if quota["rpm"] >= limits.get("rpm", 30):
            return False, f"RPM limit reached ({quota['rpm']}/{limits['rpm']})"

        # Check RPD (critical for Scout!)
        if quota["rpd"] >= limits.get("rpd", 1000):
            return False, f"RPD limit reached ({quota['rpd']}/{limits['rpd']})"

        # Check TPM
        if quota["tpm"] + estimated_tokens > limits.get("tpm", 6000):
            return False, f"TPM limit would be exceeded ({quota['tpm'] + estimated_tokens}/{limits['tpm']})"

        # Check TPD
        if quota["tpd"] + estimated_tokens > limits.get("tpd", 600000):
            return False, f"TPD limit would be exceeded ({quota['tpd'] + estimated_tokens}/{limits['tpd']})"

        return True, None

    async def get_all_quotas(self) -> dict[str, dict]:
        """
        Get quota usage for all models.

        Returns:
            Dict mapping model names to their quota stats
        """
        from app.ai.groq_client.client import GroqClient

        result = {}
        for model in GroqClient.RATE_LIMITS.keys():
            quota = await self.get_quota(model)
            limits = GroqClient.RATE_LIMITS[model]
            result[model] = {
                "usage": quota,
                "limits": limits,
                "percentage": {
                    "rpm": (quota["rpm"] / limits["rpm"] * 100) if limits["rpm"] > 0 else 0,
                    "rpd": (quota["rpd"] / limits["rpd"] * 100) if limits["rpd"] > 0 else 0,
                },
            }
        return result

    async def close(self) -> None:
        """Close connections."""
        if self.redis_client:
            await self.redis_client.close()


# Global singleton
_quota_tracker: Optional[QuotaTracker] = None


def get_quota_tracker() -> QuotaTracker:
    """Get or create the global quota tracker instance."""
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = QuotaTracker()
    return _quota_tracker
