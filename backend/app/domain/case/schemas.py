from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.case.models import CaseStatus


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    created_by: str | None = Field(default=None, max_length=255)


class CaseStatusUpdate(BaseModel):
    status: CaseStatus


class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: CaseStatus
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class CaseSummaryResponse(CaseResponse):
    evidence_count: int
    event_count: int
    # Phase 13 — Investigator Dashboard: existing counts, read-only,
    # computed from already-persisted data (no new tables/columns).
    detection_count: int
    ioc_count: int
    incident_count: int
    failed_evidence_count: int