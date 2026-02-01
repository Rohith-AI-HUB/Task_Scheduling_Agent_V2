from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from firebase_admin import messaging

from app.database.collections import get_collection


def _now() -> datetime:
    return datetime.utcnow()


async def upsert_push_token(user_uid: str, token: str, metadata: Optional[dict[str, Any]] = None) -> None:
    col = get_collection("push_tokens")
    now = _now()
    doc: dict[str, Any] = {
        "user_uid": user_uid,
        "token": token,
        "updated_at": now,
    }
    if metadata:
        doc["metadata"] = metadata
    await col.update_one(
        {"user_uid": user_uid, "token": token},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )


async def delete_push_token(user_uid: str, token: str) -> None:
    col = get_collection("push_tokens")
    await col.delete_one({"user_uid": user_uid, "token": token})


async def send_push_to_user(user_uid: str, title: str, body: str, url: str) -> dict[str, Any]:
    col = get_collection("push_tokens")
    docs = await col.find({"user_uid": user_uid}).to_list(length=200)
    tokens = [d.get("token") for d in docs if isinstance(d.get("token"), str) and d.get("token")]
    if not tokens:
        return {"success": True, "sent": 0, "failed": 0}

    message = messaging.MulticastMessage(
        tokens=tokens,
        data={"url": url},
        notification=messaging.Notification(title=title, body=body),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(title=title, body=body),
            fcm_options=messaging.WebpushFCMOptions(link=url),
        ),
    )

    batch = messaging.send_each_for_multicast(message)

    invalid_tokens: list[str] = []
    for idx, resp in enumerate(batch.responses):
        if resp.success:
            continue
        err = resp.exception
        msg = str(err or "")
        if "registration-token-not-registered" in msg or "Requested entity was not found" in msg:
            invalid_tokens.append(tokens[idx])

    if invalid_tokens:
        await col.delete_many({"user_uid": user_uid, "token": {"$in": invalid_tokens}})

    return {"success": True, "sent": batch.success_count, "failed": batch.failure_count}

