import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventBase(BaseModel):
    artifact_id: uuid.UUID | None = None
    evidence_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    event_type: str = Field(..., max_length=255)
    source: str = Field(..., max_length=255)
    timestamp: datetime
    timestamp_desc: str | None = Field(None, max_length=255)
    schema_version: int = 1
    data: dict = Field(default_factory=dict)


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
