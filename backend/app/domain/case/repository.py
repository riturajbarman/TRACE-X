from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.case.models import Case


class CaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, case: Case) -> Case:
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def update(self, case: Case) -> Case:
        self.db.commit()
        self.db.refresh(case)
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
