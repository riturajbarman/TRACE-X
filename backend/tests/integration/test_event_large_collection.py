"""Large event collection integration test.

Verifies that the Event Store can handle a realistically sized
synthetic event collection with correct insertion, querying,
ordering, and pagination.

Uses 1000 events to provide meaningful coverage without
excessive test duration.
"""

import time
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.case.service import CaseService
from app.domain.event.models import Event
from app.domain.event.repository import EventRepository
from app.domain.event.schemas import EventCreate
from app.domain.event.service import EventService
from app.domain.evidence.service import EvidenceService


EVENT_COUNT = 1000


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _setup_provenance(db: Session):
    """Create case and evidence for provenance chain."""
    import tempfile
    from pathlib import Path

    case_service = CaseService(db)
    case = case_service.create(
        title=f"Large Collection Case {uuid4()}",
        description="Integration test",
        created_by="pytest",
    )

    evidence_service = EvidenceService(db)
    content = f"large-collection-evidence-{uuid4()}".encode()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
        f.write(content)
        tmp_path = Path(f.name)

    try:
        evidence = evidence_service.ingest(
            case_id=case.id,
            name=f"ev-large-{uuid4()}",
            source_path=tmp_path,
            description="large collection test evidence",
            source="pytest",
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return case.id, evidence.id


def test_large_event_collection(db: Session):
    """Insert and query a large synthetic event collection.

    Verifies:
    - Batch insertion of EVENT_COUNT events succeeds
    - Query retrieval succeeds
    - Ordering is deterministic (timestamp ascending)
    - Expected record count is correct
    - Pagination works across the full collection
    """
    case_id, evidence_id = _setup_provenance(db)
    artifact_id = uuid4()
    service = EventService(db)

    base_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    event_creates = []
    for i in range(EVENT_COUNT):
        event_creates.append(EventCreate(
            artifact_id=artifact_id,
            evidence_id=evidence_id,
            case_id=case_id,
            event_type="file_creation" if i % 2 == 0 else "registry_modification",
            source="evtx" if i % 3 == 0 else "regipy",
            timestamp=base_time + timedelta(seconds=i),
            timestamp_desc="SystemTime",
            schema_version=1,
            data={"index": i, "host": "WORKSTATION-01"},
        ))

    # Insert
    start = time.monotonic()
    events = service.ingest_events(event_creates)
    insert_elapsed = time.monotonic() - start

    assert len(events) == EVENT_COUNT

    # Query full collection via artifact
    start = time.monotonic()
    page_size = 100
    all_results = []
    offset = 0
    while True:
        page = service.list_by_artifact(artifact_id, skip=offset, limit=page_size)
        all_results.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    query_elapsed = time.monotonic() - start

    assert len(all_results) == EVENT_COUNT

    # Verify deterministic ordering
    timestamps = [r.timestamp for r in all_results]
    assert timestamps == sorted(timestamps)

    # Verify provenance is preserved
    for r in all_results:
        assert r.artifact_id == artifact_id
        assert r.evidence_id == evidence_id
        assert r.case_id == case_id

    # Verify data payload round-trip
    first = all_results[0]
    assert first.data["index"] == 0
    assert first.data["host"] == "WORKSTATION-01"

    last = all_results[-1]
    assert last.data["index"] == EVENT_COUNT - 1

    # Report timing (informational, not asserted)
    print(f"\n  Large collection test ({EVENT_COUNT} events):")
    print(f"    Insert: {insert_elapsed:.2f}s")
    print(f"    Paginated query: {query_elapsed:.2f}s")
