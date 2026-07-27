import type { ReactNode } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  formatWorkbookValue,
  type PresentationTable,
  type QueryResult,
  type Stage,
} from "@/lib/workbook-contract"

function rowNoun(count: number) {
  return count === 1 ? "row" : "rows"
}

export function WorkbookDataTable({
  table,
  ariaLabel,
  emptyDescription,
  emphasizeChanges = false,
}: {
  table: PresentationTable
  ariaLabel: string
  emptyDescription: string
  emphasizeChanges?: boolean
}) {
  if (table.rows.length === 0) {
    return (
      <Empty className="min-h-32">
        <EmptyHeader>
          <EmptyTitle>No rows to display</EmptyTitle>
          <EmptyDescription>{emptyDescription}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <Table aria-label={ariaLabel}>
      <TableHeader>
        <TableRow>
          {table.columns.map((column) => (
            <TableHead key={column}>{column}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {table.rows.map((row, rowIndex) => (
          <TableRow
            data-state={emphasizeChanges ? "selected" : undefined}
            key={`${rowIndex}-${row.join("-")}`}
          >
            {row.map((value, columnIndex) => (
              <TableCell key={`${table.columns[columnIndex]}-${columnIndex}`}>
                {formatWorkbookValue(value)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function ResultCard({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <Card className="mx-3 max-w-4xl">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export function WorkbookResult({ result }: { result: QueryResult }) {
  if (result.kind === "table") {
    const displayed = result.rows.length
    return (
      <ResultCard
        description={`${result.row_count} matching ${rowNoun(result.row_count)}; showing ${displayed}.`}
        title="Workbook results"
      >
        <div className="flex flex-col gap-3">
          <WorkbookDataTable
            ariaLabel="Workbook results"
            emptyDescription="No rows matched this query."
            table={result}
          />
          {result.truncated ? (
            <Alert>
              <AlertTitle>Results limited</AlertTitle>
              <AlertDescription>
                One or more matching rows are not shown. Refine the request to
                inspect a narrower result.
              </AlertDescription>
            </Alert>
          ) : null}
        </div>
      </ResultCard>
    )
  }

  if (result.kind === "selection") {
    const table: PresentationTable = {
      columns: Object.keys(result.row),
      rows: [Object.values(result.row)],
    }
    return (
      <ResultCard
        description={`Stable ID: ${result.stable_id_field} ${result.stable_id}`}
        title="Workbook selection"
      >
        <div className="flex flex-col gap-3">
          <CardDescription>
            <strong>{result.column}: </strong>
            {formatWorkbookValue(result.value)}
          </CardDescription>
          <WorkbookDataTable
            ariaLabel="Selected workbook row"
            emptyDescription="The selected row is unavailable."
            table={table}
          />
        </div>
      </ResultCard>
    )
  }

  const metricTitle = result.column
    ? `${result.metric} of ${result.column}`
    : result.metric
  return (
    <ResultCard
      description={`${result.row_count} matching ${rowNoun(result.row_count)}.`}
      title="Workbook metric"
    >
      {result.unavailable ? (
        <Alert>
          <AlertTitle>Metric unavailable</AlertTitle>
          <AlertDescription>{result.reason ?? "No value is available."}</AlertDescription>
        </Alert>
      ) : (
        <CardTitle>
          {metricTitle}: {formatWorkbookValue(result.value)}
        </CardTitle>
      )}
    </ResultCard>
  )
}

export function MutationPreview({
  stage,
  compact = false,
}: {
  stage: Stage
  compact?: boolean
}) {
  const isFieldDiff = stage.preview.kind === "field_diff"
  return (
    <Card className="mx-3 max-w-4xl" size={compact ? "sm" : "default"}>
      <CardHeader>
        <CardTitle>Review proposed {stage.operation}</CardTitle>
        <CardDescription>
          {stage.stable_id_field}: {stage.stable_id} · Stage ID: {stage.stage_id}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Badge variant="outline">
          {isFieldDiff ? "Changed fields" : "Complete workbook row"}
        </Badge>
        <WorkbookDataTable
          ariaLabel={`Proposed ${stage.operation} preview`}
          emphasizeChanges={isFieldDiff}
          emptyDescription="This staged change has no displayable values."
          table={stage.preview}
        />
        {stage.warnings.map((warning) => (
          <Alert key={warning}>
            <AlertTitle>Review note</AlertTitle>
            <AlertDescription>{warning}</AlertDescription>
          </Alert>
        ))}
      </CardContent>
    </Card>
  )
}
