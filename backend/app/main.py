from fastapi import FastAPI

app = FastAPI(
    title="TRACE-X API",
    version="0.1.0",
    description="Digital forensics and cyber triage platform API",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}