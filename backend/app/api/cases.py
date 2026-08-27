from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.case.models import CaseStatus
from app.domain.case.schemas import (
    CaseCreate,
    CaseResponse,
    CaseStatusUpdate,
)
from app.domain.case.service import CaseService
from app.domain.evidence.schemas import EvidenceResponse


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
