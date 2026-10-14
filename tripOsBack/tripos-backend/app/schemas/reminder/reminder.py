from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.reminder.reminder import ReminderType, ReminderStatus


def normalize_due_date(value: datetime) -> datetime:
    # SQLite may drop the UTC offset when storing timezone-aware datetimes.
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ReminderCreate(BaseModel):
    trip_id: int

    title: str = Field(
        min_length=1,
        max_length=255
    )

    description: str | None = None

    due_date: datetime

    type: ReminderType

    status: ReminderStatus = ReminderStatus.PENDING

    @field_validator("due_date")
    @classmethod
    def due_date_is_utc(cls, value: datetime) -> datetime:
        return normalize_due_date(value)


class ReminderUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255
    )

    description: str | None = None

    due_date: datetime | None = None

    type: ReminderType | None = None

    status: ReminderStatus | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_is_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_due_date(value) if value is not None else None


class ReminderRead(ReminderCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
