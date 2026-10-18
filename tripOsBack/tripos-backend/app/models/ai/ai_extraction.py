from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    false,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AIExtractionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AIExtraction(Base):
    __tablename__ = "ai_extractions"

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
        nullable=False,
        index=True
    )

    screenshot_id = Column(
        BigInteger,
        ForeignKey("screenshots.id"),
        nullable=True,
        index=True
    )

    document_id = Column(
        BigInteger,
        ForeignKey("documents.id"),
        nullable=True,
        index=True
    )

    type = Column(
        String(100),
        nullable=False
    )

    extracted_data = Column(
        JSON,
        nullable=False
    )

    status = Column(
        SQLEnum(
            AIExtractionStatus,
            name="ai_extraction_status"
        ),
        nullable=False
    )

    requires_human_review = Column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship(
        "User",
        back_populates="ai_extractions"
    )

    trip = relationship(
        "Trip",
        back_populates="ai_extractions"
    )

    screenshot = relationship(
        "Screenshot",
        back_populates="ai_extractions"
    )

    document = relationship(
        "Document",
        back_populates="ai_extractions"
    )
