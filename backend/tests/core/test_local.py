from pathlib import Path
from uuid import uuid4

import pytest

from app.core.storage.local import LocalEvidenceStorage


def test_save_original_copies_source(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    content = b"TRACE-X test evidence"
    source.write_bytes(content)

    evidence_id = uuid4()

    stored = storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    assert source.exists()
    assert stored.exists()
    assert stored.read_bytes() == content


def test_save_original_makes_original_read_only(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X immutable evidence")

    evidence_id = uuid4()

    stored = storage.save_original(
        evidence_id=evidence_id,
        source_path=source,
    )

    assert stored.exists()
    assert stored.stat().st_mode & 0o222 == 0


def test_save_original_rejects_missing_source(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "missing.bin"

    with pytest.raises(FileNotFoundError):
        storage.save_original(
            evidence_id=uuid4(),
            source_path=source,
        )


def test_save_original_rejects_existing_original(tmp_path: Path):
    storage = LocalEvidenceStorage(str(tmp_path / "evidence-data"))

    source = tmp_path / "upload.bin"
    source.write_bytes(b"TRACE-X evidence")

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
