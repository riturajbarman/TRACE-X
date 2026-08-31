"""
Phase 13 — Investigator Dashboard API tests.

Covers the read-only, case-scoped endpoints added in Phase 13:
  GET /cases/{case_id}/summary   (extended: detection/ioc/incident/failed counts)
  GET /cases/{case_id}/detections
  GET /cases/{case_id}/iocs
  GET /cases/{case_id}/incidents
  GET /cases/{case_id}/audit

All of these are read-only aggregations over already-existing forensic
data (Phase 5/6/8 Detection/IOC/Incident, Phase 2 Evidence, and the
existing audit log) — no new tables, no mutation, no forensic
recomputation. See backend/app/domain/case/repository.py,
backend/app/domain/detection/repository.py, and
backend/app/domain/audit/repository.py.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.audit.models import AuditEvent
from app.domain.case.models import Case, CaseStatus
from app.domain.detection.models import IOC, Detection, Incident
from app.domain.evidence.models import Evidence, EvidenceStatus
from app.domain.event.models import Event

client = TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_case(db, title="Dashboard Test Case") -> str:
    case = Case(title=title, status=CaseStatus.OPEN, created_by="pytest")
    db.add(case)
    db.flush()
    return str(case.id)


def _create_evidence(db, case_id: str, status: EvidenceStatus = EvidenceStatus.READY) -> str:
    evidence = Evidence(
        case_id=case_id,
        name="dashboard_test.dd",
        size_bytes=1024,
        source="local",
        sha256=uuid4().hex,
        status=status,
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
        data={"test": "data"},
    )
    db.add(event)
    db.flush()
    return str(event.id)


# ---------------------------------------------------------------------
# A. Case summary API contract
# ---------------------------------------------------------------------

def test_case_summary_includes_all_dashboard_counts(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)
    _create_evidence(db_session, case_id, status=EvidenceStatus.FAILED)
    event_id = _create_event(db_session, case_id, evidence_id)

    db_session.add(Detection(case_id=case_id, event_id=event_id, detection_type="rule_match", severity="HIGH", confidence=90))
    db_session.add(IOC(case_id=case_id, event_id=event_id, ioc_type="ip", value="1.2.3.4", severity="HIGH", confidence=90))
    db_session.add(Incident(case_id=case_id, title="Test Incident", severity="HIGH", confidence=90, status="OPEN"))
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["evidence_count"] == 2
    assert data["event_count"] == 1
    assert data["detection_count"] == 1
    assert data["ioc_count"] == 1
    assert data["incident_count"] == 1
    assert data["failed_evidence_count"] == 1


def test_case_summary_missing_case_returns_404():
    resp = client.get(f"/cases/{uuid4()}/summary")
    assert resp.status_code == 404


def test_case_summary_empty_case_returns_zero_counts(db_session):
    case_id = _create_case(db_session)
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    for field in ("evidence_count", "event_count", "detection_count", "ioc_count", "incident_count", "failed_evidence_count"):
        assert data[field] == 0


# ---------------------------------------------------------------------
# B. Detections endpoint
# ---------------------------------------------------------------------

def test_list_case_detections(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)
    event_id = _create_event(db_session, case_id, evidence_id)
    db_session.add(Detection(case_id=case_id, event_id=event_id, detection_type="rule_match", rule_id="R1", severity="HIGH", confidence=90))
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/detections")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["rule_id"] == "R1"
    assert data[0]["case_id"] == case_id


def test_list_case_detections_missing_case_returns_404():
    resp = client.get(f"/cases/{uuid4()}/detections")
    assert resp.status_code == 404


def test_list_case_detections_empty_case_returns_empty_list(db_session):
    case_id = _create_case(db_session)
    db_session.commit()
    resp = client.get(f"/cases/{case_id}/detections")
    assert resp.status_code == 200
    assert resp.json() == []


def test_detections_case_isolation(db_session):
    case_a = _create_case(db_session)
    evidence_a = _create_evidence(db_session, case_a)
    event_a = _create_event(db_session, case_a, evidence_a)
    db_session.add(Detection(case_id=case_a, event_id=event_a, detection_type="rule_match", severity="HIGH", confidence=90))
    case_b = _create_case(db_session)
    db_session.commit()

    resp = client.get(f"/cases/{case_b}/detections")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------
# C. IOCs endpoint
# ---------------------------------------------------------------------

def test_list_case_iocs(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)
    event_id = _create_event(db_session, case_id, evidence_id)
    db_session.add(IOC(case_id=case_id, event_id=event_id, ioc_type="domain", value="evil.example", severity="CRITICAL", confidence=100))
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/iocs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["value"] == "evil.example"
    assert data[0]["case_id"] == case_id


def test_list_case_iocs_missing_case_returns_404():
    resp = client.get(f"/cases/{uuid4()}/iocs")
    assert resp.status_code == 404


def test_iocs_case_isolation(db_session):
    case_a = _create_case(db_session)
    evidence_a = _create_evidence(db_session, case_a)
    event_a = _create_event(db_session, case_a, evidence_a)
    db_session.add(IOC(case_id=case_a, event_id=event_a, ioc_type="ip", value="9.9.9.9", severity="HIGH", confidence=90))
    case_b = _create_case(db_session)
    db_session.commit()

    resp = client.get(f"/cases/{case_b}/iocs")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------
# Incidents endpoint (Phase 13 correction: Incident IS a first-class
# model — backend/app/domain/detection/models.py — already produced by
# the Phase 8 correlation engine. See final report §2.)
# ---------------------------------------------------------------------

def test_list_case_incidents(db_session):
    case_id = _create_case(db_session)
    db_session.add(Incident(case_id=case_id, title="Suspicious Login Chain", severity="CRITICAL", confidence=95, status="OPEN"))
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/incidents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Suspicious Login Chain"
    assert data[0]["case_id"] == case_id


def test_list_case_incidents_missing_case_returns_404():
    resp = client.get(f"/cases/{uuid4()}/incidents")
    assert resp.status_code == 404


def test_incidents_case_isolation(db_session):
    case_a = _create_case(db_session)
    db_session.add(Incident(case_id=case_a, title="Case A Incident", severity="HIGH", confidence=80, status="OPEN"))
    case_b = _create_case(db_session)
    db_session.commit()

    resp = client.get(f"/cases/{case_b}/incidents")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------
# D. Audit endpoint
# ---------------------------------------------------------------------

def test_list_case_audit_includes_case_created_event(db_session):
    # Going through the real API (not the ORM directly) so the real
    # CASE_CREATED audit event is recorded exactly as production does it.
    resp = client.post("/cases", json={"title": "Audited Case"})
    assert resp.status_code == 201
    case_id = resp.json()["id"]

    audit_resp = client.get(f"/cases/{case_id}/audit")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    assert any(e["action"] == "CASE_CREATED" for e in events)


def test_list_case_audit_includes_evidence_scoped_event(db_session):
    case_id = _create_case(db_session)
    db_session.commit()
    evidence = Evidence(case_id=case_id, name="a.dd", size_bytes=10, source="local", sha256=uuid4().hex)
    db_session.add(evidence)
    db_session.flush()
    db_session.add(
        AuditEvent(
            action="EVIDENCE_INGESTED",
            entity_type="evidence",
            entity_id=evidence.id,
            outcome="SUCCESS",
            details={"case_id": case_id},
        )
    )
    db_session.commit()

    resp = client.get(f"/cases/{case_id}/audit")
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["action"] == "EVIDENCE_INGESTED" for e in events)


def test_list_case_audit_missing_case_returns_404():
    resp = client.get(f"/cases/{uuid4()}/audit")
    assert resp.status_code == 404


def test_list_case_audit_empty_case_returns_empty_list(db_session):
    case_id = _create_case(db_session)
    db_session.commit()
    resp = client.get(f"/cases/{case_id}/audit")
    assert resp.status_code == 200
    assert resp.json() == []


def test_audit_case_isolation_evidence_scoped_event(db_session):
    """An evidence-scoped audit event belonging to case A's evidence must
    never appear in case B's audit trail — this is the exact leakage
    pattern the union query in AuditRepository.list_by_case must prevent."""
    case_a = _create_case(db_session)
    case_b = _create_case(db_session)
    db_session.commit()

    evidence_a = Evidence(case_id=case_a, name="a.dd", size_bytes=10, source="local", sha256=uuid4().hex)
    db_session.add(evidence_a)
    db_session.flush()
    db_session.add(
        AuditEvent(
            action="EVIDENCE_INGESTED",
            entity_type="evidence",
            entity_id=evidence_a.id,
            outcome="SUCCESS",
            details={"case_id": case_a},
        )
    )
    db_session.commit()

    resp_b = client.get(f"/cases/{case_b}/audit")
    assert resp_b.status_code == 200
    assert resp_b.json() == []


def test_audit_case_isolation_case_scoped_event(db_session):
    """A case-scoped audit event (e.g. CASE_STATUS_CHANGED) for case A
    must never appear in case B's audit trail."""
    case_a = _create_case(db_session)
    case_b = _create_case(db_session)
    db_session.commit()

    db_session.add(
        AuditEvent(
            action="CASE_STATUS_CHANGED",
            entity_type="case",
            entity_id=case_a,
            outcome="SUCCESS",
            details={"old_status": "OPEN", "new_status": "CLOSED"},
        )
    )
    db_session.commit()

    resp_b = client.get(f"/cases/{case_b}/audit")
    assert resp_b.status_code == 200
    assert resp_b.json() == []


# ---------------------------------------------------------------------
# I. Read-only behavior: dashboard GETs must never mutate forensic data
# ---------------------------------------------------------------------

def test_dashboard_endpoints_do_not_mutate_forensic_data(db_session):
    case_id = _create_case(db_session)
    evidence_id = _create_evidence(db_session, case_id)
    event_id = _create_event(db_session, case_id, evidence_id)
    db_session.add(Detection(case_id=case_id, event_id=event_id, detection_type="rule_match", severity="HIGH", confidence=90))
    db_session.add(IOC(case_id=case_id, event_id=event_id, ioc_type="ip", value="1.2.3.4", severity="HIGH", confidence=90))
    db_session.add(Incident(case_id=case_id, title="Inc", severity="HIGH", confidence=90, status="OPEN"))
    db_session.commit()

    def _row_counts():
        return {
            "evidence": db_session.query(Evidence).filter(Evidence.case_id == case_id).count(),
            "events": db_session.query(Event).filter(Event.case_id == case_id).count(),
            "detections": db_session.query(Detection).filter(Detection.case_id == case_id).count(),
            "iocs": db_session.query(IOC).filter(IOC.case_id == case_id).count(),
            "incidents": db_session.query(Incident).filter(Incident.case_id == case_id).count(),
        }

    before = _row_counts()

    for path in ("summary", "detections", "iocs", "incidents", "audit", "evidence", "timeline", "risk"):
        r = client.get(f"/cases/{case_id}/{path}")
        assert r.status_code == 200

    db_session.expire_all()
    after = _row_counts()
    assert before == after
