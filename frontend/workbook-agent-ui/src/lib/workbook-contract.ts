export type WorkbookValue = string | number | boolean | null

export type PresentationTable = {
  columns: string[]
  rows: WorkbookValue[][]
}

export type TableQueryResult = PresentationTable & {
  kind: "table"
  row_count: number
  truncated: boolean
  stable_id_field: string
  calculation_source: "tool_computed"
}

export type MetricQueryResult = {
  kind: "metric"
  metric: "count" | "sum" | "min" | "max"
  value: WorkbookValue
  column: string | null
  row_count: number
  unavailable: boolean
  reason: string | null
  calculation_source: "tool_computed"
}

export type SelectionQueryResult = {
  kind: "selection"
  column: string
  value: WorkbookValue
  row: Record<string, WorkbookValue>
  stable_id_field: string
  stable_id: string
  calculation_source: "tool_computed"
}

export type QueryResult =
  | TableQueryResult
  | MetricQueryResult
  | SelectionQueryResult

type PreviewKind = "field_diff" | "after_row" | "before_row"

export type Stage = {
  stage_id: string
  operation: "insert" | "update" | "delete"
  stable_id_field: string
  stable_id: string
  warnings: string[]
  preview: PresentationTable & { kind: PreviewKind }
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isWorkbookValue(value: unknown): value is WorkbookValue {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  )
}

function isPresentationTable(value: unknown): value is PresentationTable {
  if (!isRecord(value)) return false
  const { columns, rows } = value
  if (!Array.isArray(columns) || !Array.isArray(rows)) return false
  if (!columns.every((column) => typeof column === "string")) return false
  return rows.every(
    (row) =>
      Array.isArray(row) &&
      row.length === columns.length &&
      row.every(isWorkbookValue)
  )
}

function isCalculationSource(value: unknown): value is "tool_computed" {
  return value === "tool_computed"
}

function isNonNegativeInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0
}

function isMetricKind(value: unknown): value is MetricQueryResult["metric"] {
  return value === "count" || value === "sum" || value === "min" || value === "max"
}

function isOperation(value: unknown): value is Stage["operation"] {
  return value === "insert" || value === "update" || value === "delete"
}

function toWorkbookRow(
  value: Record<string, unknown>
): Record<string, WorkbookValue> | null {
  const row: Record<string, WorkbookValue> = {}
  for (const [column, cell] of Object.entries(value)) {
    if (!isWorkbookValue(cell)) return null
    row[column] = cell
  }
  return row
}

export function parseQueryResult(value: unknown): QueryResult | null {
  if (!isRecord(value) || !isCalculationSource(value.calculation_source)) return null

  if (value.kind === "table") {
    const rowCount = value.row_count
    const truncated = value.truncated
    const stableIdField = value.stable_id_field
    if (
      !isPresentationTable(value) ||
      !isNonNegativeInteger(rowCount) ||
      typeof truncated !== "boolean" ||
      typeof stableIdField !== "string"
    )
      return null
    return {
      kind: "table",
      columns: value.columns,
      rows: value.rows,
      row_count: rowCount,
      truncated,
      stable_id_field: stableIdField,
      calculation_source: "tool_computed",
    }
  }

  if (value.kind === "metric") {
    const metric = value.metric
    const column = value.column
    const rowCount = value.row_count
    const unavailable = value.unavailable
    const reason = value.reason
    if (
      !isMetricKind(metric) ||
      !isWorkbookValue(value.value) ||
      !(typeof column === "string" || column === null) ||
      !isNonNegativeInteger(rowCount) ||
      typeof unavailable !== "boolean" ||
      !(typeof reason === "string" || reason === null)
    )
      return null
    return {
      kind: "metric",
      metric,
      value: value.value,
      column,
      row_count: rowCount,
      unavailable,
      reason,
      calculation_source: "tool_computed",
    }
  }

  if (value.kind === "selection") {
    const row = isRecord(value.row) ? toWorkbookRow(value.row) : null
    if (
      typeof value.column !== "string" ||
      !isWorkbookValue(value.value) ||
      row === null ||
      typeof value.stable_id_field !== "string" ||
      typeof value.stable_id !== "string"
    )
      return null
    return {
      kind: "selection",
      column: value.column,
      value: value.value,
      row,
      stable_id_field: value.stable_id_field,
      stable_id: value.stable_id,
      calculation_source: "tool_computed",
    }
  }

  return null
}

export function parseStage(value: unknown): Stage | null {
  if (!isRecord(value)) return null
  const preview = value.preview
  const operation = value.operation
  const previewKind = isRecord(preview) ? preview.kind : null
  if (
    typeof value.stage_id !== "string" ||
    !isOperation(operation) ||
    typeof value.stable_id_field !== "string" ||
    typeof value.stable_id !== "string" ||
    !Array.isArray(value.warnings) ||
    !value.warnings.every((warning) => typeof warning === "string") ||
    !isRecord(preview) ||
    !isPresentationTable(preview)
  )
    return null

  if (
    previewKind !== "field_diff" &&
    previewKind !== "after_row" &&
    previewKind !== "before_row"
  )
    return null
  const expectedKind: Record<Stage["operation"], PreviewKind> = {
    update: "field_diff",
    insert: "after_row",
    delete: "before_row",
  }
  if (previewKind !== expectedKind[operation]) return null

  return {
    stage_id: value.stage_id,
    operation,
    stable_id_field: value.stable_id_field,
    stable_id: value.stable_id,
    warnings: value.warnings,
    preview: { kind: previewKind, columns: preview.columns, rows: preview.rows },
  }
}

export function formatWorkbookValue(value: WorkbookValue): string {
  if (value === null) return "—"
  if (typeof value === "number") return new Intl.NumberFormat().format(value)
  if (typeof value === "boolean") return value ? "Yes" : "No"
  return value
}
