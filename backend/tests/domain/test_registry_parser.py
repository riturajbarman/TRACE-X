"""Tests for the Registry parser.

The primary success test (test_registry_parser_valid_real_fixture) attempts to
exercise the real regipy library against the committed fixture.

KNOWN BLOCKER: The committed tests/fixtures/sample_registry.dat is 14 bytes
and is not a valid Windows Registry hive.  regipy.RegistryHive raises a
ConstError on open.  This test is therefore marked xfail with reason explaining
the blocker so that it is visible in CI without blocking the suite.

Once a valid hive fixture is committed, remove the xfail marker.

Error-path tests do NOT mock the parser and operate on controlled bad files.
"""

import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.registry import RegistryParser


# ---------------------------------------------------------------------------
# Resolve fixture paths
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_REAL_REG = _FIXTURES_DIR / "sample_registry.dat"


# ---------------------------------------------------------------------------
# Success path — REAL parser (currently blocked by invalid fixture)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    reason=(
        "tests/fixtures/sample_registry.dat is only 14 bytes and is not a "
        "valid Windows Registry hive. regipy raises ConstError on open. "
        "Replace with a genuine .hiv/.dat fixture to remove this xfail."
    ),
    strict=True,
)
def test_registry_parser_valid_real_fixture():
    """Use real regipy against real fixture. No mocks.

    This test is xfail(strict=True) because the committed fixture is invalid.
    Once a valid fixture is supplied, this test must pass without the xfail.
    """
    assert _REAL_REG.exists(), f"Fixture missing: {_REAL_REG}"
    assert _REAL_REG.stat().st_size > 512, (
        f"Fixture appears to be a stub ({_REAL_REG.stat().st_size} bytes). "
        "A valid registry hive is at least several KB."
    )

    parser = RegistryParser()
    evidence_id = uuid.uuid4()

    result = parser.parse(_REAL_REG, evidence_id)

    assert result.extraction_status == ExtractionStatus.SUCCESS, (
        f"Expected SUCCESS but got {result.extraction_status}. "
        f"Error: {result.error_message}"
    )
    assert result.parser_name == "registry_parser"
    assert result.parser_version is not None and result.parser_version != ""
    assert result.evidence_id == evidence_id
    assert result.source_location == str(_REAL_REG)
    assert result.record_count > 0
    first = result.data[0]
    assert "path" in first or "name" in first or "subkey_name" in first


# ---------------------------------------------------------------------------
# Invalid header — real parser, no mocks
# ---------------------------------------------------------------------------

def test_registry_parser_invalid_header(tmp_path):
    """Files lacking the 'regf' magic header must return FAILED."""
    parser = RegistryParser()
    evidence_id = uuid.uuid4()

    bad_file = tmp_path / "bad.dat"
    bad_file.write_bytes(b"NotARegfFile...")

    result = parser.parse(bad_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert "invalid header" in result.error_message.lower()


# ---------------------------------------------------------------------------
# Corrupt body — valid header, corrupt content — exercises real regipy error
# ---------------------------------------------------------------------------

def test_registry_parser_corrupt_body(tmp_path):
    """A file with 'regf' header but zeroed body must return FAILED.

    This test does NOT mock regipy; it relies on regipy raising an error
    when it encounters a corrupt hive.
    """
    parser = RegistryParser()
    evidence_id = uuid.uuid4()

    bad_file = tmp_path / "corrupt.dat"
    bad_file.write_bytes(b"regf" + b"\x00" * 100)

    # The real parser is called here — regipy should raise ConstError or similar.
    result = parser.parse(bad_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# Empty file
# ---------------------------------------------------------------------------

def test_registry_parser_empty_file(tmp_path):
    parser = RegistryParser()
    evidence_id = uuid.uuid4()

    empty_file = tmp_path / "empty.dat"
    empty_file.write_bytes(b"")

    result = parser.parse(empty_file, evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED
    assert result.error_message is not None


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------

def test_registry_parser_missing_file(tmp_path):
    parser = RegistryParser()
    evidence_id = uuid.uuid4()

    result = parser.parse(tmp_path / "nonexistent.dat", evidence_id)

    assert result.extraction_status == ExtractionStatus.FAILED


# ---------------------------------------------------------------------------
# Parser metadata
# ---------------------------------------------------------------------------

def test_registry_parser_metadata():
    parser = RegistryParser()
    assert parser.name == "registry_parser"
    assert parser.version != ""
    assert "registry" in parser.supported_types
