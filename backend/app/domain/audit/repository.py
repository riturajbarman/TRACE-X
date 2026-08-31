from typing import Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from app.domain.audit.models import AuditEvent

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, event: AuditEvent) -> AuditEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_by_case(self, case_id: UUID) -> Sequence[AuditEvent]:
        """Phase 13 — case-scoped audit history, read-only.

        AuditEvent has no dedicated case_id column: case-level actions
        (CASE_CREATED, CASE_STATUS_CHANGED, AI_QUERY_EXECUTED) are recorded
        with entity_type="case" and entity_id=case_id directly, while
        evidence-level actions (EVIDENCE_INGESTED, etc.) are recorded with
        entity_type="evidence" and entity_id=evidence_id. This query
        reconstructs the case-scoped audit trail by matching both
        provenance patterns explicitly — it never matches on anything
        else, so an event belonging to a different case's evidence can
        never appear here.
        """
        from app.domain.evidence.models import Evidence

        case_evidence_ids = select(Evidence.id).where(Evidence.case_id == case_id)

        stmt = (
            select(AuditEvent)
            .where(
                or_(
                    (AuditEvent.entity_type == "case") & (AuditEvent.entity_id == case_id),
                    (AuditEvent.entity_type == "evidence") & (AuditEvent.entity_id.in_(case_evidence_ids)),
                )
            )
            .order_by(AuditEvent.timestamp.asc())
        )
        return self.db.execute(stmt).scalars().all()
