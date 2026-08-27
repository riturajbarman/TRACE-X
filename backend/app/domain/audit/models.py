from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    action: Mapped[str] = mapped_column(String(255), nullable=False)
    
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    
    outcome: Mapped[str] = mapped_column(String(255), nullable=False)
    
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
