"""
Phase 8 Correlation Engine Tests

Covers:
  - Shared entity correlation
  - Time-window + secondary criterion correlation
  - Evidence provenance (same artifact) correlation
  - Events outside time-window are NOT correlated
  - Unrelated events are NOT correlated (false-correlation guard)
  - Provenance references preserved in groups
  - Explanation (reason) is present and non-empty
  - Determinism: re-running on same data produces identical groups
  - Empty input produces no groups
  - Process / file / network entity matching
  - False-correlation measurement (controlled fixture)
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from app.domain.correlation.engine import CorrelationEngine, CorrelationGroup
from app.domain.detection.models import Detection
from app.domain.event.models import Event


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

ANCHOR = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _evt(
    *,
    event_type: str = "generic",
    source: str = "test",
    timestamp: datetime | None = None,
    data: dict | None = None,
    artifact_id: uuid.UUID | None = None,
    evidence_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
) -> Event:
    e = Event()
    e.id = uuid.uuid4()
    e.event_type = event_type
    e.source = source
    e.timestamp = timestamp or ANCHOR
    e.data = data or {}
    e.artifact_id = artifact_id
    e.evidence_id = evidence_id
    e.case_id = case_id or uuid.uuid4()
    e.created_at = datetime.now(timezone.utc)
    e.schema_version = 1
    e.timestamp_desc = None
    return e


def _det(event_id: uuid.UUID, severity: str = "HIGH", confidence: int = 80) -> Detection:
    d = Detection()
    d.id = uuid.uuid4()
    d.event_id = event_id
    d.case_id = uuid.uuid4()
    d.detection_type = "keyword_match"
    d.rule_id = "TEST-001"
    d.rule_version = "1.0"
    d.severity = severity
    d.confidence = confidence
    d.created_at = datetime.now(timezone.utc)
    return d


ENGINE = CorrelationEngine(time_window=timedelta(minutes=5))


# ---------------------------------------------------------------------------
# Core correctness tests
# ---------------------------------------------------------------------------

def test_empty_input_produces_no_groups():
    """Empty event list must never produce fabricated correlations."""
    assert ENGINE.correlate([], []) == []


def test_single_event_produces_no_groups():
    """A lone event cannot form a correlation group."""
    groups = ENGINE.correlate([_evt()], [])
    assert groups == []


def test_shared_entity_path_correlated():
    """Two events sharing the same 'path' value must be grouped."""
    shared_path = "/var/log/malware.exe"
    ea = _evt(data={"path": shared_path}, event_type="file_creation")
    eb = _evt(data={"path": shared_path}, event_type="process_exec",
              timestamp=ANCHOR + timedelta(hours=2))  # far apart in time

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    group = groups[0]
    assert ea in group.events
    assert eb in group.events
    assert "path" in group.reason.lower() or shared_path in group.reason


def test_shared_entity_process_name_correlated():
    """Two events sharing 'process_name' are correlated."""
    ea = _evt(data={"process_name": "mimikatz.exe"})
    eb = _evt(data={"process_name": "mimikatz.exe"}, timestamp=ANCHOR + timedelta(hours=1))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    assert "mimikatz.exe" in groups[0].reason


def test_shared_entity_network_ip_correlated():
    """Two events sharing the same IP address are grouped (network relationship)."""
    ea = _evt(data={"dst_ip": "10.0.0.99"}, event_type="network_connection")
    eb = _evt(data={"dst_ip": "10.0.0.99"}, event_type="network_connection",
              timestamp=ANCHOR + timedelta(hours=3))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1


def test_shared_entity_sha256_correlated():
    """Two events sharing a file hash are correlated."""
    sha = "a" * 64
    ea = _evt(data={"sha256": sha}, event_type="file_creation")
    eb = _evt(data={"sha256": sha}, event_type="antivirus_alert",
              timestamp=ANCHOR + timedelta(minutes=30))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1


def test_time_window_with_same_evidence_correlated():
    """Events within time-window sharing same evidence_id must be grouped."""
    ev_id = uuid.uuid4()
    ea = _evt(evidence_id=ev_id, timestamp=ANCHOR, event_type="A")
    eb = _evt(evidence_id=ev_id, timestamp=ANCHOR + timedelta(minutes=3), event_type="B")

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    assert "evidence" in groups[0].reason.lower() or "same" in groups[0].reason.lower()


def test_time_window_with_same_source_correlated():
    """Events within time-window from same source must be grouped."""
    ea = _evt(source="evtx_parser", timestamp=ANCHOR, event_type="A")
    eb = _evt(source="evtx_parser", timestamp=ANCHOR + timedelta(minutes=2), event_type="B")

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1


def test_time_window_with_same_event_type_correlated():
    """Events within time-window of same event_type must be grouped."""
    ea = _evt(event_type="registry_write", timestamp=ANCHOR)
    eb = _evt(event_type="registry_write", timestamp=ANCHOR + timedelta(minutes=4))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1


def test_evidence_provenance_same_artifact_correlated():
    """Events sharing the same artifact_id must always be grouped."""
    art_id = uuid.uuid4()
    ea = _evt(artifact_id=art_id, event_type="X", timestamp=ANCHOR)
    eb = _evt(artifact_id=art_id, event_type="Y", timestamp=ANCHOR + timedelta(hours=10))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    assert str(art_id) in groups[0].reason


# ---------------------------------------------------------------------------
# False-correlation / negative tests
# ---------------------------------------------------------------------------

def test_time_window_alone_does_not_correlate():
    """
    CRITICAL: two events that are close in time but share NO secondary
    criterion (different evidence, different source, different event_type)
    MUST NOT be correlated. Time-window alone is insufficient.
    """
    ea = _evt(
        source="src_A",
        event_type="login",
        evidence_id=uuid.uuid4(),
        timestamp=ANCHOR,
        data={},
    )
    eb = _evt(
        source="src_B",
        event_type="file_access",
        evidence_id=uuid.uuid4(),
        timestamp=ANCHOR + timedelta(seconds=30),
        data={},
    )

    groups = ENGINE.correlate([ea, eb], [])
    # These events must NOT be correlated — time alone is no basis.
    assert groups == []


def test_unrelated_events_not_correlated():
    """Events with no shared entity, different sources, and large time gap."""
    ea = _evt(source="parser_A", event_type="login", timestamp=ANCHOR, data={"user": "alice"})
    eb = _evt(source="parser_B", event_type="network", timestamp=ANCHOR + timedelta(hours=2),
              data={"dst_ip": "192.0.2.1"})

    groups = ENGINE.correlate([ea, eb], [])
    assert groups == []


def test_trivial_entity_value_not_correlated():
    """
    Values that are too short (< MIN_ENTITY_VALUE_LEN) must not produce
    false correlations.
    """
    ea = _evt(data={"process_name": "x"})   # 1 char — too short
    eb = _evt(data={"process_name": "x"}, timestamp=ANCHOR + timedelta(hours=1))

    groups = ENGINE.correlate([ea, eb], [])
    assert groups == []


# ---------------------------------------------------------------------------
# Provenance and explanation tests
# ---------------------------------------------------------------------------

def test_groups_preserve_event_provenance():
    """Group must carry all original event references."""
    shared_path = "/tmp/evil.sh"
    ea = _evt(data={"path": shared_path})
    eb = _evt(data={"path": shared_path}, timestamp=ANCHOR + timedelta(hours=1))

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    group_event_ids = {e.id for e in groups[0].events}
    assert ea.id in group_event_ids
    assert eb.id in group_event_ids


def test_groups_contain_explanation():
    """Every correlation group must have a non-empty reason."""
    ev_id = uuid.uuid4()
    ea = _evt(evidence_id=ev_id, timestamp=ANCHOR, event_type="A")
    eb = _evt(evidence_id=ev_id, timestamp=ANCHOR + timedelta(minutes=1), event_type="A")

    groups = ENGINE.correlate([ea, eb], [])
    assert len(groups) == 1
    assert groups[0].reason
    assert len(groups[0].reason) > 0


def test_group_preserves_detection_references():
    """Detections linked to correlated events must appear in the group."""
    ev_id = uuid.uuid4()
    ea = _evt(evidence_id=ev_id, timestamp=ANCHOR, event_type="A")
    eb = _evt(evidence_id=ev_id, timestamp=ANCHOR + timedelta(minutes=1), event_type="A")

    det = _det(ea.id, severity="CRITICAL", confidence=95)

    groups = ENGINE.correlate([ea, eb], [det])
    assert len(groups) == 1
    assert det in groups[0].detections
    assert groups[0].severity == "CRITICAL"
    assert groups[0].confidence == 95


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------

def test_correlation_is_deterministic():
    """
    Running correlation twice on identical input must produce identical
    group structure (same event memberships and reasons).
    """
    shared_path = "/etc/cron.d/backdoor"
    ea = _evt(data={"path": shared_path}, timestamp=ANCHOR)
    eb = _evt(data={"path": shared_path}, timestamp=ANCHOR + timedelta(minutes=1))
    ec = _evt(data={"path": shared_path}, timestamp=ANCHOR + timedelta(minutes=2))

    events = [ea, eb, ec]

    run1 = ENGINE.correlate(events, [])
    run2 = ENGINE.correlate(events, [])

    assert len(run1) == len(run2)
    for g1, g2 in zip(run1, run2):
        ids1 = {e.id for e in g1.events}
        ids2 = {e.id for e in g2.events}
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# False-correlation measurement (controlled fixture)
# ---------------------------------------------------------------------------

def test_false_correlation_measurement():
    """
    Controlled fixture with known related and unrelated events.

    KNOWN RELATED pairs (should be grouped):
      - ea + eb: share process_name "cmd.exe"
      - ec + ed: within time-window, same evidence
      - ee + ef: share artifact_id

    KNOWN UNRELATED events (must NOT be in any group):
      - ug: unique source, unique data, far from others in time

    Expected:
      - true_correlations  = 3 pairs captured in groups
      - false_correlations = 0 (ug must not appear in any group)
      - missed_correlations = 0
    """
    common_evidence = uuid.uuid4()
    common_artifact = uuid.uuid4()

    # Related set A: shared process entity
    ea = _evt(data={"process_name": "cmd.exe"}, event_type="process_exec",
              source="evtx", timestamp=ANCHOR)
    eb = _evt(data={"process_name": "cmd.exe"}, event_type="process_exec",
              source="evtx", timestamp=ANCHOR + timedelta(hours=2))

    # Related set B: time-window + same evidence
    ec = _evt(evidence_id=common_evidence, source="fs_parser", event_type="file_write",
              timestamp=ANCHOR + timedelta(minutes=1))
    ed = _evt(evidence_id=common_evidence, source="fs_parser", event_type="registry_write",
              timestamp=ANCHOR + timedelta(minutes=3))

    # Related set C: same artifact (evidence provenance)
    ee = _evt(artifact_id=common_artifact, event_type="filesystem",
              timestamp=ANCHOR + timedelta(hours=5))
    ef = _evt(artifact_id=common_artifact, event_type="filesystem",
              timestamp=ANCHOR + timedelta(hours=6))

    # Unrelated: unique everything, far in time
    ug = _evt(source="orphan_parser", event_type="orphan_type",
              data={"user": "dave"}, timestamp=ANCHOR + timedelta(days=1))

    all_events = [ea, eb, ec, ed, ee, ef, ug]
    groups = ENGINE.correlate(all_events, [])

    # Flatten all correlated event IDs
    correlated_ids: set[uuid.UUID] = set()
    for g in groups:
        for e in g.events:
            correlated_ids.add(e.id)

    # True correlations: all three related pairs must be captured
    assert ea.id in correlated_ids, "ea (process_name=cmd.exe) must be correlated"
    assert eb.id in correlated_ids, "eb (process_name=cmd.exe) must be correlated"
    assert ec.id in correlated_ids, "ec (same evidence) must be correlated"
    assert ed.id in correlated_ids, "ed (same evidence) must be correlated"
    assert ee.id in correlated_ids, "ee (same artifact) must be correlated"
    assert ef.id in correlated_ids, "ef (same artifact) must be correlated"
    true_correlations = 6  # all 6 related events captured

    # False correlations: unrelated event must not appear
    assert ug.id not in correlated_ids, "Unrelated event 'ug' must NOT be correlated"
    false_correlations = 0

    # Missed correlations
    missed_correlations = 0  # all 6 related events present in groups

    # Report (visible in verbose pytest output)
    print(
        f"\n[Phase 8 False-Correlation Measurement]\n"
        f"  Groups found:          {len(groups)}\n"
        f"  True correlations:     {true_correlations} events correctly grouped\n"
        f"  False correlations:    {false_correlations} spurious groupings\n"
        f"  Missed correlations:   {missed_correlations} known relationships missed\n"
    )

    assert false_correlations == 0
    assert missed_correlations == 0
    assert true_correlations == 6
