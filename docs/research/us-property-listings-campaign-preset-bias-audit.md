# Preset-bias audit: U.S. property listings and campaign user-needs research

**Verdict:** the report is **partly anchored by presets in the repository**, but the bias is concentrated in its solution and scoring recommendations rather than its workbook facts, metric definitions, or legal constraints. Treat the first half as evidence-led domain analysis and the architecture/UX/evaluation sections as hypotheses that still need independent validation.

## Audit method

The report was compared with four kinds of evidence:

1. the assignment brief;
2. the two supplied workbooks;
3. first-party domain sources cited by the report; and
4. repo material that predates the report: `docs/research/agent-from-scratch-research.md`, `README.md`, `.env.example`, the backend configuration, the invoice UI scaffold, and the generated design-system master.

The repo is entirely untracked, so Git history cannot establish authorship or a commit sequence. Filesystem timestamps do establish that the architecture research (July 23) and the scaffold/design presets (July 25) predate the domain report (July 26). Conceptual overlap is therefore evidence of anchoring, although not proof that every repeated recommendation came only from the preset.

## Findings

| Area in the current report | Classification | Evidence of preset influence | Audit judgment |
|---|---|---|---|
| Workbook row counts, status/channel counts, missing values, repeated names, date/name mismatches, Aurora ambiguity, weighted CTR, and ROAS | Evidence-led | These are derived directly from the supplied workbooks and include explicit warnings not to generalize the synthetic sample to the U.S. market (current report lines 23-76, 311-324). | Low preset bias. Retain, with reproducible profiling code or tests as provenance. |
| RESO terminology, campaign formulas, and Fair Housing/privacy constraints | Source-led | The report cites RESO, Google Ads, U.S. Code, DOJ, FTC, HUD, Census, and NAR (lines 49-51, 95-118, 261-276). | Low repo-preset bias. Some material is broader than the assignment, but it is domain-risk framing rather than evidence inherited from the scaffold. |
| Personas and “real user jobs” | Inferred, not observed | The report says users “likely” include buyers, agents, analysts, marketing managers, finance owners, and operations users (lines 122-165), but there are no interviews, search logs, usability tests, grader examples, or stakeholder statements in the repo. | Medium methodological bias. Rename these to **hypothesized user jobs**; do not claim they represent real user needs yet. |
| Typed filter/aggregation AST; no arbitrary Python, SQL, or formulas | Strong preset anchoring | The earlier architecture report already prescribes a structured filter AST and prohibits arbitrary execution (`agent-from-scratch-research.md` lines 48-51 and 66). The current report repeats this at lines 169 and 189. The assignment requires custom tools but does not prescribe an AST or forbid model-generated formulas. | Technically defensible, but not independently established by this user-needs research. Mark it as an architecture candidate to validate against coverage and implementation time. |
| Staged diffs, explicit confirmation, unchanged original, verified new artifact, append-only trace | Strong preset anchoring | These appear before the domain report in `agent-from-scratch-research.md` lines 36-43, 67-68, 82-84, 94, 118-119; `README.md` lines 9-10 and 37-38; `.env.example` line 5; backend config/tests; and the invoice UI. The current report repeats them at lines 19, 132, 185-186, 236-244, 257-258, 282-291, 345, 348, and 375-376. The task asks for insert/modify/delete but does not require a copy-only workflow or confirmation for every write. | High solution anchoring. Safety supports confirmation for destructive or broad operations, but confirmation for every insert/update and never overwriting the input may add user friction and should be tested rather than declared correct. Line 376 is circular: “the current architecture correctly proposes” presupposes the answer. |
| Evaluation-first framing, safe-success metrics, trace-as-authority, security cases | Strong preset anchoring | The prior report makes deterministic fixture evals its central decision and defines safe success, mutation precision/recall, traces, and nearly the same case categories (`agent-from-scratch-research.md` lines 3, 15, 96-123, 138-166, 181-193). The current report repeats this at lines 21, 278-336, and 340-381. | Evaluation is excellent engineering practice and useful for the live defense, but this report overstates it as a discovered user need or proven scoring lever. Separate “quality assurance strategy” from “user-needs evidence.” |
| “60-80 cases,” 25/25/15/15 split, and 40/20/15/15/10 scorecard | Unsupported local hypothesis | The assignment explicitly contains no numeric rubric. The current report acknowledges this at line 11 and labels the scorecard non-official at line 326. No primary source establishes these exact counts or weights. | High uncertainty, transparently labeled. Use these numbers only as planning budgets, not evidence about the grader. |
| Answer-first result, visible scope, evidence, formulas, caveats, and next action | Mixed | The assignment rewards making answers easier, and the domain data has real ambiguity. However, the rigid six-part contract at lines 209-220 also fits the existing data-dense dashboard/tool-trace scaffold. | Directionally sound but over-prescriptive. Simple lookups should not always show formulas or a next action. Validate progressive disclosure with task-based usability checks. |
| Interface implications: tables, KPI summaries, charts, filter chips, collapsible trace | Moderate preset anchoring | The current report explicitly observes the invoice scaffold (lines 246-259). The existing UI already displays raw tool calls, staged changes, and confirmation; the design master prescribes a data-dense dashboard, charts/widgets, KPI cards, and tables. | This section is a critique/adaptation of the preset, not independent user research. Keep it separate from domain findings and compare against at least one lower-density conversational alternative. |
| Invoice sample content | Corrective use of a preset | The current report says to replace the invoice content with the actual schemas (lines 248-251). | Not harmful bias; it correctly identifies irrelevant scaffold content. |
| NVIDIA provider, React/shadcn stack, purple/pink visual theme, “Cybersecurity Platform” category | No meaningful propagation into the report | These are present in `.env.example`, backend settings, README, frontend dependencies, and the design master, but the report does not recommend a provider, frontend framework, color palette, or cybersecurity positioning. | No material preset bias detected in the report on these choices. |

## What the assignment actually fixes

The brief fixes only these product constraints: Python; two named Excel datasets; custom tools built without agent frameworks; read/query/insert/modify/delete; reasonable natural-language requests; a free LLM option; a public repo with README and decisions; and a live defense. It says easier answers earn a higher score, but supplies no personas, scenarios, scoring weights, UI pattern, confirmation rule, evaluation size, or artifact policy.

Therefore the report should distinguish:

- **Required:** Python, framework-free custom tools, both workbook domains, CRUD, natural language, free LLM, documented decisions.
- **Observed:** workbook schema/content and reproducible derived statistics.
- **Externally constrained:** domain terminology, metric semantics, housing-law/privacy boundaries.
- **Hypothesized:** personas, likely questions, answer layout, evaluation quantities, score weights.
- **Inherited architecture:** typed AST, staged changes, confirmation gates, traces, output copies, eval-first workflow.

## Recommended de-biasing changes

1. Add a provenance tag to every major recommendation: `brief`, `workbook`, `primary source`, `user evidence`, or `architecture hypothesis`.
2. Rename “Real user jobs” to “Hypothesized user jobs from the supplied schemas” until interviews, grader examples, or usability sessions exist.
3. Split the report after the domain findings. Put AST design, mutation flow, traces, and eval mechanics in `DECISIONS.md` or an architecture note, not in user-needs findings.
4. Replace absolute wording such as “the strongest submission will” and “correctly proposes” with testable hypotheses and explicit disconfirming evidence.
5. Test at least two interaction policies: confirmation for every write versus risk-based confirmation; and dense analytical output versus concise answer with progressive disclosure.
6. Treat the numeric scorecard and 60-80-case target as planning defaults. Update them only from actual grader feedback, observed failures, or a measured risk model.
7. Preserve the verified workbook facts, formula rules, ambiguity findings, and legal boundaries; these are the least preset-dependent parts of the report.

## Bottom line

The current research is usable, but it is not a clean-room study of users. It combines domain research with an already-selected product architecture. That combination makes the recommendations coherent, yet creates confirmation bias: the report often explains why the existing staged, deterministic, evaluation-heavy design is good instead of neutrally comparing it with alternatives. The appropriate correction is not to discard the report; it is to label provenance, separate findings from design decisions, and validate the inherited choices with user tasks and competing prototypes.
