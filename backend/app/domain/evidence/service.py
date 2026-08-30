from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core.hashing import calculate_sha256
from app.core.storage.factory import get_evidence_storage
from app.domain.evidence.models import Evidence, EvidenceStatus
from app.domain.evidence.repository import EvidenceRepository
from app.domain.evidence.schemas import EvidenceCreate
from app.domain.audit.service import AuditService


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = EvidenceRepository(db)
        self.audit_service = AuditService(db)


    def ingest(
        self,
        case_id: UUID,
        name: str,
        source_path: Path,
        description: str | None = None,
        source: str | None = None,
    ) -> Evidence:
        case = self.repository.get_case_by_id(case_id)

        if case is None:
            self.audit_service.record_event(
                action="EVIDENCE_INGESTION_FAILED",
                entity_type="evidence",
                entity_id=None,
                outcome="FAILURE",
                details={"case_id": str(case_id), "error": "Case not found"}
            )
            raise ValueError("Case not found")

        evidence_id = None
        try:
            sha256 = calculate_sha256(source_path)
            existing = self.repository.get_by_sha256(sha256)
            if existing:
                raise ValueError("Evidence with this SHA-256 already exists")

            evidence_id = uuid4()
            storage = get_evidence_storage()

            stored_path = storage.save_original(
                evidence_id=evidence_id,
                source_path=source_path,
            )
        except Exception as exc:
            try:
                self.audit_service.record_event(
                    action="EVIDENCE_INGESTION_FAILED",
                    entity_type="evidence",
                    entity_id=evidence_id,
                    outcome="FAILURE",
                    details={"case_id": str(case_id), "error": str(exc)}
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise

        try:
            evidence = Evidence(
                id=evidence_id,
                case_id=case_id,
                name=name,
                description=description,
                sha256=sha256,
                size_bytes=stored_path.stat().st_size,
                source=source,
                status=EvidenceStatus.PENDING,
            )
            created_evidence = self.repository.create(evidence)
        except Exception as exc:
            self.db.rollback()
            storage.delete_original(evidence_id)
            try:
                self.audit_service.record_event(
                    action="EVIDENCE_INGESTION_FAILED",
                    entity_type="evidence",
                    entity_id=evidence_id,
                    outcome="FAILURE",
                    details={"case_id": str(case_id), "error": str(exc)}
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
            raise

        try:
            self.audit_service.record_event(
                action="EVIDENCE_INGESTED",
                entity_type="evidence",
                entity_id=created_evidence.id,
                outcome="SUCCESS",
                details={"case_id": str(case_id), "sha256": sha256}
            )
            self.db.commit()
            self.db.refresh(created_evidence)
            return created_evidence
        except Exception as exc:
            self.db.rollback()
            raise RuntimeError(f"Ingestion succeeded but audit persistence failed: {exc}")

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        return self.repository.get_by_id(evidence_id)

    def list(self, limit: int, offset: int) -> list[Evidence]:
        return self.repository.list(
            limit=limit,
            offset=offset,
        )

    def update_status(
        self,
        evidence_id: UUID,
        new_status: EvidenceStatus,
    ) -> Evidence | None:
        evidence = self.repository.get_by_id(evidence_id)

        if evidence is None:
            return None

        allowed_transitions = {
            EvidenceStatus.PENDING: {
                EvidenceStatus.PROCESSING,
            },
            EvidenceStatus.PROCESSING: {
                EvidenceStatus.READY,
                EvidenceStatus.FAILED,
            },
            EvidenceStatus.READY: set(),
            EvidenceStatus.FAILED: set(),
        }

        if new_status not in allowed_transitions[evidence.status]:
            raise ValueError(
                f"Invalid evidence status transition: "
                f"{evidence.status} -> {new_status}"
            )

        old_status = evidence.status
        evidence.status = new_status

        if new_status != EvidenceStatus.FAILED:
            evidence.processing_error = None

        try:
            updated_evidence = self.repository.update(evidence)
            
            self.audit_service.record_event(
                action="EVIDENCE_STATUS_CHANGED",
                entity_type="evidence",
                entity_id=updated_evidence.id,
                outcome="SUCCESS",
                details={"old_status": old_status, "new_status": new_status}
            )
            self.db.commit()
            self.db.refresh(updated_evidence)
            return updated_evidence
        except Exception:
            self.db.rollback()
            raise

    def verify_integrity(self, evidence_id: UUID) -> str:
        evidence = self.get_by_id(evidence_id)
        if evidence is None:
            raise ValueError("Evidence not found")

        storage = get_evidence_storage()
        try:
            is_valid = storage.verify_integrity(evidence_id, evidence.sha256)
            return "valid" if is_valid else "modified"
        except FileNotFoundError:
            return "missing"
