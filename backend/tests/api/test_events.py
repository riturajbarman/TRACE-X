"""API tests for event query endpoints."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _create_case():
    response = client.post(
        "/cases",
        json={
            "title": f"API Event Case {uuid4()}",
            "description": "Test",
            "created_by": "pytest",
        },
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


def _insert_events_via_service(case_id, evidence_id, count=3):
    """Insert events directly via service for API query testing."""
    from app.core.database import SessionLocal
    from app.domain.event.service import EventService
    from app.domain.event.schemas import EventCreate

    db = SessionLocal()
    try:
        service = EventService(db)
        artifact_id = uuid4()
        base_time = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)

        ecs = [
            EventCreate(
                artifact_id=artifact_id,
                evidence_id=evidence_id,
                case_id=case_id,
                event_type="file_creation",
                source="evtx",
                timestamp=base_time + timedelta(minutes=i),
                timestamp_desc="SystemTime",
                schema_version=1,
                data={"index": i},
            )
            for i in range(count)
        ]

        service.ingest_events(ecs)
        return artifact_id
    finally:
        db.close()


def test_list_events_by_evidence():
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    _insert_events_via_service(case_id, evidence_id, count=5)

    response = client.get(f"/events/evidence/{evidence_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5

    for event in data:
        assert event["evidence_id"] == evidence_id
        assert "id" in event
        assert "timestamp" in event
        assert "event_type" in event
        assert "source" in event
        assert "schema_version" in event


def test_list_events_by_case():
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    _insert_events_via_service(case_id, evidence_id, count=4)

    response = client.get(f"/events/case/{case_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4

    for event in data:
        assert event["case_id"] == case_id


def test_list_events_by_artifact():
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    artifact_id = _insert_events_via_service(case_id, evidence_id, count=3)

    response = client.get(f"/events/artifact/{artifact_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    for event in data:
        assert event["artifact_id"] == str(artifact_id)


def test_events_pagination():
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    _insert_events_via_service(case_id, evidence_id, count=10)

    response = client.get(
        f"/events/evidence/{evidence_id}",
        params={"limit": 3, "offset": 0},
    )
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1) == 3

    response = client.get(
        f"/events/evidence/{evidence_id}",
        params={"limit": 3, "offset": 3},
    )
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2) == 3

    # Pages must not overlap
    page1_ids = {e["id"] for e in page1}
    page2_ids = {e["id"] for e in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_events_empty_result():
    """Querying events for a nonexistent evidence should return empty list."""
    response = client.get(f"/events/evidence/{uuid4()}")
    assert response.status_code == 200
    assert response.json() == []


def test_events_timestamp_ordering():
    """Events returned via API must be ordered by timestamp ascending."""
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    _insert_events_via_service(case_id, evidence_id, count=5)

    response = client.get(f"/events/evidence/{evidence_id}")
    assert response.status_code == 200
    data = response.json()

    timestamps = [e["timestamp"] for e in data]
    assert timestamps == sorted(timestamps)
