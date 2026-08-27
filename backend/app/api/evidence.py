import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    Query,
    status,
)
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
    "/ingest",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_evidence(
    case_id: UUID = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    source: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)

    suffix = Path(file.filename or "").suffix

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=suffix,
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            total_size = 0
            from app.core.config import MAX_UPLOAD_SIZE_BYTES
            
            while chunk := file.file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE_BYTES:
                    temporary_file.close()
                    temporary_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Upload exceeds maximum allowed size",
                    )
                temporary_file.write(chunk)


        try:
            return service.ingest(
                case_id=case_id,
                name=name,
                source_path=temporary_path,
                description=description,
                source=source,
            )

        except ValueError as exc:
            if str(exc) == "Case not found":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Case not found",
                ) from exc

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

    finally:
        if "temporary_path" in locals():
            temporary_path.unlink(missing_ok=True)

        file.file.close()


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

    try:
        evidence = service.update_status(
            evidence_id=evidence_id,
            new_status=new_status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if evidence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence not found",
        )

    return evidence

@router.post(
    "/{evidence_id}/verify",
)
def verify_evidence_integrity(
    evidence_id: UUID,
    db: Session = Depends(get_db),
):
    service = EvidenceService(db)
    try:
        integrity_status = service.verify_integrity(evidence_id)
        return {"integrity_status": integrity_status}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )