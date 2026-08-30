"""
Phase 12 — static external-knowledge source loader.

Loads a versioned, read-only JSON snapshot from disk (no network access,
no database, no CaseService/EventService/etc. dependency of any kind).
The snapshot contains ONLY external cybersecurity knowledge (MITRE ATT&CK
technique/tactic reference data) — it must never contain a case_id or any
case-specific data (see backend/tests/domain/test_knowledge.py for a
standing regression check of that invariant).

Provenance of the bundled default snapshot
(app/domain/knowledge/data/mitre_attack_enterprise_v19_2.json):
  - Source: MITRE ATT&CK Enterprise STIX data,
    https://github.com/mitre-attack/attack-stix-data
  - ATT&CK version: 19.2 (x_mitre_version, from the STIX
    x-mitre-collection object)
  - STIX collection modified: 2026-08-05T21:33:58.496Z
  - Acquired via a direct download of enterprise-attack.json on the date
    recorded in the snapshot's own "acquired_at" field.
  - Attribution (copied verbatim from the STIX marking-definition):
    "Copyright 2015-2026, The MITRE Corporation. MITRE ATT&CK and ATT&CK
    are registered trademarks of The MITRE Corporation."
  - Review MITRE's Terms of Use (https://attack.mitre.org/resources/terms-of-use/)
    before any redistribution beyond this project's internal use — this
    loader does not certify a license, it only records what MITRE's own
    STIX bundle states.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DEFAULT_SNAPSHOT_PATH = Path(__file__).parent / "data" / "mitre_attack_enterprise_v19_2.json"

_REQUIRED_TOP_LEVEL_FIELDS = {"source_id", "source_type", "document_id", "version", "techniques", "tactics"}


class KnowledgeSourceError(Exception):
    """Raised when the static knowledge snapshot cannot be found, read, or
    parsed. Callers (KnowledgeService) must treat this as a recoverable
    knowledge-layer failure — never let it fail the whole assistant
    request (Phase 11 case-grounded answers must remain available)."""


@dataclass(frozen=True)
class TechniqueRecord:
    technique_id: str
    name: str
    is_subtechnique: bool
    tactics: tuple[str, ...]
    platforms: tuple[str, ...]
    description: str
    url: str


@dataclass(frozen=True)
class TacticRecord:
    tactic_id: str
    shortname: str
    name: str


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """A single loaded, versioned external-knowledge source. Contains no
    case_id and no case-specific data of any kind."""
    source_id: str
    source_type: str
    document_id: str
    version: str
    techniques: tuple[TechniqueRecord, ...]
    tactics: tuple[TacticRecord, ...]


def load_snapshot(path: Path | None = None) -> KnowledgeSnapshot:
    """Load and validate a knowledge snapshot from `path` (defaults to the
    bundled MITRE ATT&CK snapshot). Malformed individual records are
    skipped rather than crashing the whole load; a missing/corrupt file or
    missing top-level fields raises KnowledgeSourceError."""
    p = path or _DEFAULT_SNAPSHOT_PATH
    try:
        raw_text = p.read_text()
    except OSError as exc:
        raise KnowledgeSourceError(f"knowledge snapshot not found or unreadable at {p}") from exc

    try:
        raw = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise KnowledgeSourceError(f"knowledge snapshot at {p} is not valid JSON") from exc

    if not isinstance(raw, dict):
        raise KnowledgeSourceError(f"knowledge snapshot at {p} must be a JSON object")

    missing = _REQUIRED_TOP_LEVEL_FIELDS - raw.keys()
    if missing:
        raise KnowledgeSourceError(
            f"knowledge snapshot at {p} is missing required field(s): {sorted(missing)}"
        )

    techniques: list[TechniqueRecord] = []
    for t in raw.get("techniques", []):
        try:
            techniques.append(
                TechniqueRecord(
                    technique_id=t["id"],
                    name=t["name"],
                    is_subtechnique=bool(t.get("is_subtechnique", False)),
                    tactics=tuple(t.get("tactics", []) or []),
                    platforms=tuple(t.get("platforms", []) or []),
                    description=t.get("description", "") or "",
                    url=t.get("url", "") or "",
                )
            )
        except (KeyError, TypeError):
            continue  # skip malformed record; one bad row must not break the whole source

    tactics: list[TacticRecord] = []
    for tac in raw.get("tactics", []):
        try:
            tactics.append(
                TacticRecord(
                    tactic_id=tac["id"],
                    shortname=tac["shortname"],
                    name=tac["name"],
                )
            )
        except (KeyError, TypeError):
            continue

    return KnowledgeSnapshot(
        source_id=raw["source_id"],
        source_type=raw["source_type"],
        document_id=raw["document_id"],
        version=raw["version"],
        techniques=tuple(techniques),
        tactics=tuple(tactics),
    )


@lru_cache(maxsize=1)
def get_default_snapshot() -> KnowledgeSnapshot:
    """Cached load of the bundled default snapshot — the file is static
    and read-only at runtime, so loading it once per process is safe and
    avoids re-parsing ~450KB of JSON on every assistant query."""
    return load_snapshot()
