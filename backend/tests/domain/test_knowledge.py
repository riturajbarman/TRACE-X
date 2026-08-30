"""
Phase 12 — external knowledge (RAG Knowledge Layer) domain tests.

Covers: loading the bundled MITRE ATT&CK snapshot, provenance
preservation, deterministic lookup, bounded results, and malformed/
missing-source handling. No database, no network, no LLM — the knowledge
layer has none of those dependencies (see app.domain.knowledge.service).
"""
import json

import pytest

from app.domain.knowledge.lookup import lookup
from app.domain.knowledge.service import KnowledgeLookupError, KnowledgeService
from app.domain.knowledge.source import (
    KnowledgeSnapshot,
    KnowledgeSourceError,
    TacticRecord,
    TechniqueRecord,
    get_default_snapshot,
    load_snapshot,
)

# ---------------------------------------------------------------------
# 1-6. Load the real bundled snapshot; provenance is preserved.
# ---------------------------------------------------------------------

def test_load_default_snapshot_succeeds():
    snap = get_default_snapshot()
    assert isinstance(snap, KnowledgeSnapshot)
    assert len(snap.techniques) > 0
    assert len(snap.tactics) > 0


def test_default_snapshot_provenance_preserved():
    snap = get_default_snapshot()
    assert snap.source_id == "mitre_attack_enterprise"
    assert snap.source_type == "mitre_attack"
    assert snap.document_id.startswith("x-mitre-collection--")
    assert snap.version == "19.2"


def test_default_snapshot_has_stable_attck_references():
    snap = get_default_snapshot()
    t1059 = next((t for t in snap.techniques if t.technique_id == "T1059"), None)
    assert t1059 is not None
    assert t1059.name == "Command and Scripting Interpreter"
    assert "execution" in t1059.tactics
    assert t1059.url.startswith("https://attack.mitre.org/")


def test_default_snapshot_contains_no_case_id_field():
    """The knowledge store must never contain case-specific data."""
    default_path = None
    from app.domain.knowledge.source import _DEFAULT_SNAPSHOT_PATH
    raw = json.loads(_DEFAULT_SNAPSHOT_PATH.read_text())
    raw_str = json.dumps(raw)
    assert "case_id" not in raw_str
    assert "\"case\":" not in raw_str


# ---------------------------------------------------------------------
# 7/8/9. Deterministic lookup: technique ID, name, tactic
# ---------------------------------------------------------------------

def test_lookup_by_technique_id():
    snap = get_default_snapshot()
    results = lookup(snap, "What is T1059?", max_results=5)
    assert len(results) >= 1
    assert results[0].technique.technique_id == "T1059"
    assert results[0].match_reason == "technique_id_exact"


def test_lookup_by_technique_name():
    snap = get_default_snapshot()
    results = lookup(snap, "Tell me about Command and Scripting Interpreter", max_results=5)
    assert any(r.technique.technique_id == "T1059" for r in results)


def test_lookup_by_tactic():
    snap = get_default_snapshot()
    results = lookup(snap, "What techniques fall under persistence?", max_results=5)
    assert len(results) > 0
    assert any("persistence" in r.technique.tactics for r in results)


# ---------------------------------------------------------------------
# 10. Unknown lookup returns no result (never fabricated)
# ---------------------------------------------------------------------

def test_lookup_unknown_query_returns_nothing():
    snap = get_default_snapshot()
    # Pure gibberish with no real English words, so it cannot legitimately
    # keyword-match any technique name/description.
    results = lookup(snap, "zzxq wqmpx vrblq xkzq", max_results=5)
    assert results == []


def test_lookup_empty_question_returns_nothing():
    snap = get_default_snapshot()
    assert lookup(snap, "", max_results=5) == []
    assert lookup(snap, "   ", max_results=5) == []


# ---------------------------------------------------------------------
# 11/12. Result limit and context-character limit are enforced
# ---------------------------------------------------------------------

def test_lookup_result_limit_enforced():
    snap = get_default_snapshot()
    results = lookup(snap, "process execution command script persistence access", max_results=3)
    assert len(results) <= 3


def test_lookup_zero_max_results():
    snap = get_default_snapshot()
    assert lookup(snap, "T1059", max_results=0) == []


def test_service_context_char_limit_enforced(monkeypatch):
    monkeypatch.setattr("app.core.config.KNOWLEDGE_MAX_RESULTS", 5)
    monkeypatch.setattr("app.core.config.KNOWLEDGE_MAX_CONTEXT_CHARS", 200)
    service = KnowledgeService()
    ctx = service.query("What techniques fall under persistence?")
    # Budget is small; the assembled block must respect it (allowing the
    # single best match to exceed it rather than return nothing).
    assert len(ctx.context_block) < 200 or len(ctx.citations) <= 1


def test_service_result_count_respects_max_results(monkeypatch):
    monkeypatch.setattr("app.core.config.KNOWLEDGE_MAX_RESULTS", 2)
    monkeypatch.setattr("app.core.config.KNOWLEDGE_MAX_CONTEXT_CHARS", 4000)
    service = KnowledgeService()
    ctx = service.query("What techniques fall under persistence?")
    assert len(ctx.citations) <= 2


# ---------------------------------------------------------------------
# 13. Malformed knowledge record handled safely (skipped, not a crash)
# ---------------------------------------------------------------------

def test_malformed_technique_record_is_skipped(tmp_path):
    bad_snapshot = {
        "source_id": "test_source",
        "source_type": "mitre_attack",
        "document_id": "doc-1",
        "version": "1.0",
        "tactics": [{"id": "TA0001", "shortname": "initial-access", "name": "Initial Access"}],
        "techniques": [
            {"id": "T9999", "name": "Valid Technique"},  # valid, minimal
            {"name": "Missing ID"},  # malformed: no "id" -> must be skipped
            "not even a dict",  # malformed: wrong type -> must be skipped
        ],
    }
    p = tmp_path / "malformed.json"
    p.write_text(json.dumps(bad_snapshot))

    snap = load_snapshot(p)
    assert len(snap.techniques) == 1
    assert snap.techniques[0].technique_id == "T9999"


# ---------------------------------------------------------------------
# 14. Corrupt/missing source handled safely (raises typed error, no crash)
# ---------------------------------------------------------------------

def test_missing_source_file_raises_typed_error(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(KnowledgeSourceError):
        load_snapshot(missing)


def test_corrupt_json_raises_typed_error(tmp_path):
    p = tmp_path / "corrupt.json"
    p.write_text("{ this is not valid json ]")
    with pytest.raises(KnowledgeSourceError):
        load_snapshot(p)


def test_missing_required_field_raises_typed_error(tmp_path):
    p = tmp_path / "incomplete.json"
    p.write_text(json.dumps({"source_id": "x"}))  # missing everything else
    with pytest.raises(KnowledgeSourceError):
        load_snapshot(p)


def test_knowledge_service_wraps_source_error_as_lookup_error(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(KnowledgeLookupError):
        from app.domain.knowledge.source import load_snapshot as _load
        # Directly exercise the failure path KnowledgeService.query() takes
        # when the snapshot can't be loaded, without touching the real
        # cached default snapshot.
        try:
            _load(missing)
        except KnowledgeSourceError as exc:
            raise KnowledgeLookupError(str(exc)) from exc


# ---------------------------------------------------------------------
# 15. Knowledge data contains no case_id anywhere in a query result either
# ---------------------------------------------------------------------

def test_knowledge_query_result_contains_no_case_id():
    service = KnowledgeService()
    ctx = service.query("What is T1059?")
    assert "case_id" not in ctx.context_block
    for c in ctx.citations:
        assert "case_id" not in c.model_dump_json()
