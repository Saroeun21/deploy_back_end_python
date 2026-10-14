from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DestinationCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255
    )

    country: str = Field(
        min_length=1,
        max_length=255
    )

    country_code: str = Field(
        min_length=2,
        max_length=10
    )

    description: str | None = None

    image: str | None = Field(
        default=None,
        max_length=500
    )

    currency: str | None = Field(
        default=None,
        max_length=10
    )

    language: str | None = Field(
        default=None,
        max_length=100
    )

    timezone: str | None = Field(
        default=None,
        max_length=100
    )

    best_time: str | None = None

    average_daily_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description="Average daily cost in the destination's local currency.",
    )

    average_daily_cost_usd: Decimal | None = Field(
        default=None,
        ge=0,
        description="Curated average daily visitor budget in US dollars.",
    )


class DestinationRead(DestinationCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
