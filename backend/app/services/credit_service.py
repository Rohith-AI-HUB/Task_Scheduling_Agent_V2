"""
Credit Service
Manages daily AI chat credits for users.
Students: 25 messages/day
Teachers: 50 messages/day
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


# Credit limits by role
CREDIT_LIMITS = {
    "student": 25,
    "teacher": 50
}


class CreditService:
    """Service for managing AI chat credits"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.ai_credits

    async def ensure_indexes(self):
        """Create necessary database indexes"""
        await self.collection.create_index("user_uid", unique=True)
        await self.collection.create_index("last_reset")

    async def get_credits(self, user_uid: str, role: str) -> dict:
        """
        Get current credit status for a user.
        Creates record if doesn't exist.

        Returns:
            dict with credits_remaining, credits_limit, resets_at
        """
        # Get or create credit record
        record = await self.collection.find_one({"user_uid": user_uid})

        now = datetime.utcnow()
        credit_limit = CREDIT_LIMITS.get(role, CREDIT_LIMITS["student"])

        # Calculate next reset time (midnight UTC)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        if record is None:
            # Create new record
            record = {
                "user_uid": user_uid,
                "role": role,
                "credits_used": 0,
                "credits_limit": credit_limit,
                "last_reset": now,
                "created_at": now,
                "updated_at": now
            }
            await self.collection.insert_one(record)
        else:
            # Check if we need to reset (new day)
            last_reset = record.get("last_reset", now)
            last_reset_date = last_reset.replace(hour=0, minute=0, second=0, microsecond=0)
            today = now.replace(hour=0, minute=0, second=0, microsecond=0)

            if last_reset_date < today:
                # New day - reset credits
                await self.collection.update_one(
                    {"user_uid": user_uid},
                    {
                        "$set": {
                            "credits_used": 0,
                            "last_reset": now,
                            "updated_at": now,
                            "credits_limit": credit_limit  # Update in case role changed
                        }
                    }
                )
                record["credits_used"] = 0
                record["credits_limit"] = credit_limit

        credits_remaining = max(0, record.get("credits_limit", credit_limit) - record.get("credits_used", 0))

        return {
            "credits_remaining": credits_remaining,
            "credits_limit": record.get("credits_limit", credit_limit),
            "credits_used": record.get("credits_used", 0),
            "resets_at": tomorrow.isoformat() + "Z"
        }

    async def use_credit(self, user_uid: str, role: str) -> dict:
        """
        Use one credit for a chat message.

        Returns:
            dict with success, credits_remaining, error (if any)
        """
        # Get current status first
        status = await self.get_credits(user_uid, role)

        if status["credits_remaining"] <= 0:
            return {
                "success": False,
                "credits_remaining": 0,
                "error": "Daily message limit reached. Credits reset at midnight UTC."
            }

        # Decrement credit
        result = await self.collection.update_one(
            {"user_uid": user_uid},
            {
                "$inc": {"credits_used": 1},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.modified_count == 0:
            return {
                "success": False,
                "credits_remaining": status["credits_remaining"],
                "error": "Failed to update credits"
            }

        return {
            "success": True,
            "credits_remaining": status["credits_remaining"] - 1,
            "credits_limit": status["credits_limit"],
            "error": None
        }

    async def reset_credits(self, user_uid: str, role: str = None) -> dict:
        """
        Manually reset credits for a user (admin function).

        Args:
            user_uid: User to reset
            role: Optional role to update credit limit

        Returns:
            dict with success status
        """
        now = datetime.utcnow()

        update_data = {
            "credits_used": 0,
            "last_reset": now,
            "updated_at": now
        }

        if role:
            update_data["credits_limit"] = CREDIT_LIMITS.get(role, CREDIT_LIMITS["student"])
            update_data["role"] = role

        result = await self.collection.update_one(
            {"user_uid": user_uid},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            # User doesn't have a credit record yet - create one
            credit_limit = CREDIT_LIMITS.get(role or "student", CREDIT_LIMITS["student"])
            await self.collection.insert_one({
                "user_uid": user_uid,
                "role": role or "student",
                "credits_used": 0,
                "credits_limit": credit_limit,
                "last_reset": now,
                "created_at": now,
                "updated_at": now
            })

        return {"success": True, "message": f"Credits reset for user {user_uid}"}

    async def get_all_credits_admin(self, skip: int = 0, limit: int = 50) -> dict:
        """
        Get all credit records (admin function).

        Returns:
            dict with records list and total count
        """
        total = await self.collection.count_documents({})

        cursor = self.collection.find({}).skip(skip).limit(limit).sort("updated_at", -1)
        records = await cursor.to_list(length=limit)

        # Convert ObjectId to string
        for record in records:
            record["_id"] = str(record["_id"])

        return {
            "records": records,
            "total": total,
            "skip": skip,
            "limit": limit
        }


# Factory function to create service with database
def get_credit_service(db: AsyncIOMotorDatabase) -> CreditService:
    """Get credit service instance with database connection"""
    return CreditService(db)
