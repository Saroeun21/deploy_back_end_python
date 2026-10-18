from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ReminderType(str, Enum):
    BOOKING = "booking"
    PAYMENT = "payment"
    DOCUMENT = "document"
    ACTIVITY = "activity"
    PACKING = "packing"
    FLIGHT = "flight"
    CUSTOM = "custom"


class ReminderStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True
    )

    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
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

    due_date = Column(
        DateTime(timezone=True),
        nullable=False
    )

    type = Column(
        SQLEnum(
            ReminderType,
            name="reminder_type"
        ),
        nullable=False
    )

    status = Column(
        SQLEnum(
            ReminderStatus,
            name="reminder_status"
        ),
        nullable=False,
        default=ReminderStatus.PENDING
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    email_sent_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    email_claimed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    trip = relationship(
        "Trip",
        back_populates="reminders"
    )

    user = relationship(
        "User",
        back_populates="reminders"
    )

    notifications = relationship(
        "Notification",
        back_populates="reminder"
    )
