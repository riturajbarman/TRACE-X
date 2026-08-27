import pytest
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.domain.audit.models import AuditEvent
from app.domain.audit.service import AuditService
from app.domain.case.service import CaseService
from app.domain.case.models import CaseStatus, Case
from app.domain.evidence.service import EvidenceService
from app.domain.evidence.models import EvidenceStatus, Evidence
from app.core.storage.local import LocalEvidenceStorage

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_audit_service_creates_event(db: Session):
    service = AuditService(db)
    entity_id = uuid4()

    event = service.record_event(
        action="TEST_ACTION",
        entity_type="test_entity",
        entity_id=entity_id,
        outcome="SUCCESS",
        details={"key": "value"}
    )

    assert event.id is not None
    assert event.timestamp is not None
    assert event.action == "TEST_ACTION"
    assert event.entity_type == "test_entity"
    assert event.entity_id == entity_id
    assert event.outcome == "SUCCESS"
    assert event.details == {"key": "value"}

    # Verify persistence
    persisted = db.get(AuditEvent, event.id)
    assert persisted is not None
    assert persisted.action == "TEST_ACTION"

def test_case_creation_audits(db: Session):
    case_service = CaseService(db)
    case = case_service.create(title=f"Audit Case {uuid4()}", description="Test", created_by="pytest")

    # Check audit
    stmt = select(AuditEvent).where(
        AuditEvent.entity_id == case.id,
        AuditEvent.action == "CASE_CREATED"
    )
    audit = db.scalar(stmt)
    assert audit is not None
    assert audit.outcome == "SUCCESS"
    assert audit.entity_type == "case"

def test_case_status_change_audits(db: Session):
    case_service = CaseService(db)
    case = case_service.create(title=f"Audit Case Status {uuid4()}", description="Test", created_by="pytest")

    updated_case = case_service.update_status(case.id, CaseStatus.CLOSED)

    stmt = select(AuditEvent).where(
        AuditEvent.entity_id == updated_case.id,
        AuditEvent.action == "CASE_STATUS_CHANGED"
    )
    audit = db.scalar(stmt)
    assert audit is not None
    assert audit.outcome == "SUCCESS"
    assert audit.details["old_status"] == CaseStatus.OPEN.value
    assert audit.details["new_status"] == CaseStatus.CLOSED.value

def test_invalid_case_status_transition_no_audit(db: Session):
    case_service = CaseService(db)
    case = case_service.create(title=f"Audit Case Inv Status {uuid4()}", description="Test", created_by="pytest")

    with pytest.raises(ValueError):
        case_service.update_status(case.id, CaseStatus.OPEN) # Already OPEN

    stmt = select(AuditEvent).where(
        AuditEvent.entity_id == case.id,
        AuditEvent.action == "CASE_STATUS_CHANGED"
    )
    audit = db.scalar(stmt)
    assert audit is None  # No false success

def test_evidence_ingestion_audits(db: Session, tmp_path, monkeypatch):
    case_service = CaseService(db)
    case = case_service.create(title=f"Ev Audit {uuid4()}", description="Test", created_by="pytest")

    source = tmp_path / "ev.bin"
    source.write_bytes(f"audit test data {uuid4()}".encode())

    storage = LocalEvidenceStorage(str(tmp_path / "ev-data"))
    monkeypatch.setattr("app.domain.evidence.service.get_evidence_storage", lambda: storage)

    evidence_service = EvidenceService(db)
    evidence = evidence_service.ingest(case_id=case.id, name="ev", source_path=source)

    stmt = select(AuditEvent).where(
        AuditEvent.entity_id == evidence.id,
        AuditEvent.action == "EVIDENCE_INGESTED"
    )
    audit = db.scalar(stmt)
    assert audit is not None
    assert audit.outcome == "SUCCESS"
    assert audit.entity_type == "evidence"

def test_evidence_ingestion_failure_audits(db: Session, tmp_path, monkeypatch):
    case_service = CaseService(db)
    case = case_service.create(title=f"Ev Audit Fail {uuid4()}", description="Test", created_by="pytest")

    source = tmp_path / "ev-fail.bin"
    source.write_bytes(f"audit fail data {uuid4()}".encode())

    storage = LocalEvidenceStorage(str(tmp_path / "ev-data"))
    monkeypatch.setattr("app.domain.evidence.service.get_evidence_storage", lambda: storage)

    evidence_service = EvidenceService(db)

    # Simulate DB failure during ingestion
    def failing_create(ev):
        raise RuntimeError("simulated database failure")
    monkeypatch.setattr(evidence_service.repository, "create", failing_create)

    with pytest.raises(RuntimeError):
        evidence_service.ingest(case_id=case.id, name="ev-fail", source_path=source)

    # We should have an EVIDENCE_INGESTION_FAILED audit log, but wait, the failing_create is raised.
    # Because failing_create doesn't commit, we might need a separate session to check the audit log,
    # OR since the service logs the failure AFTER the rollback? Wait, the service catches the exception and logs it!
    # Let's check if the failure audit was recorded.
    stmt = select(AuditEvent).where(
        AuditEvent.action == "EVIDENCE_INGESTION_FAILED",
        AuditEvent.details.op('->>')('case_id') == str(case.id)
    )
    audit = db.scalar(stmt)
    assert audit is not None
    assert audit.outcome == "FAILURE"

def test_evidence_status_change_audits(db: Session, tmp_path, monkeypatch):
    case_service = CaseService(db)
    case = case_service.create(title=f"Ev Status Audit {uuid4()}", description="Test", created_by="pytest")

    source = tmp_path / "ev-status.bin"
    source.write_bytes(f"audit status data {uuid4()}".encode())

    storage = LocalEvidenceStorage(str(tmp_path / "ev-data"))
    monkeypatch.setattr("app.domain.evidence.service.get_evidence_storage", lambda: storage)

    evidence_service = EvidenceService(db)
    evidence = evidence_service.ingest(case_id=case.id, name="ev-status", source_path=source)

    updated_evidence = evidence_service.update_status(evidence.id, EvidenceStatus.PROCESSING)

    stmt = select(AuditEvent).where(
        AuditEvent.entity_id == updated_evidence.id,
        AuditEvent.action == "EVIDENCE_STATUS_CHANGED"
    )
    audit = db.scalar(stmt)
    assert audit is not None
    assert audit.outcome == "SUCCESS"

def test_rolled_back_transaction_leaves_no_success_audit(db: Session, monkeypatch):
    case_service = CaseService(db)
    # Simulate DB failure during case creation
    def failing_create(c):
        raise RuntimeError("db failed")
    monkeypatch.setattr(case_service.repository, "create", failing_create)

    with pytest.raises(RuntimeError):
        case_service.create(title="never created", description="desc", created_by="pytest")

    stmt = select(AuditEvent).where(
        AuditEvent.action == "CASE_CREATED",
        AuditEvent.details.op('->>')('title') == "never created"
    )
    audit = db.scalar(stmt)
    assert audit is None

def test_case_audit_write_failure(db: Session, monkeypatch):
    case_service = CaseService(db)

    def failing_record_event(*args, **kwargs):
        raise RuntimeError("simulated audit write failure")

    monkeypatch.setattr(case_service.audit_service, "record_event", failing_record_event)

    with pytest.raises(RuntimeError, match="simulated audit write failure"):
        case_service.create(title="Audit fail case", description="test", created_by="pytest")

    stmt = select(Case).where(Case.title == "Audit fail case")
    assert db.scalar(stmt) is None

def test_evidence_audit_write_failure(db: Session, tmp_path, monkeypatch):
    case_service = CaseService(db)
    case = case_service.create(title=f"Ev Audit Fail {uuid4()}", description="Test", created_by="pytest")

    source = tmp_path / "ev-audit-fail.bin"
    source.write_bytes(f"audit write failure data {uuid4()}".encode())

    storage = LocalEvidenceStorage(str(tmp_path / "ev-data"))
    monkeypatch.setattr("app.domain.evidence.service.get_evidence_storage", lambda: storage)

    evidence_service = EvidenceService(db)

    def failing_record_event(action, *args, **kwargs):
        if action == "EVIDENCE_INGESTED":
            raise RuntimeError("simulated audit write failure")
        return AuditEvent(id=uuid4(), action=action, entity_type="test", outcome="SUCCESS")

    monkeypatch.setattr(evidence_service.audit_service, "record_event", failing_record_event)

    with pytest.raises(RuntimeError, match="Ingestion succeeded but audit persistence failed"):
        evidence_service.ingest(case_id=case.id, name="ev-audit-fail", source_path=source)

    stmt = select(Evidence).where(Evidence.name == "ev-audit-fail")
    assert db.scalar(stmt) is None

    # Verify the original evidence file is NOT deleted because the ingestion part succeeded
    # It will remain in the evidence_root directory, but how do we know the ID?
    # We can check if ANY file exists in the directory.
    evidence_root = storage.root_path
    assert any(evidence_root.iterdir())
