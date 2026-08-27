"""Windows Event Log (EVTX) parser."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from Evtx.Evtx import Evtx
from Evtx.Views import evtx_file_xml_view

from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.base import BaseParser


class EvtxParser(BaseParser):
    """Parses Windows Event Log (.evtx) files."""

    @property
    def name(self) -> str:
        return "evtx_parser"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_types(self) -> list[str]:
        return ["evtx"]

    def _parse(self, input_path: Path, evidence_id: UUID) -> ArtifactResult:
        data = []

        # Verify it looks like an EVTX file
        with open(input_path, "rb") as f:
            header = f.read(8)
            if header != b"ElfFile\x00":
                return ArtifactResult(
                    artifact_id=uuid4(),
                    evidence_id=evidence_id,
                    artifact_type="evtx",
                    source_location=str(input_path),
                    parser_name=self.name,
                    parser_version=self.version,
                    extraction_status=ExtractionStatus.FAILED,
                    extracted_at=datetime.now(timezone.utc),
                    error_message="Not a valid EVTX file (invalid header).",
                )

        try:
            with Evtx(str(input_path)) as log:
                # Iterate through records and convert to simple dicts for MVP
                # Limit to 1000 records for MVP to avoid hanging on large files
                for i, record in enumerate(log.records()):
                    if i >= 1000:
                        break
                    data.append({
                        "record_num": record.record_num(),
                        "xml": record.xml()
                    })
        except Exception as exc:
            # If we partially parsed something before failure, we could return PARTIAL,
            # but python-evtx usually raises on open if the file is corrupt,
            # or during iteration. If data is not empty, it's a partial success.
            status = ExtractionStatus.PARTIAL if data else ExtractionStatus.FAILED
            return ArtifactResult(
                artifact_id=uuid4(),
                evidence_id=evidence_id,
                artifact_type="evtx",
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
            artifact_type="evtx",
            source_location=str(input_path),
            parser_name=self.name,
            parser_version=self.version,
            extraction_status=ExtractionStatus.SUCCESS,
            extracted_at=datetime.now(timezone.utc),
            data=data,
            record_count=len(data),
        )
