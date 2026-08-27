"""Abstract base class for all TRACE-X artifact parsers.

Every parser must:
- Declare its name, version, and supported artifact types
- Accept a file path and evidence_id
- Return an ArtifactResult with full provenance
- Handle errors safely without modifying input
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.artifact.models import ArtifactResult, ExtractionStatus


class BaseParser(ABC):
    """Abstract base for forensic artifact parsers.

    Subclasses must implement:
    - name, version, supported_types properties
    - _parse(input_path, evidence_id) method
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique parser identifier."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Parser version string."""

    @property
    @abstractmethod
    def supported_types(self) -> list[str]:
        """List of artifact type strings this parser handles."""

    @abstractmethod
    def _parse(self, input_path: Path, evidence_id: UUID) -> ArtifactResult:
        """Core parsing logic. Implemented by each parser.

        Must not modify the input file.
        Must return a fully populated ArtifactResult.
        """

    def parse(self, input_path: Path, evidence_id: UUID) -> ArtifactResult:
        """Validate input, then delegate to _parse.

        This method provides common input validation so each parser
        does not need to repeat it.
        """
        # Input validation
        if not input_path.exists():
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=self.supported_types[0] if self.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=self.name,
                parser_version=self.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Input path does not exist: {input_path.name}",
            )

        if input_path.is_file() and input_path.stat().st_size == 0:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=self.supported_types[0] if self.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=self.name,
                parser_version=self.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message="Input file is empty",
            )

        if not os.access(input_path, os.R_OK):
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=self.supported_types[0] if self.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=self.name,
                parser_version=self.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Input is not readable: {input_path.name}",
            )

        try:
            return self._parse(input_path, evidence_id)
        except Exception as exc:
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type=self.supported_types[0] if self.supported_types else "unknown",
                source_location=str(input_path),
                parser_name=self.name,
                parser_version=self.version,
                extraction_status=ExtractionStatus.FAILED,
                extracted_at=datetime.now(timezone.utc),
                error_message=f"Parser error: {type(exc).__name__}: {exc}",
            )
