# Workbook Agent

A framework-free, Python-first spreadsheet agent workbench. The agent loop, tool registry,
policy gates, and evaluation harness remain application code owned by this repository.

## Stack

- **Backend:** Python 3.12, FastAPI, Pydantic Settings, HTTPX, openpyxl, and pandas.
- **Frontend:** React + TypeScript + Vite + shadcn/ui. It will display chat, tool traces,
  staged workbook diffs, and confirmation prompts; it does not own agent orchestration.
- **Model provider:** NVIDIA NIM through a small provider adapter that will be implemented in
  the backend. Keep `NVIDIA_API_KEY` in `.env`, never in source control.

## Run locally

```powershell
uv sync
uv run fastapi dev backend/app/main.py
```

In a second terminal:

```powershell
cd frontend/workbook-agent-ui
pnpm install --frozen-lockfile
pnpm dev
```

The API runs at `http://localhost:8000`; the SPA runs at `http://localhost:5173`.

## Current API surface

- `GET /api/health`
- `GET /api/agent/configuration`

The initial endpoints expose safe configuration only. Workbook mutation endpoints will be
introduced with the staged-diff and explicit-confirmation design described in
[`docs/research/agent-from-scratch-research.md`](docs/research/agent-from-scratch-research.md).
