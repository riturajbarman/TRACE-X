"""
Correlation Engine — Phase 8

Pure-logic, deterministic correlator. No ML, no probability.
All decisions must be explainable from the input data alone.

Supported correlation strategies:

1. Evidence provenance  — events from the same artifact are related.
2. Shared entity        — events share a meaningful JSONB field value
                          (path, process, ip, domain, hash, etc.)
3. Time-window          — events occur within a configured window AND share
                          at least one secondary criterion (same evidence,
                          same source, or same event_type). Time alone is
                          NOT sufficient — this guards against false positives.

Each correlated cluster becomes a CorrelationGroup with title, reason,
severity, confidence, linked events, and linked detections.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from app.domain.detection.models import Detection
from app.domain.event.models import Event


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIME_WINDOW: timedelta = timedelta(minutes=5)

# JSONB keys considered meaningful entity signals (more specific first).
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

# Values shorter than this are rejected as too generic.
MIN_ENTITY_VALUE_LEN: int = 2


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CorrelationGroup:
    """A cluster of related events and their contributing detections."""

    group_id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    reason: str = ""
    severity: str = "LOW"
    confidence: int = 0
    events: list[Event] = field(default_factory=list)
    detections: list[Detection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_entities(data: dict[str, Any]) -> dict[str, str]:
    """
    Extract meaningful entity key-value pairs from event JSONB data.
    Searches one level of nesting.
    """
    entities: dict[str, str] = {}
    for key in ENTITY_KEYS:
        if key in data:
            val = str(data[key]).strip()
            if len(val) >= MIN_ENTITY_VALUE_LEN:
                entities[key] = val
        for nested in data.values():
            if isinstance(nested, dict) and key in nested:
                val = str(nested[key]).strip()
                if len(val) >= MIN_ENTITY_VALUE_LEN:
                    entities.setdefault(key, val)
    return entities


def _max_severity(severities: list[str]) -> str:
    order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    return max(severities, key=lambda s: order.get(s.upper(), 0), default="LOW").upper()


def _build_detection_map(detections: list[Detection]) -> dict[uuid.UUID, list[Detection]]:
    """Return {event_id -> [detections]}."""
    m: dict[uuid.UUID, list[Detection]] = {}
    for d in detections:
        m.setdefault(d.event_id, []).append(d)
    return m


def _derive_severity_confidence(
    events: list[Event],
    det_map: dict[uuid.UUID, list[Detection]],
) -> tuple[str, int]:
    """Derive severity and confidence from contributing detections."""
    severities: list[str] = []
    confidences: list[int] = []
    for evt in events:
        for det in det_map.get(evt.id, []):
            severities.append(det.severity)
            confidences.append(det.confidence)
    if not severities:
        return "LOW", 50
    return _max_severity(severities), max(confidences)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class CorrelationEngine:
    """
    Deterministic, explainable correlation engine.

    Usage::

        engine = CorrelationEngine(time_window=timedelta(minutes=5))
        groups = engine.correlate(events, detections)

    Singleton events (cannot be correlated with anything) are NOT returned.
    """

    def __init__(self, time_window: timedelta = DEFAULT_TIME_WINDOW) -> None:
        self.time_window = time_window

    def correlate(
        self,
        events: list[Event],
        detections: list[Detection],
    ) -> list[CorrelationGroup]:
        """
        Group events by deterministic correlation rules.

        Returns one CorrelationGroup per cluster that contains >= 2 events.
        """
        if len(events) < 2:
            return []

        det_map = _build_detection_map(detections)

        # Union-Find
        parent: dict[uuid.UUID, uuid.UUID] = {e.id: e.id for e in events}

        def find(x: uuid.UUID) -> uuid.UUID:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: uuid.UUID, b: uuid.UUID) -> None:
            parent[find(a)] = find(b)

        reasons: dict[frozenset, str] = {}

        entity_cache: dict[uuid.UUID, dict[str, str]] = {
            e.id: _extract_entities(e.data) for e in events
        }

        # Sort by (timestamp, id) for deterministic and break-early behaviour.
        by_time = sorted(events, key=lambda e: (e.timestamp, str(e.id)))

        # -- Strategy 1: Evidence provenance (same artifact_id) --
        for i, ea in enumerate(by_time):
            if ea.artifact_id is None:
                continue
            for eb in by_time[i + 1:]:
                if ea.artifact_id == eb.artifact_id:
                    pair: frozenset = frozenset({ea.id, eb.id})
                    reasons[pair] = (
                        f"Both events originate from the same artifact ({ea.artifact_id})"
                    )
                    union(ea.id, eb.id)

        # -- Strategy 2: Shared entity (JSONB key-value) --
        for i, ea in enumerate(by_time):
            ents_a = entity_cache[ea.id]
            if not ents_a:
                continue
            for eb in by_time[i + 1:]:
                ents_b = entity_cache[eb.id]
                for key in ENTITY_KEYS:
                    va = ents_a.get(key)
                    vb = ents_b.get(key)
                    if va and vb and va == vb:
                        pair = frozenset({ea.id, eb.id})
                        reasons.setdefault(pair, f"Shared {key} value '{va}'")
                        union(ea.id, eb.id)
                        break

        # -- Strategy 3: Time-window + secondary criterion --
        for i, ea in enumerate(by_time):
            for eb in by_time[i + 1:]:
                delta = eb.timestamp - ea.timestamp
                if delta > self.time_window:
                    break  # by_time is sorted; no later pair will be closer

                secondary: str | None = None
                if ea.evidence_id and ea.evidence_id == eb.evidence_id:
                    secondary = f"same evidence ({ea.evidence_id})"
                elif ea.source and ea.source == eb.source:
                    secondary = f"same source '{ea.source}'"
                elif ea.event_type and ea.event_type == eb.event_type:
                    secondary = f"same event_type '{ea.event_type}'"

                if secondary:
                    pair = frozenset({ea.id, eb.id})
                    secs = int(delta.total_seconds())
                    reasons.setdefault(
                        pair,
                        f"Events within {secs}s and {secondary}",
                    )
                    union(ea.id, eb.id)

        # Build cluster -> events mapping
        clusters: dict[uuid.UUID, list[Event]] = {}
        for evt in by_time:
            root = find(evt.id)
            clusters.setdefault(root, []).append(evt)

        groups: list[CorrelationGroup] = []
        for _, cluster_events in clusters.items():
            if len(cluster_events) < 2:
                continue

            # Pick the first recorded reason as the group's representative reason
            rep_reason = "Related events detected"
            for ea in cluster_events:
                found = False
                for eb in cluster_events:
                    if ea.id == eb.id:
                        continue
                    pair = frozenset({ea.id, eb.id})
                    if pair in reasons:
                        rep_reason = reasons[pair]
                        found = True
                        break
                if found:
                    break

            cluster_detections: list[Detection] = []
            for evt in cluster_events:
                cluster_detections.extend(det_map.get(evt.id, []))

            sev, conf = _derive_severity_confidence(cluster_events, det_map)

            groups.append(CorrelationGroup(
                title=f"Correlated Activity ({len(cluster_events)} events)",
                reason=rep_reason,
                severity=sev,
                confidence=conf,
                events=cluster_events,
                detections=cluster_detections,
            ))

        # Stable sort by descending severity
        sev_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        groups.sort(key=lambda g: sev_order.get(g.severity, 0), reverse=True)
        return groups
