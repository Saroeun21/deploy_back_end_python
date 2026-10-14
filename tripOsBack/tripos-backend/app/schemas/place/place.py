from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.place.place import PlaceStatus


class PlaceCreate(BaseModel):
    destination_id: int

    name: str = Field(
        min_length=1,
        max_length=255
    )

    category: str = Field(
        min_length=1,
        max_length=100
    )

    description: str | None = None

    image: str | None = Field(
        default=None,
        max_length=500
    )

    address: str | None = None

    latitude: Decimal | None = None

    longitude: Decimal | None = None

    estimated_cost: Decimal | None = Field(
        default=None,
        ge=0,
        description="Admission fee in the destination's local currency; zero means no admission charge.",
    )

    admission_fee_usd: Decimal | None = Field(
        default=None,
        ge=0,
        description="Admission fee converted to US dollars.",
    )

    estimated_visit_cost_usd: Decimal | None = Field(
        default=None,
        ge=0,
        description="Estimated total per-person visit spend in US dollars, including admission and typical local extras.",
    )

    opening_time: time | None = None

    closing_time: time | None = None

    best_time_to_visit: str | None = Field(
        default=None,
        max_length=100
    )

    website: str | None = Field(
        default=None,
        max_length=500
    )

    rating: Decimal | None = Field(
        default=None,
        ge=0,
        le=5
    )

    status: PlaceStatus = PlaceStatus.ACTIVE


class PlaceRead(PlaceCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
