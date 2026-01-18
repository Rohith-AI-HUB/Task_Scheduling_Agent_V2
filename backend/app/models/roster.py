from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StudentRosterItem(BaseModel):
    uid: str
    name: Optional[str] = None
    email: Optional[str] = None
    enrolled_at: Optional[datetime] = None

