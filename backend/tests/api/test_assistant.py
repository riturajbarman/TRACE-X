"""
Phase 11/12 — AI Investigation Assistant API tests.
"""
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.cases import get_assistant_provider, get_knowledge_service
from app.core.database import SessionLocal
from app.domain.assistant.provider import (
    AssistantProvider,
    ProviderClaim,
    ProviderKnowledgeRef,
    ProviderResult,
    ProviderTimeoutError,
)
from app.domain.case.models import Case, CaseStatus
from app.domain.knowledge.schemas import KnowledgeCitation
from app.domain.knowledge.service import KnowledgeContext, KnowledgeLookupError, KnowledgeService
from app.main import app


class _FixedProvider(AssistantProvider):
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.received_knowledge_context = None

    @property
    def name(self) -> str:
        return "fake"

    def answer(self, *, system_prompt, context, knowledge_context, question):
        self.received_knowledge_context = knowledge_context
        if self._error is not None:
            raise self._error
        return self._result


class _EmptyKnowledgeService(KnowledgeService):
    def __init__(self):
        pass

    def query(self, question: str) -> KnowledgeContext:
        return KnowledgeContext(context_block="", citations=[])


class _FailingKnowledgeService(KnowledgeService):
    def __init__(self):
        pass

    def query(self, question: str) -> KnowledgeContext:
        raise KnowledgeLookupError("simulated outage")


class _FixedKnowledgeService(KnowledgeService):
    def __init__(self, citations, context_block="knowledge block"):
        self._citations = citations
        self._context_block = context_block

    def query(self, question: str) -> KnowledgeContext:
        return KnowledgeContext(context_block=self._context_block, citations=list(self._citations))


def _citation() -> KnowledgeCitation:
    return KnowledgeCitation(
        source_id="mitre_attack_enterprise",
        source_type="mitre_attack",
        document_id="T1059",
        version="19.2",
        title="Command and Scripting Interpreter",
        reference="https://attack.mitre.org/techniques/T1059/",
    )


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
    app.dependency_overrides.pop(get_knowledge_service, None)


def _override_provider(provider: AssistantProvider) -> None:
    app.dependency_overrides[get_assistant_provider] = lambda: provider


def _override_knowledge(service: KnowledgeService) -> None:
    app.dependency_overrides[get_knowledge_service] = lambda: service


# ---------------------------------------------------------------------
# 46/47/48. Existing endpoint remains functional — 404 / 422
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# 49. Response schema is valid; existing behavior intact
# ---------------------------------------------------------------------

def test_assistant_query_valid_returns_grounded_response(client, test_case):
    _override_provider(
        _FixedProvider(result=ProviderResult(answer="All quiet.", claims=[], model="fake-model"))
    )
    _override_knowledge(_EmptyKnowledgeService())
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
    _override_knowledge(_EmptyKnowledgeService())
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
    # No provider override registered -> falls through to
    # get_assistant_provider(), which returns UnconfiguredProvider when
    # ANTHROPIC_API_KEY is unset in this test environment.
    _override_knowledge(_EmptyKnowledgeService())
    response = client.post(
        f"/cases/{test_case.id}/assistant/query",
        json={"question": "Is there anything suspicious?"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] == "unavailable"


def test_assistant_response_schema_separate_from_other_endpoints(client, test_case):
    _override_provider(_FixedProvider(result=ProviderResult(answer="x", claims=[], model="m")))
    _override_knowledge(_EmptyKnowledgeService())
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


# ---------------------------------------------------------------------
# 50. External citations serialize correctly over the wire
# ---------------------------------------------------------------------

def test_external_citations_serialize_correctly(client, test_case):
    real = _citation()
    _override_provider(
        _FixedProvider(
            result=ProviderResult(
                answer="T1059 is a common execution technique.",
                claims=[
                    ProviderClaim(
                        text="T1059 covers command/script interpreters.",
                        type="external_knowledge",
                        knowledge_refs=[
                            ProviderKnowledgeRef(
                                source_id=real.source_id, document_id=real.document_id, version=real.version
                            )
                        ],
                    )
                ],
                model="m",
            )
        )
    )
    _override_knowledge(_FixedKnowledgeService(citations=[real]))
    response = client.post(f"/cases/{test_case.id}/assistant/query", json={"question": "What is T1059?"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] == "ok"
    claim = data["claims"][0]
    assert claim["type"] == "external_knowledge"
    assert claim["refs"] == []
    assert claim["knowledge_refs"][0]["document_id"] == "T1059"
    assert claim["knowledge_refs"][0]["source_type"] == "mitre_attack"
    assert claim["knowledge_refs"][0]["retrieval_method"] == "deterministic_lookup"


def test_invented_citation_rejected_at_api_level(client, test_case):
    real = _citation()
    _override_provider(
        _FixedProvider(
            result=ProviderResult(
                answer="x",
                claims=[
                    ProviderClaim(
                        text="fabricated",
                        type="external_knowledge",
                        knowledge_refs=[ProviderKnowledgeRef(source_id="fake", document_id="T0000", version="0.0")],
                    )
                ],
                model="m",
            )
        )
    )
    _override_knowledge(_FixedKnowledgeService(citations=[real]))
    response = client.post(f"/cases/{test_case.id}/assistant/query", json={"question": "q?"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    claim = data["claims"][0]
    assert claim["knowledge_refs"] == []
    assert claim["type"] == "inference"
    assert data["grounding_status"] == "partial"


# ---------------------------------------------------------------------
# 51. Retrieval (knowledge) failure does not produce a 5xx
# ---------------------------------------------------------------------

def test_knowledge_retrieval_failure_does_not_5xx(client, test_case):
    _override_provider(
        _FixedProvider(result=ProviderResult(answer="Answered from case data.", claims=[], model="m"))
    )
    _override_knowledge(_FailingKnowledgeService())
    response = client.post(f"/cases/{test_case.id}/assistant/query", json={"question": "q?"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] in ("ok", "partial", "unavailable")
    assert any("external knowledge" in w.lower() for w in data["warnings"])


# ---------------------------------------------------------------------
# 52. No secrets returned
# ---------------------------------------------------------------------

def test_no_secrets_in_response_at_api_level(client, test_case, monkeypatch):
    secret = "sk-ant-api-level-secret"
    monkeypatch.setattr("app.core.config.ASSISTANT_API_KEY", secret)
    _override_provider(_FixedProvider(error=ProviderTimeoutError(f"timeout near key {secret}")))
    _override_knowledge(_EmptyKnowledgeService())
    response = client.post(f"/cases/{test_case.id}/assistant/query", json={"question": "q?"})
    assert secret not in response.text


# ---------------------------------------------------------------------
# Real end-to-end with the actual bundled MITRE snapshot (no test double
# for the knowledge layer) — proves the production wiring works, not just
# the mocked paths.
# ---------------------------------------------------------------------

def test_real_knowledge_service_end_to_end_with_fixed_provider(client, test_case):
    real_citation_key_source = "mitre_attack_enterprise"
    _override_provider(
        _FixedProvider(
            result=ProviderResult(
                answer="T1059 covers command and scripting interpreters.",
                claims=[
                    ProviderClaim(
                        text="T1059 is a MITRE ATT&CK execution technique.",
                        type="external_knowledge",
                        knowledge_refs=[
                            ProviderKnowledgeRef(source_id=real_citation_key_source, document_id="T1059", version="19.2")
                        ],
                    )
                ],
                model="m",
            )
        )
    )
    # No knowledge override — uses the real get_knowledge_service() wired
    # into the actual endpoint, backed by the real bundled snapshot.
    response = client.post(f"/cases/{test_case.id}/assistant/query", json={"question": "What is T1059?"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["grounding_status"] == "ok"
    assert data["claims"][0]["type"] == "external_knowledge"
    assert data["claims"][0]["knowledge_refs"][0]["document_id"] == "T1059"
    assert data["claims"][0]["knowledge_refs"][0]["title"] == "Command and Scripting Interpreter"
