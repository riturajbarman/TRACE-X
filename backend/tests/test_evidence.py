import hashlib
from uuid import uuid4
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_test_case():
    response = client.post(
        "/cases",
        json={
            "title": f"Test Case {uuid4()}",
            "description": "Test forensic case",
            "created_by": "pytest",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]

def ingest_test_evidence(case_id=None, content=None, name="test-evidence"):
    if case_id is None:
        case_id = create_test_case()
    if content is None:
        content = f"TRACE-X forensic evidence test {uuid4()}".encode()
    
    response = client.post(
        "/evidence/ingest",
        data={
            "case_id": str(case_id),
            "name": name,
            "description": "Test forensic evidence",
            "source": "pytest",
        },
        files={
            "file": ("evidence.txt", content, "text/plain")
        }
    )
    assert response.status_code == 201
    return response.json()


def test_get_evidence():
    data = ingest_test_evidence()
    evidence_id = data["id"]

    response = client.get(f"/evidence/{evidence_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == evidence_id
    assert response_data["name"] == "test-evidence"
    assert response_data["status"] == "PENDING"

def test_get_nonexistent_evidence():
    response = client.get(f"/evidence/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"

def test_invalid_evidence_id():
    response = client.get("/evidence/not-a-uuid")
    assert response.status_code == 422

def test_duplicate_sha256():
    case_id = create_test_case()
    content = f"duplicate test content {uuid4()}".encode()
    
    first_response = client.post(
        "/evidence/ingest",
        data={"case_id": str(case_id), "name": "first-upload"},
        files={"file": ("first.txt", content, "text/plain")}
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/evidence/ingest",
        data={"case_id": str(case_id), "name": "duplicate-test"},
        files={"file": ("second.txt", content, "text/plain")}
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == "Evidence with this SHA-256 already exists"

def test_ingest_evidence_multipart():
    case_id = create_test_case()
    content = f"TRACE-X forensic evidence test {uuid4()}".encode()
    expected_sha256 = hashlib.sha256(content).hexdigest()

    response = client.post(
        "/evidence/ingest",
        data={
            "case_id": str(case_id),
            "name": "uploaded-evidence",
            "description": "Multipart upload test",
            "source": "pytest",
        },
        files={
            "file": ("evidence.txt", content, "text/plain")
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"] == case_id
    assert data["name"] == "uploaded-evidence"
    assert data["sha256"] == expected_sha256
    assert data["size_bytes"] == len(content)

def test_ingest_evidence_server_calculates_hash_and_size():
    case_id = create_test_case()
    content = f"server calculates everything {uuid4()}".encode()

    response = client.post(
        "/evidence/ingest",
        data={
            "case_id": str(case_id),
            "name": "server-calculated",
        },
        files={
            "file": ("sample.bin", content, "application/octet-stream")
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sha256"] == hashlib.sha256(content).hexdigest()
    assert data["size_bytes"] == len(content)

def test_ingest_evidence_stores_original():
    case_id = create_test_case()
    content = f"immutable original evidence {uuid4()}".encode()

    response = client.post(
        "/evidence/ingest",
        data={
            "case_id": str(case_id),
            "name": "stored-original",
        },
        files={
            "file": ("original.txt", content, "text/plain")
        },
    )
    assert response.status_code == 201
    evidence_id = response.json()["id"]

    from app.core.storage.factory import get_evidence_storage
    storage = get_evidence_storage()
    stored_path = storage.original_path(evidence_id)

    assert stored_path.is_file()
    assert stored_path.read_bytes() == content
    assert stored_path.stat().st_mode & 0o777 == 0o444

def test_ingest_nonexistent_case():
    content = b"orphan evidence"
    response = client.post(
        "/evidence/ingest",
        data={
            "case_id": str(uuid4()),
            "name": "missing-case",
        },
        files={
            "file": ("missing.txt", content, "text/plain")
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Case not found"

def test_list_evidence():
    case_id = create_test_case()
    ingest_test_evidence(case_id)
    ingest_test_evidence(case_id)

    response = client.get("/evidence")
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_list_evidence_pagination():
    case_id = create_test_case()
    for _ in range(3):
        ingest_test_evidence(case_id)

    response = client.get("/evidence?limit=2&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_list_evidence_invalid_pagination():
    assert client.get("/evidence?limit=0").status_code == 422
    assert client.get("/evidence?limit=101").status_code == 422
    assert client.get("/evidence?offset=-1").status_code == 422

def test_update_evidence_status():
    data = ingest_test_evidence()
    evidence_id = data["id"]
    case_id = data["case_id"]

    response = client.patch(f"/evidence/{evidence_id}/status?new_status=PROCESSING")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == evidence_id
    assert data["case_id"] == case_id
    assert data["status"] == "PROCESSING"

def test_update_evidence_status_to_ready():
    data = ingest_test_evidence()
    evidence_id = data["id"]
    case_id = data["case_id"]

    client.patch(f"/evidence/{evidence_id}/status?new_status=PROCESSING")
    response = client.patch(f"/evidence/{evidence_id}/status?new_status=READY")
    
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["status"] == "READY"
    assert data["processing_error"] is None

def test_invalid_evidence_status_transition():
    data = ingest_test_evidence()
    evidence_id = data["id"]

    response = client.patch(f"/evidence/{evidence_id}/status?new_status=READY")
    assert response.status_code == 409
    assert "Invalid evidence status transition" in response.json()["detail"]

def test_update_nonexistent_evidence_status():
    response = client.patch(f"/evidence/{uuid4()}/status?new_status=PROCESSING")
    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"

def test_ingest_exceeds_upload_limit():
    case_id = create_test_case()
    
    with patch("app.core.config.MAX_UPLOAD_SIZE_BYTES", 10):
        content = b"This is larger than 10 bytes"
        response = client.post(
            "/evidence/ingest",
            data={"case_id": str(case_id), "name": "large-file"},
            files={"file": ("evidence.txt", content, "text/plain")}
        )
        assert response.status_code == 413
        assert "maximum allowed size" in response.json()["detail"]