import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.evtx import EvtxParser


from unittest.mock import MagicMock, patch

def test_evtx_parser_valid(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()
    
    # Create a file that passes the header check
    fixture_path = tmp_path / "sample.evtx"
    fixture_path.write_bytes(b"ElfFile\x00" + b"\x00" * 100)
        
    with patch("app.domain.artifact.parsers.evtx.Evtx") as mock_evtx_cls:
        # Setup mock records
        mock_record = MagicMock()
        mock_record.record_num.return_value = 1
        mock_record.xml.return_value = "<Event></Event>"
        
        mock_log = MagicMock()
        mock_log.records.return_value = [mock_record]
        
        mock_evtx_cls.return_value.__enter__.return_value = mock_log
        
        result = parser.parse(fixture_path, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.parser_name == "evtx_parser"
    assert result.record_count == 1
    assert "xml" in result.data[0]
    assert "record_num" in result.data[0]
    assert result.evidence_id == evidence_id


def test_evtx_parser_invalid_header(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()
    
    bad_file = tmp_path / "bad.evtx"
    bad_file.write_bytes(b"NotAnEvtxFile...")
    
    result = parser.parse(bad_file, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "invalid header" in result.error_message


def test_evtx_parser_corrupt_file(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()
    
    bad_file = tmp_path / "corrupt.evtx"
    # Valid header, but corrupt body
    bad_file.write_bytes(b"ElfFile\x00" + b"\x00" * 100)
    
    with patch("app.domain.artifact.parsers.evtx.Evtx", side_effect=Exception("Parser error")):
        result = parser.parse(bad_file, evidence_id)
    
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "Parser error" in result.error_message
