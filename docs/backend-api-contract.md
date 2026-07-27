# Backend API and frontend handoff contract

This is the implementation handoff for the separate frontend task. It preserves the backend's authority over agent execution, `WorkbookSession`, confirmation, artifact verification, and cancellation.

## Lifecycle

1. The frontend creates a backend `WorkbookSession` bound to one selected workbook.
2. It submits a user turn, creating a backend-owned run.
3. It opens the run's SSE stream and renders only the received safe events.
4. A `workbook_result` event presents only a validated query result from the current Session Workbook. The frontend renders its typed data; it never recovers rows from assistant Markdown.
5. A `confirmation_required` event presents an exact Staged Mutation. The frontend submits its `stage_id` to the confirmation endpoint; it cannot convert chat text into authorization.
6. Terminal events are `completed`, `cancelled`, or `failed`. A completed mutation may contain an opaque artifact reference, downloaded through its dedicated endpoint.

Session state and the bounded event replay window are in memory only. They end on an API-process restart.

## Endpoint shape

| Endpoint | Purpose |
| --- | --- |
| `POST /api/sessions` | Create a Session Workbook and return an opaque `session_id`. |
| `POST /api/sessions/{session_id}/runs` | Submit one user turn and return an opaque `run_id`. |
| `GET /api/sessions/{session_id}/runs/{run_id}/events` | SSE stream. A reconnect uses `Last-Event-ID` to receive a bounded replay. |
| `POST /api/sessions/{session_id}/runs/{run_id}/confirmation` | Confirm exactly one unchanged Staged Mutation with `stage_id`. |
| `POST /api/sessions/{session_id}/runs/{run_id}/cancel` | Request cancellation of an active run. It can never commit a mutation. |
| `GET /api/sessions/{session_id}/artifacts/{artifact_id}` | Download one verified output artifact. |

## SSE envelope

Every SSE message has a monotonic event ID and a JSON payload:

```json
{
  "event_id": 41,
  "run_id": "opaque-run-id",
  "type": "confirmation_required",
  "data": {}
}
```

The event types are `run_started`, `activity`, `workbook_result`, `assistant_message`, `confirmation_required`, `artifact_ready`, `completed`, `cancelled`, and `failed`. They contain only user-safe content and opaque IDs: never provider errors, filesystem paths, API keys, raw workbook data beyond the requested response, or orchestration instructions.

`activity` is an incremental, UI-safe trace. It may identify an approved tool by name, a generic safe-reasoning phase, status, and elapsed time in milliseconds. It must never include model chain-of-thought, prompts, tool arguments, tool results, or workbook rows. This lets the browser show a truthful activity timeline such as “Reviewing the request” and “Querying workbook data” without exposing private or untrusted content.

`workbook_result` is the only event that may carry requested workbook values. Its data has one `result` object with one of these validated forms:

```json
{
  "kind": "table",
  "columns": ["City", "List Price", "Listing ID"],
  "rows": [["Example City", 850000, "LST-5017"]],
  "row_count": 1,
  "truncated": false,
  "stable_id_field": "Listing ID",
  "calculation_source": "tool_computed"
}
```

Table rows follow `columns` exactly; `row_count` is the number of matching rows before `limit`, and `truncated` says whether any matching row was omitted. The Stable ID is always present in a table, including when the model did not select it. A highest/lowest result uses `kind: "selection"` and carries its `column`, `value`, full `row`, `stable_id_field`, and `stable_id` atomically. Count and sum use `kind: "metric"`, with `metric`, `value`, `column` when applicable, and `row_count`. An unavailable numeric metric has `unavailable: true` and a `reason`; it never substitutes zero.

`confirmation_required` contains `stage_id`, `operation`, `stable_id_field`, `stable_id`, `warnings`, and a typed `preview`. An update preview has `kind: "field_diff"`, columns `Field`, `Before`, `After`, and only changed fields. Insert and delete previews are respectively `after_row` and `before_row`, each with the complete workbook row as `columns` and one `rows` entry. The same `stage_id` remains the only mutation authorization target.

`run_started`, `assistant_message`, and terminal events include timing metadata. The API currently streams lifecycle and activity events; final assistant prose is emitted as one `assistant_message`, rather than provider token deltas.

## Errors

HTTP failures and `failed` events use the same safe envelope:

```json
{
  "code": "provider_error",
  "message": "The model provider is temporarily unavailable. Please try again.",
  "retryable": true,
  "run_id": "opaque-run-id",
  "correlation_id": "opaque-correlation-id"
}
```

The `code` uses the D-010 taxonomy where applicable. Diagnostic details remain in the redacted server trace, keyed by the correlation ID.
