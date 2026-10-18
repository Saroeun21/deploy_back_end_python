from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationCreate(BaseModel):
    trip_id: int | None = None
    reminder_id: int | None = None
    due_date: datetime | None = None

    title: str = Field(
        min_length=1,
        max_length=255
    )

    message: str = Field(
        min_length=1
    )

    type: str = Field(
        min_length=1,
        max_length=100
    )

    is_read: bool = False

    @field_validator("due_date")
    @classmethod
    def due_date_is_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class NotificationUpdate(BaseModel):
    due_date: datetime | None = None

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255
    )

    message: str | None = Field(
        default=None,
        min_length=1
    )

    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    is_read: bool | None = None

    @field_validator("due_date")
    @classmethod
    def due_date_is_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class NotificationRead(NotificationCreate):
    id: int
    user_id: int
    created_at: datetime
    email_sent_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
