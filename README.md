# Workbook Agent

A framework-free, Python-first spreadsheet-agent backend. The agent loop, workbook tools,
policy gates, and evaluation harness are application code owned by this repository.

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

## Verify submission evidence

Before representing a commit as submission-ready, run:

```powershell
uv sync
uv run pytest
uv run python scripts/verify_submission.py
```

The final command creates `artifacts/submission-proof.json`. It fails closed until both
runnable workbook tools and the 72-case baseline corpus exist; a contract or passing unit
tests alone is not a passing evaluation. See [the evidence checklist](docs/submission-evidence.md)
and [the live-defense runbook](docs/live-defense.md) for the required final report, demo,
and limitation statement.

## Current API surface

- `GET /api/health`
- `GET /api/agent/configuration`

The current endpoints expose safe configuration only. Workbook mutation endpoints and the
runnable baseline corpus are not implemented yet, so this commit is not submission-ready.
Their required staged-diff and explicit-confirmation behavior is recorded in
[`DECISIONS.md`](DECISIONS.md) and [`docs/backend-api-contract.md`](docs/backend-api-contract.md).
