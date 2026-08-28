from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.case.models import Case, CaseStatus

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
        title="Report Test Case",
        description="Testing MVP reporting",
        status=CaseStatus.OPEN,
        created_by="pytest",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return str(case.id)

def test_get_case_report(db_session):
    case_id = _create_case(db_session)

    resp = client.get(f"/cases/{case_id}/report")
    assert resp.status_code == 200

    data = resp.json()
    assert data["case"]["id"] == case_id
    assert data["case"]["title"] == "Report Test Case"
    assert "risk_assessment" in data
    assert "evidence" in data
    assert "findings" in data
    assert "timeline_summary" in data

def test_get_case_report_not_found():
    resp = client.get(f"/cases/{uuid4()}/report")
    assert resp.status_code == 404

def test_get_case_report_invalid_format(db_session):
    case_id = _create_case(db_session)
    resp = client.get(f"/cases/{case_id}/report?format=pdf")
    assert resp.status_code == 400
    assert "Only JSON format" in resp.json()["detail"]
