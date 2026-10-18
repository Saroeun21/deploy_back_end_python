from datetime import time
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ItineraryItemType(str, Enum):
    ACTIVITY = "activity"
    FOOD = "food"
    TRANSPORT = "transport"
    HOTEL = "hotel"
    FREE_TIME = "free_time"
    OTHER = "other"


class ItineraryItemStatus(str, Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True,
    )

    itinerary_day_id = Column(
        BigInteger,
        ForeignKey("itinerary_days.id"),
        nullable=False,
        index=True
    )

    place_id = Column(
        BigInteger,
        ForeignKey("places.id"),
        nullable=True,
        index=True
    )

    title = Column(
        String(255),
        nullable=False
    )

    description = Column(
        Text,
        nullable=True
    )

    start_time = Column(
        Time,
        nullable=True
    )

    end_time = Column(
        Time,
        nullable=True
    )

    estimated_cost = Column(
        Numeric(12, 2),
        nullable=True
    )

    type = Column(
        SQLEnum(
            ItineraryItemType,
            name="itinerary_item_type"
        ),
        nullable=False
    )

    order_index = Column(
        Integer,
        nullable=False
    )

    status = Column(
        SQLEnum(
            ItineraryItemStatus,
            name="itinerary_item_status"
        ),
        nullable=False,
        default=ItineraryItemStatus.PLANNED
    )

    itinerary_day = relationship(
        "ItineraryDay",
        back_populates="items"
    )

    place = relationship(
        "Place",
        back_populates="itinerary_items"
    )
