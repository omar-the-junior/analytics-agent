# Structured Query and Presentation Specification

**Status:** backend contract implemented; frontend presentation pending  
**Owner:** any backend or frontend agent working on deterministic workbook results  
**Last updated:** 2026-07-27

## Purpose

Make the **WorkbookSession** responsible for selecting, calculating, and binding workbook data. The model may choose a validated query, but it must not reconstruct rows, pair values with adjacent Stable IDs, calculate metrics itself, or generate data tables from memory.

The browser must render user-requested workbook data and Staged Mutation previews from structured backend data. Assistant Markdown remains explanatory prose only.

## Problem

The current `query_workbook` rows operation returns worksheet-order records and the UI receives only final assistant prose. For requests such as “which listing has the highest price?”, the model can correctly identify the value but attach the Stable ID from an adjacent row. The existing `min`/`max` selection extension removes that particular failure mode, but the broader query and presentation contract is still incomplete.

## Non-goals

- Arbitrary Python, pandas expressions, formulas, SQL, workbook paths, or uploads.
- A tool per natural-language phrase.
- Model-authored values, row IDs, calculations, or Markdown tables as the source of truth.
- Changing mutation authorization: every Staged Mutation still requires explicit confirmation of its unchanged `stage_id`.
- Exposing workbook rows through `activity` events.

## Design principles

1. Keep `WorkbookSession` as the deep module and the only seam for workbook data access, calculation, selection, and presentation shape.
2. Prefer one bounded declarative `query_workbook` interface over multiple shallow “top rows”, “group”, or “show row” tools.
3. Return a Stable ID whenever returned data represents workbook rows. Never infer identity from row position or an adjacent array element.
4. Define deterministic ordering: when requested values tie, break ties by Stable ID ascending.
5. Only repository-owned code computes metrics. Use approved named calculations rather than arbitrary expressions.
6. The UI renders typed tables; the model supplies a concise explanation only.

## Query contract

`query_workbook` remains the model-facing read tool. It accepts the existing `filters`, `aggregate`, `column`, and `limit` fields during migration, then grows to this validated shape.

```json
{
  "filters": [
    {"column": "Listing Status", "operator": "eq", "value": "Active"},
    {"column": "List Price", "operator": "gte", "value": 500000}
  ],
  "select": ["Listing ID", "Address", "List Price"],
  "order_by": [
    {"column": "List Price", "direction": "desc"}
  ],
  "limit": 10,
  "calculation": {
    "kind": "rows"
  },
  "presentation": "table"
}
```

### Filters

Support only explicitly allowlisted operators:

| Operator | Intended use |
| --- | --- |
| `eq`, `in` | exact categorical and Stable ID lookup |
| `lt`, `lte`, `gt`, `gte`, `between` | numeric and date ranges |
| `is_null`, `not_null` | missing-value questions |
| `overlaps` | Campaign Interval queries only; inclusive start/end overlap |

Column existence, type compatibility, row limits, City Scope, Fair Housing rules, and the source workbook binding remain backend-enforced. `select` must either contain the workbook’s Stable ID or the backend adds it automatically.

### Ordering and selection

`order_by` may name validated sortable columns. Apply it after filters and before `limit`; append Stable ID ascending as the final deterministic tie-break.

`calculation.kind` starts with:

| Kind | Result |
| --- | --- |
| `rows` | filtered/projected rows |
| `count`, `sum`, `mean`, `median` | one tool-computed metric |
| `min`, `max` | selected value plus the complete matching row and Stable ID |
| `grouped_count`, `grouped_sum` | tool-computed table grouped by validated columns |
| approved derived metric | named domain metric only, such as List Price per Square Foot |

Do not add `mean`, `median`, grouped metrics, or derived metrics until their domain semantics and tests are specified. Campaign ratios must remain **Totals-Based Campaign Metrics**; a bare “best campaign/channel” still needs an explicit Campaign KPI.

### Result contract

Return a normalized, JSON-safe `QueryResult`, never an implicit row order:

```json
{
  "kind": "table",
  "columns": ["Listing ID", "Address", "List Price"],
  "rows": [["LST-5017", "123 Example Ave", 850000]],
  "row_count": 1,
  "truncated": false,
  "stable_id_field": "Listing ID",
  "calculation_source": "tool_computed"
}
```

For `min` and `max`, include the canonical selection fields as well:

```json
{
  "kind": "selection",
  "column": "List Price",
  "value": 850000,
  "stable_id_field": "Listing ID",
  "stable_id": "LST-5017",
  "row": {"Listing ID": "LST-5017", "List Price": 850000},
  "calculation_source": "tool_computed"
}
```

An empty result is a valid `table` with empty `rows`; an unavailable metric uses `unavailable: true` and an explicit reason. Do not substitute zero or invent a value.

## Tool description and system-prompt requirements

Update `MODEL_TOOL_DEFINITIONS` so `query_workbook` states:

> Read, filter, select, order, and compute approved metrics from the bound Session Workbook only. For highest/lowest or ranked results, use the query selection and ordering fields. The tool returns Stable IDs and result rows atomically; do not re-pair values, rows, or IDs yourself.

Add the following behavioral rules to `ACTION_INSTRUCTIONS` and the runtime system prompt:

1. Use `query_workbook` whenever workbook data is needed.
2. For highest/lowest, use `min`/`max`; for ranked lists, use `order_by` plus `limit`.
3. Quote values, Stable IDs, and rows exactly as returned by a tool; never calculate, sort, match, or construct them in prose.
4. When a query result is meant for the user, request its supported presentation mode; explain its scope and relevant domain caveats in prose.
5. Never embed a workbook table in Markdown when a structured result is available.
6. For changes, call `stage_mutation` once, describe the exact Staged Mutation, and never commit it.

## Browser presentation contract

Add a new SSE event type named `workbook_result`. It is **not** an `activity` event. It may contain only a validated `QueryResult` generated by the user’s approved query in the current Session Workbook.

```json
{
  "event_id": 42,
  "run_id": "opaque-run-id",
  "type": "workbook_result",
  "data": {"result": {"kind": "table", "columns": [], "rows": []}}
}
```

The event must not include model prompts, tool arguments, raw provider responses, filesystem paths, or hidden reasoning. Update `docs/backend-api-contract.md`, `StreamEvent`, API tests, and frontend event parsing together. Keep the existing rule that `activity` never contains workbook data.

The frontend renders `workbook_result` with a reusable table component:

- First row: `columns` as headers.
- Remaining rows: `rows` in the same column order.
- Use horizontal scrolling for wide tables, format values by type, and show a clear empty state.
- Display `row_count` and `truncated`; do not pretend a truncated result is the entire workbook.
- Render selection results as a one-row table plus the computed metric.
- Never parse assistant Markdown to recover data.

## Staged Mutation preview contract

Retain `confirmation_required`, but replace the generic `before`/`after` JSON block with an explicit typed payload:

```json
{
  "operation": "update",
  "stable_id_field": "Listing ID",
  "stable_id": "LST-5001",
  "preview": {
    "kind": "field_diff",
    "columns": ["Field", "Before", "After"],
    "rows": [["List Price", 351000, 351001]]
  }
}
```

Presentation rules:

| Operation | UI table |
| --- | --- |
| `update` | `Field`, `Before`, `After`; only changed fields, with visual change emphasis |
| `insert` | one complete `After` row using workbook column headers |
| `delete` | one complete `Before` row using workbook column headers |

The confirmation dialog must reference the same preview and exact `stage_id`. It cannot derive an authorization target from display text.

## Implementation TODO

- [x] Add deterministic `min`/`max` selection that binds value, full row, and Stable ID; add a regression test for maximum List Price.
- [x] Finalize the `QueryRequest` migration strategy: legacy `filters` mapping and `aggregate`/`column` remain accepted; new callers use predicate lists and `calculation`.
- [x] Add validated filter operators, projection, deterministic `order_by`, and `limit` behavior to `WorkbookSession`.
- [x] Implement normalized `QueryResult` models and rejection/unavailable result shapes.
- [x] Specify and implement the currently approved calculations (`rows`, `count`, `sum`, `min`, `max`) with deterministic tests. Mean, median, grouped, and derived metrics remain deliberately unsupported until their domain semantics are added.
- [x] Add an internal result-publication seam from `WorkbookToolExecutor` to `ApiRuntime`; do not put rows in trace events.
- [x] Add the `workbook_result` SSE event and update the backend API contract and event schema.
- [ ] Render `workbook_result` using a reusable typed table component in the frontend.
- [ ] Replace JSON Staged Mutation previews with typed field-diff/row-preview tables.
- [x] Update native tool definitions, `ACTION_INSTRUCTIONS`, and the runtime system prompt.
- [x] Add backend contract, query determinism, and SSE tests for the implemented backend result kinds.
- [ ] Add baseline evaluation cases for extrema, ranking, projection, grouped metrics, truncation, and mutation previews.
- [ ] Run the full Python suite, frontend tests/typecheck/build, lint, and the Baseline Evaluation Corpus before marking this specification complete.

## Handoff checklist for a new session

Before changing code, read this file, `CONTEXT.md`, `DECISIONS.md` entries D-008 through D-010, and `docs/backend-api-contract.md`. Preserve the existing Session Workbook, Stable ID, Staged Mutation, Mutation Authorization, and Verified Output Artifact rules. Work one unchecked TODO at a time; add its tests before implementation and update this checklist when verified.

## Acceptance criteria

1. A highest/lowest or ranked result always names the Stable ID from the same returned row.
2. Repeating the same query on the same Session Workbook produces the same order and table.
3. A user-requested table is rendered from structured backend data, not model Markdown.
4. The UI never receives workbook data through `activity` or hidden reasoning fields.
5. Mutation confirmation remains exact-stage, explicit, and independent of model prose.
6. Existing source preservation, mutation verification, and baseline hard gates continue to pass.
