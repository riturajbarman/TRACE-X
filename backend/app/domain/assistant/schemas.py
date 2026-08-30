"""
Phase 11 — AI Investigation Assistant API schemas.

Deliberately structurally separate from RiskResponse / GraphResponse /
the report JSON — an AssistantQueryResponse can never be mistaken for a
deterministic TRACE-X finding. Every claim is explicitly typed as
observed / inference / recommendation (see app.domain.assistant.grounding
for how that type is enforced).
"""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

ClaimType = Literal["observed", "inference", "recommendation"]
GroundingStatus = Literal["ok", "partial", "unavailable"]


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class AssistantClaim(BaseModel):
    text: str
    type: ClaimType
    refs: list[str] = Field(default_factory=list)


class AssistantQueryResponse(BaseModel):
    case_id: uuid.UUID
    answer: str
    claims: list[AssistantClaim]
    grounding_status: GroundingStatus
    provider: str
    model: str | None = None
    warnings: list[str] = Field(default_factory=list)
