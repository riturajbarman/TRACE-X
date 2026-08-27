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
            .order_by(Evidence.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        return list(self.db.scalars(statement).all())
