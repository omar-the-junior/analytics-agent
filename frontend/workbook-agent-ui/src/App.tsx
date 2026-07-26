import { useEffect, useMemo, useState, type FormEvent } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowLeft,
  Bot,
  Check,
  ChevronDown,
  FileSpreadsheet,
  History,
  Info,
  Moon,
  PanelLeft,
  PanelRight,
  Plus,
  Send,
  Sparkles,
  Sun,
  Table2,
  Trash2,
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
import { Separator } from "@/components/ui/separator"
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
import { useTheme } from "@/components/theme-provider"
import {
  type DemoScenario,
  type DemoScenarioId,
  type MutationPreview,
  type WorkbookId,
  DEMO_SCENARIOS,
  WORKBOOKS,
  findScenario,
  starterPromptsFor,
} from "@/demo/workbooks"
import {
  type SessionStore,
  type WorkbookSession,
  createExampleSessions,
  createSession,
  loadSessionStore,
  persistSessionStore,
  sessionTitleForPrompt,
} from "@/demo/sessions"
import { cn } from "@/lib/utils"

type AgentConfiguration = {
  provider: string
  model: string
  write_confirmation_required: boolean
  available_tools: string[]
}

type PendingConfirmation = {
  sessionId: string
  scenarioId: DemoScenarioId
}

type PendingDeletion = {
  sessionId: string
  title: string
}

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
                  {row.detail ? <p className="text-xs text-muted-foreground">{row.detail}</p> : null}
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

function WorkspaceNavigation({
  activeSession,
  sessions,
  onNewChat,
  onOpenSource,
  onRequestDelete,
  onSelectSession,
}: {
  activeSession: WorkbookSession | null
  sessions: WorkbookSession[]
  onNewChat: () => void
  onOpenSource: (workbookId: WorkbookId) => void
  onRequestDelete: (session: WorkbookSession) => void
  onSelectSession: (sessionId: string) => void
}) {
  return (
    <nav aria-label="Workbook workspace" className="flex min-h-0 flex-1 flex-col gap-4 p-3">
      <div className="flex flex-col gap-1">
        <p className="px-2 text-xs font-medium tracking-wide text-muted-foreground uppercase">Sources</p>
        {Object.values(WORKBOOKS).map((workbook) => (
          <Button
            className="justify-start"
            key={workbook.id}
            onClick={() => onOpenSource(workbook.id)}
            size="sm"
            variant={workbook.id === activeSession?.workbookId ? "secondary" : "ghost"}
          >
            <FileSpreadsheet data-icon="inline-start" />
            <span className="truncate">{workbook.name.replace(".xlsx", "")}</span>
          </Button>
        ))}
      </div>

      <Separator />

      <div className="flex min-h-0 flex-1 flex-col gap-2">
        <div className="flex items-center justify-between px-2">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Chats</p>
          <Button
            aria-label="Start a new chat"
            onClick={onNewChat}
            size="icon-sm"
            variant="ghost"
          >
            <Plus />
          </Button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-1">
          {Object.values(WORKBOOKS).map((workbook) => {
            const workbookSessions = sessions.filter((session) => session.workbookId === workbook.id)

            return (
              <div className="flex flex-col gap-1" key={workbook.id}>
                <p className="px-2 text-xs text-muted-foreground">{workbook.name.replace(".xlsx", "")}</p>
                {workbookSessions.map((session) => (
                  <div className="flex items-center gap-1" key={session.id}>
                    <Button
                      className="min-w-0 flex-1 justify-start"
                      onClick={() => onSelectSession(session.id)}
                      size="sm"
                      variant={session.id === activeSession?.id ? "secondary" : "ghost"}
                    >
                      <History data-icon="inline-start" />
                      <span className="truncate">{session.title}</span>
                    </Button>
                    <Button
                      aria-label={`Delete chat titled ${session.title}`}
                      onClick={() => onRequestDelete(session)}
                      size="icon-sm"
                      variant="ghost"
                    >
                      <Trash2 />
                    </Button>
                  </div>
                ))}
                {workbookSessions.length === 0 ? (
                  <p className="px-2 py-1 text-xs text-muted-foreground">No chats yet</p>
                ) : null}
              </div>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

export function App() {
  const { setTheme, theme } = useTheme()
  const configuration = useQuery({ queryKey: ["agent-configuration"], queryFn: fetchAgentConfiguration })
  const [sessionStore, setSessionStore] = useState<SessionStore>(() => loadSessionStore())
  const [draftSession, setDraftSession] = useState<WorkbookSession | null>(null)
  const [prompt, setPrompt] = useState("")
  const [respondingSessionId, setRespondingSessionId] = useState<string | null>(null)
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation | null>(null)
  const [confirmationOpen, setConfirmationOpen] = useState(false)
  const [pendingDeletion, setPendingDeletion] = useState<PendingDeletion | null>(null)
  const [deletionOpen, setDeletionOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [navigationOpen, setNavigationOpen] = useState(false)
  const [sourcePickerOpen, setSourcePickerOpen] = useState(false)
  const [pickerWorkbookId, setPickerWorkbookId] = useState<WorkbookId | null>(null)

  const isMobile = useIsMobile()
  const isDark = theme === "dark"
  const confirmationRequired = configuration.data?.write_confirmation_required ?? true
  const apiUnavailable = configuration.isError
  const activeSession = useMemo(
    () =>
      sessionStore.sessions.find((session) => session.id === sessionStore.activeSessionId) ??
      draftSession,
    [draftSession, sessionStore]
  )
  const workbook = activeSession ? WORKBOOKS[activeSession.workbookId] : null
  const isResponding = activeSession ? respondingSessionId === activeSession.id : false
  const pickerWorkbook = pickerWorkbookId ? WORKBOOKS[pickerWorkbookId] : null
  const pickerSessions = pickerWorkbookId
    ? sessionStore.sessions.filter((session) => session.workbookId === pickerWorkbookId)
    : []

  useEffect(() => {
    persistSessionStore(sessionStore)
  }, [sessionStore])

  function updateSession(sessionId: string, update: (session: WorkbookSession) => WorkbookSession) {
    setSessionStore((currentStore) => ({
      ...currentStore,
      sessions: currentStore.sessions.map((session) => (session.id === sessionId ? update(session) : session)),
    }))
  }

  function selectSession(sessionId: string) {
    setSessionStore((currentStore) => ({ ...currentStore, activeSessionId: sessionId }))
    setPrompt("")
    setNavigationOpen(false)
    setSourcePickerOpen(false)
  }

  function showNewChat() {
    setDraftSession(null)
    setSessionStore((currentStore) => ({ ...currentStore, activeSessionId: null }))
    setPrompt("")
    setNavigationOpen(false)
    setSourcePickerOpen(false)
  }

  function chooseDraftSource(workbookId: WorkbookId) {
    setDraftSession(createSession(workbookId))
    setSessionStore((currentStore) => ({ ...currentStore, activeSessionId: null }))
    setPrompt("")
    setNavigationOpen(false)
    setSourcePickerOpen(false)
  }

  function loadExampleChats() {
    const sessions = createExampleSessions()

    setDraftSession(null)
    setSessionStore({
      version: 1,
      activeSessionId: sessions[0].id,
      sessions,
    })
    setPrompt("")
  }

  function requestDeleteChat(session: WorkbookSession) {
    setPendingDeletion({ sessionId: session.id, title: session.title })
    setDeletionOpen(true)
  }

  function confirmDeleteChat() {
    if (!pendingDeletion) {
      return
    }

    const willHaveNoSavedChats = sessionStore.sessions.length === 1

    setSessionStore((currentStore) => {
      const remainingSessions = currentStore.sessions.filter((session) => session.id !== pendingDeletion.sessionId)

      if (remainingSessions.length === 0) {
        return {
          ...currentStore,
          activeSessionId: null,
          sessions: [],
        }
      }

      return {
        ...currentStore,
        activeSessionId:
          currentStore.activeSessionId === pendingDeletion.sessionId
            ? remainingSessions[0].id
            : currentStore.activeSessionId,
        sessions: remainingSessions,
      }
    })
    if (willHaveNoSavedChats) {
      setDraftSession(null)
    }
    setPrompt("")
    setDeletionOpen(false)
    setPendingDeletion(null)
  }

  function openSourcePicker(workbookId?: WorkbookId) {
    setPickerWorkbookId(workbookId ?? null)
    setSourcePickerOpen(true)
    setNavigationOpen(false)
  }

  function receivePrompt(nextPrompt: string) {
    const text = nextPrompt.trim()
    const targetSession = activeSession

    if (!targetSession || !text || respondingSessionId === targetSession.id) {
      return
    }

    const startedSession: WorkbookSession = {
      ...targetSession,
      entries: [...targetSession.entries, { id: crypto.randomUUID(), kind: "user", text }],
      title: targetSession.entries.length === 0 ? sessionTitleForPrompt(text) : targetSession.title,
      updatedAt: new Date().toISOString(),
    }

    if (sessionStore.activeSessionId === targetSession.id) {
      updateSession(targetSession.id, () => startedSession)
    } else {
      setSessionStore((currentStore) => ({
        ...currentStore,
        activeSessionId: startedSession.id,
        sessions: [startedSession, ...currentStore.sessions],
      }))
    }
    setPrompt("")
    setRespondingSessionId(targetSession.id)

    window.setTimeout(() => {
      const scenario = findScenario(text, targetSession.workbookId)

      updateSession(targetSession.id, (session) => ({
        ...session,
        entries: [
          ...session.entries,
          scenario
            ? { id: crypto.randomUUID(), kind: "answer", scenarioId: scenario.id }
            : { id: crypto.randomUUID(), kind: "unsupported", text },
        ],
        updatedAt: new Date().toISOString(),
      }))
      setRespondingSessionId((currentSessionId) =>
        currentSessionId === targetSession.id ? null : currentSessionId
      )
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

    if (!scenario || !activeSession) {
      return
    }

    if (!confirmationRequired) {
      updateSession(activeSession.id, (session) => ({
        ...session,
        confirmedScenarioIds: [...new Set([...session.confirmedScenarioIds, scenario.id])],
      }))
      return
    }

    setPendingConfirmation({ sessionId: activeSession.id, scenarioId: scenario.id })
    setConfirmationOpen(true)
  }

  function confirmDemoChange() {
    if (pendingConfirmation) {
      updateSession(pendingConfirmation.sessionId, (session) => ({
        ...session,
        confirmedScenarioIds: [...new Set([...session.confirmedScenarioIds, pendingConfirmation.scenarioId])],
      }))
    }

    setConfirmationOpen(false)
    setPendingConfirmation(null)
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <aside className="hidden h-full w-72 shrink-0 border-r bg-card md:flex md:flex-col">
        <div className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <div className="grid size-7 place-items-center rounded-md bg-primary font-mono text-xs font-bold text-primary-foreground">
            W
          </div>
          <p className="text-sm font-semibold tracking-tight">Workbook Assistant</p>
        </div>
        <WorkspaceNavigation
          activeSession={activeSession}
          onNewChat={showNewChat}
          onOpenSource={openSourcePicker}
          onRequestDelete={requestDeleteChat}
          onSelectSession={selectSession}
          sessions={sessionStore.sessions}
        />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b bg-background/90 px-3 backdrop-blur sm:px-5">
          <div className="flex min-w-0 items-center gap-2">
            <Sheet onOpenChange={setNavigationOpen} open={navigationOpen}>
              <SheetTrigger asChild>
                <Button aria-label="Open workspace navigation" className="md:hidden" size="icon-sm" variant="ghost">
                  <PanelLeft />
                </Button>
              </SheetTrigger>
              <SheetContent className="w-[min(20rem,calc(100%-2rem))] p-0" side="left">
                <SheetHeader className="border-b px-4 py-4 text-left">
                  <SheetTitle>Workbook Assistant</SheetTitle>
                  <SheetDescription>Sources and saved chats</SheetDescription>
                </SheetHeader>
                <WorkspaceNavigation
                  activeSession={activeSession}
                  onNewChat={showNewChat}
                  onOpenSource={openSourcePicker}
                  onRequestDelete={requestDeleteChat}
                  onSelectSession={selectSession}
                  sessions={sessionStore.sessions}
                />
              </SheetContent>
            </Sheet>
            <div className="grid size-7 shrink-0 place-items-center rounded-md bg-primary font-mono text-xs font-bold text-primary-foreground md:hidden">
              W
            </div>
            <p className="truncate text-sm font-semibold tracking-tight md:hidden">Workbook Assistant</p>
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
            {activeSession && workbook ? (
              <Sheet onOpenChange={setDetailsOpen} open={detailsOpen}>
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
                  <WorkbookDetails workbookId={activeSession.workbookId} />
                </SheetContent>
              </Sheet>
            ) : (
              <Button aria-label="Choose a source to view workbook details" disabled size="icon-sm" variant="ghost">
                <PanelRight />
              </Button>
            )}
            <Button
              aria-label="Toggle color theme"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              size="icon-sm"
              variant="ghost"
            >
              {isDark ? <Sun /> : <Moon />}
            </Button>
          </div>
        </header>

        <main className="flex min-h-0 flex-1 flex-col">
          {activeSession && workbook ? (
          <section aria-labelledby="workspace-heading" className="flex min-h-0 flex-1 flex-col">
            <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b px-4 py-3 sm:px-6">
              <div className="min-w-0">
                <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">Working in</p>
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <FileSpreadsheet className="text-primary" />
                  <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg" id="workspace-heading">
                    {workbook.name}
                  </h1>
                  <Badge variant="secondary">{workbook.rowCount.toLocaleString()} rows</Badge>
                  {apiUnavailable ? <Badge variant="outline">Demo mode</Badge> : null}
                </div>
              </div>
              <Button onClick={() => openSourcePicker()} size="sm" variant="outline">
                <FileSpreadsheet data-icon="inline-start" />
                Change source
              </Button>
            </div>

            <MessageScrollerProvider>
              <MessageScroller className="min-h-0 flex-1 rounded-none border-0 bg-background shadow-none">
                <MessageScrollerViewport>
                  <MessageScrollerContent className="mx-auto w-full max-w-4xl gap-5 px-4 py-5 sm:px-6">
                    <Marker variant="separator">
                      <MarkerContent>{activeSession.title} · {workbook.name}</MarkerContent>
                    </Marker>

                    {activeSession.entries.length === 0 ? (
                      <Empty className="mx-auto w-full max-w-xl border-0 py-8 sm:py-12">
                        <EmptyHeader>
                          <EmptyMedia variant="icon">
                            <Sparkles />
                          </EmptyMedia>
                          <EmptyTitle>Ask about this workbook</EmptyTitle>
                          <EmptyDescription>
                            Choose a prepared question for {workbook.name.replace(".xlsx", "")}, or type your own.
                          </EmptyDescription>
                        </EmptyHeader>
                        <EmptyContent className="w-full items-stretch">
                          {starterPromptsFor(activeSession.workbookId).map((scenario) => (
                            <Button key={scenario.id} onClick={() => receivePrompt(scenario.prompt)} variant="outline">
                              {scenario.prompt}
                            </Button>
                          ))}
                        </EmptyContent>
                      </Empty>
                    ) : null}

                    {activeSession.entries.map((entry) => (
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
                                isConfirmed={activeSession.confirmedScenarioIds.includes(entry.scenarioId)}
                                onConfirm={startConfirmation}
                                scenario={DEMO_SCENARIOS[entry.scenarioId]}
                              />
                            </MessageContent>
                          </Message>
                        ) : null}

                        {entry.kind === "agent" ? (
                          <Message>
                            <MessageAvatar>
                              <Bot />
                            </MessageAvatar>
                            <MessageContent>
                              <MessageHeader>Workbook Assistant</MessageHeader>
                              <Bubble variant="tinted">
                                <BubbleContent>{entry.text}</BubbleContent>
                              </Bubble>
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
                                {starterPromptsFor(activeSession.workbookId).map((scenario) => (
                                  <Button key={scenario.id} onClick={() => receivePrompt(scenario.prompt)} size="sm" variant="outline">
                                    {scenario.id === "channel-roas" ? "Channel ROAS" : "Campaign budget update"}
                                  </Button>
                                ))}
                              </div>
                            </MessageContent>
                          </Message>
                        ) : null}
                      </MessageScrollerItem>
                    ))}

                    {isResponding ? (
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

            <form className="shrink-0 border-t bg-background px-4 py-3 sm:px-6" onSubmit={submitPrompt}>
              <div className="mx-auto max-w-4xl">
                <InputGroup>
                  <InputGroupTextarea
                    aria-label="Ask the workbook assistant"
                    disabled={isResponding}
                    onChange={(event) => setPrompt(event.target.value)}
                    placeholder={`Ask about ${workbook.name.replace(".xlsx", "")}…`}
                    rows={2}
                    value={prompt}
                  />
                  <InputGroupAddon align="block-end" className="border-t">
                    <span className="mr-auto text-xs text-muted-foreground">Local chat · no workbook writes</span>
                    <InputGroupButton disabled={!prompt.trim() || isResponding} size="sm" type="submit">
                      <Send data-icon="inline-start" />
                      Send
                    </InputGroupButton>
                  </InputGroupAddon>
                </InputGroup>
              </div>
            </form>
          </section>
          ) : (
            <section aria-labelledby="new-chat-heading" className="flex min-h-0 flex-1 flex-col">
              <div className="shrink-0 border-b px-4 py-3 sm:px-6">
                <p className="mb-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">New chat</p>
                <h1 className="text-base font-semibold tracking-tight sm:text-lg" id="new-chat-heading">
                  Choose a source to begin
                </h1>
              </div>
              <Empty className="m-auto w-full max-w-xl border-0 px-4 py-8 sm:py-12">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileSpreadsheet />
                  </EmptyMedia>
                  <EmptyTitle>What would you like to work in?</EmptyTitle>
                  <EmptyDescription>
                    Select a workbook to open an unsaved draft chat. It will be added to your history after your first message.
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent className="w-full items-stretch">
                  {Object.values(WORKBOOKS).map((source) => (
                    <Button
                      aria-label={`Start a new chat with ${source.name}`}
                      className="h-auto justify-start py-3"
                      key={source.id}
                      onClick={() => chooseDraftSource(source.id)}
                      variant="outline"
                    >
                      <FileSpreadsheet data-icon="inline-start" />
                      <span className="flex min-w-0 flex-col items-start gap-0.5">
                        <span className="truncate">{source.name}</span>
                        <span className="text-xs font-normal text-muted-foreground">
                          {source.rowCount.toLocaleString()} rows
                        </span>
                      </span>
                    </Button>
                  ))}
                  {sessionStore.sessions.length === 0 ? (
                    <Button onClick={loadExampleChats} variant="secondary">
                      <Sparkles data-icon="inline-start" />
                      Load 3 example chats
                    </Button>
                  ) : null}
                </EmptyContent>
                {sessionStore.sessions.length === 0 ? (
                  <p className="mt-3 text-center text-xs text-muted-foreground">
                    Includes analysis follow-ups and a confirmed change preview. Examples are stored locally and can be deleted.
                  </p>
                ) : null}
              </Empty>
            </section>
          )}
        </main>
      </div>

      <Sheet
        onOpenChange={(open) => {
          setSourcePickerOpen(open)
          if (!open) {
            setPickerWorkbookId(null)
          }
        }}
        open={sourcePickerOpen}
      >
        <SheetContent className="w-[min(28rem,calc(100%-2rem))]" side={isMobile ? "bottom" : "right"}>
          <SheetHeader>
            <SheetTitle>{pickerWorkbook ? `Open ${pickerWorkbook.name}` : "Choose a workbook"}</SheetTitle>
            <SheetDescription>
              {pickerWorkbook
                ? "Choose an existing chat or start a fresh one."
                : "Choose the workbook you want to work in."}
            </SheetDescription>
          </SheetHeader>
          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 pb-6">
            {pickerWorkbook ? (
              <>
                <Button className="justify-start" onClick={() => setPickerWorkbookId(null)} size="sm" variant="ghost">
                  <ArrowLeft data-icon="inline-start" />
                  All workbooks
                </Button>
                <Button onClick={() => chooseDraftSource(pickerWorkbook.id)}>
                  <Plus data-icon="inline-start" />
                  Start new chat
                </Button>
                <Separator />
                <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Existing chats</p>
                {pickerSessions.map((session) => (
                  <Button className="justify-start" key={session.id} onClick={() => selectSession(session.id)} variant="outline">
                    <History data-icon="inline-start" />
                    <span className="truncate">{session.title}</span>
                  </Button>
                ))}
              </>
            ) : (
              Object.values(WORKBOOKS).map((source) => (
                <Button className="h-auto justify-start py-3" key={source.id} onClick={() => setPickerWorkbookId(source.id)} variant="outline">
                  <FileSpreadsheet data-icon="inline-start" />
                  <span className="flex min-w-0 flex-col items-start gap-0.5">
                    <span className="truncate">{source.name}</span>
                    <span className="text-xs font-normal text-muted-foreground">{source.rowCount.toLocaleString()} rows</span>
                  </span>
                </Button>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog onOpenChange={setConfirmationOpen} open={confirmationOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirm this demo change?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingConfirmation ? DEMO_SCENARIOS[pendingConfirmation.scenarioId].mutationPreview?.matchedIds.join(", ") : "This campaign"} will show a proposed Budget Allocated change from $24,500 to $30,000. This confirms frontend demo state only.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep reviewing</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDemoChange}>Confirm demo change</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        onOpenChange={(open) => {
          setDeletionOpen(open)
          if (!open) {
            setPendingDeletion(null)
          }
        }}
        open={deletionOpen}
      >
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDeletion
                ? `“${pendingDeletion.title}” and its messages will be removed from this device.`
                : "This chat and its messages will be removed from this device."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep chat</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDeleteChat} variant="destructive">
              Delete chat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default App
