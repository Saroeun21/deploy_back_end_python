from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )

    country: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    country_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True
    )

    language: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    timezone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    best_time: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    average_daily_cost: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 2),
        nullable=True
    )

    average_daily_cost_usd: Mapped[Decimal | None] = mapped_column(
        DECIMAL(10, 2),
        nullable=True
    )

    data: Mapped[dict] = mapped_column(
        JSON,
        default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    trips = relationship(
        "Trip",
        back_populates="destination"
    )

    places = relationship(
        "Place",
        back_populates="destination"
    )