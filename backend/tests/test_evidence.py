from uuid import uuid4

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


def evidence_payload(case_id=None, **overrides):
    if case_id is None:
        case_id = create_test_case()

    payload = {
        "case_id": str(case_id),
        "name": "test-evidence",
        "description": "Test forensic evidence",
        "sha256": uuid4().hex * 2,
        "size_bytes": 1024,
        "source": "pytest",
    }
    payload.update(overrides)
    return payload


def test_create_evidence():
    case_id = create_test_case()

    response = client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["case_id"] == case_id
    assert data["name"] == "test-evidence"
    assert data["description"] == "Test forensic evidence"
    assert data["size_bytes"] == 1024
    assert data["source"] == "pytest"
    assert data["status"] == "PENDING"


def test_get_evidence():
    case_id = create_test_case()

    create_response = client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    assert create_response.status_code == 201

    evidence_id = create_response.json()["id"]

    response = client.get(f"/evidence/{evidence_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == evidence_id
    assert data["case_id"] == case_id
    assert data["name"] == "test-evidence"
    assert data["status"] == "PENDING"


def test_get_nonexistent_evidence():
    evidence_id = uuid4()

    response = client.get(f"/evidence/{evidence_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"


def test_invalid_evidence_id():
    response = client.get("/evidence/not-a-uuid")

    assert response.status_code == 422


def test_invalid_evidence_input():
    payload = evidence_payload(
        name="",
        sha256="invalid",
        size_bytes=-1,
    )

    response = client.post(
        "/evidence",
        json=payload,
    )

    assert response.status_code == 422


def test_duplicate_sha256():
    case_id = create_test_case()
    payload = evidence_payload(case_id)

    first_response = client.post(
        "/evidence",
        json=payload,
    )

    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/evidence",
        json={
            **payload,
            "name": "duplicate-test",
        },
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "Evidence with this SHA-256 already exists"
    )


def test_list_evidence():
    case_id = create_test_case()

    client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    response = client.get("/evidence")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 2


def test_list_evidence_pagination():
    case_id = create_test_case()

    for _ in range(3):
        response = client.post(
            "/evidence",
            json=evidence_payload(case_id),
        )

        assert response.status_code == 201

    response = client.get("/evidence?limit=2&offset=0")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 2


def test_list_evidence_invalid_pagination():
    response = client.get("/evidence?limit=0")

    assert response.status_code == 422

    response = client.get("/evidence?limit=101")

    assert response.status_code == 422

    response = client.get("/evidence?offset=-1")

    assert response.status_code == 422


def test_update_evidence_status():
    case_id = create_test_case()

    create_response = client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    assert create_response.status_code == 201

    evidence_id = create_response.json()["id"]

    response = client.patch(
        f"/evidence/{evidence_id}/status?new_status=PROCESSING",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == evidence_id
    assert data["case_id"] == case_id
    assert data["status"] == "PROCESSING"


def test_update_evidence_status_to_ready():
    case_id = create_test_case()

    create_response = client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    assert create_response.status_code == 201

    evidence_id = create_response.json()["id"]

    processing_response = client.patch(
        f"/evidence/{evidence_id}/status?new_status=PROCESSING",
    )

    assert processing_response.status_code == 200

    response = client.patch(
        f"/evidence/{evidence_id}/status?new_status=READY",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["case_id"] == case_id
    assert data["status"] == "READY"
    assert data["processing_error"] is None


def test_invalid_evidence_status_transition():
    case_id = create_test_case()

    create_response = client.post(
        "/evidence",
        json=evidence_payload(case_id),
    )

    assert create_response.status_code == 201

    evidence_id = create_response.json()["id"]

    response = client.patch(
        f"/evidence/{evidence_id}/status?new_status=READY",
    )

    assert response.status_code == 409
    assert "Invalid evidence status transition" in response.json()["detail"]


def test_update_nonexistent_evidence_status():
    evidence_id = uuid4()

    response = client.patch(
        f"/evidence/{evidence_id}/status?new_status=PROCESSING",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"
