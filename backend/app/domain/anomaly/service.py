import uuid
import numpy as np
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.domain.event.repository import EventRepository
from app.domain.detection.models import Detection
from app.domain.anomaly.features import extract_features
from app.domain.anomaly.model import AnomalyModel
from app.domain.anomaly.schemas import AnomalyScanResponse, AnomalyFinding
import json

class AnomalyService:
    def __init__(self, db: Session):
        self.db = db
        self.event_repo = EventRepository(db)
        self.model = AnomalyModel()
        
    def _load_baseline(self):
        """
        Load synthetic training fixture to fit the baseline.
        In a production scenario, this might pull historical events for the host/user.
        """
        try:
            with open("tests/fixtures/anomaly/normal_events.json", "r") as f:
                raw_events = json.load(f)
                
            from app.domain.event.models import Event
            # Convert basic dicts to mock Event objects for feature extraction
            training_events = []
            for d in raw_events:
                e = Event()
                e.id = uuid.UUID(d["id"])
                e.event_type = d.get("event_type", "generic")
                e.source = d.get("source", "test")
                e.timestamp = datetime.fromisoformat(d["timestamp"]) if "timestamp" in d else datetime.now(timezone.utc)
                e.data = d.get("data", {})
                training_events.append(e)
                
            if training_events:
                X_train = np.array([extract_features(e) for e in training_events])
                self.model.fit(X_train)
        except Exception as e:
            print(f"Warning: Could not load baseline data: {e}")
            # Fallback to fitting on the current case data if baseline fails
            pass
            
    def scan_case(self, case_id: uuid.UUID) -> AnomalyScanResponse:
        """
        Run anomaly detection on all events in a case.
        Persist findings as Detection rows.
        """
        events = self.event_repo.list_by_case(case_id, limit=100000)
        if not events:
            return AnomalyScanResponse(
                case_id=case_id,
                model_version=self.model.VERSION,
                anomaly_count=0,
                findings=[]
            )
            
        self._load_baseline()
        
        # If baseline loading failed, fit on the current dataset
        X = np.array([extract_features(e) for e in events])
        if not self.model.is_fitted:
            self.model.fit(X)
            
        is_anomaly, scores = self.model.predict(X)
        
        findings = []
        
        # Clear previous anomaly detections for this case to be idempotent
        self.db.query(Detection).filter(
            Detection.case_id == case_id,
            Detection.detection_type == "anomaly"
        ).delete()
        
        for i, (is_anom, score) in enumerate(zip(is_anomaly, scores)):
            if is_anom:
                evt = events[i]
                feature_vec = X[i]
                explanation = self.model.explain(feature_vec)
                
                # Severity based on score
                severity = "HIGH" if score > 75 else "MEDIUM"
                if score > 90:
                    severity = "CRITICAL"
                    
                det = Detection(
                    id=uuid.uuid4(),
                    case_id=case_id,
                    event_id=evt.id,
                    detection_type="anomaly",
                    rule_id=f"ML-IFOREST",
                    rule_version=self.model.VERSION,
                    severity=severity,
                    confidence=int(score),  # Map score 0-100 to confidence
                )
                self.db.add(det)
                
                findings.append(AnomalyFinding(
                    event_id=evt.id,
                    score=float(score),
                    explanation=explanation
                ))
                
        self.db.commit()
        
        return AnomalyScanResponse(
            case_id=case_id,
            model_version=self.model.VERSION,
            anomaly_count=len(findings),
            findings=findings
        )
