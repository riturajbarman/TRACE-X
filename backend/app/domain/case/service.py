from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.case.models import Case, CaseStatus
from app.domain.case.repository import CaseRepository


class CaseService:
    def __init__(self, db: Session):
        self.repository = CaseRepository(db)

    def create(
        self,
        title: str,
        description: str | None,
        created_by: str | None,
    ) -> Case:
        case = Case(
            title=title,
            description=description,
            created_by=created_by,
            status=CaseStatus.OPEN,
        )

        return self.repository.create(case)

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

        if case.status == new_status:
            return case

        case.status = new_status

        return self.repository.update(case)
