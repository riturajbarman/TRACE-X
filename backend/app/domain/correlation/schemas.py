"""Pydantic schemas for Phase 8 Correlation API responses."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.detection.schemas import DetectionResponse
from app.domain.event.schemas import EventResponse


class CorrelationGroupResponse(BaseModel):
    """API representation of one correlation cluster."""

    group_id: uuid.UUID
    title: str
    reason: str
    severity: str
    confidence: int
    event_count: int
    detection_count: int
    events: list[EventResponse]
    detections: list[DetectionResponse]

    model_config = ConfigDict(from_attributes=True)


class CorrelationResponse(BaseModel):
    """Top-level response returned by POST /cases/{id}/correlate."""

    case_id: uuid.UUID
    group_count: int
    groups: list[CorrelationGroupResponse]
