from datetime import datetime, timezone
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.case.models import Case, CaseStatus
from app.domain.evidence.models import Evidence

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
        title="Processing Test Case",
        description="Testing MVP orchestrator",
        status=CaseStatus.OPEN,
        created_by="pytest",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return str(case.id)

def test_process_evidence_not_found():
    resp = client.post(f"/evidence/{uuid4()}/process")
    assert resp.status_code == 404

def test_process_evidence_no_file(db_session, tmp_path):
    # This will fail since no file is actually on disk to extract
    case_id = _create_case(db_session)
    evidence = Evidence(
        case_id=case_id,
        name="dummy.evtx",
        size_bytes=100,
        source="local",
        sha256=uuid4().hex,
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    resp = client.post(f"/evidence/{evidence.id}/process")
    assert resp.status_code == 500
    assert "Original evidence file missing" in resp.json()["detail"]
