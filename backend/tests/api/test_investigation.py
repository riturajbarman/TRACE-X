"""API tests for the Phase 5 Investigation workflow."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def _create_case():
    response = client.post(
        "/cases",
        json={"title": f"Test Case {uuid4()}", "description": "Phase 5 Test", "created_by": "pytest"},
    )
    assert response.status_code == 201
    return response.json()["id"]

def _create_evidence(case_id):
    content = f"evidence-{uuid4()}".encode()
    response = client.post(
        "/evidence/ingest",
        data={"case_id": str(case_id), "name": f"ev-{uuid4()}"},
        files={"file": ("evidence.bin", content, "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]

def _insert_events(case_id, evidence_id, events_data):
    """Insert events via the repository/service layer."""
    from app.core.database import SessionLocal
    from app.domain.event.service import EventService
    from app.domain.event.schemas import EventCreate

    db = SessionLocal()
    try:
        service = EventService(db)
        ecs = [
            EventCreate(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                case_id=case_id,
                event_type=e.get("event_type", "file_creation"),
                source=e.get("source", "evtx"),
                timestamp=e.get("timestamp", datetime.now(timezone.utc)),
                timestamp_desc="SystemTime",
                schema_version=1,
                data=e.get("data", {})
            )
            for e in events_data
        ]
        service.ingest_events(ecs)
    finally:
        db.close()


def test_case_summary():
    """Verify Case Summary returns correct counts and metadata."""
    case_id = _create_case()
    evidence_1 = _create_evidence(case_id)
    evidence_2 = _create_evidence(case_id)

    # Insert 3 events for evidence 1
    _insert_events(case_id, evidence_1, [{"event_type": "x"}] * 3)
    # Insert 2 events for evidence 2
    _insert_events(case_id, evidence_2, [{"event_type": "y"}] * 2)

    response = client.get(f"/cases/{case_id}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == case_id
    assert data["evidence_count"] == 2
    assert data["event_count"] == 5


def test_case_summary_not_found():
    """Verify 404 behavior for Case Summary."""
    response = client.get(f"/cases/{uuid4()}/summary")
    assert response.status_code == 404


def test_event_detail():
    """Verify single event can be fetched and maintains provenance."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    
    _insert_events(case_id, evidence_id, [{"event_type": "detail_test"}])
    
    # First, get the event ID from timeline
    timeline_response = client.get(f"/cases/{case_id}/timeline")
    event_id = timeline_response.json()[0]["id"]

    # Now fetch detail
    response = client.get(f"/events/{event_id}")
    assert response.status_code == 200
    event = response.json()
    assert event["id"] == event_id
    assert event["event_type"] == "detail_test"
    # Verify provenance
    assert "artifact_id" in event
    assert event["evidence_id"] == evidence_id
    assert event["case_id"] == case_id


def test_event_detail_not_found():
    response = client.get(f"/events/{uuid4()}")
    assert response.status_code == 404


def test_timeline_filters():
    """Verify timeline filters (event_type, source, start_time, end_time) work."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)

    base_time = datetime(2025, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    _insert_events(case_id, evidence_id, [
        {"event_type": "A", "source": "src1", "timestamp": base_time},
        {"event_type": "A", "source": "src2", "timestamp": base_time + timedelta(hours=1)},
        {"event_type": "B", "source": "src1", "timestamp": base_time + timedelta(hours=2)},
        {"event_type": "B", "source": "src2", "timestamp": base_time + timedelta(hours=3)},
    ])

    # Filter by event_type
    resp = client.get(f"/cases/{case_id}/timeline?event_type=A")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    for e in resp.json():
        assert e["event_type"] == "A"

    # Filter by source
    resp = client.get(f"/cases/{case_id}/timeline?source=src1")
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    for e in resp.json():
        assert e["source"] == "src1"

    # Filter by combined type and source
    resp = client.get(f"/cases/{case_id}/timeline?event_type=A&source=src2")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["event_type"] == "A"
    assert resp.json()[0]["source"] == "src2"

    # Filter by time range
    import urllib.parse
    start_str = urllib.parse.quote((base_time + timedelta(hours=1)).isoformat())
    end_str = urllib.parse.quote((base_time + timedelta(hours=2)).isoformat())
    resp = client.get(f"/cases/{case_id}/timeline?start_time={start_str}&end_time={end_str}")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # Verify chronological ordering inside timeline
    timestamps = [e["timestamp"] for e in resp.json()]
    assert timestamps == sorted(timestamps)


def test_timeline_isolation():
    """Verify one case's timeline does not leak events from another case."""
    case1 = _create_case()
    evidence1 = _create_evidence(case1)
    _insert_events(case1, evidence1, [{"event_type": "case1_event"}])

    case2 = _create_case()
    evidence2 = _create_evidence(case2)
    _insert_events(case2, evidence2, [{"event_type": "case2_event"}])

    resp1 = client.get(f"/cases/{case1}/timeline")
    assert len(resp1.json()) == 1
    assert resp1.json()[0]["case_id"] == case1

    resp2 = client.get(f"/cases/{case2}/timeline")
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["case_id"] == case2
