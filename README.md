# RootsAndQi

AI-powered wellness insights combining Traditional Chinese Medicine (TCM) syndrome
differentiation with Indigenous herbal traditions from around the world, built on a production-style
FastAPI + LangChain + MLOps + Kubernetes stack.

> **Disclaimer:** This project is for educational and portfolio purposes. It does
> not provide medical diagnoses and is not a substitute for professional medical
> care.

## Status: Milestone 3 — MLOps: Experiment Tracking, Dataset Versioning, Orchestration

Milestones 1-2 implemented the syndrome-mapping pipeline and herb retrieval.
Milestone 3 adds MLOps tooling:

- **Experiment tracking (MLflow)**: every `POST /diagnose` call is logged as
  an MLflow run, capturing:
  - **Params**: LLM provider/model, prompt version, whether a tongue
    observation was provided, symptom text length
  - **Metrics**: classification confidence, number of secondary patterns,
    number of herb recommendations, top herb relevance score
  - **Tags**: primary syndrome pattern, top herb ID/tradition, set of herb
    traditions returned (useful for investigating the Indigenous/TCM
    retrieval balance noted in [BUILD_LOG.md](BUILD_LOG.md))
  - MLflow tracking is provider-agnostic: defaults to local file-based tracking
    (`./mlruns`, no server needed), or can point at a Dockerized MLflow
    tracking server for a shared UI. Tracking is best-effort and never breaks
    `/diagnose` if logging fails.

- **Dataset versioning (DVC)**: `app/data/herbs.json` is tracked with DVC,
  using a Google Drive remote for storing dataset versions. Every change to
  the herb knowledge base can be versioned, pushed, and rolled back
  independently of the Qdrant index or application code — see
  [Expanding the herb knowledge base](#expanding-the-herb-knowledge-base-with-dvc-versioning)
  below.

- **Orchestration (Airflow)**: a DAG (`reindex_herb_knowledge_base`) runs
  daily (or on manual trigger) with two tasks:
  1. `validate_herbs_data` — validates `herbs.json` against the `Herb` schema,
     checks every `syndromes` value is a valid `TCMSyndrome`, and checks for
     duplicate herb IDs
  2. `index_herbs` — re-indexes the herb knowledge base into Qdrant, but only
     if validation passed

  This means a bad edit to `herbs.json` (e.g. a typo'd syndrome name) fails
  the DAG at validation and Qdrant keeps its last-known-good index, rather
  than silently indexing broken data. See
  [Running Airflow](#running-airflow) below.

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
    ├── syndrome_mapper.py    # LangChain pipeline: LLM call -> structured output
    ├── herb_retriever.py     # Qdrant indexing + vector retrieval for herbs
    └── experiment_tracker.py # MLflow run logging for /diagnose calls

scripts/
└── index_herbs.py       # CLI script to (re)index herbs.json into Qdrant

airflow/
├── docker-compose.yaml  # Airflow (LocalExecutor) via docker-compose
├── .env.example          # AIRFLOW_UID setup
└── dags/
    └── reindex_herbs_dag.py  # validate_herbs_data -> index_herbs DAG
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

9. (Optional) View MLflow experiment runs. By default, runs are logged to a
   local `./mlruns` folder. To browse them in the MLflow UI:

   ```bash
   mlflow ui --backend-store-uri ./mlruns
   ```

   Then open `http://localhost:5000` to see each `/diagnose` call as a run,
   with its params (LLM provider/model, prompt version), metrics (confidence,
   herb relevance scores), and tags (syndrome pattern, herb traditions
   returned).

## Running Airflow

Airflow runs the `reindex_herb_knowledge_base` DAG, which validates
`app/data/herbs.json` and re-indexes it into Qdrant. It runs via
docker-compose, separate from the FastAPI app.

**Prerequisites**: Qdrant (Docker) and Ollama must already be running on your
host machine — Airflow's containers connect to them via
`host.docker.internal`.

1. Set your `AIRFLOW_UID` (avoids file permission issues):

   ```bash
   cd airflow
   cp .env.example .env
   ```

   Then edit `.env` and set `AIRFLOW_UID` to the output of `id -u` (run that
   command to get your user ID).

2. Initialize Airflow's metadata database (one-time):

   ```bash
   docker compose up airflow-init
   ```

   This also installs the Python packages the DAG needs (`langchain-ollama`,
   `qdrant-client`, etc.) into the Airflow containers.

3. Start Airflow:

   ```bash
   docker compose up
   ```

   This starts Postgres (Airflow's metadata DB), the scheduler, and the
   webserver. First startup can take a minute or two.

4. Open the Airflow UI at `http://localhost:8081` (login: `airflow` /
   `airflow`).

5. Find `reindex_herb_knowledge_base` in the DAG list. It's paused by default
   (`AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'`) — toggle it on, or
   trigger a single run manually via the "Trigger DAG" (play) button to see
   it execute immediately.

6. Click into a run to see the two tasks (`validate_herbs_data` ->
   `index_herbs`) and their logs. A successful run's logs will show the
   validation summary and "Indexed 15 herbs into Qdrant."

To stop Airflow:

```bash
docker compose down
```

> Note: port `8081` is used for Airflow's webserver (not the default `8080`),
> since `8080`/`8090` can conflict with other local tools — see
> [BUILD_LOG.md](BUILD_LOG.md) Issue 10.

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

## Expanding the herb knowledge base (with DVC versioning)

The herb knowledge base lives in `app/data/herbs.json` and is version-controlled
with [DVC](https://dvc.org), with a Google Drive remote for storing dataset
versions separately from git history. This means every change to the herb
dataset is tracked as a distinct version, retrievable later — useful for
auditing "what did the knowledge base look like when this diagnosis was made"
or rolling back a bad edit.

### One-time setup (per machine)

1. Install dependencies (already includes `dvc[gdrive]`):

   ```bash
   pip install -r requirements.txt
   ```

2. Create a folder in your Google Drive (e.g. "rootsandqi-dvc-storage"), open
   it, and copy the folder ID from the URL:
   `https://drive.google.com/drive/folders/`**`<this-part-is-the-folder-id>`**

3. Set the DVC remote to point at that folder:

   ```bash
   dvc remote modify gdrive_remote url gdrive://<your-folder-id>
   ```

4. The first time you run `dvc push`, a browser window will open asking you
   to authorize DVC to access that Google Drive folder. Approve it — this is
   a one-time OAuth step per machine.

### Adding or updating herbs

1. Edit `app/data/herbs.json` — add a new entry following the existing
   structure (`id`, `name`, `tradition`, `syndromes`, `description`,
   `preparation`, `cautions`). `syndromes` values must match the
   `TCMSyndrome` enum values defined in `app/models/diagnosis.py`.

2. Re-run the indexing script to update Qdrant:

   ```bash
   python -m scripts.index_herbs
   ```

3. Track the new version with DVC and push it to the remote:

   ```bash
   dvc add app/data/herbs.json
   dvc push
   ```

4. Commit the small `.dvc` pointer file to git (the actual data lives in the
   DVC remote, not git):

   ```bash
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

This checks out an older `.dvc` pointer, pulls the corresponding data version
from Google Drive, and re-indexes Qdrant to match.

## Roadmap

- [x] Milestone 1: AI diagnostic core (FastAPI + LangChain syndrome mapping)
- [x] Milestone 2: Indigenous + TCM herb knowledge base (Qdrant retrieval)
- [x] Milestone 3: MLOps layer
  - [x] MLflow experiment tracking for /diagnose runs
  - [x] DVC dataset versioning for herbs.json (Google Drive remote)
  - [x] Airflow scheduled re-indexing (validate -> index DAG)
- [ ] Milestone 4: Minimal web UI
- [ ] Milestone 5: DevOps/infra wrap (Terraform, EKS, CI/CD, Trivy, Prometheus/Grafana)
- [ ] Milestone 6: Compliance docs + polish

## Build Log

For a detailed account of environment setup issues encountered and how they
were debugged and resolved, see [BUILD_LOG.md](BUILD_LOG.md).
