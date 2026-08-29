"""
Phase 10 — Investigation Graph Schemas

GraphNode: a typed, provenance-carrying node (event, detection, ioc, incident).
GraphEdge: a directed, labelled relationship between two nodes.
GraphResponse: the full graph for a case.
"""
from __future__ import annotations

import uuid
from typing import Any
from pydantic import BaseModel


class GraphNode(BaseModel):
    """A single node in the investigation graph."""
    id: uuid.UUID
    type: str  # "event" | "detection" | "ioc" | "incident"
    label: str
    evidence_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    timestamp: str | None = None
    severity: str | None = None
    data: dict[str, Any] = {}


class GraphEdge(BaseModel):
    """A directed relationship between two nodes."""
    source: uuid.UUID
    target: uuid.UUID
    relationship: str   # e.g. "TRIGGERED", "PRODUCED", "PART_OF", "SHARES_ENTITY"
    label: str | None = None


class GraphResponse(BaseModel):
    """Full investigation graph for a case."""
    case_id: uuid.UUID
    node_count: int
    edge_count: int
    nodes: list[GraphNode]
    edges: list[GraphEdge]
