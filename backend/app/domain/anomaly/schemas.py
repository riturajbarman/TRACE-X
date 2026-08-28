from pydantic import BaseModel
from typing import List
from uuid import UUID

class AnomalyFinding(BaseModel):
    event_id: UUID
    score: float
    explanation: str

class AnomalyScanResponse(BaseModel):
    case_id: UUID
    model_version: str
    anomaly_count: int
    findings: List[AnomalyFinding]
