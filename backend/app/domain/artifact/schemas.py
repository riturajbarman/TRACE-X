"""Pydantic response schemas for the artifact extraction API.

These are API boundary types only.  Persistence is deferred to Phase 4.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.artifact.models import ExtractionStatus


class ArtifactResultResponse(BaseModel):
    """Response schema for a single artifact extraction result.

    Mirrors the fields of :class:`~app.domain.artifact.models.ArtifactResult`
    exactly so that no invented fields appear in the API.
    """

    artifact_id: UUID
    evidence_id: UUID | None
    artifact_type: str
    source_location: str
    parser_name: str
    parser_version: str
    extraction_status: ExtractionStatus
    extracted_at: datetime
    data: list[dict]
    record_count: int
    error_message: str | None
