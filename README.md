# RootsAndQi

AI-powered wellness insights combining Traditional Chinese Medicine (TCM) syndrome
differentiation with Indigenous herbal traditions from around the world, built on a production-style
FastAPI + LangChain + MLOps + Kubernetes stack.

> **Disclaimer:** This project is for educational and portfolio purposes. It does
> not provide medical diagnoses and is not a substitute for professional medical
> care.

## Status: Milestone 2 — Herb Knowledge Base + Retrieval

Milestone 1 implemented the syndrome-mapping pipeline. Milestone 2 adds:

- A knowledge base of 15 TCM and Indigenous herbs (`app/data/herbs.json`), each
  tagged with the TCM syndrome patterns they're traditionally associated with.
- A Qdrant-backed vector retrieval layer: herb descriptions are embedded
  (via a local Ollama embedding model) and indexed into Qdrant.
- `POST /diagnose` now returns `herb_recommendations` alongside the syndrome
  classification — herbs are retrieved by vector similarity to the identified
  syndrome pattern(s), spanning both TCM and Indigenous traditions.
- `GET /health` — basic health check.

## Project Structure

```
app/
├── main.py              # FastAPI app entrypoint
├── api/
│   └── diagnosis.py     # /diagnose endpoint
├── core/
│   ├── config.py        # Settings (env vars)
│   └── prompts.py        # TCM syndrome-mapping system prompt
├── data/
│   └── herbs.json        # TCM + Indigenous herb knowledge base
├── models/
│   ├── diagnosis.py      # Pydantic request/response/schema models
│   └── herb.py           # Herb and HerbRecommendation models
└── services/
    ├── syndrome_mapper.py  # LangChain pipeline: LLM call -> structured output
    └── herb_retriever.py   # Qdrant indexing + vector retrieval for herbs

scripts/
└── index_herbs.py       # CLI script to (re)index herbs.json into Qdrant
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

4. Start Qdrant (vector database) via Docker:

   ```bash
   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

   Leave this running in its own terminal. Qdrant's dashboard is available at
   `http://localhost:6333/dashboard`.

5. Pull the embedding model (used to vectorize herb descriptions):

   ```bash
   ollama pull nomic-embed-text
   ```

6. Index the herb knowledge base into Qdrant:

   ```bash
   python -m scripts.index_herbs
   ```

   This embeds all 15 herbs from `app/data/herbs.json` and loads them into a
   Qdrant collection. Re-run this any time `herbs.json` is updated.

   > Note: run as a module (`python -m scripts.index_herbs`), not as a script
   > path (`python scripts/index_herbs.py`) — the latter won't resolve the
   > `app` package import. See [BUILD_LOG.md](BUILD_LOG.md) for details.

7. Run the API:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

   > Note: use `python -m uvicorn ...` rather than `uvicorn ...` directly —
   > see [BUILD_LOG.md](BUILD_LOG.md) for why.

8. Open the interactive docs at `http://localhost:8000/docs`.

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

The response now includes `herb_recommendations` — herbs retrieved by vector
similarity to the identified syndrome pattern(s), each with a `relevance_score`.

> **Known behavior:** retrieval currently ranks all 15 herbs together by
> similarity, without guaranteeing representation from both traditions. In
> testing, a `qi_deficiency` query returned only TCM herbs in the top 5, even
> though Indigenous herbs are tagged for that pattern too — likely because the
> embedding model finds TCM-originated terminology semantically closer to
> other TCM-described herbs. A planned improvement is retrieving top-N results
> *per tradition* and merging them, to guarantee both TCM and Indigenous herbs
> appear when relevant — directly supporting the project's core differentiator.

## Expanding the herb knowledge base

The herb knowledge base lives in `app/data/herbs.json` as a simple list of
entries. To add a new herb:

1. Add a new entry to `app/data/herbs.json` following the existing structure
   (`id`, `name`, `tradition`, `syndromes`, `description`, `preparation`,
   `cautions`). `syndromes` values must match the `TCMSyndrome` enum values
   defined in `app/models/diagnosis.py`.
2. Re-run the indexing script:

   ```bash
   python scripts/index_herbs.py
   ```

   This recreates the Qdrant collection with the updated herb set — no code
   changes required.

## Roadmap

- [x] Milestone 1: AI diagnostic core (FastAPI + LangChain syndrome mapping)
- [x] Milestone 2: Indigenous + TCM herb knowledge base (Qdrant retrieval)
- [ ] Milestone 3: MLOps layer (MLflow, DVC, Airflow)
- [ ] Milestone 4: Minimal web UI
- [ ] Milestone 5: DevOps/infra wrap (Terraform, EKS, CI/CD, Trivy, Prometheus/Grafana)
- [ ] Milestone 6: Compliance docs + polish

## Build Log

For a detailed account of environment setup issues encountered and how they
were debugged and resolved, see [BUILD_LOG.md](BUILD_LOG.md).
