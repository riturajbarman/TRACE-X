from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.event.schemas import EventResponse
from app.domain.event.service import EventService


router = APIRouter(
    prefix="/events",
    tags=["events"],
)


@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
):
    service = EventService(db)

    event = service.get_by_id(event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.get(
    "/evidence/{evidence_id}",
    response_model=list[EventResponse],
)
def list_events_by_evidence(
    evidence_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = EventService(db)

    return service.list_by_evidence(
        evidence_id=evidence_id,
        skip=offset,
        limit=limit,
    )


@router.get(
    "/case/{case_id}",
    response_model=list[EventResponse],
)
def list_events_by_case(
    case_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = EventService(db)

    return service.list_by_case(
        case_id=case_id,
        skip=offset,
        limit=limit,
    )


@router.get(
    "/artifact/{artifact_id}",
    response_model=list[EventResponse],
)
def list_events_by_artifact(
    artifact_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = EventService(db)

    return service.list_by_artifact(
        artifact_id=artifact_id,
        skip=offset,
        limit=limit,
    )
