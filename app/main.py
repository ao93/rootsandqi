from fastapi import FastAPI

from app.api.diagnosis import router as diagnosis_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered wellness insights combining Traditional Chinese Medicine "
        "(TCM) syndrome differentiation with Indigenous herbal traditions from "
        "around the world."
    ),
    version="0.1.0",
)

app.include_router(diagnosis_router, tags=["diagnosis"])


@app.get("/health")
def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok", "service": settings.app_name}
