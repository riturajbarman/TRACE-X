"""
Correlation Service — Phase 8

Orchestrates DB reads, runs the CorrelationEngine, persists results as
Incidents, and returns structured CorrelationGroup output.
"""
from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.correlation.engine import CorrelationEngine, CorrelationGroup
from app.domain.detection.models import Detection, IOC, Incident
from app.domain.detection.repository import DetectionRepository
from app.domain.event.models import Event


class CorrelationService:
    """
    Runs deterministic correlation for a case and persists the results
    as Incident records.

    Safe to call multiple times — existing Incidents for the case are
    deleted first and regenerated, ensuring idempotency.
    """

    def __init__(
        self,
        session: Session,
        time_window: timedelta = timedelta(minutes=5),
    ) -> None:
        self.session = session
        self.det_repo = DetectionRepository(session)
        self.engine = CorrelationEngine(time_window=time_window)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def correlate_case(self, case_id: uuid.UUID) -> list[CorrelationGroup]:
        """
        Correlate all events for a case, persist Incidents, return groups.

        This is idempotent: re-running produces the same result from the
        same underlying events and detections.
        """
        events = self._load_events(case_id)
        detections = list(self.det_repo.list_detections_by_case(case_id))

        groups = self.engine.correlate(events, detections)

        # Wipe existing auto-generated correlation incidents and regenerate.
        self._delete_auto_incidents(case_id)
        for group in groups:
            self._persist_incident(case_id, group)

        self.session.commit()
        return groups

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_events(self, case_id: uuid.UUID) -> list[Event]:
        stmt = select(Event).where(Event.case_id == case_id).order_by(
            Event.timestamp.asc(), Event.id.asc()
        )
        return list(self.session.execute(stmt).scalars().all())

    def _delete_auto_incidents(self, case_id: uuid.UUID) -> None:
        """Remove all auto-generated correlation Incidents for this case."""
        stmt = select(Incident).where(
            Incident.case_id == case_id,
            Incident.status == "AUTO_CORRELATED",
        )
        for inc in self.session.execute(stmt).scalars().all():
            self.session.delete(inc)
        self.session.flush()

    def _persist_incident(
        self,
        case_id: uuid.UUID,
        group: CorrelationGroup,
    ) -> Incident:
        incident = Incident(
            id=group.group_id,
            case_id=case_id,
            title=group.title,
            severity=group.severity,
            confidence=group.confidence,
            status="AUTO_CORRELATED",
        )
        # Attach events and detections via the existing M2M tables.
        incident.events = group.events
        incident.detections = group.detections
        self.session.add(incident)
        self.session.flush()
        return incident
