from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.case.models import Case


class CaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, case: Case) -> Case:
        self.db.add(case)
        self.db.flush()
        return case

    def update(self, case: Case) -> Case:
        self.db.flush()
        return case

    def get_by_id(self, case_id: UUID) -> Case | None:
        return self.db.get(Case, case_id)

    def list(
        self,
        limit: int,
        offset: int,
    ) -> list[Case]:
        statement = (
            select(Case)
            .order_by(Case.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(statement).all())

    def get_summary_counts(self, case_id: UUID) -> dict:
        from sqlalchemy import func
        from app.domain.evidence.models import Evidence, EvidenceStatus
        from app.domain.event.models import Event
        from app.domain.detection.models import IOC, Detection, Incident

        evidence_count = self.db.scalar(
            select(func.count(Evidence.id)).where(Evidence.case_id == case_id)
        ) or 0

        event_count = self.db.scalar(
            select(func.count(Event.id)).where(Event.case_id == case_id)
        ) or 0

        detection_count = self.db.scalar(
            select(func.count(Detection.id)).where(Detection.case_id == case_id)
        ) or 0

        ioc_count = self.db.scalar(
            select(func.count(IOC.id)).where(IOC.case_id == case_id)
        ) or 0

        incident_count = self.db.scalar(
            select(func.count(Incident.id)).where(Incident.case_id == case_id)
        ) or 0

        # "Processing failures" (Phase 13, ROADMAP §16 DoD): evidence whose
        # ingestion/processing did not complete successfully. Reuses the
        # existing Evidence.status field — no new column, no migration.
        failed_evidence_count = self.db.scalar(
            select(func.count(Evidence.id)).where(
                Evidence.case_id == case_id,
                Evidence.status == EvidenceStatus.FAILED,
            )
        ) or 0

        return {
            "evidence_count": evidence_count,
            "event_count": event_count,
            "detection_count": detection_count,
            "ioc_count": ioc_count,
            "incident_count": incident_count,
            "failed_evidence_count": failed_evidence_count,
        }

    def list_evidence_by_case(
        self,
        case_id: UUID,
        limit: int,
        offset: int,
    ):
        from app.domain.evidence.models import Evidence
        statement = (
            select(Evidence)
            .where(Evidence.case_id == case_id)
            .order_by(Evidence.created_at.desc(), Evidence.id.asc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(statement).all())
