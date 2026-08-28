import uuid

from sqlalchemy.orm import Session

from app.domain.detection.repository import DetectionRepository
from app.domain.detection.schemas import RiskResponse, RiskSignal


class RiskService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = DetectionRepository(session)

    def calculate_case_risk(self, case_id: uuid.UUID) -> RiskResponse:
        detections = self.repository.list_detections_by_case(case_id)
        iocs = self.repository.list_iocs_by_case(case_id)

        signals = []
        total_score = 0

        # Simple deterministic scoring for Detections
        for d in detections:
            score = self._get_severity_weight(d.severity)
            signals.append(
                RiskSignal(
                    source="Rule Detection",
                    description=f"Rule {d.rule_id} triggered ({d.severity})",
                    score=score,
                    detection_id=d.id,
                )
            )
            total_score += score

        # Simple deterministic scoring for IOCs
        for ioc in iocs:
            score = self._get_severity_weight(ioc.severity)
            signals.append(
                RiskSignal(
                    source="IOC Match",
                    description=f"{ioc.ioc_type} matched ({ioc.severity})",
                    score=score,
                    ioc_id=ioc.id,
                )
            )
            total_score += score

        # Cap at 100
        final_score = min(total_score, 100)

        # Map to Risk Level
        if final_score == 0:
            risk_level = "NONE"
            explanation = "No suspicious findings detected."
        elif final_score < 30:
            risk_level = "LOW"
            explanation = "Minor findings detected. Investigation may be warranted."
        elif final_score < 60:
            risk_level = "MEDIUM"
            explanation = "Suspicious findings detected. Investigation recommended."
        elif final_score < 90:
            risk_level = "HIGH"
            explanation = "High severity findings detected. Immediate investigation required."
        else:
            risk_level = "CRITICAL"
            explanation = "Critical severity findings detected. Immediate response required."

        return RiskResponse(
            case_id=case_id,
            risk_score=final_score,
            risk_level=risk_level,
            contributing_signals=signals,
            explanation=explanation,
        )

    def _get_severity_weight(self, severity: str) -> int:
        mapping = {
            "CRITICAL": 25,
            "HIGH": 20,
            "MEDIUM": 10,
            "LOW": 5,
        }
        return mapping.get(severity.upper(), 0)
