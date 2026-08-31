from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: str
    entity_type: str
    entity_id: UUID | None
    outcome: str
    details: dict | None
