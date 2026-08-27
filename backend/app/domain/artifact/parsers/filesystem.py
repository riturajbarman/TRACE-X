"""Filesystem metadata parser."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser


class FilesystemMetadataParser(BaseParser):
    """Extracts basic filesystem metadata without reading file contents."""

    @property
    def name(self) -> str:
        return "filesystem_metadata"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_types(self) -> list[str]:
        return ["filesystem"]

    def _parse(self, input_path: Path, evidence_id: UUID) -> ArtifactResult:
        data = []
        
        def process_path(p: Path):
            stat = p.stat()
            return {
                "filename": p.name,
                "path": str(p),
                "size_bytes": stat.st_size,
                "is_dir": p.is_dir(),
                "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            }

        if input_path.is_file():
            data.append(process_path(input_path))
        elif input_path.is_dir():
            for p in input_path.rglob("*"):
                data.append(process_path(p))

        return ArtifactResult(
            artifact_id=uuid4(),
            evidence_id=evidence_id,
            artifact_type="filesystem",
            source_location=str(input_path),
            parser_name=self.name,
            parser_version=self.version,
            extraction_status=ExtractionStatus.SUCCESS,
            extracted_at=datetime.now(timezone.utc),
            data=data,
            record_count=len(data),
        )
