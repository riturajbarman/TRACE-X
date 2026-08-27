from sqlalchemy.orm import Session
from app.domain.audit.models import AuditEvent

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: AuditEvent) -> AuditEvent:
        self.db.add(event)
        self.db.flush()
        return event
