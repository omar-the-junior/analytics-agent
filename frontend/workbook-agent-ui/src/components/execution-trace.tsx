import {
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  Clock3,
  LoaderCircle,
  Wrench,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Separator } from "@/components/ui/separator"
import type { Activity, TraceValue } from "@/lib/workbook-contract"

export type ExecutionStatus =
  | "active"
  | "awaiting_confirmation"
  | "completed"
  | "cancelled"
  | "failed"

type TraceStep = Activity & { input?: Record<string, TraceValue>; output?: Record<string, TraceValue> }

function formatDuration(milliseconds: number) {
  return `${(milliseconds / 1000).toFixed(milliseconds < 10_000 ? 1 : 0)}s`
}

function statusLabel(status: ExecutionStatus) {
  return {
    active: "Running",
    awaiting_confirmation: "Review needed",
    completed: "Complete",
    cancelled: "Cancelled",
    failed: "Stopped",
  }[status]
}

function statusVariant(status: ExecutionStatus) {
  return status === "failed" ? "destructive" : status === "active" ? "default" : "secondary"
}

function visibleSteps(activities: Activity[]): TraceStep[] {
  const steps: TraceStep[] = []
  for (const activity of activities) {
    if (activity.kind !== "tool" || activity.status === "active") {
      steps.push({ ...activity })
      continue
    }
    const started = [...steps]
      .reverse()
      .find(
        (step) =>
          step.kind === "tool" &&
          step.status === "active" &&
          step.tool === activity.tool &&
          step.iteration === activity.iteration
      )
    if (started) {
      started.status = activity.status
      started.summary = activity.summary
      started.elapsed_ms = activity.elapsed_ms
      started.output = activity.output
      continue
    }
    steps.push({ ...activity })
  }
  return steps
}

function TracePayload({ label, value }: { label: string; value: Record<string, TraceValue> }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="overflow-x-auto font-mono text-xs">{JSON.stringify(value, null, 2)}</pre>
      </CardContent>
    </Card>
  )
}

function ToolStep({ step }: { step: TraceStep }) {
  const title = `${step.tool ?? "Tool"} (${step.status})`
  return (
    <Collapsible>
      <CollapsibleTrigger asChild>
        <Button className="w-full justify-between" size="sm" variant="outline">
          <span className="flex min-w-0 items-center gap-2">
            {step.status === "active" ? <LoaderCircle className="animate-spin" /> : <Wrench />}
            <span className="truncate">{step.summary}</span>
          </span>
          <span className="flex shrink-0 items-center gap-2">
            <Badge variant={step.status === "active" ? "outline" : "secondary"}>{step.status}</Badge>
            <ChevronDown data-icon="inline-end" />
          </span>
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent className="flex flex-col gap-3 px-3 pb-3">
        <Separator />
        <p className="font-mono text-xs text-muted-foreground">{title}</p>
        {step.input ? <TracePayload label="Input" value={step.input} /> : null}
        {step.output ? <TracePayload label="Output" value={step.output} /> : null}
      </CollapsibleContent>
    </Collapsible>
  )
}

function AgentStep({ step }: { step: TraceStep }) {
  const Icon = step.kind === "response" ? CheckCircle2 : BrainCircuit
  return (
    <div className="flex items-start gap-2 px-1 text-sm">
      <Icon />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <p>{step.summary}</p>
        {step.iteration ? <p className="text-xs text-muted-foreground">Step {step.iteration}</p> : null}
      </div>
      <span className="shrink-0 text-xs text-muted-foreground">{formatDuration(step.elapsed_ms)}</span>
    </div>
  )
}

export function ExecutionTrace({
  activities,
  elapsedMs,
  status,
}: {
  activities: Activity[]
  elapsedMs: number
  status: ExecutionStatus
}) {
  const steps = visibleSteps(activities)
  return (
    <Collapsible className="mx-3 max-w-xl" defaultOpen={status === "active"}>
      <Card size="sm">
        <CardHeader>
          <CardTitle>Execution</CardTitle>
          <CardDescription>Agent steps and approved tool calls, in order.</CardDescription>
          <CardAction className="flex items-center gap-2">
            <Badge variant={statusVariant(status)}>{statusLabel(status)}</Badge>
            <CollapsibleTrigger asChild>
              <Button aria-label="Toggle execution details" size="icon-sm" variant="ghost">
                <ChevronDown />
              </Button>
            </CollapsibleTrigger>
          </CardAction>
        </CardHeader>
        <CollapsibleContent>
          <CardContent className="flex flex-col gap-2">
            {steps.length === 0 ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <CircleDashed className="animate-spin" />
                <span>Starting the run</span>
              </div>
            ) : (
              steps.map((step, index) =>
                step.kind === "tool" ? (
                  <ToolStep key={`${step.activity}-${step.tool}-${index}`} step={step} />
                ) : (
                  <AgentStep key={`${step.activity}-${index}`} step={step} />
                )
              )
            )}
          </CardContent>
          <CardFooter className="text-xs text-muted-foreground">
            <Clock3 />
            <span>{formatDuration(elapsedMs)}</span>
          </CardFooter>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  )
}
