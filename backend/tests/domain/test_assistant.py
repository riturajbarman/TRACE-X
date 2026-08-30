"""
Phase 11 — AI Investigation Assistant domain tests.

Covers: provider abstraction (mockable), grounding validation, service
orchestration (with a fake provider — no real network/API key required),
and the read-only/regression guarantee.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.core.database import SessionLocal
from app.domain.assistant.context import build_context
from app.domain.assistant.grounding import validate_claims
from app.domain.assistant.provider import (
    AssistantProvider,
    ProviderClaim,
    ProviderResponseError,
    ProviderResult,
    ProviderTimeoutError,
    ProviderUnavailableError,
    UnconfiguredProvider,
)
from app.domain.assistant.schemas import AssistantQueryResponse
from app.domain.assistant.service import AssistantService
from app.domain.case.models import Case, CaseStatus
from app.domain.detection.models import Detection
from app.domain.event.models import Event


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_case(test_db):
    c = Case(title="Assistant Test Case", status=CaseStatus.OPEN, created_by="pytest")
    test_db.add(c)
    test_db.commit()
    test_db.refresh(c)
    return c


@pytest.fixture
def test_event(test_db, test_case):
    e = Event(
        case_id=test_case.id,
        event_type="process_exec",
        source="test",
        timestamp=datetime.now(timezone.utc),
        data={"process_name": "evil.exe"},
    )
    test_db.add(e)
    test_db.commit()
    test_db.refresh(e)
    return e


@pytest.fixture
def test_detection(test_db, test_case, test_event):
    d = Detection(
        case_id=test_case.id,
        event_id=test_event.id,
        detection_type="rule",
        rule_id="RULE-1",
        severity="HIGH",
        confidence=80,
    )
    test_db.add(d)
    test_db.commit()
    test_db.refresh(d)
    return d


class FakeProvider(AssistantProvider):
    """Test double — never touches the network."""

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.received_context = None
        self.received_question = None

    @property
    def name(self) -> str:
        return "fake"

    def answer(self, *, system_prompt, context, question):
        self.received_context = context
        self.received_question = question
        if self._error is not None:
            raise self._error
        return self._result


# ---------------------------------------------------------------------
# 1. Provider abstraction is mockable
# ---------------------------------------------------------------------

def test_provider_is_mockable_without_network():
    fake = FakeProvider(result=ProviderResult(answer="hi", claims=[], model="fake-model"))
    result = fake.answer(system_prompt="sys", context={}, question="q?")
    assert result.answer == "hi"
    assert fake.received_question == "q?"


def test_unconfigured_provider_raises_unavailable():
    provider = UnconfiguredProvider()
    with pytest.raises(ProviderUnavailableError):
        provider.answer(system_prompt="sys", context={}, question="q?")


# ---------------------------------------------------------------------
# 2. Grounding validation
# ---------------------------------------------------------------------

def test_grounding_ok_when_all_refs_known():
    known = {"abc-1"}
    claims = [ProviderClaim(text="X happened", type="observed", refs=["abc-1"])]
    validated, gstatus, warnings = validate_claims(claims, known)
    assert gstatus == "ok"
    assert warnings == []
    assert validated[0].type == "observed"
    assert validated[0].refs == ["abc-1"]


def test_grounding_drops_unknown_ref_and_flags_partial():
    known = {"abc-1"}
    claims = [ProviderClaim(text="X happened", type="observed", refs=["abc-1", "made-up-id"])]
    validated, gstatus, warnings = validate_claims(claims, known)
    assert gstatus == "partial"
    assert validated[0].refs == ["abc-1"]
    assert any("did not match" in w for w in warnings)


def test_grounding_demotes_unsupported_observed_claim():
    known = {"abc-1"}
    claims = [ProviderClaim(text="Something happened", type="observed", refs=[])]
    validated, gstatus, warnings = validate_claims(claims, known)
    assert validated[0].type == "inference"  # never presented as observed w/o refs
    assert gstatus == "partial"
    assert any("downgraded" in w for w in warnings)


def test_grounding_never_invents_ids():
    known = {"real-id"}
    claims = [ProviderClaim(text="X", type="observed", refs=["fake-id-1", "fake-id-2"])]
    validated, _, _ = validate_claims(claims, known)
    assert validated[0].refs == []
    assert "fake-id-1" not in validated[0].refs


def test_grounding_recommendation_needs_no_refs():
    validated, gstatus, warnings = validate_claims(
        [ProviderClaim(text="Investigate further", type="recommendation", refs=[])],
        known_ids=set(),
    )
    assert validated[0].type == "recommendation"
    assert gstatus == "ok"
    assert warnings == []


def test_grounding_empty_claims_is_unavailable():
    validated, gstatus, warnings = validate_claims([], known_ids={"x"})
    assert validated == []
    assert gstatus == "unavailable"


# ---------------------------------------------------------------------
# 3. Context assembly — provenance preserved, bounded, case-scoped
# ---------------------------------------------------------------------

def test_build_context_returns_none_for_missing_case(test_db):
    assert build_context(test_db, uuid.uuid4()) is None


def test_build_context_carries_provenance_ids(test_db, test_case, test_event, test_detection):
    ctx = build_context(test_db, test_case.id)
    assert ctx is not None
    assert str(test_case.id) in ctx.known_ids
    assert str(test_event.id) in ctx.known_ids
    assert str(test_detection.id) in ctx.known_ids
    assert ctx.payload["case"]["id"] == str(test_case.id)
    assert ctx.payload["context_limits"]["max_events"] > 0


def test_build_context_does_not_leak_other_cases_data(test_db, test_case, test_event, test_detection):
    """Case isolation: a second case's events/detections must never appear
    in this case's context or known_ids, and grounding must not accept a
    reference to another case's object."""
    other_case = Case(title="Other Case", status=CaseStatus.OPEN, created_by="pytest")
    test_db.add(other_case)
    test_db.commit()
    test_db.refresh(other_case)

    other_event = Event(
        case_id=other_case.id,
        event_type="process_exec",
        source="test",
        timestamp=datetime.now(timezone.utc),
        data={"process_name": "other-case.exe"},
    )
    test_db.add(other_event)
    test_db.commit()
    test_db.refresh(other_event)
    other_detection = Detection(
        case_id=other_case.id,
        event_id=other_event.id,
        detection_type="rule",
        rule_id="RULE-OTHER",
        severity="CRITICAL",
        confidence=95,
    )
    test_db.add(other_detection)
    test_db.commit()
    test_db.refresh(other_detection)

    ctx = build_context(test_db, test_case.id)
    assert ctx is not None
    # This case's own data is present.
    assert str(test_event.id) in ctx.known_ids
    assert str(test_detection.id) in ctx.known_ids
    # The other case's data must never leak in.
    assert str(other_case.id) not in ctx.known_ids
    assert str(other_event.id) not in ctx.known_ids
    assert str(other_detection.id) not in ctx.known_ids
    assert str(other_event.id) not in str(ctx.payload)
    assert "other-case.exe" not in str(ctx.payload)

    # And a provider that cites the other case's object id must have it
    # stripped by grounding, never accepted as this case's evidence.
    fake = FakeProvider(
        result=ProviderResult(
            answer="x",
            claims=[
                ProviderClaim(text="Cross-case claim", type="observed", refs=[str(other_detection.id)])
            ],
            model="m",
        )
    )
    resp = AssistantService(test_db, fake).query(test_case.id, "question?")
    assert resp.claims[0].refs == []
    assert resp.claims[0].type == "inference"  # demoted: no valid same-case provenance
    assert resp.grounding_status == "partial"


# ---------------------------------------------------------------------
# 4/5/6. Service: valid query, provider timeout, provider error, malformed
# ---------------------------------------------------------------------

def test_service_valid_query_grounded_ok(test_db, test_case, test_event, test_detection):
    fake = FakeProvider(
        result=ProviderResult(
            answer="This case shows one high-severity detection.",
            claims=[
                ProviderClaim(
                    text="A HIGH severity rule detection was triggered.",
                    type="observed",
                    refs=[str(test_detection.id)],
                )
            ],
            model="fake-model-1",
        )
    )
    service = AssistantService(test_db, fake)
    resp = service.query(test_case.id, "What happened in this case?")
    assert resp.grounding_status == "ok"
    assert resp.claims[0].type == "observed"
    assert resp.claims[0].refs == [str(test_detection.id)]
    assert resp.provider == "fake"
    # Prove the provider actually received bounded, provenance-carrying context.
    assert str(test_detection.id) in str(fake.received_context)


def test_service_provider_timeout_is_unavailable_not_raised(test_db, test_case):
    fake = FakeProvider(error=ProviderTimeoutError("slow"))
    service = AssistantService(test_db, fake)
    resp = service.query(test_case.id, "question?")
    assert resp.grounding_status == "unavailable"
    assert resp.claims == []
    assert "temporarily" in resp.answer.lower() or "timed out" in resp.answer.lower()


def test_service_provider_error_is_unavailable_not_raised(test_db, test_case):
    fake = FakeProvider(error=ProviderUnavailableError("down"))
    service = AssistantService(test_db, fake)
    resp = service.query(test_case.id, "question?")
    assert resp.grounding_status == "unavailable"
    assert resp.claims == []


def test_service_malformed_provider_response_is_unavailable(test_db, test_case):
    fake = FakeProvider(error=ProviderResponseError("bad json"))
    service = AssistantService(test_db, fake)
    resp = service.query(test_case.id, "question?")
    assert resp.grounding_status == "unavailable"


def test_service_unknown_case_returns_none(test_db):
    fake = FakeProvider(result=ProviderResult(answer="x", claims=[], model="m"))
    service = AssistantService(test_db, fake)
    assert service.query(uuid.uuid4(), "question?") is None


# ---------------------------------------------------------------------
# 7/8. Nonexistent cited object id / observed claim without valid ref,
# exercised through the full service (not just grounding.py directly)
# ---------------------------------------------------------------------

def test_service_rejects_invented_object_id(test_db, test_case, test_event, test_detection):
    fake = FakeProvider(
        result=ProviderResult(
            answer="Suspicious activity found.",
            claims=[
                ProviderClaim(
                    text="An IOC was matched.",
                    type="observed",
                    refs=[str(uuid.uuid4())],  # never in this case's context
                )
            ],
            model="fake-model-1",
        )
    )
    service = AssistantService(test_db, fake)
    resp = service.query(test_case.id, "question?")
    assert resp.grounding_status == "partial"
    assert resp.claims[0].refs == []
    assert resp.claims[0].type == "inference"  # demoted: no valid provenance
    assert any("did not match" in w or "downgraded" in w for w in resp.warnings)


# ---------------------------------------------------------------------
# 9. Deterministic forensic data is unchanged by an assistant query
# ---------------------------------------------------------------------

def test_assistant_query_does_not_mutate_forensic_data(test_db, test_case, test_event, test_detection):
    from app.domain.detection.models import IOC, Incident

    def snapshot():
        return {
            "events": test_db.query(Event).filter(Event.case_id == test_case.id).count(),
            "detections": test_db.query(Detection).filter(Detection.case_id == test_case.id).count(),
            "iocs": test_db.query(IOC).filter(IOC.case_id == test_case.id).count(),
            "incidents": test_db.query(Incident).filter(Incident.case_id == test_case.id).count(),
            "event_data": test_event.data,
            "detection_severity": test_detection.severity,
        }

    before = snapshot()

    fake = FakeProvider(
        result=ProviderResult(
            answer="Summary.",
            claims=[ProviderClaim(text="X", type="observed", refs=[str(test_detection.id)])],
            model="m",
        )
    )
    AssistantService(test_db, fake).query(test_case.id, "question?")

    test_db.expire_all()
    after = snapshot()
    assert before == after


# ---------------------------------------------------------------------
# 10. API key is never returned or logged in the response
# ---------------------------------------------------------------------

def test_response_never_contains_api_key(test_db, test_case, monkeypatch):
    secret = "sk-ant-super-secret-test-key"
    monkeypatch.setattr("app.core.config.ASSISTANT_API_KEY", secret)

    fake = FakeProvider(result=ProviderResult(answer="ok", claims=[], model="m"))
    resp = AssistantService(test_db, fake).query(test_case.id, "question?")
    serialized = resp.model_dump_json()
    assert secret not in serialized

    unavailable_provider = FakeProvider(error=ProviderUnavailableError(f"failed with key {secret}"))
    resp2 = AssistantService(test_db, unavailable_provider).query(test_case.id, "question?")
    assert secret not in resp2.model_dump_json()


# ---------------------------------------------------------------------
# 11. Response schema is structurally separate from Risk/Graph/Report
# ---------------------------------------------------------------------

def test_assistant_schema_is_structurally_distinct():
    from app.domain.detection.schemas import RiskResponse
    from app.domain.graph.schemas import GraphResponse

    assistant_fields = set(AssistantQueryResponse.model_fields.keys())
    risk_fields = set(RiskResponse.model_fields.keys())
    graph_fields = set(GraphResponse.model_fields.keys())

    assert "grounding_status" in assistant_fields
    assert "claims" in assistant_fields
    # None of the deterministic response shapes carry the assistive fields,
    # and the assistant response carries none of the deterministic score/
    # graph fields — they cannot be confused for one another.
    assert "grounding_status" not in risk_fields
    assert "grounding_status" not in graph_fields
    assert "risk_score" not in assistant_fields
    assert "nodes" not in assistant_fields
