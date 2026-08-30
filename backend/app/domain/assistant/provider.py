"""
Phase 11 — AI Investigation Assistant provider abstraction.

The assistant domain must never depend on a specific vendor SDK directly.
`AssistantService` is always constructed with an `AssistantProvider`
implementation injected — it never imports a vendor SDK itself. This keeps
the core assistant logic (context assembly, grounding validation) fully
mockable in tests without any network access or API key.

Only one concrete provider is implemented for Phase 11 (Anthropic). Adding
another vendor later means adding another `AssistantProvider` subclass here
— nothing else in the assistant domain, API layer, or frontend needs to
change.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProviderClaim:
    """One factual claim as returned by the provider, before grounding validation."""
    text: str
    type: str  # "observed" | "inference" | "recommendation" — validated later by grounding.py
    refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProviderResult:
    """The provider's raw structured answer, before grounding validation."""
    answer: str
    claims: list[ProviderClaim]
    model: str


class ProviderError(Exception):
    """Base class for all assistant-provider failures."""


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the configured timeout."""


class ProviderUnavailableError(ProviderError):
    """The provider could not be reached, is unconfigured, or returned an
    auth/rate-limit/server error."""


class ProviderResponseError(ProviderError):
    """The provider responded, but its output could not be parsed into the
    expected structured shape."""


class AssistantProvider(ABC):
    """Thin abstraction over a concrete LLM backend."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short machine-readable provider identifier, e.g. "anthropic"."""

    @abstractmethod
    def answer(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        question: str,
    ) -> ProviderResult:
        """
        Ask the provider a question grounded in `context`.

        `context` is a JSON-serializable, case-scoped, already-validated
        TRACE-X data structure (see app.domain.assistant.context) — never
        raw evidence bytes or unvalidated parser output.

        Must raise a ProviderError subclass on any failure. Must never
        return a partially-populated or best-effort result silently.
        """


class UnconfiguredProvider(AssistantProvider):
    """
    Used when no provider credentials are configured.

    Fails every call with ProviderUnavailableError, so a missing
    ANTHROPIC_API_KEY degrades the assistant gracefully (grounding_status
    "unavailable") through the exact same code path as a live provider
    outage, instead of raising an unhandled exception.
    """

    @property
    def name(self) -> str:
        return "unconfigured"

    def answer(self, *, system_prompt: str, context: dict[str, Any], question: str) -> ProviderResult:
        raise ProviderUnavailableError(
            "No AI assistant provider is configured (ANTHROPIC_API_KEY is not set)."
        )


class AnthropicProvider(AssistantProvider):
    """
    Concrete provider backed by the Anthropic API.

    Uses a single structured-output request (client.messages.parse) — not
    an agentic tool-use loop. The assistant answers one question per call;
    it never calls tools, browses, or takes multi-step autonomous action.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_tokens: int = 4096,
    ) -> None:
        import anthropic  # imported lazily so the rest of the app never

        # requires the SDK to be installed to run.
        self._anthropic = anthropic
        # api_key is read from configuration by the caller (see
        # app.core.config) and passed in here — never hardcoded, never
        # logged, never echoed back in a response.
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "anthropic"

    def answer(self, *, system_prompt: str, context: dict[str, Any], question: str) -> ProviderResult:
        from pydantic import BaseModel, Field

        class _ClaimSchema(BaseModel):
            text: str
            type: str
            refs: list[str] = Field(default_factory=list)

        class _AnswerSchema(BaseModel):
            answer: str
            claims: list[_ClaimSchema] = Field(default_factory=list)

        user_content = (
            "CASE CONTEXT (structured TRACE-X data — JSON, already validated, "
            "no raw evidence bytes):\n"
            f"{json.dumps(context, default=str, sort_keys=True)}\n\n"
            f"INVESTIGATOR QUESTION:\n{question}"
        )

        anthropic = self._anthropic
        try:
            response = self._client.messages.parse(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                output_format=_AnswerSchema,
            )
        except anthropic.APITimeoutError as exc:
            raise ProviderTimeoutError(str(exc)) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderUnavailableError(f"rate limited: {exc}") from exc
        except anthropic.AuthenticationError as exc:
            raise ProviderUnavailableError("provider authentication failed") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderUnavailableError(f"provider status error ({exc.status_code})") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(f"connection error: {exc}") from exc

        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise ProviderResponseError("provider returned no parsable structured output")

        return ProviderResult(
            answer=parsed.answer,
            claims=[
                ProviderClaim(text=c.text, type=c.type, refs=list(c.refs))
                for c in parsed.claims
            ],
            model=response.model,
        )
