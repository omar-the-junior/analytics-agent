import { useEffect, useState, type FormEvent } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  Bot,
  Check,
  ChevronDown,
  FileSpreadsheet,
  Info,
  Moon,
  PanelRight,
  Send,
  Sparkles,
  Sun,
  Table2,
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
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
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
import { Marker, MarkerContent, MarkerIcon } from "@/components/ui/marker"
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "@/components/theme-provider"
import {
  type DemoScenario,
  type MutationPreview,
  type WorkbookId,
  DEMO_SCENARIOS,
  WORKBOOKS,
  findScenario,
  starterPromptsFor,
} from "@/demo/workbooks"
import { cn } from "@/lib/utils"

type AgentConfiguration = {
  provider: string
  model: string
  write_confirmation_required: boolean
  available_tools: string[]
}

type SessionState =
  | "idle"
  | "responding"
  | "answered"
  | "staged"
  | "confirmed"
  | "backendUnavailable"

type ChatEntry =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "answer"; scenario: DemoScenario }
  | { id: string; kind: "unsupported"; text: string }

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia("(max-width: 639px)").matches)

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 639px)")
    const update = () => setIsMobile(mediaQuery.matches)

    update()
    mediaQuery.addEventListener("change", update)

    return () => mediaQuery.removeEventListener("change", update)
  }, [])

  return isMobile
}

async function fetchAgentConfiguration(): Promise<AgentConfiguration> {
  const response = await fetch(`${apiBaseUrl}/api/agent/configuration`)

  if (!response.ok) {
    throw new Error("The local API is not running yet.")
  }

  return response.json() as Promise<AgentConfiguration>
}

function ResultCard({
  scenario,
  onConfirm,
  confirmationRequired,
  isConfirmed,
}: {
  scenario: DemoScenario
  onConfirm: (preview: MutationPreview) => void
  confirmationRequired: boolean
  isConfirmed: boolean
}) {
  const { answer, mutationPreview } = scenario

  return (
    <Card className="w-full max-w-2xl gap-0 overflow-hidden py-0 shadow-sm">
      <CardHeader className="gap-3 border-b px-4 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">Demo result</Badge>
          {answer.scope.map((item) => (
            <Badge key={item} variant="outline">
              {item}
            </Badge>
          ))}
        </div>
        <CardTitle className="text-lg tracking-tight">{answer.directResult}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 px-4 py-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Evidence</TableHead>
              <TableHead className="text-right">Value</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {answer.evidence.map((row) => (
              <TableRow key={row.label}>
                <TableCell>
                  <p className="font-medium">{row.label}</p>
                  {row.detail ? (
                    <p className="text-xs text-muted-foreground">{row.detail}</p>
                  ) : null}
                </TableCell>
                <TableCell className="text-right font-mono text-xs">{row.value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {answer.calculation ? (
          <Collapsible>
            <CollapsibleTrigger asChild>
              <Button className="w-full justify-between" size="sm" variant="ghost">
                How this was calculated
                <ChevronDown data-icon="inline-end" />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="px-2 pt-2 text-sm leading-6 text-muted-foreground">
              {answer.calculation}
            </CollapsibleContent>
          </Collapsible>
        ) : null}

        {answer.caveat ? (
          <Alert>
            <Info />
            <AlertTitle>Scope note</AlertTitle>
            <AlertDescription>{answer.caveat}</AlertDescription>
          </Alert>
        ) : null}

        {mutationPreview ? (
          <div className="flex flex-col gap-3 rounded-lg border bg-muted/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-medium">Write preview</p>
                <p className="text-xs text-muted-foreground">
                  {mutationPreview.operation} · {mutationPreview.matchedIds.join(", ")}
                </p>
              </div>
              <Badge variant="outline">1 field</Badge>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Field</TableHead>
                  <TableHead>Before</TableHead>
                  <TableHead>After</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mutationPreview.changes.map((change) => (
                  <TableRow key={change.field}>
                    <TableCell className="font-medium">{change.field}</TableCell>
                    <TableCell className="font-mono text-xs">{change.before}</TableCell>
                    <TableCell className="font-mono text-xs">{change.after}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {isConfirmed ? (
              <Alert>
                <Check />
                <AlertTitle>Demo change confirmed</AlertTitle>
                <AlertDescription>Demo change confirmed; no workbook was written.</AlertDescription>
              </Alert>
            ) : (
              <Button onClick={() => onConfirm(mutationPreview)} size="sm">
                <Check data-icon="inline-start" />
                {confirmationRequired ? "Review demo change" : "Confirm demo change"}
              </Button>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )
}

function WorkbookDetails({ workbookId }: { workbookId: WorkbookId }) {
  const workbook = WORKBOOKS[workbookId]

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4 pb-6">
      <Card className="gap-2 py-4 shadow-none">
        <CardHeader className="px-4 pb-0">
          <CardTitle className="text-sm">Source summary</CardTitle>
          <CardDescription>{workbook.description}</CardDescription>
        </CardHeader>
        <CardContent className="px-4 pb-0">
          <Badge variant="secondary">{workbook.rowCount.toLocaleString()} rows</Badge>
        </CardContent>
      </Card>
      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Columns</p>
        <div className="flex flex-wrap gap-2">
          {workbook.columns.map((column) => (
            <Badge key={column} variant="outline">
              {column}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  )
}

export function App() {
  const { setTheme, theme } = useTheme()
  const configuration = useQuery({ queryKey: ["agent-configuration"], queryFn: fetchAgentConfiguration })
  const [workbookId, setWorkbookId] = useState<WorkbookId>("real-estate")
  const [prompt, setPrompt] = useState("")
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [sessionState, setSessionState] = useState<SessionState>("idle")
  const [pendingScenario, setPendingScenario] = useState<DemoScenario | null>(null)
  const [confirmationOpen, setConfirmationOpen] = useState(false)

  const workbook = WORKBOOKS[workbookId]
  const isMobile = useIsMobile()
  const isDark = theme === "dark"
  const confirmationRequired = configuration.data?.write_confirmation_required ?? true
  const apiUnavailable = configuration.isError

  function switchWorkbook(nextWorkbookId: string) {
    const nextWorkbook = nextWorkbookId as WorkbookId

    setWorkbookId(nextWorkbook)
    setEntries([])
    setPrompt("")
    setSessionState(apiUnavailable ? "backendUnavailable" : "idle")
  }

  function receivePrompt(nextPrompt: string) {
    const text = nextPrompt.trim()

    if (!text || sessionState === "responding") {
      return
    }

    setEntries((currentEntries) => [
      ...currentEntries,
      { id: crypto.randomUUID(), kind: "user", text },
    ])
    setPrompt("")
    setSessionState("responding")

    window.setTimeout(() => {
      const scenario = findScenario(text, workbookId)

      if (scenario) {
        setEntries((currentEntries) => [
          ...currentEntries,
          { id: crypto.randomUUID(), kind: "answer", scenario },
        ])
        setSessionState(scenario.mutationPreview ? "staged" : "answered")
        return
      }

      setEntries((currentEntries) => [
        ...currentEntries,
        { id: crypto.randomUUID(), kind: "unsupported", text },
      ])
      setSessionState(apiUnavailable ? "backendUnavailable" : "answered")
    }, 280)
  }

  function submitPrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    receivePrompt(prompt)
  }

  function startConfirmation(preview: MutationPreview) {
    const scenario = Object.values(DEMO_SCENARIOS).find(
      (candidate) => candidate.mutationPreview === preview
    )

    if (!scenario) {
      return
    }

    setPendingScenario(scenario)

    if (confirmationRequired) {
      setConfirmationOpen(true)
      return
    }

    setSessionState("confirmed")
  }

  function confirmDemoChange() {
    setConfirmationOpen(false)
    setSessionState("confirmed")
  }

  return (
    <div className="min-h-svh bg-background">
      <header className="border-b bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1024px] items-center justify-between gap-3 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            <div className="grid size-7 shrink-0 place-items-center rounded-md bg-primary font-mono text-xs font-bold text-primary-foreground">
              W
            </div>
            <p className="truncate text-sm font-semibold tracking-tight">Workbook Assistant</p>
            <Badge className="hidden sm:inline-flex" variant="outline">Frontend demo</Badge>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Badge className="hidden sm:inline-flex" variant="secondary">
              <span
                aria-hidden="true"
                className={cn(
                  "size-1.5 rounded-full",
                  configuration.isError
                    ? "bg-destructive"
                    : configuration.isSuccess
                      ? "bg-primary"
                      : "bg-muted-foreground"
                )}
              />
              {configuration.isError ? "API offline" : configuration.isSuccess ? "API ready" : "Checking API"}
            </Badge>
            <Sheet>
              <SheetTrigger asChild>
                <Button aria-label="Open workbook details" size="icon-sm" variant="ghost">
                  <PanelRight />
                </Button>
              </SheetTrigger>
              <SheetContent
                className="max-h-[calc(100svh-2rem)] w-[calc(100%-2rem)] rounded-xl data-[side=bottom]:inset-x-4 data-[side=bottom]:bottom-4 data-[side=bottom]:w-auto sm:w-96 sm:rounded-none"
                side={isMobile ? "bottom" : "right"}
              >
                <SheetHeader>
                  <SheetTitle>{workbook.name}</SheetTitle>
                  <SheetDescription>Preloaded source details</SheetDescription>
                </SheetHeader>
                <WorkbookDetails workbookId={workbookId} />
              </SheetContent>
            </Sheet>
            <Button
              aria-label="Toggle color theme"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              size="icon-sm"
              variant="ghost"
            >
              {isDark ? <Sun /> : <Moon />}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100svh-3.5rem)] max-w-[1024px] flex-col px-4 sm:px-6">
        <section aria-label="Workbook selection" className="border-b py-4">
          <Tabs onValueChange={switchWorkbook} value={workbookId}>
            <div className="overflow-x-auto pb-1">
              <TabsList aria-label="Preloaded workbooks" className="min-w-max" variant="line">
                {Object.values(WORKBOOKS).map((item) => (
                  <TabsTrigger key={item.id} value={item.id}>
                    <FileSpreadsheet data-icon="inline-start" />
                    {item.name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
          </Tabs>
        </section>

        <section aria-labelledby="workspace-heading" className="flex min-h-0 flex-1 flex-col py-6">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="mb-1 font-mono text-xs text-muted-foreground">
                {workbook.rowCount.toLocaleString()} ROWS · PRELOADED SOURCE
              </p>
              <h1 className="text-2xl font-semibold tracking-[-0.04em] sm:text-3xl" id="workspace-heading">
                Ask about {workbook.name.replace(".xlsx", "")}.
              </h1>
            </div>
            {apiUnavailable ? (
              <Badge variant="outline">Demo works while API is offline</Badge>
            ) : null}
          </div>

          <MessageScrollerProvider>
            <MessageScroller className="min-h-[22rem] flex-1 rounded-xl border bg-card shadow-sm">
              <MessageScrollerViewport>
                <MessageScrollerContent className="gap-5 p-4 sm:p-5">
                  <Marker variant="separator">
                    <MarkerContent>{workbook.name} · demo session</MarkerContent>
                  </Marker>

                  {entries.length === 0 ? (
                    <Empty className="border-0 p-4 sm:p-8">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <Sparkles />
                        </EmptyMedia>
                        <EmptyTitle>Choose a source-backed example</EmptyTitle>
                        <EmptyDescription>
                          This demo responds to the prepared workbook questions below. Free-form prompts explain what is not connected yet.
                        </EmptyDescription>
                      </EmptyHeader>
                      <EmptyContent className="max-w-xl items-stretch">
                        {starterPromptsFor(workbookId).map((scenario) => (
                          <Button
                            key={scenario.id}
                            onClick={() => receivePrompt(scenario.prompt)}
                            variant="outline"
                          >
                            {scenario.prompt}
                          </Button>
                        ))}
                      </EmptyContent>
                    </Empty>
                  ) : null}

                  {entries.map((entry) => (
                    <MessageScrollerItem key={entry.id} scrollAnchor>
                      {entry.kind === "user" ? (
                        <Message align="end">
                          <MessageContent>
                            <Bubble align="end">
                              <BubbleContent>{entry.text}</BubbleContent>
                            </Bubble>
                          </MessageContent>
                        </Message>
                      ) : null}

                      {entry.kind === "answer" ? (
                        <Message>
                          <MessageAvatar>
                            <Bot />
                          </MessageAvatar>
                          <MessageContent>
                            <MessageHeader>Workbook Assistant</MessageHeader>
                            <ResultCard
                              confirmationRequired={confirmationRequired}
                              isConfirmed={
                                sessionState === "confirmed" &&
                                entry.scenario.id === pendingScenario?.id
                              }
                              onConfirm={startConfirmation}
                              scenario={entry.scenario}
                            />
                          </MessageContent>
                        </Message>
                      ) : null}

                      {entry.kind === "unsupported" ? (
                        <Message>
                          <MessageAvatar>
                            <Bot />
                          </MessageAvatar>
                          <MessageContent>
                            <MessageHeader>Workbook Assistant</MessageHeader>
                            <Bubble variant="tinted">
                              <BubbleContent>
                                The agent endpoint is not connected for arbitrary prompts. Try one of the prepared examples for this source instead.
                              </BubbleContent>
                            </Bubble>
                            <div className="flex flex-wrap gap-2 px-3">
                              {starterPromptsFor(workbookId).map((scenario) => (
                                <Button
                                  key={scenario.id}
                                  onClick={() => receivePrompt(scenario.prompt)}
                                  size="sm"
                                  variant="outline"
                                >
                                  {scenario.id === "channel-roas" ? "Channel ROAS" : "Campaign budget update"}
                                </Button>
                              ))}
                            </div>
                          </MessageContent>
                        </Message>
                      ) : null}
                    </MessageScrollerItem>
                  ))}

                  {sessionState === "responding" ? (
                    <MessageScrollerItem scrollAnchor>
                      <Message>
                        <MessageAvatar>
                          <Bot />
                        </MessageAvatar>
                        <MessageContent>
                          <Marker role="status">
                            <MarkerIcon>
                              <Table2 />
                            </MarkerIcon>
                            <MarkerContent>Checking the prepared demo result…</MarkerContent>
                          </Marker>
                          <Skeleton className="h-24 max-w-md" />
                        </MessageContent>
                      </Message>
                    </MessageScrollerItem>
                  ) : null}
                </MessageScrollerContent>
              </MessageScrollerViewport>
              <MessageScrollerButton />
            </MessageScroller>
          </MessageScrollerProvider>

          <form className="mt-4 shrink-0" onSubmit={submitPrompt}>
            <InputGroup>
              <InputGroupTextarea
                aria-label="Ask the workbook assistant"
                disabled={sessionState === "responding"}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder="Ask a prepared question or try one of the examples…"
                rows={3}
                value={prompt}
              />
              <InputGroupAddon align="block-end" className="border-t">
                <span className="mr-auto text-xs text-muted-foreground">Frontend demo · no workbook writes</span>
                <InputGroupButton disabled={!prompt.trim() || sessionState === "responding"} size="sm" type="submit">
                  <Send data-icon="inline-start" />
                  Send
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </form>
        </section>
      </main>

      <AlertDialog onOpenChange={setConfirmationOpen} open={confirmationOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm this demo change?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingScenario?.mutationPreview?.matchedIds.join(", ")} will show a proposed Budget Allocated change from $24,500 to $30,000. This confirms frontend demo state only.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDemoChange}>Confirm demo change</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default App
