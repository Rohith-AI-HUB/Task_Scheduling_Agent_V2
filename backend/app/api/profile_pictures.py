from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.profile_pictures import iter_public_picture

router = APIRouter()


@router.get("/public/{public_id}")
async def get_public_profile_picture(public_id: str):
    content_type, body_iter = await iter_public_picture(public_id)
    return StreamingResponse(
        body_iter,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/health")
async def health():
    return {"status": "ok", "service": "profile_pictures"}

