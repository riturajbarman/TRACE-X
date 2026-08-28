from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.case.models import CaseStatus
from app.domain.case.schemas import (
    CaseCreate,
    CaseResponse,
    CaseStatusUpdate,
    CaseSummaryResponse,
)
from app.domain.case.service import CaseService
from app.domain.detection.schemas import RiskResponse
from app.domain.detection.service import RiskService
from app.domain.evidence.schemas import EvidenceResponse
from app.domain.event.schemas import EventResponse
from app.domain.event.service import EventService


router = APIRouter(
    prefix="/cases",
    tags=["cases"],
)


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case(
    data: CaseCreate,
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    return service.create(
        title=data.title,
        description=data.description,
        created_by=data.created_by,
    )


@router.get(
    "",
    response_model=list[CaseResponse],
)
def list_cases(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    return service.list(
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
)
def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    case = service.get_by_id(case_id)

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return case


@router.get(
    "/{case_id}/evidence",
    response_model=list[EvidenceResponse],
)
def list_case_evidence(
    case_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    case = service.get_by_id(case_id)

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return service.list_evidence(
        case_id=case_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{case_id}/status",
    response_model=CaseResponse,
)
def update_case_status(
    case_id: UUID,
    data: CaseStatusUpdate,
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    case = service.update_status(
        case_id=case_id,
        new_status=data.status,
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return case


@router.get(
    "/{case_id}/summary",
    response_model=CaseSummaryResponse,
)
def get_case_summary(
    case_id: UUID,
    db: Session = Depends(get_db),
):
    service = CaseService(db)

    summary = service.get_summary(case_id)

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    return summary


@router.get(
    "/{case_id}/timeline",
    response_model=list[EventResponse],
)
def get_case_timeline(
    case_id: UUID,
    event_type: str | None = Query(default=None),
    source: str | None = Query(None, description="Filter by event source"),
    start_time: datetime | None = Query(None, description="Start time"),
    end_time: datetime | None = Query(None, description="End time"),
    severity: str | None = Query(None, description="Filter by finding severity"),
    incident_id: UUID | None = Query(None, description="Filter by incident ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get the chronological timeline of events for a case.
    """
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    service = EventService(db)
    return service.list_by_case(
        case_id,
        skip=skip,
        limit=limit,
        event_type=event_type,
        source=source,
        start_time=start_time,
        end_time=end_time,
        severity=severity,
        incident_id=incident_id,
    )


@router.get(
    "/{case_id}/risk",
    response_model=RiskResponse,
    summary="Get case risk score",
)
def get_case_risk(
    case_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Calculate and return the deterministic risk score for a case based on findings.
    """
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    service = RiskService(db)
    return service.calculate_case_risk(case_id)

@router.get(
    "/{case_id}/report",
    summary="Get case report",
)
def get_case_report(
    case_id: UUID,
    format: str = Query("json", description="Format of the report (only json supported currently)"),
    db: Session = Depends(get_db),
):
    """
    Download a comprehensive report for the case.
    """
    from app.domain.report.service import ReportService
    service = ReportService(db)

    try:
        report = service.generate_json_report(case_id)
        if format.lower() != "json":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JSON format is currently supported",
            )
        return report
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
