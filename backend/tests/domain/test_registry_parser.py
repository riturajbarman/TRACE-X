import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.registry import RegistryParser


from unittest.mock import MagicMock, patch

def test_registry_parser_valid(tmp_path):
    parser = RegistryParser()
    evidence_id = uuid.uuid4()
    
    # Create a file that passes the header check
    fixture_path = tmp_path / "sample_registry.dat"
    fixture_path.write_bytes(b"regf" + b"\x00" * 100)
        
    with patch("app.domain.artifact.parsers.registry.RegistryHive") as mock_hive_cls:
        mock_hive = MagicMock()
        mock_hive.recurse_subkeys.return_value = [{"key": "test"}]
        mock_hive_cls.return_value = mock_hive
        
        result = parser.parse(fixture_path, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.SUCCESS, result.error_message
    assert result.parser_name == "registry_parser"
    assert result.record_count == 1
    assert result.evidence_id == evidence_id


def test_registry_parser_invalid_header(tmp_path):
    parser = RegistryParser()
    evidence_id = uuid.uuid4()
    
    bad_file = tmp_path / "bad.dat"
    bad_file.write_bytes(b"NotARegfFile...")
    
    result = parser.parse(bad_file, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "invalid header" in result.error_message


def test_registry_parser_corrupt_file(tmp_path):
    parser = RegistryParser()
    evidence_id = uuid.uuid4()
    
    bad_file = tmp_path / "corrupt.dat"
    # Valid header, but corrupt body
    bad_file.write_bytes(b"regf" + b"\x00" * 100)
    
    result = parser.parse(bad_file, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "Parser error" in result.error_message
