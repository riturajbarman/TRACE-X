from pathlib import Path
from uuid import uuid4

import pytest

from app.core.storage.local import LocalEvidenceStorage


def test_save_original_copies_source_and_makes_destination_read_only(
    tmp_path: Path,
):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X test evidence")

    evidence_id = uuid4()

    destination = storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    assert destination == (
        tmp_path / "evidence-data" / str(evidence_id) / "original"
    )

    assert source.exists()
    assert source.read_bytes() == b"TRACE-X test evidence"

    assert destination.exists()
    assert destination.read_bytes() == b"TRACE-X test evidence"

    assert destination.stat().st_mode & 0o222 == 0


def test_save_original_rejects_missing_source(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    evidence_id = uuid4()
    source = tmp_path / "missing.bin"

    with pytest.raises(FileNotFoundError):
        storage.save_original(
            evidence_id=evidence_id,
            source_path=source,
        )


def test_save_original_rejects_existing_original(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X test evidence")

    evidence_id = uuid4()

    storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    with pytest.raises(FileExistsError):
        storage.save_original(
            evidence_id=evidence_id,
            source_path=source,
        )


def test_exists(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X test evidence")

    evidence_id = uuid4()

    assert storage.exists(evidence_id) is False

    storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    assert storage.exists(evidence_id) is True


def test_open_original_reads_stored_evidence(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X test evidence")

    evidence_id = uuid4()

    storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    with storage.open_original(evidence_id) as original:
        assert original.read() == b"TRACE-X test evidence"


def test_open_original_rejects_missing_evidence(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    with pytest.raises(FileNotFoundError):
        storage.open_original(uuid4())
def test_delete_original(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X test evidence")

    evidence_id = uuid4()

    storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    assert storage.exists(evidence_id) is True

    storage.delete_original(evidence_id)

    assert storage.exists(evidence_id) is False