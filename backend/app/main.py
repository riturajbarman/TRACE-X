from fastapi import FastAPI

from app.api.evidence import router as evidence_router


app = FastAPI(
    title="TRACE-X API",
    version="0.1.0",
    description="Digital forensics and cyber triage platform API",
)

app.include_router(evidence_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}