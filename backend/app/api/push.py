from fastapi import APIRouter, Depends

from app.models.push import PushTokenDeleteRequest, PushTokenResponse, PushTokenUpsertRequest
from app.services.push_notification_service import delete_push_token, upsert_push_token
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.post("/tokens", response_model=PushTokenResponse)
async def register_push_token(
    payload: PushTokenUpsertRequest,
    current_user: dict = Depends(get_current_user),
):
    await upsert_push_token(current_user["uid"], payload.token)
    return PushTokenResponse(success=True)


@router.delete("/tokens", response_model=PushTokenResponse)
async def unregister_push_token(
    payload: PushTokenDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    await delete_push_token(current_user["uid"], payload.token)
    return PushTokenResponse(success=True)

