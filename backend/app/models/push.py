from pydantic import BaseModel, Field


class PushTokenUpsertRequest(BaseModel):
    token: str = Field(..., min_length=10)


class PushTokenDeleteRequest(BaseModel):
    token: str = Field(..., min_length=10)


class PushTokenResponse(BaseModel):
    success: bool

