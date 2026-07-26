# Live-defense runbook

Use this runbook only after the release checklist in
[`submission-evidence.md`](submission-evidence.md) is complete. The presenter should
show the generated evidence, not recite unverified claims.

## Opening: outcome and boundary (3 minutes)

State the goal: maximize **Safe Task Success** for reasonable single-workbook requests,
not fluent but unsafe spreadsheet interaction. Point to `DECISIONS.md` for the
framework-free Python boundary, the free-provider adapter, and the fixed evaluation
contract.

## Demonstrate the normal path (8 minutes)

1. Start from the documented clean environment and show `GET /api/health`.
2. Use one property-listings read/query case and one campaign read/query case.
3. Explain the result scope using the canonical terms: List Price per Square Foot,
   Finalized Sale Price, Recorded Campaign Revenue, and Campaign Interval.
4. Show the matching deterministic evaluation rows and safe trace events.

## Demonstrate mutation integrity (8 minutes)

1. Run an insert, update, or delete request against a fresh Session Workbook.
2. Show the exact Stable-ID Staged Mutation and pause for explicit confirmation.
3. Confirm once, download the new artifact, and show its reopened exact-diff result.
4. Show that the source fixture hash is unchanged and that a stale or broad target
   fails closed.

## Defend the consequential choices (7 minutes)

| Likely challenge | Evidence-backed answer |
| --- | --- |
| Why no agent framework? | The assignment forbids it; the tool and orchestration boundary is local Python code, with libraries used only for data handling and HTTP. |
| Why confirmation for every mutation? | Exact Stable-ID confirmation is the simplest visible authorization boundary and is a hard-gate requirement in D-008. |
| Why constrain the model? | The model selects only validated actions; deterministic tools enforce workbook semantics, bounds, and policy. |
| How do you know it works? | Show the exact baseline report, category counts, and any failures. A contract alone is not evidence of success. |
| What would you change? | Use the measured limitation statement from the final report; do not speculate beyond it. |

## Close: limitations and reproducibility (4 minutes)

Run `uv run python scripts/verify_submission.py`, show its JSON report, and state
whether it is release-ready. If it reports a blocker, do not submit or claim a passing
baseline. Point reviewers to the clean-run commands and the full evaluation report.
