# Backend Goals and Evaluation Charter

**Status:** Goal portfolio approved on 2026-07-26; thresholds and implementation policies remain open Wayfinder decisions.

## Destination

Deliver a public-repository-ready, framework-free Python backend that handles reasonable natural-language read, query, insert, modify, and delete requests across both supplied workbooks, maximizes Safe Task Success on deterministic evaluations, records consequential choices in `DECISIONS.md`, and is defensible in the assignment's 30-minute live review. Frontend work is outside this effort.

## Evidence and provenance

- **Brief:** `docs/task-reqs/Task- Junior AI Engineer.pdf` fixes the language, framework, model-cost, workbook, CRUD, public-repository, documentation, and live-review constraints. It provides no numeric rubric.
- **Workbook evidence and domain sources:** `docs/research/us-property-listings-campaign-user-needs.md` supplies reproducible workbook facts, semantic traps, formulas, ambiguity cases, safety constraints, and hypothesized user jobs.
- **Bias control:** `docs/research/us-property-listings-campaign-preset-bias-audit.md` distinguishes assignment requirements and observed facts from inherited architecture and scoring hypotheses.
- **Architecture hypotheses:** `docs/research/agent-from-scratch-research.md` proposes a constrained custom agent loop, narrow tools, mutation staging, and deterministic evaluations. These are candidates to validate, not settled requirements.

## North-star measure

**Safe Task Success** is the proportion and raw count of evaluation cases in which the required answer or workbook outcome is correct and no forbidden action or safety condition occurs.

The following are hard gates. A case that violates one cannot earn positive comparative credit:

1. Assignment compliance.
2. Correct answer or workbook artifact.
3. No unintended or unauthorized workbook change.
4. No forbidden tool, path, shell, or network action.

After the gates pass, compare approaches by coverage, user effort, robustness, latency, and implementation complexity. Report raw numerators and denominators and category-level results; do not hide failures inside one weighted average.

## Outcome goals

### G1 - Assignment compliance

Build the agent and tool layer from scratch in Python, use no pre-built agent/tool framework, support a free LLM option, operate on both supplied workbooks, and cover read, query, insert, modify, and delete.

**Proof:** dependency and import inspection; configuration evidence for a free model path; automated cases exercising every required operation against each workbook; public-repository checklist covering `README.md` and `DECISIONS.md`.

### G2 - Semantic correctness

Use the intended workbook, sheet, rows, columns, types, date rule, aggregation formula, and null behavior; resolve material ambiguity; do not invent unavailable facts.

**Proof:** deterministic fact and formula graders; golden workbook checks; ambiguity cases such as Aurora, repeated campaign names, campaign period meaning, weighted campaign metrics, and Pending sale-price semantics; answer assertions for scope and limitations.

### G3 - Reasonable-request coverage

Handle representative property and campaign jobs across lookup, filtering, sorting, projection, comparison, aggregation, derived metrics, data-quality questions, follow-ups, and CRUD—not only hand-picked demonstrations.

**Proof:** a versioned request matrix with category, difficulty, and workbook tags; raw Safe Task Success by category; held-out paraphrases; explicit unsupported-request behavior.

### G4 - Mutation integrity

Apply exactly the authorized insert, modify, or delete operation and no collateral changes; make ambiguous or broad matches fail safely; verify committed workbook postconditions.

**Proof:** reopened-artifact graders; mutation precision and recall; input/output hashes; zero-, one-, and many-match cases; authorization and rejection cases; workbook-fidelity comparisons outside the allowed change region.

### G5 - Low user effort

Return the decisive result and interpreted scope directly, ask only clarifications that materially affect the answer, and make errors or unsupported requests recoverable without requiring workbook jargon.

**Proof:** deterministic response-contract assertions where possible; turns-to-resolution, clarification count, and successful-recovery measures; a small human-reviewed set for usefulness and clarity. Backend responses must expose enough structured evidence for the separate frontend task without prescribing its visual design.

### G6 - Robustness and defensibility

Fail closed on malformed model output, invalid tools or fields, resource limits, workbook errors, and untrusted cell content; retain enough reproducible evidence to explain every consequential implementation choice during the live review.

**Proof:** fault-injection and policy cases; deterministic traces with prompt/model/tool versions and timings; regression reports; `DECISIONS.md` entries containing evidence, tradeoffs, and reconsideration conditions; a reproducible demo/evaluation command documented in `README.md`.

## Evaluation principles

- The workbook artifact and deterministic tool trace outrank fluent prose.
- Expected numeric values are stored at full precision and formatted only at presentation time.
- Each feature needs success, ambiguity, empty/error, and safety coverage where applicable.
- Evaluation quantities and score weights are planning hypotheses until grader evidence exists.
- Architecture complexity must earn its place by improving the fixed corpus without weakening a hard gate.

## Open decisions for Wayfinder

1. Evaluation corpus scope, case schema, graders, and release thresholds.
2. Supported request semantics and ambiguity defaults.
3. Deterministic workbook tool contracts and query representation.
4. Mutation authorization, artifact, and verification policy.
5. Agent loop, model boundary, and free-provider baseline.
6. Backend API, session state, and frontend handoff contract.
7. Trace, resource-limit, prompt-injection, and error-recovery policy.
8. Documentation and live-defense evidence package.

