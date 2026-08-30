"""
Phase 12 — deterministic external-knowledge lookup.

This is keyword/identifier matching, NOT semantic similarity — every match
is explainable by an exact rule (technique ID, exact/substring name match,
tactic name match, or a word-boundary keyword hit against name+description).
`match_reason` on every result states exactly which rule fired, so a
result is always auditable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.knowledge.source import KnowledgeSnapshot, TechniqueRecord

_TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-zA-Z]{4,}")
_STOPWORDS = {
    "this", "that", "with", "from", "have", "about", "does", "which",
    "been", "were", "what", "case", "when", "where", "there", "their",
    "would", "could", "should", "technique", "please", "explain",
}


@dataclass(frozen=True)
class KnowledgeMatch:
    technique: TechniqueRecord
    match_reason: str


def lookup(snapshot: KnowledgeSnapshot, question: str, max_results: int) -> list[KnowledgeMatch]:
    """Deterministic lookup over a KnowledgeSnapshot. Never returns more
    than `max_results` matches; returns [] for max_results <= 0 or an
    empty/whitespace-only question."""
    if max_results <= 0:
        return []
    q = (question or "").strip()
    if not q:
        return []
    q_lower = q.lower()

    matches: list[KnowledgeMatch] = []
    seen_ids: set[str] = set()

    def _add(t: TechniqueRecord, reason: str) -> bool:
        """Returns True if the result buffer is now full."""
        if t.technique_id in seen_ids:
            return False
        matches.append(KnowledgeMatch(t, reason))
        seen_ids.add(t.technique_id)
        return len(matches) >= max_results

    # 1. Exact ATT&CK technique ID mention — highest precedence, unambiguous.
    for raw_id in _TECHNIQUE_ID_RE.findall(q):
        tid = raw_id.upper()
        for t in snapshot.techniques:
            if t.technique_id.upper() == tid:
                if _add(t, "technique_id_exact"):
                    return matches

    # 2. Exact or substring technique name match.
    for t in snapshot.techniques:
        if t.technique_id in seen_ids:
            continue
        name_lower = t.name.lower()
        if name_lower == q_lower or name_lower in q_lower:
            if _add(t, "name_match"):
                return matches

    # 3. Tactic name/shortname mentioned -> techniques under that tactic.
    for tac in snapshot.tactics:
        if tac.name.lower() not in q_lower and tac.shortname.lower() not in q_lower:
            continue
        for t in snapshot.techniques:
            if t.technique_id in seen_ids or tac.shortname not in t.tactics:
                continue
            if _add(t, f"tactic_match:{tac.shortname}"):
                return matches

    # 4. Deterministic keyword match against name + description. This is
    # plain substring matching, explicitly NOT semantic similarity.
    words = [w for w in _WORD_RE.findall(q_lower) if w not in _STOPWORDS]
    if words:
        for t in snapshot.techniques:
            if t.technique_id in seen_ids:
                continue
            haystack = f"{t.name} {t.description}".lower()
            if any(w in haystack for w in words):
                if _add(t, "keyword_match"):
                    return matches

    return matches
