from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    profile: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )
    avatar_filename: Mapped[str | None] = mapped_column(String(40), nullable=True)
    google_avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    ai_conversations = relationship("AIConversation", back_populates="user")
    ai_extractions = relationship("AIExtraction", back_populates="user")
    content_reports = relationship("ContentReport", back_populates="reporter")
    documents = relationship("Document", back_populates="user")
    expenses = relationship("Expense", back_populates="user")
    expense_splits = relationship("ExpenseSplit", back_populates="user")
    memories = relationship("Memory", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    reminders = relationship("Reminder", back_populates="user")
    saved_places = relationship("SavedPlace", back_populates="user")
    screenshots = relationship("Screenshot", back_populates="user")
    trips = relationship("Trip", back_populates="user")
    trip_memberships = relationship("TripMember", back_populates="user")
    wallet_transactions = relationship("WalletTransaction", back_populates="user")

    @property
    def avatar_url(self) -> str | None:
        if self.google_avatar_url is not None:
            return self.google_avatar_url
        if self.avatar_filename is not None:
            return f"/api/v1/users/avatars/{self.avatar_filename}"
        return None
