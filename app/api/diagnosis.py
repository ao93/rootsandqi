from fastapi import APIRouter, HTTPException

from app.models.diagnosis import DiagnosisRequest, DiagnosisResponse
from app.services.herb_retriever import retrieve_herbs_for_syndrome
from app.services.syndrome_mapper import classify_syndrome

router = APIRouter()


@router.post("/diagnose", response_model=DiagnosisResponse)
def diagnose(request: DiagnosisRequest) -> DiagnosisResponse:
    """
    Accepts symptom text and an optional tongue observation, runs the
    syndrome-mapping pipeline, retrieves relevant TCM + Caribbean herbs
    from the Qdrant knowledge base based on the identified syndrome
    pattern(s), and returns a structured response with both.
    """
    try:
        classification = classify_syndrome(request)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        herb_recommendations = retrieve_herbs_for_syndrome(
            primary_pattern=classification.primary_pattern.value,
            secondary_patterns=[p.value for p in classification.secondary_patterns],
        )
    except Exception:
        # Retrieval failure shouldn't block returning the syndrome
        # classification itself - degrade gracefully with no recommendations.
        herb_recommendations = []

    return DiagnosisResponse(
        classification=classification,
        herb_recommendations=herb_recommendations,
    )
