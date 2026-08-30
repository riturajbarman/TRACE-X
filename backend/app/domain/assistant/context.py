"""
Phase 11 — bounded, case-scoped context assembly for the AI Investigation
Assistant.

Reuses the same read-only domain services other endpoints already use
(CaseService, EventService, RiskService, DetectionRepository, GraphService)
— no new retrieval layer, no raw evidence access.

IMPORTANT: CorrelationService.correlate_case() and AnomalyService.scan_case()
are deliberately NOT called here — both mutate the database (they delete
and regenerate Incidents / anomaly Detections). Building assistant context
must never write to forensic data, so:
  - correlation results are read directly from already-persisted Incident
    rows (status == "AUTO_CORRELATED"); if correlation has never been run
    for a case, this context simply has none, honestly reflecting that.
  - anomaly results are already persisted as ordinary Detection rows
    (detection_type == "anomaly") by AnomalyService.scan_case, so they are
    read via the same DetectionRepository call used for all detections —
    no separate anomaly query is needed.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.domain.case.service import CaseService
from app.domain.detection.models import Incident
from app.domain.detection.repository import DetectionRepository
from app.domain.detection.service import RiskService
from app.domain.event.service import EventService
from app.domain.graph.service import GraphService

_SEVERITY_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}


@dataclass
class AssistantContext:
    """Everything handed to the LLM provider, plus the set of provenance
    ids it's allowed to cite (used by grounding.py to validate claims)."""
    payload: dict[str, Any]
    known_ids: set[str] = field(default_factory=set)


def _severity_key(value: str | None):
    return _SEVERITY_RANK.get((value or "").upper(), 0)


def build_context(session: Session, case_id: uuid.UUID) -> AssistantContext | None:
    """Assemble bounded, provenance-carrying context for one case.

    Returns None if the case does not exist (caller maps this to a 404).
    Every DB access here is read-only.
    """
    case_service = CaseService(session)
    case = case_service.get_by_id(case_id)
    if case is None:
        return None

    known_ids: set[str] = {str(case_id)}

    summary = case_service.get_summary(case_id) or {}
    case_payload = {
        "id": str(case_id),
        "title": case.title,
        "description": case.description,
        "status": case.status.value if hasattr(case.status, "value") else case.status,
        "evidence_count": summary.get("evidence_count"),
        "event_count": summary.get("event_count"),
    }

    # --- Evidence metadata (never file bytes) --------------------------
    evidence_list = case_service.list_evidence(
        case_id, limit=config.ASSISTANT_MAX_EVIDENCE, offset=0
    )
    evidence_payload = []
    for e in evidence_list:
        known_ids.add(str(e.id))
        evidence_payload.append(
            {
                "evidence_id": str(e.id),
                "name": e.name,
                "source": e.source,
                "status": e.status.value if hasattr(e.status, "value") else e.status,
                "sha256": e.sha256,
            }
        )

    # --- Risk (already deterministic, already small) --------------------
    risk = RiskService(session).calculate_case_risk(case_id)
    for s in risk.contributing_signals:
        if s.detection_id:
            known_ids.add(str(s.detection_id))
        if s.ioc_id:
            known_ids.add(str(s.ioc_id))
    risk_payload = {
        "risk_score": risk.risk_score,
        "risk_level": risk.risk_level,
        "explanation": risk.explanation,
        "contributing_signals": [
            {
                "source": s.source,
                "description": s.description,
                "score": s.score,
                "detection_id": str(s.detection_id) if s.detection_id else None,
                "ioc_id": str(s.ioc_id) if s.ioc_id else None,
            }
            for s in risk.contributing_signals
        ],
    }

    # --- Detections / IOCs (includes anomaly-derived detections) --------
    det_repo = DetectionRepository(session)
    detections = list(det_repo.list_detections_by_case(case_id))
    iocs = list(det_repo.list_iocs_by_case(case_id))

    detections_sorted = sorted(
        detections,
        key=lambda d: (_severity_key(d.severity), d.created_at),
        reverse=True,
    )[: config.ASSISTANT_MAX_DETECTIONS]
    iocs_sorted = sorted(
        iocs,
        key=lambda i: (_severity_key(i.severity), i.created_at),
        reverse=True,
    )[: config.ASSISTANT_MAX_IOCS]

    detections_payload = []
    anomaly_payload = []
    for d in detections_sorted:
        known_ids.add(str(d.id))
        known_ids.add(str(d.event_id))
        entry = {
            "detection_id": str(d.id),
            "event_id": str(d.event_id),
            "detection_type": d.detection_type,
            "rule_id": d.rule_id,
            "severity": d.severity,
            "confidence": d.confidence,
        }
        detections_payload.append(entry)
        if d.detection_type == "anomaly":
            anomaly_payload.append(entry)

    iocs_payload = []
    for i in iocs_sorted:
        known_ids.add(str(i.id))
        known_ids.add(str(i.event_id))
        iocs_payload.append(
            {
                "ioc_id": str(i.id),
                "event_id": str(i.event_id),
                "ioc_type": i.ioc_type,
                "value": i.value,
                "severity": i.severity,
                "confidence": i.confidence,
            }
        )

    # --- Correlation (read-only: already-persisted Incidents only) ------
    incidents_stmt = (
        select(Incident)
        .where(Incident.case_id == case_id)
        .order_by(Incident.confidence.desc(), Incident.created_at.desc())
        .limit(config.ASSISTANT_MAX_INCIDENTS)
    )
    incidents = list(session.execute(incidents_stmt).scalars().all())
    incidents_payload = []
    for inc in incidents:
        known_ids.add(str(inc.id))
        event_ids = [str(ev.id) for ev in inc.events]
        detection_ids = [str(d.id) for d in inc.detections]
        known_ids.update(event_ids)
        known_ids.update(detection_ids)
        incidents_payload.append(
            {
                "incident_id": str(inc.id),
                "title": inc.title,
                "severity": inc.severity,
                "confidence": inc.confidence,
                "status": inc.status,
                "event_ids": event_ids,
                "detection_ids": detection_ids,
            }
        )

    # --- Graph (read-only build; bounded sample, not the full graph) ----
    graph = GraphService(session).build_graph(
        case_id=case_id, node_types=None, include_shared_entities=True
    )
    graph_nodes_sample = graph.nodes[: config.ASSISTANT_MAX_GRAPH_NODES]
    sampled_node_ids = {str(n.id) for n in graph_nodes_sample}
    for n in graph_nodes_sample:
        known_ids.add(str(n.id))
    graph_payload = {
        "node_count": graph.node_count,
        "edge_count": graph.edge_count,
        "nodes_sample": [
            {"id": str(n.id), "type": n.type, "label": n.label, "severity": n.severity}
            for n in graph_nodes_sample
        ],
        "edges_sample": [
            {
                "source": str(e.source),
                "target": str(e.target),
                "relationship": e.relationship,
            }
            for e in graph.edges
            if str(e.source) in sampled_node_ids
        ][: config.ASSISTANT_MAX_GRAPH_NODES],
    }

    # --- Events: bounded timeline sample (metadata only, no raw `data`) --
    events = EventService(session).list_by_case(case_id, limit=config.ASSISTANT_MAX_EVENTS)
    events_payload = []
    for ev in events:
        known_ids.add(str(ev.id))
        events_payload.append(
            {
                "event_id": str(ev.id),
                "evidence_id": str(ev.evidence_id) if ev.evidence_id else None,
                "event_type": ev.event_type,
                "source": ev.source,
                "timestamp": ev.timestamp.isoformat(),
            }
        )

    payload: dict[str, Any] = {
        "case": case_payload,
        "risk": risk_payload,
        "detections": detections_payload,
        "iocs": iocs_payload,
        "anomaly_detections": anomaly_payload,
        "correlation_incidents": incidents_payload,
        "graph_summary": graph_payload,
        "events_sample": events_payload,
        "evidence": evidence_payload,
        "context_limits": {
            "max_events": config.ASSISTANT_MAX_EVENTS,
            "max_detections": config.ASSISTANT_MAX_DETECTIONS,
            "max_iocs": config.ASSISTANT_MAX_IOCS,
            "max_incidents": config.ASSISTANT_MAX_INCIDENTS,
            "max_graph_nodes": config.ASSISTANT_MAX_GRAPH_NODES,
            "max_evidence": config.ASSISTANT_MAX_EVIDENCE,
        },
    }

    return AssistantContext(payload=payload, known_ids=known_ids)
