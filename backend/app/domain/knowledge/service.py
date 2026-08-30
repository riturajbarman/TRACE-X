"""
Phase 12 — KnowledgeService: the only entry point AssistantService talks to.

Independent of CaseService / EventService / RiskService / DetectionRepository
/ GraphService / evidence storage / correlation / anomaly detection — it
takes no database session and performs no forensic-domain calls of any
kind. It never mutates anything; the bundled snapshot is read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core import config
from app.domain.knowledge.lookup import lookup
from app.domain.knowledge.schemas import KnowledgeCitation
from app.domain.knowledge.source import (
    KnowledgeSnapshot,
    KnowledgeSourceError,
    get_default_snapshot,
)


class KnowledgeLookupError(Exception):
    """Raised when the knowledge layer cannot be queried at all (e.g. the
    static snapshot is missing/corrupt). Callers MUST catch this and
    degrade gracefully — a knowledge-layer failure must never fail an
    assistant request that could otherwise be answered from case context
    alone."""


@dataclass
class KnowledgeContext:
    """Everything the assistant needs for one query: a human-readable,
    already-bounded text block to place in the [EXTERNAL KNOWLEDGE]
    section of the prompt, plus the exact citation records that were
    actually retrieved — the ONLY citations grounding.py is allowed to
    accept back from the model."""
    context_block: str
    citations: list[KnowledgeCitation] = field(default_factory=list)

    @property
    def known_citation_keys(self) -> set[tuple[str, str, str]]:
        return {(c.source_id, c.document_id, c.version) for c in self.citations}


class KnowledgeService:
    def __init__(self, snapshot: KnowledgeSnapshot | None = None) -> None:
        # `snapshot` is injectable for tests; production code leaves it
        # None and resolves the cached default snapshot lazily inside
        # query(), so a missing/corrupt file only breaks a query, not
        # service construction.
        self._snapshot = snapshot

    def query(self, question: str) -> KnowledgeContext:
        """Deterministic external-knowledge lookup for one question.

        Raises KnowledgeLookupError if the knowledge source itself cannot
        be loaded. Returns an empty KnowledgeContext (never an error) when
        the source loads fine but nothing relevant was found — an empty
        result is a normal, non-fabricated outcome, not a failure.
        """
        try:
            snapshot = self._snapshot if self._snapshot is not None else get_default_snapshot()
        except KnowledgeSourceError as exc:
            raise KnowledgeLookupError(str(exc)) from exc

        max_results = config.KNOWLEDGE_MAX_RESULTS
        max_chars = config.KNOWLEDGE_MAX_CONTEXT_CHARS

        matches = lookup(snapshot, question, max_results=max_results)
        if not matches:
            return KnowledgeContext(context_block="", citations=[])

        citations: list[KnowledgeCitation] = []
        blocks: list[str] = []
        budget = max_chars
        for m in matches:
            t = m.technique
            citation = KnowledgeCitation(
                source_id=snapshot.source_id,
                source_type=snapshot.source_type,
                document_id=t.technique_id,
                version=snapshot.version,
                title=t.name,
                reference=t.url,
                retrieval_method="deterministic_lookup",
            )
            entry = (
                f"[{t.technique_id}] {t.name} "
                f"(tactics: {', '.join(t.tactics) or 'n/a'}; match: {m.match_reason})\n"
                f"{t.description}"
            )
            if blocks and len(entry) > budget:
                break  # stop once the context budget is exhausted, but
                # always keep at least the single best match even if it
                # alone exceeds the budget (better than an empty answer).
            blocks.append(entry)
            citations.append(citation)
            budget -= len(entry)

        return KnowledgeContext(context_block="\n\n---\n\n".join(blocks), citations=citations)
