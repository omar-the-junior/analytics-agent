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

## What I would do differently with more time

This section will be completed as implementation and evaluation expose limits that cannot responsibly be addressed within the assignment window.
