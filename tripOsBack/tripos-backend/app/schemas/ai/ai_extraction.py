from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai.ai_extraction import AIExtractionStatus


class AIExtractionCreate(BaseModel):
    user_id: int
    trip_id: int

    screenshot_id: int | None = None
    document_id: int | None = None

    type: str = Field(
        min_length=1,
        max_length=100
    )

    extracted_data: dict[str, Any] = Field(
        default_factory=dict
    )

    status: AIExtractionStatus = AIExtractionStatus.PENDING
    requires_human_review: bool = False


class AIExtractionUpdate(BaseModel):
    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    extracted_data: dict[str, Any] | None = None

    status: AIExtractionStatus | None = None
    requires_human_review: bool | None = None


class AIExtractionRead(AIExtractionCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
