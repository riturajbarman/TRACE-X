from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.case.models import Case, CaseStatus
from app.domain.case.repository import CaseRepository
from app.domain.audit.service import AuditService


class CaseService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CaseRepository(db)
        self.audit_service = AuditService(db)

    def create(
        self,
        title: str,
        description: str | None,
        created_by: str | None,
    ) -> Case:
        try:
            case = Case(
                title=title,
                description=description,
                created_by=created_by,
                status=CaseStatus.OPEN,
            )

            created_case = self.repository.create(case)

            self.audit_service.record_event(
                action="CASE_CREATED",
                entity_type="case",
                entity_id=created_case.id,
                outcome="SUCCESS",
                details={"title": created_case.title}
            )

            self.db.commit()
            self.db.refresh(created_case)
            return created_case
        except Exception:
            self.db.rollback()
            raise

    def get_by_id(self, case_id: UUID) -> Case | None:
        return self.repository.get_by_id(case_id)

    def list(
        self,
        limit: int,
        offset: int,
    ) -> list[Case]:
        return self.repository.list(
            limit=limit,
            offset=offset,
        )

    def update_status(
        self,
        case_id: UUID,
        new_status: CaseStatus,
    ) -> Case | None:
        case = self.repository.get_by_id(case_id)

        if case is None:
            return None

        allowed_transitions = {
            CaseStatus.OPEN: {CaseStatus.CLOSED},
            CaseStatus.CLOSED: {CaseStatus.OPEN},
        }

        if new_status not in allowed_transitions[case.status]:
            raise ValueError(
                f"Invalid case status transition: "
                f"{case.status} -> {new_status}"
            )

        old_status = case.status
        case.status = new_status

        try:
            updated_case = self.repository.update(case)

            self.audit_service.record_event(
                action="CASE_STATUS_CHANGED",
                entity_type="case",
                entity_id=updated_case.id,
                outcome="SUCCESS",
                details={"old_status": old_status, "new_status": new_status}
            )

            self.db.commit()
            self.db.refresh(updated_case)
            return updated_case
        except Exception:
            self.db.rollback()
            raise

    def list_evidence(
        self,
        case_id: UUID,
        limit: int,
        offset: int,
    ):
        return self.repository.list_evidence_by_case(
            case_id=case_id,
            limit=limit,
            offset=offset,
        )
