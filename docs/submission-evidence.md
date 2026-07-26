# Submission evidence checklist

This checklist turns the assignment brief into verifiable evidence. It is deliberately
not a scorecard: a checked static item does not replace a successful end-to-end run.

## Reproducible commands

From the repository root, run:

```powershell
uv sync
uv run pytest
uv run python scripts/verify_submission.py
```

The final command writes `artifacts/submission-proof.json`. It executes the full deterministic
72-case Baseline Evaluation Corpus and includes the commit, per-workbook and per-operation
outcomes, hard-gate failures, latency, turns, tool calls, and advisory-judge state. Exit code
`0` means all D-007 release thresholds passed; exit code `2` blocks release.

## Evidence matrix

| Assignment requirement | Required proof | Current evidence | Release gate |
| --- | --- | --- | --- |
| Python and custom tools | Dependency/import review plus executable WorkbookSession tests | `pyproject.toml`, backend tests | Workbook tools must be implemented and tested. |
| Free LLM option | Configuration and a safe provider-boundary test | `backend/app/settings.py`, `backend/app/agent_loop.py` | A configured, documented free-provider path must complete the demo. |
| Both supplied workbooks | Separate read/query and mutation cases for each workbook | Executable baseline corpus | 36 runnable cases per workbook. |
| Read, query, insert, modify, delete | Deterministic result/artifact, trace, interaction, and response assertions | `evaluation/baseline.py` and `WorkbookSession` | Every required operation must pass; every mutation requires confirmation. |
| Public README and decision record | Fresh-clone commands and consequential decisions with tradeoffs | `README.md`, `DECISIONS.md` | Commands and links must work from a clean checkout. |
| Live defense | A demonstration sequence plus an evidence-backed answer for each choice | `docs/live-defense.md` | Never claim a result that cannot be reproduced during the call. |

## Final release evidence

Before submission, attach or link all of the following to the release/commit:

1. Clean-environment `uv sync` and full test output.
2. A complete 72-case baseline report with corpus version, commit SHA, raw counts by
   workbook and operation, hard-gate failures, latency, turns, tool calls, and advisory
   judge summary.
3. The two source-workbook hashes and any verified output-artifact hashes.
4. One scripted read/query flow and one insert, update, and delete flow, each showing
   the exact Stable-ID staged diff and explicit confirmation.
5. A short limitations statement based on measured failures, rather than promises of
   future features.

## Current limitation

The baseline is deterministic and model-free: it proves the bounded WorkbookSession contract,
not that a live LLM will select the right tool sequence for every natural-language request. Any
live-model comparison must remain separately reproducible and preserve the deterministic hard
gates; the advisory independent LLM judge is not a release authority.
