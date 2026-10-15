from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ResourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    data: dict = Field(default_factory=dict)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    balance: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    category: str | None = None
    spent_on: date | None = None


class ResourceRead(ResourceCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
