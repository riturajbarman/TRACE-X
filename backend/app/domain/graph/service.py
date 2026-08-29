"""
Phase 10 — Investigation Graph Service

Builds the investigation graph for a given case by:

1. Collecting Events, Detections, IOCs, and Incidents from existing tables.
2. Deriving edges from:
   a. FK relationships (Event→Detection, Event→IOC, etc.)
   b. M2M association tables (incident_events, incident_detections)
   c. Shared-entity JSONB values (same ENTITY_KEYS logic as correlation engine)

Rules:
- Every node carries evidence_id for provenance.
- Edges are only created from FK data or validated ENTITY_KEYS values — never
  from free-text similarity or inference.
- Shared-entity edges are deduplicated: if N events share the same entity
  value, the edge is Event→IOC or represented as a group edge, not N² pairs.
- No graph database is required. All data is already in PostgreSQL.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.detection.models import (
    Detection,
    IOC,
    Incident,
    incident_events,
    incident_detections,
)
from app.domain.event.models import Event
from app.domain.graph.schemas import GraphEdge, GraphNode, GraphResponse

# Shared with correlation engine — MUST stay in sync.
ENTITY_KEYS: list[str] = [
    "process_name",
    "process_id",
    "sha256",
    "md5",
    "ip",
    "dst_ip",
    "src_ip",
    "domain",
    "path",
    "filename",
    "registry_key",
    "user",
]

MIN_ENTITY_VALUE_LEN: int = 2

# Guard against combinatorial explosion: max shared-entity edges per case.
MAX_SHARED_ENTITY_EDGES: int = 2_000


class GraphService:
    """Builds the investigation graph for a case."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_graph(
        self,
        case_id: uuid.UUID,
        node_types: list[str] | None = None,
        include_shared_entities: bool = True,
    ) -> GraphResponse:
        """
        Build and return the full investigation graph for case_id.

        node_types: restrict nodes to these types (event, detection, ioc, incident).
                    None means all types.
        include_shared_entities: whether to add JSONB shared-entity edges.
        """
        allowed = set(node_types) if node_types else {"event", "detection", "ioc", "incident"}

        nodes: dict[uuid.UUID, GraphNode] = {}
        edges: list[GraphEdge] = []

        events = self._load_events(case_id)
        detections = self._load_detections(case_id)
        iocs = self._load_iocs(case_id)
        incidents = self._load_incidents(case_id)

        # --- Nodes ---------------------------------------------------------
        if "event" in allowed:
            for ev in events:
                nodes[ev.id] = GraphNode(
                    id=ev.id,
                    type="event",
                    label=f"{ev.event_type} @ {ev.timestamp.isoformat()}",
                    evidence_id=ev.evidence_id,
                    case_id=ev.case_id,
                    timestamp=ev.timestamp.isoformat(),
                    data=ev.data or {},
                )

        if "detection" in allowed:
            for det in detections:
                nodes[det.id] = GraphNode(
                    id=det.id,
                    type="detection",
                    label=f"{det.detection_type} [{det.severity}]",
                    evidence_id=None,  # Detection has no direct evidence FK
                    case_id=det.case_id,
                    severity=det.severity,
                    data={"rule_id": det.rule_id, "confidence": det.confidence},
                )

        if "ioc" in allowed:
            for ioc in iocs:
                nodes[ioc.id] = GraphNode(
                    id=ioc.id,
                    type="ioc",
                    label=f"{ioc.ioc_type}: {ioc.value}",
                    evidence_id=ioc.evidence_id,
                    case_id=ioc.case_id,
                    severity=ioc.severity,
                    data={"ioc_type": ioc.ioc_type, "value": ioc.value, "confidence": ioc.confidence},
                )

        if "incident" in allowed:
            for inc in incidents:
                nodes[inc.id] = GraphNode(
                    id=inc.id,
                    type="incident",
                    label=inc.title,
                    evidence_id=None,
                    case_id=inc.case_id,
                    severity=inc.severity,
                    data={"status": inc.status, "confidence": inc.confidence},
                )

        # --- FK-derived Edges ----------------------------------------------

        event_ids = {ev.id for ev in events}
        detection_ids = {det.id for det in detections}
        ioc_ids = {ioc.id for ioc in iocs}
        incident_ids = {inc.id for inc in incidents}

        # Event → TRIGGERED → Detection
        if "event" in allowed and "detection" in allowed:
            for det in detections:
                if det.event_id in event_ids and det.id in detection_ids:
                    edges.append(GraphEdge(
                        source=det.event_id,
                        target=det.id,
                        relationship="TRIGGERED",
                        label=f"rule: {det.rule_id or det.detection_type}",
                    ))

        # Event → PRODUCED → IOC
        if "event" in allowed and "ioc" in allowed:
            for ioc in iocs:
                if ioc.event_id in event_ids and ioc.id in ioc_ids:
                    edges.append(GraphEdge(
                        source=ioc.event_id,
                        target=ioc.id,
                        relationship="PRODUCED",
                        label=f"{ioc.ioc_type}: {ioc.value}",
                    ))

        # Event ↔ Incident (via incident_events M2M)
        if "event" in allowed and "incident" in allowed:
            for inc in incidents:
                if inc.id in incident_ids:
                    for ev in inc.events:
                        if ev.id in event_ids:
                            edges.append(GraphEdge(
                                source=ev.id,
                                target=inc.id,
                                relationship="PART_OF",
                                label=inc.title,
                            ))

        # Detection ↔ Incident (via incident_detections M2M)
        if "detection" in allowed and "incident" in allowed:
            for inc in incidents:
                if inc.id in incident_ids:
                    for det in inc.detections:
                        if det.id in detection_ids:
                            edges.append(GraphEdge(
                                source=det.id,
                                target=inc.id,
                                relationship="PART_OF",
                                label=inc.title,
                            ))

        # --- Shared-Entity Edges (JSONB) ------------------------------------
        if include_shared_entities and "event" in allowed:
            entity_edges = self._build_shared_entity_edges(events, event_ids)
            edges.extend(entity_edges)

        # Deduplicate edges (same source/target/relationship)
        edges = _dedup_edges(edges)

        return GraphResponse(
            case_id=case_id,
            node_count=len(nodes),
            edge_count=len(edges),
            nodes=list(nodes.values()),
            edges=edges,
        )

    # ------------------------------------------------------------------
    # Private loaders
    # ------------------------------------------------------------------

    def _load_events(self, case_id: uuid.UUID) -> list[Event]:
        stmt = select(Event).where(Event.case_id == case_id)
        return list(self.db.execute(stmt).scalars().all())

    def _load_detections(self, case_id: uuid.UUID) -> list[Detection]:
        stmt = select(Detection).where(Detection.case_id == case_id)
        return list(self.db.execute(stmt).scalars().all())

    def _load_iocs(self, case_id: uuid.UUID) -> list[IOC]:
        stmt = select(IOC).where(IOC.case_id == case_id)
        return list(self.db.execute(stmt).scalars().all())

    def _load_incidents(self, case_id: uuid.UUID) -> list[Incident]:
        stmt = select(Incident).where(Incident.case_id == case_id)
        return list(self.db.execute(stmt).scalars().all())

    # ------------------------------------------------------------------
    # Shared-entity edge computation
    # ------------------------------------------------------------------

    def _build_shared_entity_edges(
        self,
        events: list[Event],
        event_ids: set[uuid.UUID],
    ) -> list[GraphEdge]:
        """
        For each ENTITY_KEY, group events by shared value.
        For each group of 2+ events sharing a value, create edges
        between the first representative and each other member.

        This avoids N² combinatorial explosion by using a single
        "hub" event per entity value.
        """
        # Map entity_key:value → list of event UUIDs
        entity_map: dict[str, list[uuid.UUID]] = {}

        for ev in events:
            data: dict[str, Any] = ev.data if isinstance(ev.data, dict) else {}
            for key in ENTITY_KEYS:
                val = data.get(key)
                if val is None:
                    continue
                val_str = str(val).strip()
                if len(val_str) < MIN_ENTITY_VALUE_LEN:
                    continue
                bucket = f"{key}:{val_str}"
                entity_map.setdefault(bucket, []).append(ev.id)

        edges: list[GraphEdge] = []
        for bucket, ids in entity_map.items():
            if len(ids) < 2:
                continue
            key, value = bucket.split(":", 1)
            hub = ids[0]
            for other in ids[1:]:
                edges.append(GraphEdge(
                    source=hub,
                    target=other,
                    relationship="SHARES_ENTITY",
                    label=f"{key}: {value}",
                ))
                if len(edges) >= MAX_SHARED_ENTITY_EDGES:
                    return edges

        return edges


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _dedup_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    """Remove exact duplicate edges (same source, target, relationship)."""
    seen: set[tuple[uuid.UUID, uuid.UUID, str]] = set()
    result: list[GraphEdge] = []
    for e in edges:
        key = (e.source, e.target, e.relationship)
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result
