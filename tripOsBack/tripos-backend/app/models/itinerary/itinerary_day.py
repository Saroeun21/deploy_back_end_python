from datetime import date

from sqlalchemy import BigInteger, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ItineraryDay(Base):
    __tablename__ = "itinerary_days"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True,
    )

    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id"),
        nullable=False,
        index=True
    )

    day_number = Column(
        Integer,
        nullable=False
    )

    date = Column(
        Date,
        nullable=False
    )

    title = Column(
        String(255),
        nullable=True
    )

    notes = Column(
        Text,
        nullable=True
    )

    trip = relationship(
        "Trip",
        back_populates="itinerary_days"
    )

    items = relationship(
        "ItineraryItem",
        back_populates="itinerary_day"
    )
