from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.connection import get_db


def get_collection(name: str) -> AsyncIOMotorCollection:
    return get_db()[name]
