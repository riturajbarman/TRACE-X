import uuid
from datetime import datetime, timezone
from fastapi import status

from app.domain.event.models import Event


import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.domain.case.models import Case, CaseStatus
from app.domain.evidence.models import Evidence

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_case(test_db):
    c = Case(title="Test Case", status=CaseStatus.OPEN, created_by="pytest")
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c

@pytest.fixture
def test_evidence(test_db, test_case):
    e = Evidence(case_id=test_case.id, name="test.evtx", sha256=str(uuid.uuid4())[:32], size_bytes=100)
    test_db.add(e)
    test_db.commit()
    test_db.refresh(e)
    return e

def test_get_graph_not_found(client, test_db):
    """Test getting a graph for non-existent case returns 404."""
    response = client.get(f"/cases/{uuid.uuid4()}/graph")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_graph_empty_case(client, test_db, test_case):
    """Test getting graph for empty case returns empty graph."""
    response = client.get(f"/cases/{test_case.id}/graph")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["case_id"] == str(test_case.id)
    assert data["node_count"] == 0
    assert data["nodes"] == []
    assert data["edges"] == []


def test_get_graph_with_events(client, test_db, test_case, test_evidence):
    """Test getting graph returns events and JSONB edges."""
    
    # Insert some data manually
    ev1 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="test",
        source="test",
        timestamp=datetime.now(timezone.utc),
        data={"process_name": "malware.exe"}
    )
    ev2 = Event(
        case_id=test_case.id,
        evidence_id=test_evidence.id,
        event_type="test2",
        source="test",
        timestamp=datetime.now(timezone.utc),
        data={"process_name": "malware.exe"}
    )
    test_db.add_all([ev1, ev2])
    test_db.commit()

    # 1. Full graph
    response = client.get(f"/cases/{test_case.id}/graph")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["node_count"] == 2
    assert data["edge_count"] == 1
    
    # 2. Filter nodes
    response = client.get(f"/cases/{test_case.id}/graph?node_types=incident")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["node_count"] == 0
    assert data["edge_count"] == 0
    
    # 3. Disable shared entities
    response = client.get(f"/cases/{test_case.id}/graph?include_shared_entities=false")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["node_count"] == 2
    assert data["edge_count"] == 0  # Edge was stripped

