from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.domain.evidence.models import EvidenceStatus
from app.domain.evidence.schemas import EvidenceCreate, EvidenceResponse
from app.domain.evidence.service import EvidenceService

router = APIRouter(
    prefix="/evidence",
    tags=["evidence"],
)


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    data: EvidenceCreate,
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)

    try:
        return service.create(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[EvidenceResponse],
)
def list_evidence(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)

    return service.list(
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{evidence_id}",
    response_model=EvidenceResponse,
)
def get_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)

    evidence = service.get_by_id(evidence_id)

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return evidence


@router.patch(
    "/{evidence_id}/status",
    response_model=EvidenceResponse,
)
def update_evidence_status(
    evidence_id: UUID,
    new_status: EvidenceStatus,
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)

    evidence = service.update_status(
        evidence_id=evidence_id,
        new_status=new_status,
    )

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return evidence
