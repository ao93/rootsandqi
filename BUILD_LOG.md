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
