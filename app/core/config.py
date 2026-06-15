from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings, loaded from environment variables / .env file.

    Supports two LLM providers:
    - "anthropic": Claude via the Anthropic API (requires ANTHROPIC_API_KEY, paid)
    - "ollama": local open-source models via Ollama (free, runs on your machine)
    """
    llm_provider: str = "ollama"  # "anthropic" or "ollama"

    # Anthropic settings (only required if llm_provider == "anthropic")
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Ollama settings (only used if llm_provider == "ollama")
    ollama_model: str = "llama3"
    ollama_base_url: str = "http://localhost:11434"

    # Embedding model (via Ollama, free/local)
    embedding_model: str = "nomic-embed-text"

    # Qdrant settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "herbs"

    app_name: str = "RootsAndQi"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
