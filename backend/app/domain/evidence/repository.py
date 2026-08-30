from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.case.models import Case
from app.domain.evidence.models import Evidence


class EvidenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, evidence: Evidence) -> Evidence:
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def update(self, evidence: Evidence) -> Evidence:
        self.db.flush()
        return evidence

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        return self.db.get(Evidence, evidence_id)

    def get_by_sha256(self, sha256: str) -> Evidence | None:
        statement = select(Evidence).where(Evidence.sha256 == sha256)
        return self.db.scalar(statement)

    def get_case_by_id(self, case_id: UUID) -> Case | None:
        return self.db.get(Case, case_id)

    def list(self, limit: int, offset: int) -> list[Evidence]:
        statement = (
            select(Evidence)
            .order_by(Evidence.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())
