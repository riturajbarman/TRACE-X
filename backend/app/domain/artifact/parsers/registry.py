"""Windows Registry parser."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from regipy.registry import RegistryHive
from regipy.exceptions import RegistryKeyNotFoundException

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser


class RegistryParser(BaseParser):
    """Parses Windows Registry hives."""

    @property
    def name(self) -> str:
        return "registry_parser"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_types(self) -> list[str]:
        return ["registry"]

    def _parse(self, input_path: Path, evidence_id: UUID) -> ArtifactResult:
        data = []

        # Verify it looks like a Registry Hive (signature 'regf' at start)
        with open(input_path, "rb") as f:
            header = f.read(4)
            if header != b"regf":
                return ArtifactResult(
                    artifact_id=uuid4(),
                    evidence_id=evidence_id,
                    artifact_type="registry",
                    source_location=str(input_path),
                    parser_name=self.name,
                    parser_version=self.version,
                    extraction_status=ExtractionStatus.FAILED,
                    extracted_at=datetime.now(timezone.utc),
                    error_message="Not a valid Registry Hive (invalid header).",
                )

        try:
            hive = RegistryHive(str(input_path))

            # Recurse over all subkeys
            for entry in hive.recurse_subkeys(as_json=True):
                data.append(entry)

        except Exception as exc:
            status = ExtractionStatus.PARTIAL if data else ExtractionStatus.FAILED
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type="registry",
                source_location=str(input_path),
                parser_name=self.name,
                parser_version=self.version,
                extraction_status=status,
                extracted_at=datetime.now(timezone.utc),
                data=data,
                record_count=len(data),
                error_message=f"Parser error: {type(exc).__name__}: {exc}"
            )

        return ArtifactResult(
            artifact_id=uuid4(),
            evidence_id=evidence_id,
            artifact_type="registry",
            source_location=str(input_path),
            parser_name=self.name,
            parser_version=self.version,
            extraction_status=ExtractionStatus.SUCCESS,
            extracted_at=datetime.now(timezone.utc),
            data=data,
            record_count=len(data),
        )
