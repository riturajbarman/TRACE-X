"""
Phase 11 — AI Investigation Assistant service.

Orchestrates: bounded context assembly -> provider call -> grounding
validation -> AssistantQueryResponse.

This service is read-only with respect to all forensic data. The only
database write it performs is an audit-log row (AI_QUERY_EXECUTED) —
never a change to events, detections, IOCs, risk, timeline, or graph data.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.domain.assistant.context import build_context
from app.domain.assistant.grounding import validate_claims
from app.domain.assistant.provider import (
    AssistantProvider,
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.domain.assistant.schemas import AssistantQueryResponse
from app.domain.audit.service import AuditService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the TRACE-X AI Investigation Assistant, embedded in a digital \
forensics platform.

You are NOT a forensic authority. You may only reason over the structured, \
already-processed TRACE-X data given to you below in CASE CONTEXT — you \
have not seen, and must never claim to have seen, any raw evidence file.

Rules you must always follow:
1. Never invent events, timestamps, IP addresses, files, registry keys, \
IOCs, attack actions, or any other fact that is not present in CASE \
CONTEXT.
2. Every claim you produce must have exactly one type:
   - "observed": a fact directly present in CASE CONTEXT. Every "observed" \
claim MUST include the id(s) of the supporting TRACE-X object(s) (an \
event_id, detection_id, ioc_id, incident_id, or evidence_id that literally \
appears in CASE CONTEXT) in its refs list.
   - "inference": a conclusion you drew from combining multiple observed \
facts. Include supporting object ids in refs where possible.
   - "recommendation": a suggested next investigative action for the human \
investigator. This is advice, not a finding — never phrase it as something \
that already happened.
3. Never present an inference or a recommendation as observed evidence.
4. Only cite ids that literally appear in CASE CONTEXT. Never fabricate an \
id.
5. If CASE CONTEXT is incomplete, empty, or does not answer the question, \
say so explicitly in your answer rather than guessing.
6. You cannot change, create, or delete any TRACE-X record. You are a \
read-only, advisory layer for a human investigator — always write as an \
assistant offering analysis, not as the system of record.
"""


class AssistantService:
    def __init__(self, session: Session, provider: AssistantProvider) -> None:
        self.session = session
        self.provider = provider
        self.audit_service = AuditService(session)

    def query(self, case_id: uuid.UUID, question: str) -> AssistantQueryResponse | None:
        """Answer one question about a case.

        Returns None if the case does not exist — callers should map that
        to an HTTP 404, matching every other /cases/{case_id}/... endpoint.
        """
        context = build_context(self.session, case_id)
        if context is None:
            return None

        try:
            result = self.provider.answer(
                system_prompt=SYSTEM_PROMPT,
                context=context.payload,
                question=question,
            )
        except ProviderTimeoutError as exc:
            return self._unavailable(case_id, "The AI assistant timed out. Please try again.", exc)
        except ProviderUnavailableError as exc:
            return self._unavailable(
                case_id, "The AI assistant is temporarily unavailable.", exc
            )
        except ProviderResponseError as exc:
            return self._unavailable(
                case_id, "The AI assistant returned an unusable response.", exc
            )
        except ProviderError as exc:  # pragma: no cover - defensive fallback
            return self._unavailable(case_id, "The AI assistant is temporarily unavailable.", exc)

        claims, grounding_status, warnings = validate_claims(result.claims, context.known_ids)

        self._record_audit(
            case_id=case_id,
            question_length=len(question),
            grounding_status=grounding_status,
            claim_count=len(claims),
            outcome="SUCCESS",
        )

        return AssistantQueryResponse(
            case_id=case_id,
            answer=result.answer,
            claims=claims,
            grounding_status=grounding_status,
            provider=self.provider.name,
            model=result.model,
            warnings=warnings,
        )

    def _unavailable(
        self, case_id: uuid.UUID, message: str, exc: Exception
    ) -> AssistantQueryResponse:
        # Log the real reason server-side only — never echo raw provider
        # exception text (which could include request internals) back to
        # the client.
        logger.warning("assistant provider failure for case %s: %s", case_id, exc)
        self._record_audit(
            case_id=case_id,
            question_length=None,
            grounding_status="unavailable",
            claim_count=0,
            outcome="FAILURE",
        )
        return AssistantQueryResponse(
            case_id=case_id,
            answer=message,
            claims=[],
            grounding_status="unavailable",
            provider=self.provider.name,
            model=None,
            warnings=[],
        )

    def _record_audit(
        self,
        case_id: uuid.UUID,
        question_length: int | None,
        grounding_status: str,
        claim_count: int,
        outcome: str,
    ) -> None:
        # An assistant invocation is a system-log entry alongside
        # CASE_CREATED / EVIDENCE_INGESTED etc — never a forensic custody
        # record, and never contains the question text, secrets, or raw
        # evidence.
        try:
            self.audit_service.record_event(
                action="AI_QUERY_EXECUTED",
                entity_type="case",
                entity_id=case_id,
                outcome=outcome,
                details={
                    "provider": self.provider.name,
                    "grounding_status": grounding_status,
                    "claim_count": claim_count,
                    "question_length": question_length,
                },
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
