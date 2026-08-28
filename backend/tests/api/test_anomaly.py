import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
import json
from datetime import datetime, timezone

from app.main import app
from app.core.database import SessionLocal
from app.domain.event.service import EventService
from app.domain.event.schemas import EventCreate

client = TestClient(app)

def _create_case() -> str:
    resp = client.post(
        "/cases",
        json={"title": f"Anomaly API Case {uuid4()}", "created_by": "pytest"},
    )
    return resp.json()["id"]

def _create_evidence(case_id: str) -> str:
    content = f"evidence-{uuid4()}".encode()
    resp = client.post(
        "/evidence/ingest",
        data={"case_id": case_id, "name": f"ev-{uuid4()}"},
        files={"file": ("ev.bin", content, "application/octet-stream")},
    )
    return resp.json()["id"]

def test_anomaly_scan_not_found_case():
    resp = client.post(f"/cases/{uuid4()}/anomaly-scan")
    assert resp.status_code == 404

def test_anomaly_scan_empty_case():
    case_id = _create_case()
    resp = client.post(f"/cases/{case_id}/anomaly-scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["anomaly_count"] == 0
    assert data["findings"] == []

def test_anomaly_scan_returns_scores():
    case_id = _create_case()
    evidence_id = _create_evidence(case_id)
    
    # Load anomalous and normal events
    with open("tests/fixtures/anomaly/normal_events.json", "r") as f:
        normal_data = json.load(f)[:10]
    with open("tests/fixtures/anomaly/anomalous_events.json", "r") as f:
        anom_data = json.load(f)
        
    db = SessionLocal()
    svc = EventService(db)
    
    all_events = normal_data + anom_data
    
    svc.ingest_events([
        EventCreate(
            artifact_id=uuid4(),
            evidence_id=evidence_id,
            case_id=case_id,
            event_type=e.get("event_type", "generic"),
            source=e.get("source", "test"),
            timestamp=datetime.fromisoformat(e["timestamp"]),
            data=e.get("data", {})
        ) for e in all_events
    ])
    db.close()
    
    resp = client.post(f"/cases/{case_id}/anomaly-scan")
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["model_version"]
    assert data["anomaly_count"] > 0
    
    for finding in data["findings"]:
        assert "event_id" in finding
        assert "score" in finding
        assert "explanation" in finding
        assert finding["score"] >= 0 and finding["score"] <= 100
        assert len(finding["explanation"]) > 0

