from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SavedItemCreate(BaseModel):
    item_type: Literal["destination", "wikipedia"]
    item_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    image: str | None = Field(default=None, max_length=500)
    location: str | None = None
    source_url: str | None = Field(default=None, max_length=500)


class SavedItemRead(SavedItemCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
