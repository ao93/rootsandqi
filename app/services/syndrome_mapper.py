import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.prompts import SYNDROME_MAPPING_SYSTEM_PROMPT
from app.models.diagnosis import DiagnosisRequest, SyndromeClassification


def _get_llm():
    """
    Return a LangChain chat model based on the configured provider.

    - "anthropic": Claude via the Anthropic API (paid, requires API key)
    - "ollama": local open-source model via Ollama (free, runs on your machine)
    """
    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0,
        )

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    raise ValueError(
        f"Unknown llm_provider '{settings.llm_provider}'. "
        "Expected 'anthropic' or 'ollama'."
    )


def _build_user_message(request: DiagnosisRequest) -> str:
    """
    Build the user-facing prompt content from the diagnosis request.
    """
    parts = [f"Symptoms: {request.symptoms}"]

    if request.tongue_observation:
        obs = request.tongue_observation
        parts.append(
            "Tongue observation:\n"
            f"- Color: {obs.color}\n"
            f"- Coating: {obs.coating}\n"
            f"- Shape: {obs.shape}\n"
            f"- Moisture: {obs.moisture}"
        )
        if obs.notes:
            parts.append(f"- Additional notes: {obs.notes}")

    return "\n\n".join(parts)


def classify_syndrome(request: DiagnosisRequest) -> SyndromeClassification:
    """
    Run the syndrome-mapping pipeline: send symptoms (and optional tongue
    observation) to the LLM and parse the structured JSON response into
    a SyndromeClassification object.
    """
    llm = _get_llm()

    messages = [
        SystemMessage(content=SYNDROME_MAPPING_SYSTEM_PROMPT),
        HumanMessage(content=_build_user_message(request)),
    ]

    response = llm.invoke(messages)

    raw_content = response.content.strip()

    # Defensive cleanup in case the model wraps output in code fences
    if raw_content.startswith("```"):
        raw_content = raw_content.strip("`")
        if raw_content.startswith("json"):
            raw_content = raw_content[4:].strip()

    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse LLM response as JSON: {raw_content!r}"
        ) from exc

    return SyndromeClassification(**data)
