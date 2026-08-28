from datetime import datetime, timezone, timedelta
import urllib.parse
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.case.models import Case, CaseStatus
from app.domain.evidence.models import Evidence
from app.domain.event.models import Event
from app.domain.detection.models import IOC, Detection, Incident

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _create_case(db) -> str:
    case = Case(
        title="Risk Test Case",
        description="Testing risk engine",
        status=CaseStatus.OPEN,
        created_by="pytest",
    )
    db.add(case)
    db.flush()
    return str(case.id)

def _create_evidence(db, case_id: str) -> str:
    evidence = Evidence(
        case_id=case_id,
        name="test_risk.dd",
        size_bytes=1024,
        source="local",
        sha256=uuid4().hex,
    )
    db.add(evidence)
    db.flush()
    return str(evidence.id)

def _create_event(db, case_id: str, evidence_id: str) -> str:
    event = Event(
        case_id=case_id,
        evidence_id=evidence_id,
        event_type="test_event",
        source="test_source",
        timestamp=datetime.now(timezone.utc),
        data={"test": "data"}
    )
    db.add(event)
    db.flush()
    return str(event.id)

def test_deterministic_risk_calculation(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)
    event1_id = _create_event(db_session, case_id, evidence_id)
    event2_id = _create_event(db_session, case_id, evidence_id)

    # Add a HIGH Detection (+20)
    det = Detection(
        case_id=case_id,
        event_id=event1_id,
        detection_type="rule_match",
        severity="HIGH",
        confidence=90
    )
    db_session.add(det)

    # Add a CRITICAL IOC (+25)
    ioc = IOC(
        case_id=case_id,
        event_id=event2_id,
        ioc_type="ip",
        value="1.2.3.4",
        severity="CRITICAL",
        confidence=100
    )
    db_session.add(ioc)
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["risk_score"] == 45
    assert data["risk_level"] == "MEDIUM"
    assert len(data["contributing_signals"]) == 2

def test_risk_case_isolation(db_session):
    case_a = _create_case(db_session)
    evidence_a = _create_evidence(db_session, case_a)
    event_a = _create_event(db_session, case_a, evidence_a)

    det = Detection(
        case_id=case_a,
        event_id=event_a,
        detection_type="rule_match",
        severity="HIGH",
        confidence=90
    )
    db_session.add(det)
    db_session.commit()

    case_b = _create_case(db_session)
    db_session.commit()

    resp_b = client.get(f"/cases/{case_b}/risk")
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert data_b["risk_score"] == 0
    assert data_b["risk_level"] == "NONE"

def test_timeline_severity_filter(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)

    event1 = Event(
        case_id=case_id, evidence_id=evidence_id, event_type="t1", source="s1", timestamp=datetime.now(timezone.utc)
    )
    event2 = Event(
        case_id=case_id, evidence_id=evidence_id, event_type="t2", source="s2", timestamp=datetime.now(timezone.utc)
    )
    db_session.add(event1)
    db_session.add(event2)
    db_session.flush()

    det = Detection(
        case_id=case_id,
        event_id=event1.id,
        detection_type="test",
        severity="CRITICAL",
        confidence=100
    )
    db_session.add(det)
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/timeline?severity=CRITICAL")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(event1.id)

def test_timeline_duplicate_leakage(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)

    event1 = Event(
        case_id=case_id,
        evidence_id=evidence_id,
        event_type="t1",
        source="s1",
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(event1)
    db_session.flush()

    # Create MULTIPLE detections of the same severity for the same event
    det1 = Detection(
        case_id=case_id,
        event_id=event1.id,
        detection_type="test1",
        severity="CRITICAL",
        confidence=100,
    )
    det2 = Detection(
        case_id=case_id,
        event_id=event1.id,
        detection_type="test2",
        severity="CRITICAL",
        confidence=80,
    )
    db_session.add_all([det1, det2])
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/timeline?severity=CRITICAL")
    assert resp.status_code == 200
    data = resp.json()

    # It must return the event exactly once despite multiple matching detections
    assert len(data) == 1
    assert data[0]["id"] == str(event1.id)


def test_timeline_incident_filter_case_isolation(db_session):
    case_a = _create_case(db_session)
    evidence_a = _create_evidence(db_session, case_a)
    event_a = _create_event(db_session, case_a, evidence_a)

    case_b = _create_case(db_session)
    evidence_b = _create_evidence(db_session, case_b)
    event_b = _create_event(db_session, case_b, evidence_b)

    incident_b = Incident(
        case_id=case_b,
        title="Case B incident",
        severity="HIGH",
        confidence=90,
        status="OPEN",
    )
    db_session.add(incident_b)
    db_session.flush()

    incident_b.events.append(db_session.get(Event, event_b))
    db_session.commit()

    resp = client.get(
        f"/cases/{case_a}/timeline?incident_id={incident_b.id}"
    )

    assert resp.status_code == 200
    assert resp.json() == []


def test_risk_missing_case_not_found():
    random_id = str(uuid4())
    resp = client.get(f"/cases/{random_id}/risk")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Case not found"