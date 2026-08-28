import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IOCBase(BaseModel):
    event_id: uuid.UUID
    evidence_id: uuid.UUID | None = None
    case_id: uuid.UUID
    ioc_type: str
    value: str
    severity: str
    confidence: int

class IOCResponse(IOCBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DetectionBase(BaseModel):
    case_id: uuid.UUID
    event_id: uuid.UUID
    detection_type: str
    rule_id: str | None = None
    rule_version: str | None = None
    severity: str
    confidence: int

class DetectionResponse(DetectionBase):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class IncidentBase(BaseModel):
    case_id: uuid.UUID
    title: str
    severity: str
    confidence: int
    status: str

class IncidentResponse(IncidentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RiskSignal(BaseModel):
    source: str
    description: str
    score: int
    detection_id: uuid.UUID | None = None
    ioc_id: uuid.UUID | None = None

class RiskResponse(BaseModel):
    case_id: uuid.UUID
    risk_score: int
    risk_level: str
    contributing_signals: list[RiskSignal]
    explanation: str
