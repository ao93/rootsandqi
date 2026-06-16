# Build Log — RootsAndQi

This log documents real issues encountered while setting up and running the
RootsAndQi environment across milestones, along with root cause analysis and
fixes. Kept for reference and as a record of the debugging process.

---

# Milestone 1: AI Diagnostic Core

---

## Issue 1: `pydantic-core` failed to build on Python 3.14

**Symptom**

Running `pip install -r requirements.txt` failed during the build step for
`pydantic-core`, with a long Rust/Cargo compilation log ending in:

```
error: the configured Python interpreter version (3.14) is newer than PyO3's
maximum supported version (3.13)
```

**Root cause**

`pydantic-core` is a Rust extension built via PyO3/maturin. The version
specified in `requirements.txt` (2.27.2, and earlier 2.23.4) does not yet have
a prebuilt wheel for Python 3.14, which was very new at the time. Without a
prebuilt wheel, pip falls back to compiling from source — and the installed
version of PyO3 doesn't support Python 3.14 as a build target yet, so
compilation fails outright.

**Fix**

Recreated the virtual environment using Python 3.12 instead of the system's
default Python 3.14:

```bash
deactivate
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

With Python 3.12, pip found a prebuilt wheel (`pydantic_core-2.27.2-cp312-cp312-macosx_11_0_arm64.whl`)
and installation succeeded with no compilation needed.

**Takeaway**

Bleeding-edge Python versions can outpace the availability of prebuilt wheels
for packages with compiled (Rust/C) extensions. When a `pip install` fails with
a Rust/Cargo/maturin build error, checking whether an older, more widely-supported
Python version resolves it is a fast and effective fix.

---

## Issue 2: `langchain-core` version conflict

**Symptom**

```
ERROR: Cannot install -r requirements.txt (line 3), -r requirements.txt (line 5)
and langchain-core==0.3.29 because these package versions have conflicting
dependencies.

The conflict is caused by:
    The user requested langchain-core==0.3.29
    langchain 0.3.14 depends on langchain-core<0.4.0 and >=0.3.29
    langchain-anthropic 0.3.3 depends on langchain-core<0.4.0 and >=0.3.30
```

**Root cause**

`langchain-anthropic==0.3.3` requires `langchain-core>=0.3.30`, but
`requirements.txt` pinned `langchain-core==0.3.29` — one patch version too low.
pip's resolver correctly identified that no single version of `langchain-core`
could satisfy both constraints as written.

**Fix**

Bumped the pin from `0.3.29` to `0.3.30`:

```diff
- langchain-core==0.3.29
+ langchain-core==0.3.30
```

**Takeaway**

When pinning versions across a family of related packages (langchain,
langchain-core, langchain-anthropic, langchain-ollama), the sub-packages often
have minimum version requirements on the core package that are easy to miss.
pip's error message directly states the constraint conflict, making this a
quick fix once read carefully.

---

## Issue 3: `uvicorn` resolved to the wrong Python environment

**Symptom**

After successfully installing all dependencies into `.venv` (Python 3.12),
running:

```bash
uvicorn app.main:app --reload
```

failed with:

```
ModuleNotFoundError: No module named 'langchain_core'
```

The traceback showed uvicorn was being executed from
`/Library/Frameworks/Python.framework/Versions/3.14/bin/uvicorn` — the *global*
Python 3.14 installation, not the project's `.venv`.

**Root cause**

Even with `.venv` activated (confirmed via `which python` →
`/Users/adolfo/rootsandqi/.venv/bin/python`), the `uvicorn` command itself was
resolving to a globally-installed `uvicorn` binary earlier in `PATH`. This
global uvicorn was running under Python 3.14, which does not have
`langchain_core` (or any of the project's dependencies) installed —
they were only installed into `.venv`'s Python 3.12 environment.

**Fix**

Ran uvicorn as a module via the venv's Python interpreter directly, which
forces it to use the correct environment regardless of `PATH`:

```bash
python -m uvicorn app.main:app --reload
```

This succeeded immediately — server started cleanly with no import errors.

**Takeaway**

`source .venv/bin/activate` updates `PATH` so that `python` resolves correctly,
but if a same-named executable (like `uvicorn`) exists earlier in `PATH` from a
global install, the shell may still resolve to that one instead of the venv's
version. Running `python -m <tool>` sidesteps this entirely by letting Python
itself locate the module within its own environment — a generally more reliable
pattern when environment issues are suspected.

---

## Result (Milestone 1)

After resolving all three issues, the API started successfully:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Both endpoints were verified working:

- `GET /health` → `200 OK`, `{"status": "ok", "service": "RootsAndQi"}`
- `POST /diagnose` → `200 OK`, returned a valid `SyndromeClassification` (Qi
  Deficiency, confidence 0.8, correct reasoning referencing both the symptom
  description and tongue observation) from a local Llama 3 model via Ollama —
  no paid API calls required for development.

---

# Milestone 2: Herb Knowledge Base + Qdrant Retrieval

## Issue 4: Docker daemon not running

**Symptom**

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

failed with:

```
failed to connect to the docker API at unix:///Users/adolfo/.docker/run/docker.sock;
check if the path is correct and if the daemon is running: dial unix
/Users/adolfo/.docker/run/docker.sock: connect: no such file or directory
```

**Root cause**

The Docker CLI was installed (`which docker` →
`/usr/local/bin/docker`), but Docker Desktop (the application that runs the
Docker daemon on macOS) was not running. The CLI can't communicate with a
daemon that isn't up.

**Fix**

Launched Docker Desktop:

```bash
open -a Docker
```

Waited for the Docker Desktop app to fully start (whale icon in the menu bar
stops animating), then re-ran the same `docker run` command — it succeeded,
pulling the `qdrant/qdrant` image and starting the container with the REST
API on port 6333 and gRPC on port 6334.

**Takeaway**

On macOS, the `docker` CLI being installed doesn't mean the daemon is running —
Docker Desktop must be launched and fully initialized first. This is a common
first-run gotcha that's easy to mistake for a more complex configuration issue.

---

## Issue 5: `ModuleNotFoundError: No module named 'app'` running indexing script directly

**Symptom**

```bash
python scripts/index_herbs.py
```

failed with:

```
Traceback (most recent call last):
  File "/Users/adolfo/rootsandqi/scripts/index_herbs.py", line 13, in <module>
    from app.services.herb_retriever import index_herbs
ModuleNotFoundError: No module named 'app'
```

**Root cause**

When a script is run directly (`python scripts/index_herbs.py`), Python adds
only the script's own directory (`scripts/`) to `sys.path` — not the project
root. Since `app` is a package living at the project root (`~/rootsandqi/app/`),
it isn't on the path and the import fails, even though the same `app.services...`
import works fine when FastAPI/uvicorn runs from the project root.

**Fix**

Ran the script as a module from the project root instead, which adds the
current directory (project root) to `sys.path`:

```bash
python -m scripts.index_herbs
```

This succeeded immediately:

```
Indexing herb knowledge base into Qdrant...
Done. Indexed 15 herbs into the 'herbs' collection.
```

**Takeaway**

This is the same underlying category of issue as Issue 3 (Milestone 1's
uvicorn/PATH problem) — Python's module resolution depends on *how* a program
is invoked, not just *where* the files live. As a general rule: when working
with an `app/`-style package layout, prefer `python -m <module.path>` over
`python <path/to/file.py>` so imports resolve relative to the project root.

---

## Result (Milestone 2)

After resolving both issues:

- Qdrant running locally via Docker (`localhost:6333`), dashboard accessible
  at `http://localhost:6333/dashboard`
- `nomic-embed-text` pulled via Ollama for local/free embeddings
- `python -m scripts.index_herbs` successfully embedded and indexed all 15
  herbs from `app/data/herbs.json` into Qdrant
- `POST /diagnose` → `200 OK`, returned the syndrome classification (Qi
  Deficiency) plus 5 ranked herb recommendations (relevance scores 0.76-0.83),
  correctly surfacing TCM herbs tagged for `qi_deficiency` and the closely
  related `yang_deficiency` pattern — confirming the vector retrieval pipeline
  works end-to-end on real embedded data, not just sample/mock data.

### Known behavior / future improvement

> **Note:** at the time of this test, the `tradition` field used "Caribbean"
> as the category label; it was later broadened to "Indigenous" to encompass
> herbal traditions from around the world, not just the Caribbean. The
> underlying herbs and the observation below are unchanged.

In this test, all 5 top-ranked herbs were from the TCM tradition, even though
the knowledge base includes Indigenous herbs tagged for `qi_deficiency` and
`blood_deficiency` (e.g., Moringa). This is not a bug — the embedding model
likely finds TCM terminology ("Qi deficiency") semantically closer to other
TCM-described herbs, since the term itself originates in TCM.

A future improvement would be to retrieve top-N results *per tradition*
separately (e.g., top 3 TCM + top 3 Indigenous) and merge them, guaranteeing
cross-tradition representation in every response — directly supporting the
project's core differentiator of bridging both traditions.

---

# Milestone 3: MLOps - DVC Dataset Versioning

## Issue 6: `pathspec` version conflict breaking DVC

**Symptom**

```bash
dvc add app/data/herbs.json
```

failed with:

```
ERROR: unexpected error - cannot import name '_DIR_MARK' from
'pathspec.patterns.gitwildmatch'
```

**Root cause**

The installed version of the `pathspec` package was incompatible with the
version DVC expects — a newer `pathspec` release removed/renamed an internal
symbol (`_DIR_MARK`) that DVC's code imports directly.

**Fix**

Pinned `pathspec` to a compatible range:

```bash
pip install "pathspec>=0.10.3,<0.13"
```

**Takeaway**

Same general class of issue as the Python 3.14/pydantic-core problem from
Milestone 1 — a fast-moving dependency (here, `pathspec`) outpacing what a
less-frequently-updated tool (DVC) expects. Pinning the conflicting transitive
dependency directly resolves it without needing to change DVC's version.

---

## Issue 7: Google blocked DVC's default OAuth client for Google Drive access

**Symptom**

Running `dvc push` for the first time opened a browser tab, but Google
returned:

```
This app is blocked
This app tried to access sensitive info in your Google Account. To keep your
account safe, Google blocked this access.
```

**Root cause**

DVC's `gdrive` remote ships with a default shared OAuth client ID. Google has
restricted/blocked this shared client for the Drive scopes DVC requests,
likely due to it being a well-known shared credential used by many DVC users
(a common target for blocking/abuse prevention).

**Fix**

Created a personal Google Cloud OAuth client so DVC authenticates as "my own
app" instead of the blocked shared one:

1. Created a new Google Cloud project (`rootsandqi-dvc`)
2. Enabled the Google Drive API for that project
3. Configured the OAuth consent screen (External user type, app name, support/
   developer email)
4. Added my own Google account as a **test user** (required since the app is
   in "Testing" publishing status, not verified)
5. Created an OAuth 2.0 Client ID of type **Desktop app**, obtaining a Client
   ID and Client Secret
6. Configured DVC to use these credentials:

   ```bash
   dvc remote modify gdrive_remote gdrive_client_id '<client-id>'
   dvc remote modify gdrive_remote gdrive_client_secret '<client-secret>'
   ```

**Takeaway**

For any project using DVC + Google Drive remotes beyond quick personal
experiments, expect to set up your own OAuth client in Google Cloud Console.
This is a one-time setup per machine/credential-set, and is genuinely the same
category of IAM/OAuth configuration work involved in setting up real cloud
integrations (e.g., a service's own OAuth app for a third-party API).

---

## Issue 8: "Access blocked... has not completed the Google verification process"

**Symptom**

After switching to a personal OAuth client (Issue 7), `dvc push` produced a
new error:

```
Access blocked: RootsAndQi DVC has not completed the Google verification process
Error 403: access_denied
```

**Root cause**

A newly-created OAuth app starts in "Testing" publishing status. In this
status, Google only allows sign-in from accounts explicitly added as **test
users** on the OAuth consent screen — even the developer's own account, if not
added.

**Fix**

In Google Cloud Console, navigated to the Audience page
(`console.cloud.google.com/auth/audience`) for the OAuth consent
configuration, and added my own Google account email under **Test users**.

**Takeaway**

"Testing" mode is a safe default for unverified OAuth apps, but it's an
allowlist — every account that needs to authenticate (including the
developer's own) must be added explicitly. This is a common first-time gotcha
when setting up any new OAuth app, not specific to DVC.

---

## Issue 9: `dvc push` failed with stale lock file

**Symptom**

```
ERROR: failed to push data to the cloud - Unable to acquire lock. Most likely
another DVC process is running or was terminated abruptly.
```

**Root cause**

A previous `dvc push` attempt (which failed during the OAuth block in Issue 7)
left behind lock files under `.dvc/tmp/` (`lock`, `rwlock`) that weren't
cleaned up when the process exited abnormally.

**Fix**

```bash
rm -f .dvc/tmp/lock .dvc/tmp/rwlock
```

then retried `dvc push`.

**Takeaway**

Many CLI tools (DVC, Terraform, etc.) use lock files to prevent concurrent
runs from corrupting state. When a process is killed or errors out ungracefully,
stale locks can remain and need manual cleanup — worth knowing this pattern
generally, not just for DVC.

---

## Issue 10: `dvc push` failed — local web server for OAuth redirect couldn't start

**Symptom**

```
Failed to start a local web server. Please check your firewall settings and
locally running programs that may be blocking or using configured ports.
Default ports are 8080 and 8090.
ERROR: unexpected error - Failed to authenticate GDrive
```

**Root cause**

DVC's OAuth flow runs a temporary local web server on port 8080 (or 8090) to
receive the redirect from Google after authentication. Both ports were already
occupied by leftover Python processes from earlier `uvicorn` and `mlflow ui`
sessions that hadn't been stopped cleanly (`Ctrl+C` in a different terminal
tab, process kept running in the background).

**Fix**

Identified and killed the stale processes:

```bash
lsof -i :8080
lsof -i :8090
kill -9 <pid1> <pid2>
```

then retried `dvc push`, which completed the OAuth flow successfully.

**Takeaway**

When running multiple local services (API server, MLflow UI, DVC, etc.) across
several terminal tabs, it's easy to accumulate orphaned processes holding onto
ports. `lsof -i :<port>` is the general-purpose way to find what's bound to a
port before assuming a tool's default port is "free."

---

## Issue 11: `dvc add` refused — file already tracked by git

**Symptom**

```
ERROR: output 'app/data/herbs.json' is already tracked by SCM (e.g. Git).
You can remove it from Git, then add to DVC.
```

**Root cause**

`herbs.json` was committed to git directly in Milestone 2, before DVC was
introduced in Milestone 3. DVC and git can't both track the same file's
content directly — DVC expects to own the file via its `.dvc` pointer +
`.gitignore` entry instead.

**Fix**

```bash
git rm --cached app/data/herbs.json
git commit -m "Stop tracking herbs.json with git, use DVC instead"
dvc add app/data/herbs.json
```

After this, `app/data/herbs.json` is gitignored (via the `.gitignore` DVC
generated), and `app/data/herbs.json.dvc` (a small pointer file with the
content hash) is committed to git instead.

**Takeaway**

When retrofitting DVC onto a file that's already in git history, the file must
first be untracked from git (`git rm --cached`, which keeps it on disk) before
`dvc add` can take it over. This is a one-time migration step per file.

---

## Result (Milestone 3 - DVC)

After resolving Issues 6-11:

- `app/data/herbs.json` is tracked by DVC, with its actual content stored in a
  Google Drive remote (via a personal OAuth client) and only a small `.dvc`
  pointer file (`app/data/herbs.json.dvc`, containing an md5 hash and size)
  committed to git.
- The OAuth client secret is stored in `.dvc/config.local` (gitignored),
  keeping it out of version control while `.dvc/config` (committed) contains
  only the non-sensitive remote URL.
- `dvc push` succeeded: `1 file pushed`.
- Future changes to `herbs.json` follow the documented workflow: edit ->
  re-index Qdrant -> `dvc add` -> `dvc push` -> commit the updated `.dvc` file.

---

# Milestone 3: MLOps - Airflow Orchestration

## Issue 12: Airflow 3.0 removed `airflow users create` command

**Symptom**

`docker compose up airflow-init` failed during user creation:

```
airflow command error: argument GROUP_OR_COMMAND: invalid choice: 'users'
airflow-init exited with code 2
```

**Root cause**

Airflow 3.0 removed the `airflow users` CLI command group as part of a
broader auth manager refactor. User creation now happens automatically via the
"simple auth manager" when the webserver/api-server first starts, generating
a random password printed to the container logs.

**Fix**

Removed the `airflow users create` step from the `airflow-init` entrypoint.
Retrieved the auto-generated admin password from webserver logs:

```bash
docker compose logs airflow-webserver | grep -i "password"
# Simple auth manager | Password for user 'admin': <generated-password>
```

**Takeaway**

Major version upgrades in Airflow (2.x → 3.x) can remove previously standard
CLI commands as part of architectural changes. Always check the migration guide
when upgrading Airflow versions; don't assume CLI interfaces are stable across
major versions.

---

## Issue 13: Airflow 3.0 task execution failed — scheduler couldn't reach API server

**Symptom**

DAG runs showed tasks immediately failing with `state=queued, pid=None`
(no process ever spawned), and scheduler logs showed:

```
httpx.ConnectError: [Errno 111] Connection refused
DAG 'reindex_herb_knowledge_base' not found in serialized_dag table
```

**Root cause**

Airflow 3.0 introduced a new architecture where the scheduler/executor
communicates with the API server via HTTP to manage task execution (the
"execution API"). By default, this is configured as
`http://localhost:8080/execution/` — but in a docker-compose setup, `localhost`
means "this container," not the container running the API server. The scheduler
container was trying to reach port 8080 on itself, where nothing was listening.

**Fix**

Added `AIRFLOW__CORE__EXECUTION_API_SERVER_URL` pointing at the webserver
service by its Docker Compose service name:

```yaml
AIRFLOW__CORE__EXECUTION_API_SERVER_URL: http://airflow-webserver:8080/execution/
```

This is a new Airflow 3.0 requirement with no equivalent in 2.x.

**Takeaway**

Airflow 3.0's task execution model is fundamentally different from 2.x —
it requires explicit inter-service HTTP communication that must be configured
for multi-container setups. This is not well-documented in early 3.0 releases
and catches most docker-compose-based setups.

---

## Issue 14: Airflow 3.0 healthcheck endpoint moved

**Symptom**

Both `airflow-webserver` and `airflow-scheduler` containers showed "unhealthy"
in `docker compose ps`, despite the webserver being accessible in the browser.
Manually hitting the health endpoint revealed:

```json
{"error":"Moved in Airflow 3. Please change config to check `/api/v2/monitor/health`"}
```

**Root cause**

Airflow 3.0 moved the health endpoint from `/health` to `/api/v2/monitor/health`.
The docker-compose healthcheck was still pointing at the old path.

**Fix**

Updated the webserver healthcheck:

```yaml
test: ["CMD", "curl", "--fail", "http://localhost:8080/api/v2/monitor/health"]
```

**Takeaway**

Cosmetic but worth knowing: Docker's "unhealthy" label doesn't always mean
the service is non-functional — it means the specific healthcheck command
failed. In Airflow 3.0, this was a path change, not a real service failure.

---

## Issue 15: Downgrading from Airflow 3.0 to 2.10 failed — DB schema conflict

**Symptom**

After switching to `apache/airflow:2.10.4` image, `airflow db migrate` failed:

```
AttributeError: execution_date
ERROR: You need to upgrade the database. Please run `airflow db upgrade`.
Make sure the command is run using Airflow version 2.10.4.
```

**Root cause**

The Postgres volume still contained the Airflow 3.0 database schema (which
removed the `execution_date` column that Airflow 2.x expects). Airflow 2.10.4
detected a schema it couldn't downgrade from.

**Fix**

Wiped the Postgres volume entirely and re-initialized with a clean DB:

```bash
docker compose down -v   # -v removes named volumes including postgres-db-volume
docker compose up airflow-init
```

**Takeaway**

Airflow database schemas are not backwards-compatible across major versions.
When switching from a higher to a lower major version, always wipe the
metadata DB (`down -v`) and re-initialize from scratch. Data in the DB
(DAG run history, task logs metadata) will be lost, but DAG code and actual
task logs (on the mounted volume) are preserved.

---

## Issue 16: Pip packages installed in `airflow-init` not available in scheduler/webserver

**Symptom**

After a successful `airflow-init` that installed `langchain-ollama` and
other packages, the DAG task still failed with:

```
ModuleNotFoundError: No module named 'langchain_ollama'
```

**Root cause**

In Docker Compose, each service runs in its own container. Installing pip
packages in the `airflow-init` container only affects that container's
filesystem — it doesn't persist to the `airflow-scheduler` or
`airflow-webserver` containers, which start fresh from the same base image.

**Fix**

Used Airflow's officially supported `_PIP_ADDITIONAL_REQUIREMENTS` environment
variable in the shared `x-airflow-common` block, so every container (init,
scheduler, webserver) installs the required packages on startup:

```yaml
_PIP_ADDITIONAL_REQUIREMENTS: >-
  langchain==0.3.14
  langchain-core==0.3.30
  langchain-ollama==0.2.2
  qdrant-client==1.12.1
  pydantic==2.10.4
  pydantic-settings==2.7.0
  python-dotenv==1.0.1
```

**Takeaway**

Docker containers have isolated filesystems. Packages installed in one
container don't appear in others, even if they share the same base image.
`_PIP_ADDITIONAL_REQUIREMENTS` is the correct Airflow mechanism for this
because it uses the container's own entrypoint (which runs as the correct
user) rather than requiring an entrypoint override.

---

## Issue 17: Overriding Airflow entrypoint broke container user context

**Symptom**

Attempted to fix Issue 16 by overriding the scheduler/webserver `entrypoint`
to run pip install then `exec airflow <command>`. Both containers restarted
immediately with:

```
AirflowConfigException: The user that Airflow is running as has no username;
you must run Airflow as a full user, with a username and home directory,
in order for it to function properly.
```

**Root cause**

Airflow's official `dumb-init` entrypoint sets up proper user context (home
directory, username lookup) before running the Airflow command. Overriding
the entrypoint with `/bin/bash` bypassed this setup, leaving the process
running as a user with no `/etc/passwd` entry for the current UID — which
Airflow's `getuser()` call couldn't resolve.

**Fix**

Reverted to the standard `command:` override (not `entrypoint:` override)
and used `_PIP_ADDITIONAL_REQUIREMENTS` instead (see Issue 16).

**Takeaway**

Airflow's container entrypoint does non-trivial setup. When customizing
container behavior, prefer `command:` overrides and officially supported
env vars (`_PIP_ADDITIONAL_REQUIREMENTS`, `_AIRFLOW_DB_MIGRATE`, etc.)
over `entrypoint:` overrides, which bypass the entrypoint's setup logic.

---

## Result (Milestone 3 - Airflow)

After resolving Issues 12-17 (including pivoting from Airflow 3.0 to 2.10.4
due to Airflow 3.0's underdocumented docker-compose architecture requirements):

- Airflow 2.10.4 running via docker-compose (LocalExecutor + Postgres metadata
  DB), webserver accessible at `http://localhost:8081`
- `reindex_herb_knowledge_base` DAG with two tasks:
  1. `validate_herbs_data` — validates `herbs.json` schema, syndrome values,
     and duplicate IDs using Pydantic + custom enum validation
  2. `index_herbs` — re-indexes the herb knowledge base into Qdrant via Ollama
     embeddings
- Both tasks completed successfully (green) on first successful run after
  resolving all infrastructure issues
- The validate → index dependency correctly enforces that Qdrant is never
  updated with invalid data
