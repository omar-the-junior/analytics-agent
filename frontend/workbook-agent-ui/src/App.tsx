import { useEffect, useRef, useState, type FormEvent } from "react"
import ReactMarkdown from "react-markdown"
import {
  Bot,
  Clock3,
  FileSpreadsheet,
  LoaderCircle,
  Send,
  ShieldCheck,
  Square,
  Upload,
} from "lucide-react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/ui/input-group"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageHeader,
} from "@/components/ui/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller"
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker"
import {
  MutationPreview,
  WorkbookResult,
} from "@/components/workbook-data"
import {
  ExecutionTrace,
  type ExecutionStatus,
} from "@/components/execution-trace"
import {
  isRecord,
  parseActivity,
  parseQueryResult,
  parseStage,
  type Activity,
  type QueryResult,
  type Stage,
} from "@/lib/workbook-contract"

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api"

type Workbook = {
  id: "listings" | "campaigns"
  name: string
  description: string
}
type TextEntry = {
  id: string
  role: "user" | "assistant" | "system"
  text: string
}
type ResultEntry = { id: string; role: "result"; result: QueryResult }
type TraceEntry = {
  id: string
  role: "trace"
  activities: Activity[]
  elapsedMs: number
  status: ExecutionStatus
}
type Entry = TextEntry | ResultEntry | TraceEntry
type ActiveSession = { id: string; workbook: Workbook }

const WORKBOOKS: Workbook[] = [
  {
    id: "listings",
    name: "Real Estate Listings",
    description: "Property listings, prices, and sale status.",
  },
  {
    id: "campaigns",
    name: "Marketing Campaigns",
    description: "Channel performance, spend, and conversions.",
  },
]

function newId() {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  })
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      message?: string
    } | null
    throw new Error(error?.message ?? "The request could not be completed.")
  }
  return response.json() as Promise<T>
}

export function AssistantMarkdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      components={{
        a: ({ children: linkChildren, ...props }) => (
          <a className="text-primary underline underline-offset-4" {...props}>
            {linkChildren}
          </a>
        ),
        code: ({ children: codeChildren, className, ...props }) => (
          <code
            className={
              className ??
              "rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em]"
            }
            {...props}
          >
            {codeChildren}
          </code>
        ),
        pre: ({ children: codeChildren }) => (
          <pre className="overflow-x-auto rounded-md bg-muted p-3 font-mono text-xs">
            {codeChildren}
          </pre>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  )
}

export default function App() {
  const [session, setSession] = useState<ActiveSession | null>(null)
  const [entries, setEntries] = useState<Entry[]>([])
  const [prompt, setPrompt] = useState("")
  const [runId, setRunId] = useState<string | null>(null)
  const [stage, setStage] = useState<Stage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmationOpen, setConfirmationOpen] = useState(false)
  const [artifactId, setArtifactId] = useState<string | null>(null)
  const [queuedMessages, setQueuedMessages] = useState<string[]>([])
  const [startPending, setStartPending] = useState(false)
  const [elapsedMs, setElapsedMs] = useState(0)
  const streamRef = useRef<EventSource | null>(null)
  const queueRef = useRef<string[]>([])
  const runActiveRef = useRef(false)
  const runStartedAtRef = useRef<number | null>(null)
  const activeTraceIdRef = useRef<string | null>(null)

  useEffect(() => () => streamRef.current?.close(), [])

  useEffect(() => {
    if (!runId && !startPending) return
    const timer = window.setInterval(() => {
      if (runStartedAtRef.current !== null)
        setElapsedMs(Date.now() - runStartedAtRef.current)
    }, 100)
    return () => window.clearInterval(timer)
  }, [runId, startPending])

  function append(role: TextEntry["role"], text: string) {
    setEntries((current) => [...current, { id: newId(), role, text }])
  }

  function appendWorkbookResult(result: QueryResult) {
    setEntries((current) => [...current, { id: newId(), role: "result", result }])
  }

  function updateActiveTrace(update: (trace: TraceEntry) => TraceEntry) {
    const traceId = activeTraceIdRef.current
    if (!traceId) return
    setEntries((current) =>
      current.map((entry) =>
        entry.role === "trace" && entry.id === traceId ? update(entry) : entry
      )
    )
  }

  async function begin(workbook: Workbook) {
    setError(null)
    try {
      const result = await request<{ session_id: string }>("/sessions", {
        method: "POST",
        body: JSON.stringify({ workbook: workbook.id }),
      })
      setSession({ id: result.session_id, workbook })
      setEntries([])
      setArtifactId(null)
      setStage(null)
      setElapsedMs(0)
      activeTraceIdRef.current = null
      queueRef.current = []
      setQueuedMessages([])
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to create a session."
      )
    }
  }

  function connectStream(nextRunId: string, activeSession: ActiveSession) {
    streamRef.current?.close()
    const stream = new EventSource(
      `${API_BASE}/sessions/${activeSession.id}/runs/${nextRunId}/events`
    )
    streamRef.current = stream
    stream.onmessage = (event) => {
      let payload: unknown
      try {
        payload = JSON.parse(event.data)
      } catch {
        return
      }
      if (
        !isRecord(payload) ||
        typeof payload.type !== "string" ||
        !isRecord(payload.data)
      )
        return

      if (
        payload.type === "assistant_message" &&
        typeof payload.data.message === "string"
      )
        append("assistant", payload.data.message)
      if (payload.type === "workbook_result") {
        const result = parseQueryResult(payload.data.result)
        if (result) appendWorkbookResult(result)
      }
      if (payload.type === "activity") {
        const activity = parseActivity(payload.data)
        if (activity)
          updateActiveTrace((trace) => ({
            ...trace,
            activities: [...trace.activities, activity],
            elapsedMs: activity.elapsed_ms,
          }))
      }
      if (payload.type === "confirmation_required") {
        const nextStage = parseStage(payload.data)
        if (nextStage) {
          setStage(nextStage)
          updateActiveTrace((trace) => ({ ...trace, status: "awaiting_confirmation" }))
        }
      }
      if (
        payload.type === "artifact_ready" &&
        typeof payload.data.artifact_id === "string"
      )
        setArtifactId(payload.data.artifact_id)
      if (payload.type === "failed")
        setError(
          typeof payload.data.message === "string"
            ? payload.data.message
            : "The run failed."
        )
      if (["completed", "cancelled", "failed"].includes(payload.type)) {
        const completedElapsedMs =
          typeof payload.data.elapsed_ms === "number" ? payload.data.elapsed_ms : elapsedMs
        setElapsedMs(completedElapsedMs)
        const traceStatus: ExecutionStatus =
          payload.type === "completed"
            ? "completed"
            : payload.type === "cancelled"
              ? "cancelled"
              : "failed"
        updateActiveTrace((trace) => ({
          ...trace,
          elapsedMs: completedElapsedMs,
          status: traceStatus,
        }))
        runActiveRef.current = false
        runStartedAtRef.current = null
        activeTraceIdRef.current = null
        setStartPending(false)
        setRunId(null)
        stream.close()
        const nextMessage = queueRef.current.shift()
        setQueuedMessages([...queueRef.current])
        if (nextMessage) {
          void startRun(nextMessage, activeSession)
        }
      }
    }
    stream.onerror = () => {
      if (stream.readyState === EventSource.CLOSED) {
        runActiveRef.current = false
        runStartedAtRef.current = null
        setStartPending(false)
        setRunId(null)
        updateActiveTrace((trace) => ({ ...trace, elapsedMs, status: "failed" }))
        activeTraceIdRef.current = null
        setError("The live run connection was lost. Please try again.")
      }
    }
  }

  async function startRun(message: string, activeSession: ActiveSession) {
    const traceId = newId()
    setEntries((current) => [
      ...current,
      { id: newId(), role: "user", text: message },
      {
        id: traceId,
        role: "trace",
        activities: [],
        elapsedMs: 0,
        status: "active",
      },
    ])
    activeTraceIdRef.current = traceId
    runActiveRef.current = true
    runStartedAtRef.current = Date.now()
    setStartPending(true)
    setElapsedMs(0)
    setError(null)
    setArtifactId(null)
    try {
      const result = await request<{ run_id: string }>(
        `/sessions/${activeSession.id}/runs`,
        { method: "POST", body: JSON.stringify({ message }) }
      )
      setRunId(result.run_id)
      setStartPending(false)
      connectStream(result.run_id, activeSession)
    } catch (reason) {
      runActiveRef.current = false
      runStartedAtRef.current = null
      setStartPending(false)
      updateActiveTrace((trace) => ({ ...trace, elapsedMs, status: "failed" }))
      activeTraceIdRef.current = null
      setError(
        reason instanceof Error ? reason.message : "Unable to start the run."
      )
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!session || !prompt.trim()) return
    const message = prompt.trim()
    setPrompt("")
    if (runActiveRef.current) {
      queueRef.current.push(message)
      setQueuedMessages([...queueRef.current])
      return
    }
    await startRun(message, session)
  }

  async function confirm() {
    if (!session || !runId || !stage) return
    setConfirmationOpen(false)
    try {
      await request(`/sessions/${session.id}/runs/${runId}/confirmation`, {
        method: "POST",
        body: JSON.stringify({ stage_id: stage.stage_id }),
      })
      setStage(null)
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "This change can no longer be confirmed."
      )
    }
  }

  async function cancel() {
    if (!session || !runId) return
    try {
      await request(`/sessions/${session.id}/runs/${runId}/cancel`, {
        method: "POST",
      })
      setStage(null)
      updateActiveTrace((trace) => ({ ...trace, status: "active" }))
      append("system", "Run cancelled. No workbook changes were committed.")
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to cancel the run."
      )
    }
  }

  const isRunning = Boolean(runId) || startPending

  if (!session) {
    return (
      <main className="grid min-h-svh place-items-center bg-background p-5">
        <Empty className="w-full max-w-2xl border bg-card shadow-sm">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FileSpreadsheet />
            </EmptyMedia>
            <EmptyTitle>Open a workbook</EmptyTitle>
            <EmptyDescription>
              Each conversation is a temporary, server-owned session. Choose one
              source to start.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent className="w-full items-stretch">
            {WORKBOOKS.map((workbook) => (
              <Button
                className="h-auto justify-start py-4"
                key={workbook.id}
                onClick={() => begin(workbook)}
                variant="outline"
              >
                <FileSpreadsheet data-icon="inline-start" />
                <span className="flex min-w-0 flex-col items-start gap-1">
                  <span>{workbook.name}</span>
                  <span className="text-xs font-normal text-muted-foreground">
                    {workbook.description}
                  </span>
                </span>
              </Button>
            ))}
          </EmptyContent>
          {error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not start session</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
        </Empty>
      </main>
    )
  }

  return (
    <main className="flex h-svh min-h-0 flex-col bg-background">
      <header className="flex shrink-0 items-center gap-3 border-b bg-card px-4 py-3 sm:px-6">
        <div className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <FileSpreadsheet />
        </div>
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold">
            {session.workbook.name}
          </h1>
          <p className="text-xs text-muted-foreground">
            Temporary workbook session
          </p>
        </div>
        <Badge className="ml-auto" variant="secondary">
          Light workspace
        </Badge>
        <Button
          onClick={() => {
            streamRef.current?.close()
            setSession(null)
            setRunId(null)
            setStartPending(false)
            runActiveRef.current = false
            runStartedAtRef.current = null
            queueRef.current = []
            setQueuedMessages([])
          }}
          size="sm"
          variant="outline"
        >
          Change workbook
        </Button>
      </header>
      <section className="flex min-h-0 flex-1 flex-col">
        <MessageScrollerProvider>
          <div className="flex min-h-0 flex-1 flex-col">
            <MessageScroller>
              <MessageScrollerViewport>
                <MessageScrollerContent className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6">
                {entries.length === 0 ? (
                  <MessageScrollerItem scrollAnchor>
                    <Empty className="mx-auto max-w-xl border-0">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <Upload />
                        </EmptyMedia>
                        <EmptyTitle>
                          Ask a question about this workbook
                        </EmptyTitle>
                        <EmptyDescription>
                          The server controls workbook access, confirmation, and
                          verified artifacts.
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  </MessageScrollerItem>
                ) : null}
                {entries.map((entry) => (
                  <MessageScrollerItem key={entry.id} scrollAnchor>
                    {entry.role === "result" ? (
                      <WorkbookResult result={entry.result} />
                    ) : entry.role === "trace" ? (
                      <ExecutionTrace
                        activities={entry.activities}
                        elapsedMs={
                          entry.status === "active" ? elapsedMs : entry.elapsedMs
                        }
                        status={entry.status}
                      />
                    ) : entry.role === "user" ? (
                      <Message align="end">
                        <MessageContent>
                          <Bubble align="end">
                            <BubbleContent>{entry.text}</BubbleContent>
                          </Bubble>
                        </MessageContent>
                      </Message>
                    ) : (
                      <Message>
                        <MessageAvatar>
                          <Bot />
                        </MessageAvatar>
                        <MessageContent>
                          <MessageHeader>
                            {entry.role === "system"
                              ? "Session"
                              : "Workbook Assistant"}
                          </MessageHeader>
                          <Bubble variant="secondary">
                            <BubbleContent>
                              {entry.role === "assistant" ? (
                                <AssistantMarkdown>{entry.text}</AssistantMarkdown>
                              ) : (
                                entry.text
                              )}
                            </BubbleContent>
                          </Bubble>
                        </MessageContent>
                      </Message>
                    )}
                  </MessageScrollerItem>
                ))}
                {stage ? (
                  <MessageScrollerItem scrollAnchor>
                    <MutationPreview stage={stage} />
                    <Button
                      className="mx-3"
                      onClick={() => setConfirmationOpen(true)}
                      size="sm"
                    >
                      <ShieldCheck data-icon="inline-start" />
                      Review and confirm
                    </Button>
                  </MessageScrollerItem>
                ) : null}
                {artifactId ? (
                  <MessageScrollerItem scrollAnchor>
                    <Alert className="mx-3 max-w-xl">
                      <ShieldCheck />
                      <AlertTitle>Verified artifact ready</AlertTitle>
                      <AlertDescription>
                        <a
                          className="underline"
                          href={`${API_BASE}/sessions/${session.id}/artifacts/${artifactId}`}
                        >
                          Download the verified workbook
                        </a>
                      </AlertDescription>
                    </Alert>
                  </MessageScrollerItem>
                ) : null}
                {error ? (
                  <MessageScrollerItem scrollAnchor>
                    <Alert className="mx-3 max-w-xl" variant="destructive">
                      <AlertTitle>Run issue</AlertTitle>
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  </MessageScrollerItem>
                ) : null}
                </MessageScrollerContent>
              </MessageScrollerViewport>
              <MessageScrollerButton />
            </MessageScroller>
          </div>
        </MessageScrollerProvider>
        {queuedMessages.length > 0 ? (
          <div className="shrink-0 border-t bg-card px-4 py-2 sm:px-6">
            <div className="mx-auto max-w-4xl">
              <Marker>
                <MarkerIcon>
                  <Clock3 />
                </MarkerIcon>
                <MarkerContent className="flex min-w-0 items-center gap-2">
                  <span className="shrink-0">Queued next</span>
                  <span className="truncate text-foreground">
                    {queuedMessages[0]}
                  </span>
                  {queuedMessages.length > 1 ? (
                    <Badge variant="secondary">+{queuedMessages.length - 1}</Badge>
                  ) : null}
                </MarkerContent>
              </Marker>
            </div>
          </div>
        ) : null}
        <form className="shrink-0 border-t bg-card px-4 py-3 sm:px-6" onSubmit={submit}>
          <div className="mx-auto max-w-4xl">
            <InputGroup>
              <InputGroupTextarea
                aria-label="Ask the workbook assistant"
                className="max-h-48 min-h-10 overflow-y-auto"
                onChange={(event) => setPrompt(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault()
                    event.currentTarget.form?.requestSubmit()
                  }
                }}
                placeholder={`Ask about ${session.workbook.name}…`}
                rows={1}
                value={prompt}
              />
              <InputGroupAddon align="block-end">
                <span className="mr-auto text-xs text-muted-foreground">
                  {isRunning
                    ? queuedMessages.length > 0
                      ? `${queuedMessages.length} message${queuedMessages.length === 1 ? "" : "s"} queued.`
                      : "You can keep typing while this reply is in progress."
                    : "Confirmation is required for every workbook change."}
                </span>
                {isRunning ? (
                  <InputGroupButton
                    onClick={cancel}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    <Square data-icon="inline-start" />
                    Cancel
                  </InputGroupButton>
                ) : null}
                <InputGroupButton
                  disabled={!prompt.trim()}
                  size="sm"
                  type="submit"
                >
                  {startPending ? <LoaderCircle className="animate-spin" data-icon="inline-start" /> : <Send data-icon="inline-start" />}
                  {isRunning ? "Queue" : "Send"}
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </div>
        </form>
      </section>
      <AlertDialog onOpenChange={setConfirmationOpen} open={confirmationOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Commit this exact change?</AlertDialogTitle>
            <AlertDialogDescription>
              The server will commit only the staged change shown above, then
              verify and provide a new workbook artifact.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {stage ? <MutationPreview compact stage={stage} /> : null}
          <AlertDialogFooter>
            <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
            <AlertDialogAction onClick={confirm}>
              Confirm change
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  )
}
