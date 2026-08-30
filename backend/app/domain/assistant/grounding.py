"""
Phase 11 — grounding validation for the AI Investigation Assistant.

Enforces the grounding contract on every claim the provider returns:
  - only ids that literally appear in this case's context are accepted;
  - an unresolvable/invented id is dropped from `refs` and reported as a
    warning — it is never silently accepted;
  - a claim typed "observed" that ends up with zero valid provenance refs
    is demoted to "inference" (never presented as directly-observed fact
    without support) and reported as a warning.
"""
from __future__ import annotations

from app.domain.assistant.provider import ProviderClaim
from app.domain.assistant.schemas import AssistantClaim, ClaimType, GroundingStatus

_VALID_TYPES: set[str] = {"observed", "inference", "recommendation"}


def validate_claims(
    claims: list[ProviderClaim],
    known_ids: set[str],
) -> tuple[list[AssistantClaim], GroundingStatus, list[str]]:
    """Validate provider claims against this case's known provenance ids.

    Returns (validated_claims, grounding_status, warnings).
    """
    validated: list[AssistantClaim] = []
    warnings: list[str] = []
    dropped_ref_count = 0
    demoted_count = 0
    unknown_type_count = 0

    for claim in claims:
        valid_refs = [r for r in claim.refs if r in known_ids]
        invalid_refs = [r for r in claim.refs if r not in known_ids]
        if invalid_refs:
            dropped_ref_count += len(invalid_refs)

        claim_type: ClaimType
        if claim.type in _VALID_TYPES:
            claim_type = claim.type  # type: ignore[assignment]
        else:
            claim_type = "inference"
            unknown_type_count += 1

        if claim_type == "observed" and not valid_refs:
            claim_type = "inference"
            demoted_count += 1

        validated.append(AssistantClaim(text=claim.text, type=claim_type, refs=valid_refs))

    if dropped_ref_count:
        warnings.append(
            f"{dropped_ref_count} referenced id(s) did not match this case's "
            "data and were removed."
        )
    if demoted_count:
        warnings.append(
            f"{demoted_count} claim(s) were labeled 'observed' without valid "
            "provenance and were downgraded to 'inference'."
        )
    if unknown_type_count:
        warnings.append(
            f"{unknown_type_count} claim(s) had an unrecognized type and were "
            "treated as 'inference'."
        )

    if not validated:
        status: GroundingStatus = "unavailable"
    elif dropped_ref_count or demoted_count or unknown_type_count:
        status = "partial"
    else:
        status = "ok"

    return validated, status, warnings
