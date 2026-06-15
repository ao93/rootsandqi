# Build Log — Milestone 1: AI Diagnostic Core

This log documents the real issues encountered while setting up and running the
Milestone 1 environment (FastAPI + LangChain + Ollama syndrome-mapping pipeline),
along with root cause analysis and fixes. Kept for reference and as a record of
the debugging process.

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

## Result

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
