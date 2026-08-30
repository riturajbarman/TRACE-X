from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.evidence.models import EvidenceStatus


class EvidenceCreate(BaseModel):
    case_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    size_bytes: int = Field(ge=0)
    source: str | None = Field(default=None, max_length=255)


class EvidenceStatusUpdate(BaseModel):
    status: EvidenceStatus
    

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    name: str
    description: str | None
    sha256: str
    size_bytes: int
    source: str | None
    status: EvidenceStatus
    processing_error: str | None
    created_at: datetime
    updated_at: datetime