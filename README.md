# Workbook Agent

Workbook Agent is a framework-free, Python-first application for answering questions about and making controlled changes to the two supplied Excel workbooks: real-estate listings and marketing campaigns. It is intentionally not a general spreadsheet executor. The model may select from a small set of validated operations; repository-owned Python code enforces the workbook, query, mutation, and artifact rules.

## What the repository contains

| Location | Responsibility |
| --- | --- |
| `backend/app/` | FastAPI application, model-provider adapter and bounded agent loop, API runtime, schemas, settings, and `WorkbookSession`. |
| `backend/tests/` | Python tests for the API, settings, agent loop, workbook-session safety boundary, evaluation contract, and release-proof checks. |
| `evaluation/` | The deterministic 72-case Baseline Evaluation Corpus and its machine-readable contract. |
| `frontend/workbook-agent-ui/` | React/Vite interface for the backend session/run workflow, including frontend unit tests. |
| `docs/task-reqs/` | Immutable source workbook fixtures used by the application and evaluation. |
| `scripts/verify_submission.py` | Runs repository checks plus the baseline evaluator and writes the release-evidence report. |
| `artifacts/` | Generated local evidence, including `submission-proof.json`; do not treat checked-in output as current evidence. |

## Runtime behavior and safety boundary

Each browser session is bound to one backend-owned `Workbook Key` (`listings` or `campaigns`). The backend creates a temporary **Session Workbook**; it never edits either source fixture in place. The agent can call only these contracts:

- `describe_workbook`
- `query_workbook`
- `stage_mutation`
- `commit_mutation`

Queries use an allowlisted JSON shape. Inserts, updates, and deletes must name a stable row ID, produce an exact staged diff, and receive explicit confirmation for that unchanged stage. A commit writes a new candidate artifact, reopens it, and verifies the authorized cell changes before it becomes the active session version. The API exposes safe lifecycle events over SSE and does not send provider diagnostics, filesystem paths, prompts, chain-of-thought, or raw workbook data to the client.

The service is in-memory: sessions, runs, artifacts, and the bounded event-replay window disappear when the API process restarts.

## Requirements and setup

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js and pnpm 10.18.3 (only for the frontend)
- An NVIDIA NIM provider key in `.env` to use live model-backed runs. Copy `.env.example` and set `NVIDIA_API_KEY`.

```powershell
uv sync
Copy-Item .env.example .env
```

The deterministic Python tests and baseline evaluation do not require a live provider key.

## Run locally

Start the API from the repository root:

```powershell
uv run fastapi dev backend/app/main.py
```

Start the UI in a second terminal:

```powershell
cd frontend/workbook-agent-ui
pnpm install --frozen-lockfile
pnpm dev
```

The API is available at `http://localhost:8000` and the Vite UI at `http://localhost:5173`. The interactive API documentation is at `http://localhost:8000/docs`.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Health check. |
| `GET /api/agent/configuration` | Exposes safe provider and write-confirmation configuration. |
| `POST /api/sessions` | Creates a session bound to `listings` or `campaigns`. |
| `POST /api/sessions/{session_id}/runs` | Submits one user message for a session. |
| `GET /api/sessions/{session_id}/runs/{run_id}/events` | Streams safe run events over SSE; supports bounded replay with `Last-Event-ID`. |
| `POST /api/sessions/{session_id}/runs/{run_id}/confirmation` | Confirms one unchanged staged mutation by `stage_id`. |
| `POST /api/sessions/{session_id}/runs/{run_id}/cancel` | Cancels an active run; cancellation cannot commit a mutation. |
| `GET /api/sessions/{session_id}/artifacts/{artifact_id}` | Downloads a verified output workbook. |

The precise request, response, event, and error contracts are in [docs/backend-api-contract.md](docs/backend-api-contract.md).

## Test and verification commands

Run commands from the repository root unless noted otherwise.

| Goal | Command | What it checks |
| --- | --- | --- |
| Full Python suite | `uv run pytest` | API, agent-loop, provider configuration, workbook-session, baseline-contract, and submission-proof tests. |
| One Python test module | `uv run pytest backend/tests/test_workbook_session.py` | The transactional Session Workbook boundary and mutation verification. |
| One Python test | `uv run pytest backend/tests/test_workbook_session.py::test_stage_requires_exact_commit_and_verifies_artifact` | A focused failure/reproduction loop. |
| Python lint | `uv run ruff check .` | Ruff rules configured in `pyproject.toml`. |
| Deterministic baseline | `uv run python -m evaluation.baseline` | Executes and prints the 72-case corpus; it is model-free and validates the bounded tool contract. |
| Release evidence | `uv run python scripts/verify_submission.py` | Executes the baseline and writes `artifacts/submission-proof.json`; exit `0` is release-ready and exit `2` blocks release. |
| Frontend tests | `pnpm test` (from `frontend/workbook-agent-ui`) | Vitest component and demo-session tests. |
| Frontend quality | `pnpm lint`, `pnpm typecheck`, `pnpm build` (from `frontend/workbook-agent-ui`) | ESLint, TypeScript, and production build checks. |

For a submission-ready verification run:

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run python scripts/verify_submission.py

cd frontend/workbook-agent-ui
pnpm install --frozen-lockfile
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```

The proof script is deliberately stricter than a passing test suite: it fails closed unless a fresh full baseline execution meets the release thresholds.

## Where decisions and contracts live

- [CONTEXT.md](CONTEXT.md) is the authoritative glossary. Use its terms—such as **Safe Task Success**, **Staged Mutation**, and **Session Workbook**—in code, tests, documentation, and user-facing behavior.
- [DECISIONS.md](DECISIONS.md) is the evolving decision record. Each consequential decision records its status, evidence, tradeoff, and condition for reconsideration. Start here for *why* the architecture or policy exists.
- [docs/evaluation-contract.md](docs/evaluation-contract.md) and [evaluation/contract.json](evaluation/contract.json) define the baseline corpus, graders, hard gates, and release thresholds. The JSON contract is the machine-readable source of truth.
- [docs/backend-api-contract.md](docs/backend-api-contract.md) defines the API/front-end handoff: lifecycle, endpoints, SSE events, and safe error envelope.
- [docs/submission-evidence.md](docs/submission-evidence.md) defines the evidence required before claiming a release is ready; [docs/live-defense.md](docs/live-defense.md) is the corresponding demonstration runbook.

## Current evaluation boundary

The deterministic baseline tests the `WorkbookSession` contract, including source preservation, authorization, safe tool use, and artifact postconditions. It does not prove that a live LLM will choose the correct tool sequence for every natural-language request. Live-model evaluation must remain separately reproducible and preserve the same deterministic hard gates; an independent LLM judge is advisory only.
