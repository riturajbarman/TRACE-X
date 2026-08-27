import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.domain.case.models import Case
from app.domain.event.models import Event
from app.domain.event.repository import EventRepository
from app.domain.event.schemas import EventCreate
from app.domain.evidence.models import Evidence


class EventService:
    def __init__(self, session: Session):
        self.session = session
        self.repository = EventRepository(session)

    def _validate_foreign_keys(self, case_id: uuid.UUID | None, evidence_id: uuid.UUID | None) -> None:
        if case_id is not None:
            case = self.session.get(Case, case_id)
            if not case:
                raise ValueError(f"Case {case_id} not found")

        if evidence_id is not None:
            evidence = self.session.get(Evidence, evidence_id)
            if not evidence:
                raise ValueError(f"Evidence {evidence_id} not found")

            if case_id is not None and evidence.case_id != case_id:
                raise ValueError(f"Evidence {evidence_id} does not belong to Case {case_id}")

    def ingest_events(self, event_creates: list[EventCreate]) -> list[Event]:
        # Perform validation for uniqueness of foreign keys to avoid repeated DB calls
        validated_case_ids: set[uuid.UUID] = set()
        validated_evidence_ids: set[uuid.UUID] = set()

        events_to_create = []
        for ec in event_creates:
            if ec.case_id and ec.case_id not in validated_case_ids:
                self._validate_foreign_keys(case_id=ec.case_id, evidence_id=None)
                validated_case_ids.add(ec.case_id)

            if ec.evidence_id and ec.evidence_id not in validated_evidence_ids:
                self._validate_foreign_keys(case_id=ec.case_id, evidence_id=ec.evidence_id)
                validated_evidence_ids.add(ec.evidence_id)

            if ec.artifact_id is None:
                raise ValueError("artifact_id is strictly required for provenance")

            event = Event(**ec.model_dump())
            events_to_create.append(event)

        self.repository.create_batch(events_to_create)
        self.session.commit()
        return events_to_create

    def list_by_case(self, case_id: uuid.UUID, skip: int = 0, limit: int = 100) -> Sequence[Event]:
        return self.repository.list_by_case(case_id, skip=skip, limit=limit)

    def list_by_evidence(self, evidence_id: uuid.UUID, skip: int = 0, limit: int = 100) -> Sequence[Event]:
        return self.repository.list_by_evidence(evidence_id, skip=skip, limit=limit)

    def list_by_artifact(self, artifact_id: uuid.UUID, skip: int = 0, limit: int = 100) -> Sequence[Event]:
        return self.repository.list_by_artifact(artifact_id, skip=skip, limit=limit)
