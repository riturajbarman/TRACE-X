"""
Phase 11/12 — grounding validation for the AI Investigation Assistant.

Enforces the grounding contract on every claim the provider returns, using
two entirely separate validation namespaces that must never cross:

  CASE REFS
      A claim's `refs` are validated against `known_ids` — the set of
      TRACE-X object ids that were actually included in this case's
      context (app.domain.assistant.context.AssistantContext.known_ids).

  KNOWLEDGE CITATIONS
      A claim's `knowledge_refs` are validated against
      `known_citations` — a dict of the EXACT KnowledgeCitation records
      app.domain.knowledge.KnowledgeService actually retrieved for this
      query, keyed by (source_id, document_id, version). The provider's
      own claimed citation metadata (title, reference/url, etc.) is NEVER
      trusted — only the (source_id, document_id, version) key is used to
      look up the real, server-held record, which is what ends up in the
      response. This prevents citation spoofing: even if the model
      invents a plausible-looking title or URL, only a real, retrieved
      record can appear in the final response.

General rules:
  - only ids/citation keys that were actually part of this case's/query's
    retrieved data are accepted; anything else is dropped and reported as
    a warning — never silently accepted;
  - a claim typed "observed" that ends up with zero valid case refs is
    demoted to "inference" (never presented as directly-observed fact
    without support);
  - a claim typed "external_knowledge" that ends up with zero valid
    citations is demoted to "inference" for the same reason — it must
    never be presented as grounded external knowledge without a real
    citation behind it;
  - a claim's `refs` and `knowledge_refs` are mutually exclusive in the
    output: only "observed"/"inference"/"recommendation" claims may carry
    `refs`, and only "external_knowledge" claims may carry
    `knowledge_refs` — a case object id can never become a knowledge
    citation, and a knowledge citation can never enter `refs`.
"""
from __future__ import annotations

from app.domain.assistant.provider import ProviderClaim
from app.domain.assistant.schemas import AssistantClaim, ClaimType, GroundingStatus
from app.domain.knowledge.schemas import KnowledgeCitation

_VALID_TYPES: set[str] = {"observed", "inference", "recommendation", "external_knowledge"}


def validate_claims(
    claims: list[ProviderClaim],
    known_ids: set[str],
    known_citations: dict[tuple[str, str, str], KnowledgeCitation],
) -> tuple[list[AssistantClaim], GroundingStatus, list[str]]:
    """Validate provider claims against this case's known provenance ids
    AND this query's actually-retrieved knowledge citations.

    Returns (validated_claims, grounding_status, warnings).
    """
    validated: list[AssistantClaim] = []
    warnings: list[str] = []
    dropped_ref_count = 0
    dropped_citation_count = 0
    demoted_count = 0
    unknown_type_count = 0

    for claim in claims:
        claim_type: ClaimType
        if claim.type in _VALID_TYPES:
            claim_type = claim.type  # type: ignore[assignment]
        else:
            claim_type = "inference"
            unknown_type_count += 1

        if claim_type == "external_knowledge":
            valid_citations: list[KnowledgeCitation] = []
            for kr in claim.knowledge_refs:
                key = (kr.source_id, kr.document_id, kr.version)
                real = known_citations.get(key)
                if real is not None:
                    # Use the server's own retrieved record — never the
                    # model's claimed title/reference metadata.
                    valid_citations.append(real)
                else:
                    dropped_citation_count += 1

            if not valid_citations:
                claim_type = "inference"
                demoted_count += 1

            validated.append(
                AssistantClaim(text=claim.text, type=claim_type, refs=[], knowledge_refs=valid_citations)
            )
            continue

        # observed / inference / recommendation: validate against case
        # known_ids only. knowledge_refs are never permitted here, even if
        # the model tried to attach them — silently stripped, since this
        # is not a spoofing attempt worth a user-facing warning by itself
        # (the claim type is simply not "external_knowledge").
        valid_refs = [r for r in claim.refs if r in known_ids]
        invalid_refs = [r for r in claim.refs if r not in known_ids]
        if invalid_refs:
            dropped_ref_count += len(invalid_refs)

        if claim_type == "observed" and not valid_refs:
            claim_type = "inference"
            demoted_count += 1

        validated.append(AssistantClaim(text=claim.text, type=claim_type, refs=valid_refs, knowledge_refs=[]))

    if dropped_ref_count:
        warnings.append(
            f"{dropped_ref_count} referenced case id(s) did not match this case's "
            "data and were removed."
        )
    if dropped_citation_count:
        warnings.append(
            f"{dropped_citation_count} external knowledge citation(s) did not match "
            "an actually-retrieved knowledge record and were removed."
        )
    if demoted_count:
        warnings.append(
            f"{demoted_count} claim(s) lacked valid provenance for their stated type "
            "and were downgraded to 'inference'."
        )
    if unknown_type_count:
        warnings.append(
            f"{unknown_type_count} claim(s) had an unrecognized type and were "
            "treated as 'inference'."
        )

    if not validated:
        status: GroundingStatus = "unavailable"
    elif dropped_ref_count or dropped_citation_count or demoted_count or unknown_type_count:
        status = "partial"
    else:
        status = "ok"

    return validated, status, warnings
