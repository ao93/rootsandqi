# RootsAndQi

AI-powered wellness insights combining Traditional Chinese Medicine (TCM) syndrome
differentiation with Indigenous herbal traditions from around the world, built on a
production-style FastAPI + LangChain + MLOps stack with a React frontend.

> **Disclaimer:** This project is for educational and portfolio purposes. It does
> not provide medical diagnoses and is not a substitute for professional medical
> care.

## Status: Milestone 4 — Minimal Web UI

Milestones 1–3 implemented the syndrome-mapping pipeline, herb retrieval, and MLOps
tooling. Milestone 4 adds a React frontend that brings the full pipeline into the browser.

- **React + Vite frontend** (`frontend/`): symptom input form with optional tongue
  observation fields (color, coating, shape, moisture) via a collapsible toggle, and a
  results view with animated fade-in
- **Two-tradition visual design**: herb results are split into two columns — terracotta
  left border for TCM herbs, gold left border for Indigenous/Shared herbs — making the
  project's core differentiator (bridging two traditions) immediately legible
- **Vite dev proxy**: `/diagnose` calls are proxied to `http://localhost:8000`, so the
  frontend talks to FastAPI with no CORS configuration needed during development
- **Design language**: dark forest green (`#1A2E1A`) background, warm cream text,
  Playfair Display serif for display/hero, Inter for body — a health-tech aesthetic
  distinct from generic dev project templates

MLOps tooling from Milestone 3 remains active:

- **Experiment tracking (MLflow)**: every `POST /diagnose` call is logged as an MLflow
  run, capturing params (LLM provider/model, prompt version), metrics (confidence,
  herb relevance scores), and tags (syndrome pattern, herb traditions returned)
- **Dataset versioning (DVC)**: `app/data/herbs.json` is tracked with DVC using a
  Google Drive remote — see
  [Expanding the herb knowledge base](#expanding-the-herb-knowledge-base-with-dvc-versioning)
- **Orchestration (Airflow)**: a DAG (`reindex_herb_knowledge_base`) runs daily (or on
  manual trigger) with two tasks:
  1. `validate_herbs_data` — validates `herbs.json` schema, syndrome enum values, and
     duplicate IDs
  2. `index_herbs` — re-indexes into Qdrant, only if validation passed

  A bad edit to `herbs.json` fails at validation and Qdrant keeps its last-known-good
  index — see [Running Airflow](#running-airflow)

## Project Structure

```
app/
├── main.py                   # FastAPI app entrypoint
├── api/
│   └── diagnosis.py          # /diagnose endpoint
├── core/
│   ├── config.py             # Settings (env vars)
│   └── prompts.py            # TCM syndrome-mapping system prompt
├── data/
│   └── herbs.json            # TCM + Indigenous herb knowledge base (DVC-tracked)
├── models/
│   ├── diagnosis.py          # Pydantic request/response/schema models
│   └── herb.py               # Herb and HerbRecommendation models
└── services/
    ├── syndrome_mapper.py    # LangChain pipeline: LLM call -> structured output
    ├── herb_retriever.py     # Qdrant indexing + vector retrieval for herbs
    └── experiment_tracker.py # MLflow run logging for /diagnose calls

scripts/
└── index_herbs.py            # CLI script to (re)index herbs.json into Qdrant

airflow/
├── docker-compose.yaml       # Airflow 2.10 (LocalExecutor) via docker-compose
├── .env.example              # AIRFLOW_UID setup
└── dags/
    └── reindex_herbs_dag.py  # validate_herbs_data -> index_herbs DAG

frontend/
├── index.html                # HTML entry point
├── package.json              # Node dependencies (React, Vite)
├── vite.config.js            # Vite config with /diagnose proxy
└── src/
    ├── main.jsx              # React entry point
    ├── App.jsx               # Main app component (form + results)
    ├── App.module.css        # Component styles (CSS Modules)
    └── index.css             # Global styles + CSS design tokens
```

## Setup

### Backend

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
   - Leave `LLM_PROVIDER=ollama` in `.env` (default)
   - Make sure Ollama is running before starting the API

   **Option B — Anthropic Claude (paid, cloud)**

   - Get an API key from https://console.anthropic.com
   - In `.env`, set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=your_key_here`

   The pipeline is provider-agnostic via LangChain — switching providers requires only
   an `.env` change, no code changes.

4. Start Qdrant (vector database) via Docker:

   ```bash
   docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
   ```

   Leave this running in its own terminal. Qdrant's dashboard is at
   `http://localhost:6333/dashboard`.

5. Pull the embedding model:

   ```bash
   ollama pull nomic-embed-text
   ```

6. Index the herb knowledge base into Qdrant:

   ```bash
   python -m scripts.index_herbs
   ```

   > Note: use `python -m scripts.index_herbs`, not `python scripts/index_herbs.py` —
   > the latter won't resolve the `app` package import.

7. Run the API:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

   > Note: use `python -m uvicorn ...` not `uvicorn ...` directly — see
   > [BUILD_LOG.md](BUILD_LOG.md) for why.

8. Open the interactive API docs at `http://localhost:8000/docs`.

9. (Optional) View MLflow experiment runs:

   ```bash
   mlflow ui --backend-store-uri ./mlruns
   ```

   Then open `http://localhost:5000` to browse each `/diagnose` call as an MLflow run.

### Frontend

1. Install Node dependencies (requires Node 18+):

   ```bash
   cd frontend
   npm install
   ```

2. Start the dev server (with the backend already running on port 8000):

   ```bash
   npm run dev
   ```

3. Open `http://localhost:5173` — the React UI proxies `/diagnose` calls to the
   FastAPI backend automatically.

## Running Airflow

Airflow runs the `reindex_herb_knowledge_base` DAG, which validates `app/data/herbs.json`
and re-indexes it into Qdrant. It uses Airflow 2.10 via docker-compose, separate from
the FastAPI app.

**Prerequisites**: Docker Desktop, Qdrant, and Ollama must be running on your host
machine — Airflow containers connect to them via `host.docker.internal`.

1. Set your `AIRFLOW_UID`:

   ```bash
   cd airflow
   echo "AIRFLOW_UID=$(id -u)" > .env
   ```

2. Initialize the metadata database (one-time):

   ```bash
   docker compose up airflow-init
   ```

3. Start Airflow:

   ```bash
   docker compose up -d
   ```

4. Open the Airflow UI at `http://localhost:8081` — login: `airflow` / `airflow`.

5. Find `reindex_herb_knowledge_base`, toggle it on, trigger a manual run via ▶.
   Both tasks should turn green within ~30 seconds.

6. To stop:

   ```bash
   docker compose down
   ```

> **Note on Airflow version**: this project uses Airflow 2.10.4. Airflow 3.0 was
> initially attempted but required undocumented configuration for LocalExecutor +
> docker-compose task execution. Full debugging history in [BUILD_LOG.md](BUILD_LOG.md)
> issues 12–17.

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

The response includes `classification` (primary pattern, secondary patterns, affected
organs, confidence, reasoning) and `herb_recommendations` (herbs retrieved by vector
similarity to the syndrome, each with a `relevance_score`).

> **Known behavior:** retrieval currently ranks all 15 herbs together by similarity,
> without guaranteeing representation from both traditions. TCM-named syndromes tend
> to rank TCM herbs higher — a planned improvement is top-N retrieval *per tradition*,
> merged, to guarantee both traditions appear.

## Expanding the herb knowledge base (with DVC versioning)

The herb knowledge base lives in `app/data/herbs.json` and is version-controlled
with [DVC](https://dvc.org), with a Google Drive remote.

### Adding or updating herbs

1. Edit `app/data/herbs.json` following the existing structure (`id`, `name`,
   `tradition`, `syndromes`, `description`, `preparation`, `cautions`). `syndromes`
   values must match the `TCMSyndrome` enum in `app/models/diagnosis.py`.

2. Re-run indexing:

   ```bash
   python -m scripts.index_herbs
   ```

3. Track and push the new version:

   ```bash
   dvc add app/data/herbs.json
   dvc push
   git add app/data/herbs.json.dvc
   git commit -m "Update herb knowledge base: add <herb name>"
   git push
   ```

### Retrieving a previous version

```bash
git checkout <previous-commit> -- app/data/herbs.json.dvc
dvc pull
python -m scripts.index_herbs
```

## Starting everything for development

```bash
# Tab 1 — Qdrant
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Tab 2 — Index herbs (after Qdrant starts)
cd ~/rootsandqi && source .venv/bin/activate && python -m scripts.index_herbs

# Tab 3 — FastAPI backend
python -m uvicorn app.main:app --reload

# Tab 4 — React frontend
cd frontend && npm run dev
```

Optional — Airflow:
```bash
cd airflow && docker compose up -d
```

## Roadmap

- [x] Milestone 1: AI diagnostic core (FastAPI + LangChain syndrome mapping)
- [x] Milestone 2: Indigenous + TCM herb knowledge base (Qdrant retrieval)
- [x] Milestone 3: MLOps layer
  - [x] MLflow experiment tracking for /diagnose runs
  - [x] DVC dataset versioning for herbs.json (Google Drive remote)
  - [x] Airflow scheduled re-indexing (validate -> index DAG)
- [x] Milestone 4: Minimal web UI (React + Vite, two-tradition herb results layout)
- [ ] Milestone 5: DevOps/infra wrap (Terraform, EKS, CI/CD, Trivy, Prometheus/Grafana)
- [ ] Milestone 6: Compliance docs + polish

## Build Log

For a detailed account of environment setup issues encountered and how they were debugged
and resolved (18 issues across Milestones 1–4, including Python 3.14 compat, DVC OAuth,
Airflow 3.0 → 2.10 migration, and node_modules gitignore), see [BUILD_LOG.md](BUILD_LOG.md).
