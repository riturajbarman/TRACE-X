from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def evidence_payload(**overrides):
    payload = {
        "name": "test-evidence",
        "description": "Test forensic evidence",
        "sha256": uuid4().hex * 2,
        "size_bytes": 1024,
        "source": "pytest",
    }
    payload.update(overrides)
    return payload


def test_create_evidence():
    response = client.post(
        "/evidence",
        json=evidence_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert "id" in data
    assert data["name"] == "test-evidence"
    assert data["description"] == "Test forensic evidence"
    assert data["size_bytes"] == 1024
    assert data["source"] == "pytest"
    assert data["status"] == "PENDING"


def test_get_evidence():
    create_response = client.post(
        "/evidence",
        json=evidence_payload(),
    )

    assert create_response.status_code == 201

    evidence_id = create_response.json()["id"]

    response = client.get(f"/evidence/{evidence_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == evidence_id
    assert data["name"] == "test-evidence"
    assert data["status"] == "PENDING"


def test_get_nonexistent_evidence():
    evidence_id = uuid4()

    response = client.get(f"/evidence/{evidence_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Evidence not found"


def test_duplicate_sha256():
    payload = evidence_payload()

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
def test_list_evidence():
    client.post(
        "/evidence",
        json=evidence_payload(),
    )

    client.post(
        "/evidence",
        json=evidence_payload(),
    )

    response = client.get("/evidence")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 2


def test_list_evidence_pagination():
    for _ in range(3):
        response = client.post(
            "/evidence",
            json=evidence_payload(),
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