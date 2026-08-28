from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router
from app.api.evidence import router as evidence_router
from app.api.events import router as events_router

from app.core.config import CORS_ALLOWED_ORIGINS
from app.domain.case.models import Case
from app.domain.evidence.models import Evidence
from app.domain.event.models import Event
from app.domain.detection.models import IOC, Detection, Incident


app = FastAPI(
    title="TRACE-X API",
    version="0.1.0",
    description="Digital forensics and cyber triage platform API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(cases_router)
app.include_router(evidence_router)
app.include_router(events_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
