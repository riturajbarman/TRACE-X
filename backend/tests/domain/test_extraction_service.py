import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.domain.case.service import CaseService
from app.domain.evidence.service import EvidenceService
from app.domain.artifact.service import ExtractionService
from app.domain.artifact.models import ExtractionStatus


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def client():
    return TestClient(app)

def test_extraction_service_success(db: Session, tmp_path: Path):
    # Setup data
    case = CaseService(db).create(
        title="Extraction Test Case",
        description="",
        created_by="test",
    )
    
    evidence_path = tmp_path / "test.txt"
    content = f"dummy_{uuid.uuid4()}"
    evidence_path.write_text(content)
    
    evidence = EvidenceService(db).ingest(
        case_id=case.id,
        name="test_ev",
        source_path=evidence_path,
    )
    
    service = ExtractionService(db)
    
    # Extract only filesystem metadata for this test
    results = service.extract(evidence.id, artifact_types=["filesystem"])
    
    assert len(results) == 1
    assert results[0].artifact_type == "filesystem"
    assert results[0].extraction_status == ExtractionStatus.SUCCESS
    assert results[0].record_count == 1
    assert results[0].data[0]["filename"] == "original"





def test_extraction_service_invalid_evidence(db: Session):
    service = ExtractionService(db)
    
    with pytest.raises(ValueError, match="Evidence not found"):
        service.extract(uuid.uuid4())


def test_extraction_service_missing_original(db: Session, tmp_path: Path, monkeypatch):
    # Setup data
    case = CaseService(db).create(
        title="Extraction Test Case",
        description="",
        created_by="test",
    )
    
    evidence_path = tmp_path / "test2.txt"
    content = f"dummy_{uuid.uuid4()}"
    evidence_path.write_text(content)
    
    evidence = EvidenceService(db).ingest(
        case_id=case.id,
        name="test_ev",
        source_path=evidence_path,
    )
    
    service = ExtractionService(db)
    
    # Manually delete original file to force FileNotFoundError
    original_path = service.storage.original_path(evidence.id)
    original_path.unlink()
    
    with pytest.raises(FileNotFoundError, match="Original evidence file missing"):
        service.extract(evidence.id)


def test_extract_api(client: TestClient, tmp_path: Path):
    # Setup via API
    case_resp = client.post(
        "/cases",
        json={"title": "API Extraction Case", "description": "", "created_by": "test"}
    )
    case_id = case_resp.json()["id"]
    
    content = f"api_dummy_content_for_extraction_{uuid.uuid4()}".encode()
    ev_resp = client.post(
        "/evidence/ingest",
        data={"case_id": str(case_id), "name": "test_api_ev", "source": "pytest"},
        files={"file": ("api_dummy.txt", content, "text/plain")}
    )
    evidence_id = ev_resp.json()["id"]
    
    response = client.post(
        f"/evidence/{evidence_id}/extract?artifact_types=filesystem"
    )
    
    assert response.status_code == 200, response.json()
    data = response.json()
    assert len(data) == 1
    assert data[0]["artifact_type"] == "filesystem"
    assert data[0]["extraction_status"] == "SUCCESS"
    assert len(data[0]["data"]) == 1
