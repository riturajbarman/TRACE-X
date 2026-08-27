"""Tests for Event domain: validation, persistence, provenance, queries."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.case.service import CaseService
from app.domain.event.models import Event
from app.domain.event.repository import EventRepository
from app.domain.event.schemas import EventCreate
from app.domain.event.service import EventService
from app.domain.evidence.service import EvidenceService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_case(db: Session) -> dict:
    service = CaseService(db)
    case = service.create(
        title=f"Event Test Case {uuid4()}",
        description="Test",
        created_by="pytest",
    )
    return {"id": case.id}


def _create_evidence(db: Session, case_id) -> dict:
    """Create evidence via the service layer for testing."""
    import tempfile
    from pathlib import Path

    service = EvidenceService(db)
    content = f"evidence-data-{uuid4()}".encode()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(content)
        tmp_path = Path(f.name)

    try:
        evidence = service.ingest(
            case_id=case_id,
            name=f"ev-{uuid4()}",
            source_path=tmp_path,
            description="test evidence",
            source="pytest",
        )
        return {"id": evidence.id, "case_id": case_id}
    finally:
        tmp_path.unlink(missing_ok=True)


def _make_event_create(
    artifact_id=None,
    evidence_id=None,
    case_id=None,
    event_type="file_creation",
    source="evtx",
    timestamp=None,
    timestamp_desc="SystemTime",
    schema_version=1,
    data=None,
):
    return EventCreate(
        artifact_id=artifact_id or uuid4(),
        evidence_id=evidence_id,
        case_id=case_id,
        event_type=event_type,
        source=source,
        timestamp=timestamp or datetime.now(timezone.utc),
        timestamp_desc=timestamp_desc,
        schema_version=schema_version,
        data=data or {},
    )


# ==================================================================
# VALIDATION TESTS
# ==================================================================


def test_event_create_valid():
    """Valid EventCreate schema with all required fields."""
    ec = _make_event_create()
    assert ec.artifact_id is not None
    assert ec.event_type == "file_creation"
    assert ec.source == "evtx"
    assert ec.schema_version == 1


def test_event_create_missing_event_type():
    """Missing event_type should raise validation error."""
    with pytest.raises(Exception):
        EventCreate(
            artifact_id=uuid4(),
            source="evtx",
            timestamp=datetime.now(timezone.utc),
        )


def test_event_create_missing_source():
    """Missing source should raise validation error."""
    with pytest.raises(Exception):
        EventCreate(
            artifact_id=uuid4(),
            event_type="file_creation",
            timestamp=datetime.now(timezone.utc),
        )


def test_event_create_missing_timestamp():
    """Missing timestamp should raise validation error."""
    with pytest.raises(Exception):
        EventCreate(
            artifact_id=uuid4(),
            event_type="file_creation",
            source="evtx",
        )


def test_service_rejects_missing_artifact_id(db: Session):
    """EventService must reject events without artifact_id (provenance)."""
    service = EventService(db)
    ec = EventCreate(
        artifact_id=None,
        event_type="file_creation",
        source="evtx",
        timestamp=datetime.now(timezone.utc),
    )

    with pytest.raises(ValueError, match="artifact_id is strictly required"):
        service.ingest_events([ec])


def test_service_rejects_invalid_case_id(db: Session):
    """EventService must reject events referencing a nonexistent Case."""
    service = EventService(db)
    ec = _make_event_create(case_id=uuid4())

    with pytest.raises(ValueError, match="Case .* not found"):
        service.ingest_events([ec])


def test_service_rejects_invalid_evidence_id(db: Session):
    """EventService must reject events referencing nonexistent Evidence."""
    service = EventService(db)
    ec = _make_event_create(evidence_id=uuid4())

    with pytest.raises(ValueError, match="Evidence .* not found"):
        service.ingest_events([ec])


def test_service_rejects_evidence_case_mismatch(db: Session):
    """EventService must reject if evidence does not belong to stated case."""
    case1 = _create_case(db)
    case2 = _create_case(db)
    ev = _create_evidence(db, case1["id"])

    service = EventService(db)
    ec = _make_event_create(
        evidence_id=ev["id"],
        case_id=case2["id"],
    )

    with pytest.raises(ValueError, match="does not belong to Case"):
        service.ingest_events([ec])


# ==================================================================
# PERSISTENCE TESTS
# ==================================================================


def test_event_can_be_stored_and_retrieved(db: Session):
    """Basic round-trip: store an event, retrieve it by ID."""
    case = _create_case(db)
    ev = _create_evidence(db, case["id"])
    artifact_id = uuid4()
    ts = datetime.now(timezone.utc)

    service = EventService(db)
    ec = _make_event_create(
        artifact_id=artifact_id,
        evidence_id=ev["id"],
        case_id=case["id"],
        timestamp=ts,
        data={"key": "value"},
    )
    events = service.ingest_events([ec])
    assert len(events) == 1

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored is not None
    assert stored.artifact_id == artifact_id
    assert stored.evidence_id == ev["id"]
    assert stored.case_id == case["id"]
    assert stored.event_type == "file_creation"
    assert stored.source == "evtx"
    assert stored.data == {"key": "value"}
    assert stored.schema_version == 1
    assert stored.created_at is not None


def test_event_retains_artifact_relationship(db: Session):
    """Verify the stored event preserves artifact_id."""
    artifact_id = uuid4()
    service = EventService(db)
    ec = _make_event_create(artifact_id=artifact_id)
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.artifact_id == artifact_id


def test_event_traceable_to_evidence(db: Session):
    """Verify event → evidence relationship."""
    case = _create_case(db)
    ev = _create_evidence(db, case["id"])

    service = EventService(db)
    ec = _make_event_create(evidence_id=ev["id"], case_id=case["id"])
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.evidence_id == ev["id"]
    assert stored.evidence is not None
    assert stored.evidence.id == ev["id"]


def test_event_traceable_to_case(db: Session):
    """Verify event → case relationship through evidence."""
    case = _create_case(db)
    ev = _create_evidence(db, case["id"])

    service = EventService(db)
    ec = _make_event_create(evidence_id=ev["id"], case_id=case["id"])
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.case_id == case["id"]
    assert stored.case is not None
    assert stored.case.id == case["id"]


# ==================================================================
# QUERY TESTS
# ==================================================================


def test_query_by_artifact(db: Session):
    """Query events by artifact_id."""
    artifact_id = uuid4()
    service = EventService(db)

    # Create 3 events for this artifact
    ecs = [_make_event_create(artifact_id=artifact_id) for _ in range(3)]
    service.ingest_events(ecs)

    results = service.list_by_artifact(artifact_id)
    assert len(results) == 3
    for r in results:
        assert r.artifact_id == artifact_id


def test_query_by_evidence(db: Session):
    """Query events by evidence_id."""
    case = _create_case(db)
    ev = _create_evidence(db, case["id"])

    service = EventService(db)
    ecs = [_make_event_create(evidence_id=ev["id"], case_id=case["id"]) for _ in range(3)]
    service.ingest_events(ecs)

    results = service.list_by_evidence(ev["id"])
    assert len(results) == 3
    for r in results:
        assert r.evidence_id == ev["id"]


def test_query_by_case(db: Session):
    """Query events by case_id."""
    case = _create_case(db)
    ev = _create_evidence(db, case["id"])

    service = EventService(db)
    ecs = [_make_event_create(evidence_id=ev["id"], case_id=case["id"]) for _ in range(5)]
    service.ingest_events(ecs)

    results = service.list_by_case(case["id"])
    assert len(results) == 5
    for r in results:
        assert r.case_id == case["id"]


def test_query_timestamp_ordering(db: Session):
    """Events returned must be ordered by timestamp ascending."""
    artifact_id = uuid4()
    service = EventService(db)

    base_time = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    ecs = []
    for i in range(5):
        ecs.append(_make_event_create(
            artifact_id=artifact_id,
            timestamp=base_time + timedelta(minutes=i * 10),
        ))

    # Shuffle insertion order to test deterministic ordering
    import random
    random.shuffle(ecs)
    service.ingest_events(ecs)

    results = service.list_by_artifact(artifact_id)
    timestamps = [r.timestamp for r in results]
    assert timestamps == sorted(timestamps)


def test_query_pagination(db: Session):
    """Verify limit/offset pagination works."""
    artifact_id = uuid4()
    service = EventService(db)

    base_time = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    ecs = [
        _make_event_create(
            artifact_id=artifact_id,
            timestamp=base_time + timedelta(minutes=i),
        )
        for i in range(10)
    ]
    service.ingest_events(ecs)

    page1 = service.list_by_artifact(artifact_id, skip=0, limit=3)
    page2 = service.list_by_artifact(artifact_id, skip=3, limit=3)
    page3 = service.list_by_artifact(artifact_id, skip=6, limit=3)
    page4 = service.list_by_artifact(artifact_id, skip=9, limit=3)

    assert len(page1) == 3
    assert len(page2) == 3
    assert len(page3) == 3
    assert len(page4) == 1

    all_ids = [e.id for e in page1] + [e.id for e in page2] + [e.id for e in page3] + [e.id for e in page4]
    assert len(set(all_ids)) == 10


def test_query_deterministic_pagination(db: Session):
    """Verify pagination is deterministic when events share the exact same timestamp."""
    artifact_id = uuid4()
    service = EventService(db)

    # All events have the exact same timestamp
    shared_time = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    ecs = [
        _make_event_create(
            artifact_id=artifact_id,
            timestamp=shared_time,
            data={"index": i}
        )
        for i in range(5)
    ]
    service.ingest_events(ecs)

    # Query all to get the expected deterministic order (timestamp ASC, ID ASC)
    all_events = service.list_by_artifact(artifact_id, limit=100)
    expected_order = [e.id for e in all_events]
    
    # Verify the primary sort is timestamp (they are all equal)
    # and secondary sort is ID ascending
    sorted_by_id = sorted(all_events, key=lambda e: e.id)
    assert [e.id for e in all_events] == [e.id for e in sorted_by_id]

    # Verify pagination strictly follows this order without duplication or skipping
    page1 = service.list_by_artifact(artifact_id, skip=0, limit=2)
    page2 = service.list_by_artifact(artifact_id, skip=2, limit=2)
    page3 = service.list_by_artifact(artifact_id, skip=4, limit=2)

    paginated_ids = [e.id for e in page1] + [e.id for e in page2] + [e.id for e in page3]
    
    assert paginated_ids == expected_order
    assert len(set(paginated_ids)) == 5


# ==================================================================
# CONSTRAINT / INTEGRITY TESTS
# ==================================================================


def test_event_schema_version_preserved(db: Session):
    """Schema version must persist as set."""
    service = EventService(db)
    ec = _make_event_create(schema_version=2)
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.schema_version == 2


def test_event_timestamp_desc_preserved(db: Session):
    """timestamp_desc must persist correctly."""
    service = EventService(db)
    ec = _make_event_create(timestamp_desc="LastWriteTime")
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.timestamp_desc == "LastWriteTime"


def test_event_data_json_roundtrip(db: Session):
    """JSONB data field must round-trip correctly."""
    service = EventService(db)
    data_payload = {
        "user": "SYSTEM",
        "process": "svchost.exe",
        "pid": 1234,
        "nested": {"key": [1, 2, 3]},
    }
    ec = _make_event_create(data=data_payload)
    events = service.ingest_events([ec])

    repo = EventRepository(db)
    stored = repo.get_by_id(events[0].id)
    assert stored.data == data_payload


def test_batch_ingest(db: Session):
    """Batch insertion of multiple events."""
    service = EventService(db)
    artifact_id = uuid4()
    ecs = [_make_event_create(artifact_id=artifact_id) for _ in range(20)]
    events = service.ingest_events(ecs)

    assert len(events) == 20
    results = service.list_by_artifact(artifact_id, limit=100)
    assert len(results) == 20
