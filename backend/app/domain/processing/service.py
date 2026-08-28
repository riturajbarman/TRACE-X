import uuid
from datetime import datetime, timezone
import json

from sqlalchemy.orm import Session

from app.domain.evidence.service import EvidenceService
from app.domain.evidence.models import EvidenceStatus
from app.domain.artifact.service import ExtractionService
from app.domain.event.service import EventService
from app.domain.event.schemas import EventCreate
from app.domain.detection.repository import DetectionRepository
from app.domain.detection.models import Detection

class ProcessingService:
    def __init__(self, session: Session):
        self.session = session
        self.evidence_service = EvidenceService(session)
        self.extraction_service = ExtractionService(session)
        self.event_service = EventService(session)
        self.detection_repo = DetectionRepository(session)

    def process_evidence(self, evidence_id: uuid.UUID) -> dict:
        """
        Orchestrates the entire MVP processing pipeline for a piece of evidence.
        """
        # 1. Start processing
        try:
            evidence = self.evidence_service.update_status(evidence_id, EvidenceStatus.PROCESSING)
            if evidence is None:
                raise ValueError("Evidence not found")
        except ValueError as exc:
            raise exc

        case_id = evidence.case_id

        try:
            # 2. Extract artifacts
            artifact_results = self.extraction_service.extract(evidence_id)

            # 3. Normalize into events
            event_creates = []
            for result in artifact_results:
                if result.extraction_status.value != "FAILED" and result.data:
                    for i, record in enumerate(result.data):
                        # Extract a timestamp if available, else use extraction time
                        timestamp = result.extracted_at
                        if isinstance(record, dict):
                            # Simplistic timestamp heuristic for MVP
                            if "timestamp" in record:
                                try:
                                    # Very naive parse
                                    timestamp = datetime.fromisoformat(str(record["timestamp"])).replace(tzinfo=timezone.utc)
                                except Exception:
                                    pass

                        event_creates.append(
                            EventCreate(
                                artifact_id=result.artifact_id,
                                evidence_id=evidence_id,
                                case_id=case_id,
                                event_type=result.artifact_type,
                                source=result.parser_name,
                                timestamp=timestamp,
                                data=record if isinstance(record, dict) else {"raw": record}
                            )
                        )

            # 4. Ingest events
            created_events = []
            if event_creates:
                created_events = self.event_service.ingest_events(event_creates)

            # 5. Run MVP Detection (Naive keyword match for MVP)
            suspicious_keywords = ["malicious", "mimikatz", "powershell -enc", "cmd.exe /c"]
            detections_to_create = []

            for event in created_events:
                event_data_str = json.dumps(event.data).lower()
                for keyword in suspicious_keywords:
                    if keyword in event_data_str:
                        detections_to_create.append(
                            Detection(
                                case_id=case_id,
                                event_id=event.id,
                                detection_type="keyword_match",
                                rule_id=f"KWD-{keyword.upper().replace(' ', '_')}",
                                rule_version="1.0",
                                severity="HIGH",
                                confidence=80,
                            )
                        )

            # Insert detections
            if detections_to_create:
                self.session.add_all(detections_to_create)
                self.session.commit()

            # 6. Mark Ready
            self.evidence_service.update_status(evidence_id, EvidenceStatus.READY)

            return {
                "status": "success",
                "extracted_artifacts": len(artifact_results),
                "events_created": len(created_events),
                "detections_created": len(detections_to_create)
            }

        except Exception as exc:
            # Mark as failed
            self.evidence_service.update_status(evidence_id, EvidenceStatus.FAILED)
            raise exc
