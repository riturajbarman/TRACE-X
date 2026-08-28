import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.detection.models import IOC, Detection, Incident


class DetectionRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_detections_by_case(self, case_id: uuid.UUID) -> Sequence[Detection]:
        stmt = select(Detection).where(Detection.case_id == case_id).order_by(Detection.created_at.asc())
        result = self.session.execute(stmt)
        return result.scalars().all()

    def list_iocs_by_case(self, case_id: uuid.UUID) -> Sequence[IOC]:
        stmt = select(IOC).where(IOC.case_id == case_id).order_by(IOC.created_at.asc())
        result = self.session.execute(stmt)
        return result.scalars().all()

    def create_detection(self, detection: Detection) -> Detection:
        self.session.add(detection)
        self.session.flush()
        return detection

    def create_ioc(self, ioc: IOC) -> IOC:
        self.session.add(ioc)
        self.session.flush()
        return ioc
