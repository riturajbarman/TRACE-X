import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.database import SessionLocal
from app.core.storage.local import LocalEvidenceStorage
from app.domain.case.models import Case
from app.domain.evidence.models import EvidenceStatus
from app.domain.evidence.service import EvidenceService


def create_case():
    db = SessionLocal()

    try:
        case = Case(
            title=f"Test Case {uuid4()}",
            description="Test forensic case",
            created_by="pytest",
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        return case.id

    finally:
        db.close()


def test_ingest_evidence(tmp_path: Path, monkeypatch):
    source = tmp_path / "evidence.bin"
    unique_value = uuid4().hex
    content = f"TRACE-X ingestion test evidence {unique_value}".encode()
    source.write_bytes(content)

    case_id = create_case()

    storage = LocalEvidenceStorage(
        str(tmp_path / "evidence-data")
    )

    monkeypatch.setattr(
        "app.domain.evidence.service.get_evidence_storage",
        lambda: storage,
    )

    db = SessionLocal()

    try:
        service = EvidenceService(db)

        evidence = service.ingest(
            case_id=case_id,
            name="test-evidence",
            source_path=source,
            description="Test ingestion",
            source="pytest",
        )

        expected_sha256 = hashlib.sha256(content).hexdigest()

        assert evidence.case_id == case_id
        assert evidence.name == "test-evidence"
        assert evidence.description == "Test ingestion"
        assert evidence.source == "pytest"
        assert evidence.sha256 == expected_sha256
        assert evidence.size_bytes == len(content)
        assert evidence.status == EvidenceStatus.PENDING

        stored_path = storage.original_path(evidence.id)

        assert stored_path.is_file()
        assert stored_path.read_bytes() == content

        # The uploaded source must still exist because storage copies it.
        assert source.is_file()
        assert source.read_bytes() == content

        # The stored original must be read-only.
        assert stored_path.stat().st_mode & 0o222 == 0

    finally:
        db.close()


def test_ingest_rejects_nonexistent_case(tmp_path: Path):
    source = tmp_path / "evidence.bin"
    source.write_bytes(b"TRACE-X missing case")

    db = SessionLocal()

    try:
        service = EvidenceService(db)

        with pytest.raises(ValueError, match="Case not found"):
            service.ingest(
                case_id=uuid4(),
                name="missing-case-evidence",
                source_path=source,
            )

    finally:
        db.close()


def test_ingest_rejects_duplicate_sha256(tmp_path: Path, monkeypatch):
    unique_value = uuid4().hex
    content = f"TRACE-X duplicate evidence {unique_value}".encode()

    first_source = tmp_path / "first.bin"
    first_source.write_bytes(content)

    second_source = tmp_path / "second.bin"
    second_source.write_bytes(content)

    storage = LocalEvidenceStorage(
        str(tmp_path / "evidence-data")
    )

    monkeypatch.setattr(
        "app.domain.evidence.service.get_evidence_storage",
        lambda: storage,
    )

    case_id = create_case()

    db = SessionLocal()

    try:
        service = EvidenceService(db)

        first = service.ingest(
            case_id=case_id,
            name="first-evidence",
            source_path=first_source,
        )

        expected_sha256 = hashlib.sha256(content).hexdigest()

        assert first.sha256 == expected_sha256

        with pytest.raises(
            ValueError,
            match="Evidence with this SHA-256 already exists",
        ):
            service.ingest(
                case_id=case_id,
                name="duplicate-evidence",
                source_path=second_source,
            )

    finally:
        db.close()


def test_ingest_cleans_up_storage_when_database_creation_fails(
    tmp_path: Path,
    monkeypatch,
):
    source = tmp_path / "evidence.bin"
    content = f"TRACE-X database failure {uuid4().hex}".encode()
    source.write_bytes(content)

    case_id = create_case()

    storage = LocalEvidenceStorage(
        str(tmp_path / "evidence-data")
    )

    monkeypatch.setattr(
        "app.domain.evidence.service.get_evidence_storage",
        lambda: storage,
    )

    db = SessionLocal()

    try:
        service = EvidenceService(db)

        def failing_create(evidence):
            raise RuntimeError("simulated database failure")

        monkeypatch.setattr(
            service.repository,
            "create",
            failing_create,
        )

        with pytest.raises(
            RuntimeError,
            match="simulated database failure",
        ):
            service.ingest(
                case_id=case_id,
                name="database-failure-evidence",
                source_path=source,
            )

        evidence_root = storage.root_path

        assert not any(evidence_root.iterdir())

    finally:
        db.close()
