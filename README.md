# RootsAndQi

AI-powered wellness insights combining Traditional Chinese Medicine (TCM) syndrome
differentiation with Caribbean herbal traditions, built on a production-style
FastAPI + LangChain + MLOps + Kubernetes stack.

> **Disclaimer:** This project is for educational and portfolio purposes. It does
> not provide medical diagnoses and is not a substitute for professional medical
> care.

## Status: Milestone 1 — AI Diagnostic Core

This milestone implements the syndrome-mapping pipeline:

- `POST /diagnose` — accepts symptom text and an optional structured tongue
  observation, sends it to Claude via LangChain with a TCM pattern-differentiation
  system prompt, and returns a structured `SyndromeClassification`.
- `GET /health` — basic health check.

Herb recommendations (TCM + Caribbean, via a Qdrant-backed retrieval layer) will be
added in Milestone 2.

## Project Structure

```
app/
├── main.py              # FastAPI app entrypoint
├── api/
│   └── diagnosis.py     # /diagnose endpoint
├── core/
│   ├── config.py        # Settings (env vars)
│   └── prompts.py        # TCM syndrome-mapping system prompt
├── models/
│   └── diagnosis.py      # Pydantic request/response/schema models
└── services/
    └── syndrome_mapper.py  # LangChain pipeline: LLM call -> structured output
```

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

3. Choose an LLM provider:

   **Option A — Ollama (free, runs locally)**

   - Install Ollama: https://ollama.com
   - Pull a model: `ollama pull llama3`
   - Leave `LLM_PROVIDER=ollama` in `.env` (this is the default)
   - Make sure Ollama is running before starting the API

   **Option B — Anthropic Claude (paid, cloud)**

   - Get an API key from https://console.anthropic.com
   - In `.env`, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your_key_here`

   The pipeline is provider-agnostic via LangChain — switching providers requires
   only an `.env` change, no code changes.

4. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```


4. Open the interactive docs at `http://localhost:8000/docs`.

## Example request

```bash
curl -X POST http://localhost:8000/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "symptoms": "I feel tired all the time, especially in the afternoon, and I bruise easily.",
    "tongue_observation": {
      "color": "pale",
      "coating": "thin white",
      "shape": "slightly swollen with tooth marks on the sides",
      "moisture": "normal"
    }
  }'
```

## Roadmap

- [x] Milestone 1: AI diagnostic core (FastAPI + LangChain syndrome mapping)
- [ ] Milestone 2: Caribbean + TCM herb knowledge base (Qdrant retrieval)
- [ ] Milestone 3: MLOps layer (MLflow, DVC, Airflow)
- [ ] Milestone 4: Minimal web UI
- [ ] Milestone 5: DevOps/infra wrap (Terraform, EKS, CI/CD, Trivy, Prometheus/Grafana)
- [ ] Milestone 6: Compliance docs + polish
