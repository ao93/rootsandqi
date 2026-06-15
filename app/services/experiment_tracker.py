import mlflow

from app.core.config import settings
from app.models.diagnosis import DiagnosisRequest, SyndromeClassification
from app.models.herb import HerbRecommendation

_experiment_initialized = False


def _ensure_experiment() -> None:
    """
    Configure MLflow's tracking URI and experiment, once per process.

    Supports two modes via settings.mlflow_tracking_uri:
    - A local path (e.g. "./mlruns") - file-based tracking, no server needed
    - An http(s) URL (e.g. "http://localhost:5000") - logs to an MLflow
      tracking server (run via Docker for a shared UI)
    """
    global _experiment_initialized
    if _experiment_initialized:
        return

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)
    _experiment_initialized = True


def log_diagnosis_run(
    request: DiagnosisRequest,
    classification: SyndromeClassification,
    herb_recommendations: list[HerbRecommendation],
) -> None:
    """
    Log a single /diagnose call as an MLflow run.

    Logs:
    - Params: LLM provider/model, prompt version, whether a tongue
      observation was provided
    - Metrics: confidence score, number of secondary patterns, number of
      herb recommendations returned, top herb relevance score
    - Tags: primary syndrome pattern, top herb tradition (for filtering,
      e.g. "show me runs where Indigenous herbs didn't appear")

    Failures here are logged but never raised - tracking issues should
    never break the /diagnose response.
    """
    try:
        _ensure_experiment()

        with mlflow.start_run():
            # Params: configuration / inputs for this run
            mlflow.log_param("llm_provider", settings.llm_provider)
            mlflow.log_param(
                "llm_model",
                settings.anthropic_model
                if settings.llm_provider == "anthropic"
                else settings.ollama_model,
            )
            mlflow.log_param("prompt_version", settings.syndrome_prompt_version)
            mlflow.log_param(
                "has_tongue_observation", request.tongue_observation is not None
            )
            mlflow.log_param("symptoms_length", len(request.symptoms))

            # Metrics: numeric outputs from this run
            mlflow.log_metric("confidence", classification.confidence)
            mlflow.log_metric(
                "num_secondary_patterns", len(classification.secondary_patterns)
            )
            mlflow.log_metric(
                "num_herb_recommendations", len(herb_recommendations)
            )
            if herb_recommendations:
                mlflow.log_metric(
                    "top_herb_relevance_score",
                    herb_recommendations[0].relevance_score,
                )

            # Tags: categorical info useful for filtering/searching runs
            mlflow.set_tag("primary_pattern", classification.primary_pattern.value)
            mlflow.set_tag(
                "secondary_patterns",
                ",".join(p.value for p in classification.secondary_patterns),
            )
            if herb_recommendations:
                mlflow.set_tag(
                    "top_herb_id", herb_recommendations[0].herb.id
                )
                mlflow.set_tag(
                    "top_herb_tradition", herb_recommendations[0].herb.tradition
                )
                mlflow.set_tag(
                    "herb_traditions_returned",
                    ",".join(
                        sorted({rec.herb.tradition for rec in herb_recommendations})
                    ),
                )
            else:
                mlflow.set_tag("top_herb_id", "none")
                mlflow.set_tag("top_herb_tradition", "none")
                mlflow.set_tag("herb_traditions_returned", "none")

            # Reasoning text as an artifact-style param (truncated for safety)
            mlflow.log_param(
                "reasoning_preview", classification.reasoning[:250]
            )

    except Exception:
        # Tracking is best-effort - never let MLflow issues break /diagnose
        pass
