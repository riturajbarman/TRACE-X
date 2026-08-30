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
from app.domain.correlation.schemas import CorrelationGroupResponse, CorrelationResponse
from app.domain.correlation.service import CorrelationService
from app.domain.detection.schemas import RiskResponse
from app.domain.detection.service import RiskService
from app.domain.evidence.schemas import EvidenceResponse
from app.domain.event.schemas import EventResponse
from app.domain.event.service import EventService
from app.domain.event.service import EventService
from app.domain.anomaly.schemas import AnomalyScanResponse
from app.domain.anomaly.service import AnomalyService
from app.domain.graph.schemas import GraphResponse
from app.domain.graph.service import GraphService
from app.core import config
from app.domain.assistant.provider import AnthropicProvider, AssistantProvider, UnconfiguredProvider
from app.domain.assistant.schemas import AssistantQueryRequest, AssistantQueryResponse
from app.domain.assistant.service import AssistantService


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


@router.post(
    "/{case_id}/correlate",
    response_model=CorrelationResponse,
    summary="Run correlation engine for a case",
)
def correlate_case(
    case_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Run the Phase 8 deterministic correlation engine against all events
    in the case.

    Returns correlation groups — each group contains related events and
    the explanation (reason) for the relationship.  Results are persisted
    as Incidents in the database and are idempotent: re-running replaces
    any previous AUTO_CORRELATED Incidents.
    """
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    service = CorrelationService(db)
    groups = service.correlate_case(case_id)

    group_responses = [
        CorrelationGroupResponse(
            group_id=g.group_id,
            title=g.title,
            reason=g.reason,
            severity=g.severity,
            confidence=g.confidence,
            event_count=len(g.events),
            detection_count=len(g.detections),
            events=g.events,
            detections=g.detections,
        )
        for g in groups
    ]

    return CorrelationResponse(
        case_id=case_id,
        group_count=len(group_responses),
        groups=group_responses,
    )

@router.post(
    "/{case_id}/anomaly-scan",
    response_model=AnomalyScanResponse,
    summary="Run Phase 9 anomaly detection on all events in the case"
)
def run_anomaly_scan(case_id: UUID, db: Session = Depends(get_db)):
    """Run Phase 9 anomaly detection on all events in the case."""
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    service = AnomalyService(db)
    return service.scan_case(case_id)

@router.get(
    "/{case_id}/graph",
    response_model=GraphResponse,
    summary="Get Phase 10 investigation graph for the case"
)
def get_case_graph(
    case_id: UUID,
    node_types: list[str] | None = Query(None, description="Filter nodes by type (e.g., event, detection, incident, ioc)"),
    include_shared_entities: bool = Query(True, description="Whether to compute and include JSONB shared-entity edges"),
    db: Session = Depends(get_db)
):
    """Return the investigation graph representing related entities and events."""
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )
    
    graph_service = GraphService(db)
    return graph_service.build_graph(
        case_id=case_id,
        node_types=node_types,
        include_shared_entities=include_shared_entities,
    )


def get_assistant_provider() -> AssistantProvider:
    """Build the Phase 11 assistant provider from configuration.

    Returns an UnconfiguredProvider (fails gracefully with
    grounding_status "unavailable") when no ANTHROPIC_API_KEY is set,
    rather than raising during app startup or on first use.
    """
    if not config.ASSISTANT_API_KEY:
        return UnconfiguredProvider()
    return AnthropicProvider(
        api_key=config.ASSISTANT_API_KEY,
        model=config.ASSISTANT_MODEL,
        timeout_seconds=config.ASSISTANT_PROVIDER_TIMEOUT_SECONDS,
    )


@router.post(
    "/{case_id}/assistant/query",
    response_model=AssistantQueryResponse,
    summary="Ask the Phase 11 AI Investigation Assistant a question about this case",
)
def query_case_assistant(
    case_id: UUID,
    data: AssistantQueryRequest,
    db: Session = Depends(get_db),
    provider: AssistantProvider = Depends(get_assistant_provider),
):
    """
    Evidence-grounded, analyst-facing AI assistant over this case's
    already-processed data. It is NOT a forensic authority: every claim in
    the response is labeled observed / inference / recommendation, and
    grounding is validated server-side before being returned — an
    "observed" claim always carries verified TRACE-X object references.

    Read-only with respect to all forensic data: the only write this
    endpoint performs is an AI_QUERY_EXECUTED audit-log entry. It never
    modifies events, detections, IOCs, risk, timeline, or graph data, and
    it never runs the correlation or anomaly-scan engines.

    KNOWN LIMITATION: this endpoint is not authenticated — TRACE-X has no
    authentication/authorization layer yet (see STATUS.md). It can incur
    provider API cost and expose case-scoped data to whichever provider is
    configured. Do not expose this deployment publicly without adding
    authentication first.
    """
    case_service = CaseService(db)
    if case_service.get_by_id(case_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    service = AssistantService(db, provider)
    return service.query(case_id=case_id, question=data.question)
