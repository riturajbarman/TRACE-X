from fastapi import FastAPI

from app.api.cases import router as cases_router
from app.api.evidence import router as evidence_router

from app.domain.case.models import Case
from app.domain.evidence.models import Evidence


app = FastAPI(
    title="TRACE-X API",
    version="0.1.0",
    description="Digital forensics and cyber triage platform API",
)

app.include_router(cases_router)
app.include_router(evidence_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
