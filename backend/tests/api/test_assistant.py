"""
Phase 11 — AI Investigation Assistant API tests.
"""
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.cases import get_assistant_provider
from app.core.database import SessionLocal
from app.domain.assistant.provider import (
    AssistantProvider,
    ProviderResult,
    ProviderTimeoutError,
)
from app.domain.case.models import Case, CaseStatus
from app.main import app


class _FixedProvider(AssistantProvider):
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    @property
    def name(self) -> str:
        return "fake"

    def answer(self, *, system_prompt, context, question):
        if self._error is not None:
            raise self._error
        return self._result


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
    c = Case(title="Assistant API Test Case", status=CaseStatus.OPEN, created_by="pytest")
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_assistant_provider, None)


def _override_provider(provider: AssistantProvider) -> None:
    app.dependency_overrides[get_assistant_provider] = lambda: provider


def test_assistant_query_unknown_case_returns_404(client):
    response = client.post(
        f"/cases/{uuid.uuid4()}/assistant/query",
        json={"question": "What happened?"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_assistant_query_malformed_request_returns_422(client, test_case):
    # Empty question violates min_length=1
    response = client.post(
        f"/cases/{test_case.id}/assistant/query",
        json={"question": ""},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing field entirely
    response2 = client.post(f"/cases/{test_case.id}/assistant/query", json={})
    assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_assistant_query_valid_returns_grounded_response(client, test_case):
    _override_provider(
        _FixedProvider(result=ProviderResult(answer="All quiet.", claims=[], model="fake-model"))
    )
    response = client.post(
        f"/cases/{test_case.id}/assistant/query",
        json={"question": "Is there anything suspicious?"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["case_id"] == str(test_case.id)
    assert data["answer"] == "All quiet."
    assert data["provider"] == "fake"
    assert data["grounding_status"] in ("ok", "partial", "unavailable")
    assert data["claims"] == []


def test_assistant_query_provider_failure_returns_200_unavailable(client, test_case):
    _override_provider(_FixedProvider(error=ProviderTimeoutError("too slow")))
    response = client.post(
        f"/cases/{test_case.id}/assistant/query",
        json={"question": "Is there anything suspicious?"},
    )
    # Provider failure must not break the endpoint — 200 with an explicit
    # unavailable grounding status, never a 5xx.
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] == "unavailable"
    assert data["claims"] == []


def test_assistant_query_no_provider_configured_is_graceful(client, test_case):
    # No override registered -> falls through to get_assistant_provider(),
    # which returns UnconfiguredProvider when ANTHROPIC_API_KEY is unset in
    # this test environment.
    response = client.post(
        f"/cases/{test_case.id}/assistant/query",
        json={"question": "Is there anything suspicious?"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] == "unavailable"


def test_assistant_response_schema_separate_from_other_endpoints(client, test_case):
    _override_provider(
        _FixedProvider(result=ProviderResult(answer="x", claims=[], model="m"))
    )
    assistant_resp = client.post(
        f"/cases/{test_case.id}/assistant/query", json={"question": "q?"}
    ).json()
    risk_resp = client.get(f"/cases/{test_case.id}/risk").json()
    graph_resp = client.get(f"/cases/{test_case.id}/graph").json()

    assert "grounding_status" in assistant_resp
    assert "grounding_status" not in risk_resp
    assert "grounding_status" not in graph_resp
    assert "risk_score" not in assistant_resp
    assert "nodes" not in assistant_resp
