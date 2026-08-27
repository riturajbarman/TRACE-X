"""Tests for the EVTX parser.

The primary success test (test_evtx_parser_valid_real_fixture) exercises the
ACTUAL python-evtx library against a real .evtx binary fixture.  No mocks are
used in that test.

Failure / error-path tests may use controlled bad fixtures or mocks where
appropriate.
"""

import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.evtx import EvtxParser


# ---------------------------------------------------------------------------
# Resolve the real fixture once at module level.
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_REAL_EVTX = _FIXTURES_DIR / "sample.evtx"


# ---------------------------------------------------------------------------
# Success path — REAL parser, REAL fixture (no mocks)
# ---------------------------------------------------------------------------

def test_evtx_parser_valid_real_fixture():
    """Verify that the real python-evtx library can parse sample.evtx.

    This test does NOT use any mocks.  It exercises the actual parser code and
    the actual file on disk to prove the success path works end-to-end.
    """
    assert _REAL_EVTX.exists(), (
        f"Real EVTX fixture not found: {_REAL_EVTX}. "
        "Cannot prove success path without a genuine fixture."
    )

    parser = EvtxParser()
    evidence_id = uuid.uuid4()

    result = parser.parse(_REAL_EVTX, evidence_id)

    assert result.extraction_status == ExtractionStatus.SUCCESS, (
        f"Expected SUCCESS but got {result.extraction_status}. "
        f"Error: {result.error_message}"
    )
    assert result.parser_name == "evtx_parser"
    assert result.parser_version is not None and result.parser_version != ""
    assert result.evidence_id == evidence_id
    assert result.source_location == str(_REAL_EVTX)
    assert result.record_count > 0, "Expected real records from sample.evtx"
    assert len(result.data) > 0
    # Verify provenance fields are present in each record.
    first_record = result.data[0]
    assert "xml" in first_record
    assert "record_num" in first_record
    # Check the extraction limit is enforced (file has 62031 records).
    assert result.record_count <= 1000, (
        f"Extraction limit of 1000 records was not enforced; "
        f"got {result.record_count}"
    )


# ---------------------------------------------------------------------------
# Invalid header
# ---------------------------------------------------------------------------

def test_evtx_parser_invalid_header(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()

    bad_file = tmp_path / "bad.evtx"
    bad_file.write_bytes(b"NotAnEvtxFile...")

    result = parser.parse(bad_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "invalid header" in result.error_message.lower()


# ---------------------------------------------------------------------------
# Corrupt file — valid header, truncated body
# ---------------------------------------------------------------------------

def test_evtx_parser_corrupt_body(tmp_path):
    """A file with valid ElfFile header but zeroed/corrupt body.

    python-evtx parses based on internal structures; a zeroed body produces an
    exception or zero records.  We test that the parser handles this gracefully
    without crashing and returns FAILED or PARTIAL.
    """
    from unittest.mock import patch

    parser = EvtxParser()
    evidence_id = uuid.uuid4()

    bad_file = tmp_path / "corrupt.evtx"
    bad_file.write_bytes(b"ElfFile\x00" + b"\x00" * 100)

    # Simulate an exception from python-evtx on a body it cannot parse.
    with patch("app.domain.artifact.parsers.evtx.Evtx", side_effect=Exception("corrupt body")):
        result = parser.parse(bad_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "corrupt body" in result.error_message


# ---------------------------------------------------------------------------
# Empty file
# ---------------------------------------------------------------------------

def test_evtx_parser_empty_file(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()

    empty_file = tmp_path / "empty.evtx"
    empty_file.write_bytes(b"")

    result = parser.parse(empty_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------

def test_evtx_parser_missing_file(tmp_path):
    parser = EvtxParser()
    evidence_id = uuid.uuid4()

    result = parser.parse(tmp_path / "nonexistent.evtx", evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED


# ---------------------------------------------------------------------------
# Parser metadata
# ---------------------------------------------------------------------------

def test_evtx_parser_metadata():
    parser = EvtxParser()
    assert parser.name == "evtx_parser"
    assert parser.version != ""
    assert "evtx" in parser.supported_types
