import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.filesystem import FilesystemMetadataParser


def test_filesystem_parser_valid_file(tmp_path):
    parser = FilesystemMetadataParser()
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("hello")
    evidence_id = uuid.uuid4()

    result = parser.parse(test_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.evidence_id == evidence_id
    assert result.parser_name == "filesystem_metadata"
    assert result.parser_version == "1.0.0"
    assert result.record_count == 1
    assert result.data[0]["filename"] == "test_doc.txt"
    assert result.data[0]["size_bytes"] == 5
    assert not result.data[0]["is_dir"]
    assert "created_at" in result.data[0]
    assert "modified_at" in result.data[0]


def test_filesystem_parser_valid_directory(tmp_path):
    parser = FilesystemMetadataParser()
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("1")
    (test_dir / "file2.txt").write_text("22")
    
    sub_dir = test_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "file3.txt").write_text("333")

    evidence_id = uuid.uuid4()
    result = parser.parse(test_dir, evidence_id)

    assert result.extraction_status == ExtractionStatus.SUCCESS
    # 3 files + 1 sub_dir = 4 items
    assert result.record_count == 4
    
    filenames = {item["filename"] for item in result.data}
    assert filenames == {"file1.txt", "file2.txt", "sub", "file3.txt"}
