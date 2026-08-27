import uuid
from pathlib import Path

import pytest

from app.domain.artifact.models import ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser
from app.domain.artifact.registry import ParserRegistry
from app.domain.artifact.models import ArtifactResult


class DummyParser(BaseParser):
    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def supported_types(self) -> list[str]:
        return ["dummy_type"]

    def _parse(self, input_path: Path, evidence_id: uuid.UUID) -> ArtifactResult:
        if input_path.name == "raise_error.txt":
            raise ValueError("Test error")
        return ArtifactResult(
            evidence_id=evidence_id,
            artifact_type="dummy_type",
            source_location=str(input_path),
            parser_name=self.name,
            parser_version=self.version,
            extraction_status=ExtractionStatus.SUCCESS,
            data=[{"test": "data"}]
        )


def test_parser_registry():
    registry = ParserRegistry()
    parser = DummyParser()
    registry.register(parser)

    assert registry.get_parser("dummy_type") == parser
    assert registry.get_parser("unknown") is None

    metadata = registry.list_parsers()
    assert len(metadata) == 1
    assert metadata[0]["name"] == "dummy"
    assert metadata[0]["supported_types"] == ["dummy_type"]


def test_base_parser_missing_input():
    parser = DummyParser()
    missing_path = Path("/does/not/exist.txt")
    evidence_id = uuid.uuid4()

    result = parser.parse(missing_path, evidence_id)
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "does not exist" in result.error_message
    assert result.evidence_id == evidence_id
    assert result.parser_name == "dummy"


def test_base_parser_empty_input(tmp_path):
    parser = DummyParser()
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    evidence_id = uuid.uuid4()

    result = parser.parse(empty_file, evidence_id)
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "empty" in result.error_message


def test_base_parser_successful_parse(tmp_path):
    parser = DummyParser()
    valid_file = tmp_path / "valid.txt"
    valid_file.write_text("content")
    evidence_id = uuid.uuid4()

    result = parser.parse(valid_file, evidence_id)
    assert result.extraction_status == ExtractionStatus.SUCCESS
    assert result.data == [{"test": "data"}]


def test_base_parser_handles_exception(tmp_path):
    parser = DummyParser()
    error_file = tmp_path / "raise_error.txt"
    error_file.write_text("content")
    evidence_id = uuid.uuid4()

    result = parser.parse(error_file, evidence_id)
    assert result.extraction_status == ExtractionStatus.FAILED
    assert "Test error" in result.error_message
