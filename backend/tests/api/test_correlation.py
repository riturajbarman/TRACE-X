"""API-level tests for POST /cases/{case_id}/correlate (Phase 8)."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.event.service import EventService
from app.domain.event.schemas import EventCreate

client = TestClient(app)

ANCHOR = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


def _create_case() -> str:
    resp = client.post(
        "/cases",
        json={"title": f"Corr API Case {uuid4()}", "created_by": "pytest"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_evidence(case_id: str) -> str:
    content = f"evidence-{uuid4()}".encode()
    resp = client.post(
        "/evidence/ingest",
        data={"case_id": case_id, "name": f"ev-{uuid4()}"},
        files={"file": ("ev.bin", content, "application/octet-stream")},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _insert_events(case_id: str, evidence_id: str, events_data: list[dict]) -> None:
    db = SessionLocal()
    try:
        svc = EventService(db)
        svc.ingest_events([
            EventCreate(
                artifact_id=e.get("artifact_id", uuid4()),
                evidence_id=evidence_id,
                case_id=case_id,
                event_type=e.get("event_type", "generic"),
                source=e.get("source", "test"),
                timestamp=e.get("timestamp", ANCHOR),
                data=e.get("data", {}),
            )
            for e in events_data
        ])
    finally:
        db.close()


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

def test_correlate_not_found_case():
    resp = client.post(f"/cases/{uuid4()}/correlate")
    assert resp.status_code == 404


def test_correlate_empty_case_returns_zero_groups():
    """A case with no events must return 0 groups, not an error."""
    case_id = _create_case()
    resp = client.post(f"/cases/{case_id}/correlate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["group_count"] == 0
    assert data["groups"] == []


def test_correlate_related_events_grouped():
    """Events sharing process_name must be returned in a group via the API."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)

    _insert_events(case_id, evidence_id, [
        {"event_type": "process_exec", "source": "evtx",
         "timestamp": ANCHOR, "data": {"process_name": "malware.exe"}},
        {"event_type": "file_write",   "source": "evtx",
         "timestamp": ANCHOR + timedelta(hours=1),
         "data": {"process_name": "malware.exe"}},
    ])

    resp = client.post(f"/cases/{case_id}/correlate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_count"] == 1
    group = data["groups"][0]
    assert group["event_count"] == 2
    assert group["reason"]
    assert len(group["events"]) == 2
    # Provenance: both events must carry their case_id
    for evt in group["events"]:
        assert evt["case_id"] == case_id


def test_correlate_unrelated_events_no_group():
    """Events that share nothing must produce 0 groups."""
    case_id = _create_case()
    ev1_id = _create_evidence(case_id)
    ev2_id = _create_evidence(case_id)

    _insert_events(case_id, ev1_id, [
        {"event_type": "login", "source": "auth_log",
         "timestamp": ANCHOR, "data": {"user": "alice"}},
    ])
    _insert_events(case_id, ev2_id, [
        {"event_type": "network", "source": "firewall",
         "timestamp": ANCHOR + timedelta(days=1),
         "data": {"dst_ip": "10.0.0.1"}},
    ])

    resp = client.post(f"/cases/{case_id}/correlate")
    assert resp.status_code == 200
    assert resp.json()["group_count"] == 0


def test_correlate_is_idempotent():
    """Calling correlate twice must produce the same group_count."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)

    shared = {"process_name": "evil.exe"}
    _insert_events(case_id, evidence_id, [
        {"event_type": "A", "source": "s", "timestamp": ANCHOR, "data": shared},
        {"event_type": "B", "source": "s",
         "timestamp": ANCHOR + timedelta(hours=1), "data": shared},
    ])

    resp1 = client.post(f"/cases/{case_id}/correlate")
    resp2 = client.post(f"/cases/{case_id}/correlate")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["group_count"] == resp2.json()["group_count"]


def test_correlate_response_contains_reason():
    """Every group returned by the API must have a non-empty reason."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)

    _insert_events(case_id, evidence_id, [
        {"event_type": "A", "source": "s", "timestamp": ANCHOR,
         "data": {"path": "/tmp/exploit.sh"}},
        {"event_type": "B", "source": "s",
         "timestamp": ANCHOR + timedelta(hours=2),
         "data": {"path": "/tmp/exploit.sh"}},
    ])

    resp = client.post(f"/cases/{case_id}/correlate")
    assert resp.status_code == 200
    for group in resp.json()["groups"]:
        assert group["reason"]
        assert len(group["reason"]) > 0
