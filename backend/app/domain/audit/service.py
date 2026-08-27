from uuid import UUID
from sqlalchemy.orm import Session
from app.domain.audit.models import AuditEvent
from app.domain.audit.repository import AuditRepository


class AuditService:
    def __init__(self, db: Session):
        self.repository = AuditRepository(db)

    def record_event(
        self,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        outcome: str,
        details: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            details=details,
        )
        return self.repository.create(event)
