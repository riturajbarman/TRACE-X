"""Extraction service."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.storage.factory import get_evidence_storage
from app.domain.artifact.models import ArtifactResult, ExtractionStatus
from app.domain.artifact.parsers.evtx import EvtxParser
from app.domain.artifact.parsers.filesystem import FilesystemMetadataParser
from app.domain.artifact.parsers.registry import RegistryParser
from app.domain.artifact.registry import ParserRegistry
from app.domain.artifact.sandbox import SandboxedExecution
from app.domain.evidence.service import EvidenceService


class ExtractionService:
    """Coordinates artifact extraction from evidence."""

    def __init__(self, db: Session):
        self.db = db
        self.evidence_service = EvidenceService(db)
        self.storage = get_evidence_storage()
        
        self.registry = ParserRegistry()
        self.registry.register(FilesystemMetadataParser())
        self.registry.register(EvtxParser())
        self.registry.register(RegistryParser())
        
        self.sandbox = SandboxedExecution(timeout_seconds=60)

    def extract(self, evidence_id: UUID, artifact_types: list[str] | None = None) -> list[ArtifactResult]:
        """Extract artifacts from the specified evidence."""
        evidence = self.evidence_service.get_by_id(evidence_id)
        if not evidence:
            raise ValueError("Evidence not found")
            
        original_path = self.storage.original_path(evidence_id)
        if not original_path.exists():
            raise FileNotFoundError("Original evidence file missing")
            
        # Determine which parsers to run
        if artifact_types is None:
            # By default try all registered artifact types
            artifact_types = list(self.registry._parsers.keys())
            
        results = []
        for a_type in artifact_types:
            parser = self.registry.get_parser(a_type)
            if not parser:
                # Unsupported type explicitly requested
                continue
                
            # Execute within the sandbox
            result = self.sandbox.execute(parser, original_path, evidence_id)
            results.append(result)
            
        return results
