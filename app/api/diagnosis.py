from fastapi import APIRouter, HTTPException

from app.models.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.services.syndrome_mapper import classify_syndrome

router = APIRouter()


@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """
    Accepts symptom text and an optional tongue observation, runs the
    syndrome-mapping pipeline, and returns a structured TCM syndrome
    classification along with an educational disclaimer.

    Herb recommendations (TCM + Caribbean) will be appended here once
    the retrieval layer (Qdrant knowledge base) is implemented.
    """
    try:
        classification = classify_syndrome(request)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return DiagnosisResponse(classification=classification)
