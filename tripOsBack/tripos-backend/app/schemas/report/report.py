from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    content_type: str | None = Field(
        default=None,
        max_length=100,
        validation_alias=AliasChoices(
            "content_type",
            "target_type",
            "resource_type",
        ),
    )
    content_id: int | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "content_id",
            "target_id",
            "resource_id",
        ),
    )
    reason: str = Field(
        min_length=1,
        max_length=2000,
        validation_alias=AliasChoices("reason", "title", "description", "message"),
    )


class ReportReview(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    resolution: str | None = Field(default=None, max_length=2000)


class ReportRead(BaseModel):
    id: int
    user_id: int
    reporter_email: str
    content_type: str | None
    content_id: int | None
    reason: str
    status: str
    resolution: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
