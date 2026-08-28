import uuid
from sqlalchemy.orm import Session

from app.domain.case.service import CaseService
from app.domain.evidence.service import EvidenceService
from app.domain.event.service import EventService
from app.domain.detection.service import RiskService
from app.domain.detection.repository import DetectionRepository


class ReportService:
    def __init__(self, session: Session):
        self.session = session
        self.case_service = CaseService(session)
        self.evidence_service = EvidenceService(session)
        self.event_service = EventService(session)
        self.risk_service = RiskService(session)
        self.detection_repo = DetectionRepository(session)

    def generate_json_report(self, case_id: uuid.UUID) -> dict:
        """
        Generates a comprehensive JSON report for a case.
        """
        case = self.case_service.get_by_id(case_id)
        if not case:
            raise ValueError("Case not found")

        # Gather Evidence
        evidence_list = case.evidence

        # Gather Timeline
        events = self.event_service.list_by_case(case_id, limit=5000)

        # Gather Risk and Signals
        risk_response = self.risk_service.calculate_case_risk(case_id)

        # Gather Detections
        detections = self.detection_repo.list_detections_by_case(case_id)
        iocs = self.detection_repo.list_iocs_by_case(case_id)

        report = {
            "case": {
                "id": str(case.id),
                "title": case.title,
                "description": case.description,
                "status": case.status.value if hasattr(case.status, 'value') else case.status,
                "created_at": case.created_at.isoformat(),
            },
            "risk_assessment": {
                "risk_score": risk_response.risk_score,
                "risk_level": risk_response.risk_level,
                "explanation": risk_response.explanation,
                "signals_count": len(risk_response.contributing_signals),
            },
            "evidence": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "status": e.status.value if hasattr(e.status, 'value') else e.status,
                    "sha256": e.sha256,
                    "source": e.source,
                }
                for e in evidence_list
            ],
            "findings": {
                "detections": [
                    {
                        "id": str(d.id),
                        "type": d.detection_type,
                        "severity": d.severity,
                        "rule_id": d.rule_id,
                        "event_id": str(d.event_id),
                    }
                    for d in detections
                ],
                "iocs": [
                    {
                        "id": str(i.id),
                        "type": i.ioc_type,
                        "value": i.value,
                        "severity": i.severity,
                        "event_id": str(i.event_id),
                    }
                    for i in iocs
                ]
            },
            "timeline_summary": {
                "total_events": len(events),
                "events": [
                    {
                        "id": str(ev.id),
                        "timestamp": ev.timestamp.isoformat(),
                        "event_type": ev.event_type,
                        "source": ev.source,
                    }
                    for ev in events
                ]
            },
            "metadata": {
                "generated_by": "TRACE-X Phase 7 MVP",
            }
        }

        return report
