from pathlib import Path

import hashlib
import pytest

from app.core.hashing import calculate_sha256


def test_calculate_sha256(tmp_path: Path):
    source = tmp_path / "evidence.bin"
    content = b"TRACE-X test evidence"
    source.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()

    assert calculate_sha256(source) == expected


def test_calculate_sha256_empty_file(tmp_path: Path):
    source = tmp_path / "empty.bin"
    source.write_bytes(b"")

    expected = hashlib.sha256(b"").hexdigest()

    assert calculate_sha256(source) == expected


def test_calculate_sha256_rejects_missing_file(tmp_path: Path):
    source = tmp_path / "missing.bin"

    with pytest.raises(FileNotFoundError):
        calculate_sha256(source)