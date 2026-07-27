---
name: InsightPilot Python backend
description: How Python/uv is set up in this project and how to install packages when the PATH-based uv isn't available.
---

# InsightPilot Python backend

The FastAPI backend lives at `artifacts/insightpilot/backend/`. It is started via `start.sh` which calls `.venv/bin/uvicorn`.

## uv path workaround

`installLanguagePackages` callback may fail with "uv not found in PATH". When that happens, use the nix-store uv directly:

```bash
/nix/store/75k8jgyjrh86099bksak7a1frph0j611-uv-0.7.20/bin/uv venv .venv --python 3.13
/nix/store/75k8jgyjrh86099bksak7a1frph0j611-uv-0.7.20/bin/uv pip install <packages>
```

**Why:** `uv` is declared in `replit.nix` deps but does not appear on PATH in the shell agent runs in. The binary exists in the nix store at the path above (uv 0.7.20).

**How to apply:** Any time you need to create the venv from scratch or install a new Python package and `installLanguagePackages` fails.

## Package list (pyproject.toml)
fastapi==0.115.6, google-genai>=1.0.0, numpy==2.1.3, openai>=1.57.0, pandas==2.2.3, pydantic==2.10.4, python-multipart==0.0.20, uvicorn[standard]==0.32.1
