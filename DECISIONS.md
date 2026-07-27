# Decisions

This is the evolving decision record for the workbook-agent backend. It captures choices, evidence, tradeoffs, and conditions for reconsideration so every consequential decision can be defended during the assignment's live review.

## D-001: Target a submission-ready backend

- **Status:** Accepted on 2026-07-26
- **Decision:** Deliver a public-repository-ready, framework-free Python backend that handles reasonable natural-language read, query, insert, modify, and delete requests across both supplied workbooks. It must be evaluated, record consequential choices here, and be defensible in the 30-minute review. Frontend work is outside this backend effort.
- **Evidence:** The assignment requires Python, custom tools built without an agent framework, both supplied Excel files, all five operation classes, a public GitHub repository, a `README.md`, a `DECISIONS.md`, and a live defense. The user explicitly assigned frontend implementation to a separate Codex task.
- **Tradeoff:** This is broader than producing an architecture specification, but it prevents planning artifacts from becoming a substitute for the evaluated submission the assignment asks for.
- **Reconsider if:** The assignment scope or submission deadline changes.

## D-002: Optimize for Safe Task Success

- **Status:** Accepted on 2026-07-26
- **Decision:** Use Safe Task Success across a representative natural-language CRUD evaluation corpus as the backend's north-star. Assignment compliance and workbook integrity are constraints; when approaches perform equally, prefer lower user effort, latency, and implementation complexity.
- **Evidence:** The brief requires broad handling of reasonable requests and explicitly says easier access to answers earns a higher score. The user-needs research shows that workbook correctness, formula semantics, stable row identity, mutation control, and honest limitations are necessary for trustworthy outcomes. The assignment publishes no numeric scoring rubric, so any internal weights remain hypotheses rather than grader facts.
- **Tradeoff:** A single north-star makes comparisons possible but can hide category-specific regressions. Reports must therefore retain raw case counts and results by operation, workbook, ambiguity, and safety category.
- **Reconsider if:** Grader feedback supplies an official rubric, or the evaluation corpus proves unrepresentative of reasonable requests.

## D-003: Apply hard gates before comparative scoring

- **Status:** Accepted on 2026-07-26
- **Decision:** An evaluation case is ineligible for positive comparative scoring if it violates assignment compliance, produces an incorrect answer or workbook artifact, makes an unintended or unauthorized workbook change, or invokes a forbidden tool, path, shell, or network action. Coverage, user effort, robustness, latency, and complexity distinguish approaches only after these gates pass.
- **Evidence:** A fluent or fast response cannot compensate for corrupt workbook output, an incorrect answer, or violation of the assignment's framework and language constraints. Separating gates from weighted dimensions also prevents a numeric average from concealing a catastrophic failure.
- **Tradeoff:** Gate-first scoring can make incremental improvements invisible while a case still fails. The evaluation report must retain diagnostic sub-results so near-misses remain useful during development.
- **Not decided here:** Whether every mutation requires confirmation and whether every committed workbook must be a new copy. Those are separate product and safety decisions.
- **Reconsider if:** A hard gate is found to combine independent failure modes that need separate release policies.

## D-004: Use outcome goals as the implementation starting point

- **Status:** Accepted on 2026-07-26
- **Decision:** Organize backend work around six observable outcomes: assignment compliance, semantic correctness, reasonable-request coverage, mutation integrity, low user effort, and robustness/defensibility. Tool classes, agent loops, providers, prompts, and endpoints are candidate means rather than goals.
- **Evidence:** The assignment judges what the assistant can do and how easily users obtain answers. The preset-bias audit shows that several existing architecture recommendations predate the domain research, so treating those components as goals would conceal whether simpler or different approaches perform better.
- **Tradeoff:** Outcome goals leave more design uncertainty at the start and require a real evaluation contract. They also make it easier to discard code that does not improve user-visible or safety outcomes.
- **Reconsider if:** A mandatory submission artifact or operational constraint cannot be represented as evidence under one of the six outcomes.

## D-005: Put the evaluation contract before architecture

- **Status:** Accepted on 2026-07-26
- **Decision:** Resolve the evaluation corpus contract, graders, and release thresholds before choosing the workbook tool grammar, agent loop, or model baseline. Resolve workbook semantics and ambiguity defaults as an independent initial-frontier decision so it can proceed without waiting on architecture.
- **Evidence:** The approved goals are outcome-based, and the research explicitly labels the proposed AST, mutation flow, evaluation size, and score weights as hypotheses. A fixed evaluation contract is needed to compare those hypotheses without moving the target after seeing results. Workbook semantics come from the supplied artifacts and domain evidence, so they can be sharpened independently.
- **Tradeoff:** This delays visible agent behavior, but the first frontier still produces executable graders and a semantic contract rather than paper-only planning. It reduces the larger risk of optimizing a demo that does not represent the required request space.
- **Reconsider if:** A thin end-to-end spike is necessary to discover what the evaluation harness must observe; such a spike remains a prototype, not the promoted architecture.

## D-008: Use a transactional WorkbookSession tool boundary

- **Status:** Accepted on 2026-07-26
- **Decision:** Expose four model-facing contracts: `describe_workbook`, `query_workbook`, `stage_mutation`, and `commit_mutation`. A chat receives an isolated Session Workbook, and all its queries and mutations use that copy while supplied source workbooks remain immutable. `WorkbookSession` validates an allowlisted JSON query AST and mutation schema before calling pandas for calculations or openpyxl for commits. Query results distinguish `ok`, `needs_clarification`, and `rejected`; approved derived metrics use `calculation` and `calculation_source: tool_computed`, never `formula`. `spreadsheet_formula` is reserved for an actual Excel expression and is never recalculated by the backend.
- **Mutation policy:** Every mutation targets a Stable ID, stages an exact diff, requires explicit confirmation, and is source-version-bound by hash. `commit_mutation` writes only a candidate version, reopens it, semantically compares normalized relevant cells against the staged diff, and advances the active version only after verification. It retains the active plus four prior versions. A failed candidate leaves the prior active version unchanged and returns structured expected-versus-actual changes.
- **Evidence:** The interactive prototype at `prototypes/workbook_session_contract/` was manually accepted after exercising queries, ambiguity and rejection behavior, confirmation gating, version advancement, transactional update/insert/delete commits, stale-source rejection, and formula preservation. The assignment requires custom Python tools and a defensible CRUD design; D-006 and D-007 require Stable IDs, confirmation, verified artifacts, semantic correctness, and deterministic evidence.
- **Tradeoff:** A restricted contract and session-local version history exclude arbitrary formulas, paths, code, joins, and persistent editing. They add validation and artifact bookkeeping, but make the safety boundary and live-review explanation concrete.
- **Reconsider if:** Baseline evaluation cases reveal a reasonable request the allowlisted AST cannot represent, or artifact-fidelity checks show openpyxl cannot safely preserve a supplied workbook.

## D-007: Adopt a fixed, gate-first baseline evaluation contract

- **Status:** Accepted on 2026-07-26
- **Decision:** Use a version-controlled 72-case baseline corpus: 36 cases each for the real-estate-listings and marketing-campaign workbooks. Each workbook has 20 read/query cases; 2 insert, 3 update, and 3 delete cases; and 2 cases each for ambiguity, safety, robustness/recovery, and follow-up behavior. A Baseline Release is a single full-corpus run with zero hard-gate failures, at least 65/72 Safe Task Success cases, at least 30/36 per workbook, at least 16/20 reads per workbook, all 16 mutation cases passing, at least 6/8 cross-cutting cases per workbook, and all safety cases passing.
- **Grading:** Every applicable deterministic result/artifact, semantic-trace, interaction-policy, and response-contract assertion must pass. Mutation artifacts are reopened and compared as exact authorized cell diffs; original fixtures remain unchanged. Tool traces check required and forbidden semantic events, not an exact call sequence. Values are exact except derived ratios, which use an absolute tolerance no greater than 0.000001; display formatting is assessed separately.
- **LLM judge:** An advisory, fixed-rubric LLM judge must use a different model from the evaluated agent. It records pass/needs-improvement and a rationale for directness, scope clarity, necessary-only interaction, and recovery behavior. It cannot alter Safe Task Success; low results create explicit improvement follow-ups. Exact judge-model selection is deferred to the agent-model-boundary decision.
- **Evidence:** The assignment requires reasonable natural-language CRUD over both workbooks and a defensible public submission, but publishes no numeric rubric. The approved backend goals require deterministic evidence, separate workbook reporting, mutation integrity, low user effort, and reproducibility. The accepted contract is captured in [`evaluation/contract.json`](evaluation/contract.json).
- **Tradeoff:** The thresholds and case allocation are internal planning choices, not evidence of the evaluator's scoring formula. A one-run policy accepts free-model rate-limit and variance constraints in exchange for practical repeatability within the assignment window.
- **Reconsider if:** Grader feedback, measured failure patterns, or reliable capacity for repeated runs shows that the corpus mix, threshold, one-run policy, or advisory-judge role is no longer representative.

## D-006: Establish the workbook semantic and ambiguity contract

- **Status:** Accepted on 2026-07-26
- **Decision:** Every tool, prompt, answer, and evaluation uses the following contract. Monetary values are USD. Pending `Sale Price` is a Recorded Sale Price with unknown business meaning: it can be displayed, filtered, and compared, but finalized-sale measures use only `Listing Status = Sold`; Pending values that materially affect an answer are neutrally labeled and their exclusion is stated. `Revenue Generated` is Recorded Campaign Revenue, not profit, collected cash, or a defined attribution measure. `Conversions` is a source-provided count with an unverified event definition and cross-channel consistency. Grouped CTR, conversion rate, CPC, CPA, and ROAS use totals-based formulas; zero denominators produce an unavailable metric. A Campaign Interval runs inclusively from start through end; bare period requests require a start/end/overlap clarification, while “active,” “running,” and “during” mean overlap. “Price per square foot” defaults to List Price divided by Square Footage; finalized-sale price per square foot is explicit and Sold-only. “Available” means Active, “typical price” means median, and “best” campaign/channel requires a KPI unless supplied by context. Ambiguous city-only requests require state disambiguation unless a small read-only result is grouped by state. Nulls are never imputed; non-matching nulls are excluded and material exclusions disclosed. Listing ID and Campaign ID are Stable IDs; mutations must resolve to exact IDs, be staged with exact diffs, explicitly confirmed, and committed to a verified new artifact. Fair Housing steering and demographic-proxy requests are refused; unsupported neighborhood, amenity, or profit claims are declined with neutral source-backed alternatives.
- **Evidence:** The supplied workbook schemas and values, including Pending listings with `Sale Price` values; the assignment's two-workbook scope; the product research; and the user's explicit decisions in the Wayfinder interview.
- **Tradeoff:** Explicit qualifiers and occasional clarifications add response text and turns, but prevent unsupported claims, unsafe mutations, misleading cross-channel comparisons, and invalid finalized-sale analysis.
- **Reconsider if:** The source workbooks receive authoritative field definitions or verified replacement data that changes a stated ambiguity.

## D-008: Require user confirmation for every workbook mutation

- **Status:** Accepted on 2026-07-26
- **Decision:** Every insert, update, and delete first becomes a Staged Mutation with an exact Stable-ID diff. It may commit only after an explicit user confirmation for that unchanged stage. A commit never overwrites the source workbook; it creates a new output artifact, reopens it, and verifies the authorized cell diff exactly. Zero or multiple target matches fail closed.
- **Evidence:** The assignment requires CRUD and rewards low effort, but it does not mandate a no-confirmation path. The accepted semantic contract requires exact IDs, staged changes, explicit confirmation, and a verified new artifact. The baseline evaluation contract treats every mutation failure and unauthorized/collateral change as a release-blocking hard-gate failure. The user chose a user-in-the-loop policy and ruled risk-based confirmation out of scope for this effort.
- **Tradeoff:** Every mutation costs one confirmation turn, including a low-risk insert. That friction is intentional: it makes the authorization boundary legible, avoids accidental writes, and keeps the initial implementation and live-defense story simple.
- **Not decided here:** Batch-confirmation ergonomics, confirmation expiry, and any risk-tiered exception. They are out of scope unless a future evaluation demonstrates material user-effort harm without a safety regression.
- **Reconsider if:** Baseline evaluation or live-review feedback shows that the universal confirmation turn materially prevents reasonable-request completion, and a replacement policy preserves exact authorization and zero unintended changes.

## D-009: Use a bounded NVIDIA-backed action loop

- **Status:** Accepted on 2026-07-26
- **Decision:** The baseline agent uses the hosted free model `nvidia/nemotron-3-nano-30b-a3b` through a provider-neutral `ModelClient` with one NVIDIA OpenAI-compatible adapter. Each model iteration returns a Pydantic-validated JSON action: either a final answer or an ordered batch of tool calls. The deterministic tool boundary remains authoritative. Tool calls in a batch execute serially in declared order; each result is recorded and returned before the next model iteration. The loop permits at most six model iterations and has no separate tool-call cap. One malformed or invalid action gets a repair prompt; a second ends the run. Recoverable tool errors return to the model while iteration budget remains, while policy rejections and required clarifications stop directly.
- **Evidence:** The assignment permits hosted free LLMs and requires custom Python tools with no agent framework. The selected NVIDIA API is OpenAI-compatible. The baseline evaluation contract requires deterministic traces, safe failure behavior, and defensible limits. The user chose the provider, interface boundary, JSON action protocol, serial batches, six-iteration limit, and repair behavior during the Wayfinder interview.
- **Tradeoff:** A JSON protocol and serial execution may be less feature-rich or fast than provider-native tool calls and parallel reads. The small adapter and explicit traces make the system easier to fake in tests, swap later, and explain during the live review.
- **Reconsider if:** The 72-case baseline shows a reasonable request cannot complete within six model iterations, malformed-output recovery materially lowers Safe Task Success, or measured read-only parallelism earns its added complexity without weakening determinism.

## D-010: Enforce a single-workbook, bounded execution policy

- **Status:** Accepted on 2026-07-26
- **Decision:** Each conversation binds to exactly one Session Workbook when it begins; the model cannot select another workbook, path, shell command, or network tool. The agent may invoke only `describe_workbook`, `query_workbook`, `stage_mutation`, and `commit_mutation`. Initial workload limits are a 5 MiB workbook, 10,000 populated rows, 50 columns, 500,000 populated cells, 100 returned detail rows, 25 returned columns, 32 KiB serialized tool output, 64 KiB model action, six model iterations, one malformed-action repair, a 30-second model-call timeout, and a 210-second run timeout. This retains D-009's deliberate absence of a separate tool-call count cap.
- **Trace and security:** Record ordered, schema-versioned semantic events with a run identifier, iteration, safe policy/budget outcome, tool name/status, and terminal outcome. Never trace secrets, API keys, raw prompts, workbook values, filesystem paths, or raw provider errors. Treat user input, workbook content, and tool results as untrusted data rather than instructions.
- **Recovery:** Clarification and policy rejection stop immediately. One malformed model action gets a repair; recoverable tool errors return to the model while time remains; provider, budget, and internal failures stop safely. Candidate verification failures leave the active workbook version unchanged.
- **Error taxonomy:** `invalid_model_action`, `tool_validation_error`, `policy_rejected`, `clarification_required`, `recoverable_tool_error`, `provider_error`, `budget_exhausted`, `candidate_verification_failed`, and `internal_error`.
- **Evidence:** Both supplied workbooks have 1,000 data rows and 11 columns, and the agent's hard gates prohibit forbidden tool, path, shell, and network actions. The user explicitly chose the one-workbook-per-conversation boundary.
- **Tradeoff:** Cross-workbook comparisons and larger data artifacts are rejected in the baseline. This reduces feature breadth but makes the Session Workbook boundary, prompt-injection defense, resource behavior, and live-review evidence deterministic.
- **Reconsider if:** Baseline evaluation shows a reasonable in-scope request cannot complete within these bounds, or a carefully designed multi-workbook feature can preserve equally strong session isolation and deterministic evaluation.

## D-011: Use a backend-owned asynchronous frontend contract

- **Status:** Accepted on 2026-07-26
- **Decision:** The frontend starts a backend-owned run and receives its progress through a replayable SSE stream. `WorkbookSession` state and its bounded version history live only in backend memory for the API-process lifetime. A Staged Mutation pauses a run in `confirmation_required`; only a dedicated endpoint carrying the exact `stage_id` can authorize its commit. The frontend can cancel an active run, which terminates safely without a commit; verified output artifacts have no undo operation. Artifact references are opaque and session-scoped, with a separate download endpoint. Events have monotonic IDs and a bounded replay window. Failures use a user-safe structured envelope with `code`, `message`, `retryable`, `run_id`, and a correlation ID; raw provider, filesystem, and workbook internals stay server-side.
- **Evidence:** The existing SPA is intentionally demo-only, whereas D-008 requires exact Staged Mutation authorization and D-010 requires bounded, redacted execution. The user selected SSE, process-lifetime sessions, dedicated confirmation, active-run-only cancellation, opaque artifacts, structured errors, and reconnect replay during the Wayfinder interview.
- **Tradeoff:** SSE and a replay buffer add endpoint and lifecycle work, while process-local sessions do not survive restarts. In return, the separately developed frontend can render progress and recover from reconnects without receiving orchestration authority or sensitive backend details.
- **Reconsider if:** Evaluation shows process restarts materially harm a reasonable in-scope workflow, or event-stream measurements show that the replay window fails to provide reliable frontend recovery.

## D-012: Render workbook data only from validated structured events

- **Status:** Accepted on 2026-07-27
- **Decision:** Treat the validated `workbook_result` event as the browser's only source of truth for complete user-requested Session Workbook data. The frontend validates and renders typed table, selection, and metric results; assistant Markdown is explanatory CommonMark prose and is never parsed to recover workbook rows, Stable IDs, or calculations. After a successful query, it leads with the direct answer copied exactly from canonical fields in that same result: metric value and column; selection value, column, and atomically paired Stable ID; or table row count and truncation status. It may then refer the user to the complete displayed result, but never copies arbitrary table cells or reconstructs rows, rankings, calculations, or ID/value pairs. `activity` is an Inspectable Execution Trace: concise agent-step labels, approved tool inputs, and bounded output summaries, never workbook result rows. A `confirmation_required` event carries a typed Staged Mutation preview that is rendered as a table both in the conversation and in the confirmation dialog; Markdown may only say it is staged and invite review and confirmation, never recreate the preview. The unchanged `stage_id` remains the sole Mutation Authorization target.
- **Evidence:** A model can identify a maximum value while associating it with the Stable ID from an adjacent worksheet row when it reads and recomposes multiple records itself. Binding values, rows, and Stable IDs in one WorkbookSession result eliminates that failure mode. The structured-query contract, browser tests, and fixed Baseline Evaluation Corpus now cover canonical extrema, ranked projected truncation, unsupported grouped-metric rejection, and typed mutation previews.
- **Tradeoff:** The browser owns runtime validation and reusable presentation components, and it deliberately ignores malformed structured events instead of attempting a best-effort display. This adds a client-side contract-maintenance step whenever a new QueryResult kind is approved, but prevents model-authored Markdown from becoming an unverified data channel.
- **Reconsider if:** A future approved QueryResult or Staged Mutation preview kind requires a materially different interaction model, or contract-versioning evidence shows that strict client validation prevents compatible browser upgrades.

## What I would do differently with more time

This section will be completed as implementation and evaluation expose limits that cannot responsibly be addressed within the assignment window.
