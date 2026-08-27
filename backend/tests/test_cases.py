from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_case():
    response = client.post(
        "/cases",
        json={
            "title": "Test Case",
            "description": "Test case description",
            "created_by": "pytest",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "Test Case"
    assert data["status"] == "OPEN"

def test_get_case():
    response = client.post("/cases", json={"title": "Test Case"})
    assert response.status_code == 201
    case_id = response.json()["id"]

    response = client.get(f"/cases/{case_id}")
    assert response.status_code == 200
    assert response.json()["id"] == case_id

def test_get_nonexistent_case():
    response = client.get(f"/cases/{uuid4()}")
    assert response.status_code == 404

def test_list_cases():
    client.post("/cases", json={"title": "Test Case 1"})
    client.post("/cases", json={"title": "Test Case 2"})
    response = client.get("/cases")
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_update_case_status():
    response = client.post("/cases", json={"title": "Test Case"})
    case_id = response.json()["id"]
    
    response = client.patch(f"/cases/{case_id}/status", json={"status": "CLOSED"})
    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"

    # Close to open should also work
    response2 = client.patch(f"/cases/{case_id}/status", json={"status": "OPEN"})
    assert response2.status_code == 200
    assert response2.json()["status"] == "OPEN"

def test_update_case_status_nonexistent():
    response = client.patch(f"/cases/{uuid4()}/status", json={"status": "CLOSED"})
    assert response.status_code == 404

def test_list_case_evidence():
    response = client.post("/cases", json={"title": "Test Case"})
    case_id = response.json()["id"]
    
    content = f"evidence for case {uuid4()}".encode()
    client.post(
        "/evidence/ingest",
        data={"case_id": case_id, "name": "ev1"},
        files={"file": ("ev1.txt", content, "text/plain")}
    )
    
    response = client.get(f"/cases/{case_id}/evidence")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "ev1"
