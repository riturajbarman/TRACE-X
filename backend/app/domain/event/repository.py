import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.event.models import Event


class EventRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, event: Event) -> Event:
        self.session.add(event)
        self.session.flush()
        return event

    def create_batch(self, events: list[Event]) -> None:
        if not events:
            return
        self.session.add_all(events)
        self.session.flush()

    def get_by_id(self, event_id: uuid.UUID) -> Event | None:
        stmt = select(Event).where(Event.id == event_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_evidence(self, evidence_id: uuid.UUID, skip: int = 0, limit: int = 100) -> Sequence[Event]:
        stmt = (
            select(Event)
            .where(Event.evidence_id == evidence_id)
            .order_by(Event.timestamp.asc(), Event.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()

    def list_by_case(
        self,
        case_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        event_type: str | None = None,
        source: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> Sequence[Event]:
        stmt = select(Event).where(Event.case_id == case_id)

        if event_type:
            stmt = stmt.where(Event.event_type == event_type)
        if source:
            stmt = stmt.where(Event.source == source)
        if start_time:
            stmt = stmt.where(Event.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(Event.timestamp <= end_time)

        stmt = stmt.order_by(Event.timestamp.asc(), Event.id.asc()).offset(skip).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def list_by_artifact(self, artifact_id: uuid.UUID, skip: int = 0, limit: int = 100) -> Sequence[Event]:
        stmt = (
            select(Event)
            .where(Event.artifact_id == artifact_id)
            .order_by(Event.timestamp.asc(), Event.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return self.session.execute(stmt).scalars().all()
