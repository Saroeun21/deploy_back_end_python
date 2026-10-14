from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.place.place import PlaceRead


class SavedPlaceCreate(BaseModel):
    place_id: int


class SavedPlaceRead(SavedPlaceCreate):
    id: int
    user_id: int
    created_at: datetime
    place: PlaceRead | None = None

    model_config = ConfigDict(from_attributes=True)
