"""
Phase 12 — external knowledge citation schema.

A KnowledgeCitation identifies a piece of EXTERNAL cybersecurity knowledge
(e.g. a MITRE ATT&CK technique) that grounded an "external_knowledge"
AssistantClaim. It is structurally unrelated to case-object provenance
(AssistantClaim.refs) — the two are never allowed to mix (see
app.domain.assistant.grounding).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class KnowledgeCitation(BaseModel):
    source_id: str
    source_type: str
    document_id: str
    version: str
    title: str
    reference: str
    retrieval_method: Literal["deterministic_lookup"] = "deterministic_lookup"
