from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True
    )

    user_id = Column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    trip_id = Column(
        BigInteger,
        ForeignKey("trips.id"),
        nullable=True,
        index=True
    )

    reminder_id = Column(
        BigInteger,
        ForeignKey("reminders.id"),
        nullable=True,
        index=True
    )

    title = Column(
        String(255),
        nullable=False
    )

    message = Column(
        Text,
        nullable=False
    )

    type = Column(
        String(100),
        nullable=False
    )

    due_date = Column(
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

    is_read = Column(
        Boolean,
        nullable=False,
        default=False
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="notifications"
    )

    trip = relationship(
        "Trip",
        back_populates="notifications"
    )

    reminder = relationship(
        "Reminder",
        back_populates="notifications"
    )
