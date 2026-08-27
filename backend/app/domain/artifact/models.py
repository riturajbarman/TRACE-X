"""Artifact extraction data models.

These are plain Python dataclasses, not SQLAlchemy models.
Database persistence for Artifacts is deferred to Phase 4 (Event Store).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ExtractionStatus(str, Enum):
    """Status of an artifact extraction operation."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class ArtifactResult:
    """Structured result from a single parser execution.

    Every ArtifactResult preserves full provenance back to its
    source evidence.
    """
    artifact_id: UUID = field(default_factory=uuid4)
    evidence_id: UUID | None = None
    artifact_type: str = ""
    source_location: str = ""
    parser_name: str = ""
    parser_version: str = ""
    extraction_status: ExtractionStatus = ExtractionStatus.FAILED
    extracted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data: list[dict] = field(default_factory=list)
    record_count: int = 0
    error_message: str | None = None
