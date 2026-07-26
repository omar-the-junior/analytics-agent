import { DEMO_SCENARIOS, type DemoScenarioId, type WorkbookId, WORKBOOKS } from "@/demo/workbooks"

export const SESSION_STORAGE_KEY = "workbook-assistant/sessions/v1"
const SESSION_STORAGE_VERSION = 1

export type ChatEntry =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "agent"; text: string }
  | { id: string; kind: "answer"; scenarioId: DemoScenarioId }
  | { id: string; kind: "unsupported"; text: string }

export type WorkbookSession = {
  id: string
  workbookId: WorkbookId
  title: string
  createdAt: string
  updatedAt: string
  entries: ChatEntry[]
  confirmedScenarioIds: DemoScenarioId[]
}

export type SessionStore = {
  version: number
  activeSessionId: string | null
  sessions: WorkbookSession[]
}

function createId() {
  return globalThis.crypto?.randomUUID?.() ?? `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function createSession(workbookId: WorkbookId, now = new Date()): WorkbookSession {
  const timestamp = now.toISOString()

  return {
    id: createId(),
    workbookId,
    title: "New chat",
    createdAt: timestamp,
    updatedAt: timestamp,
    entries: [],
    confirmedScenarioIds: [],
  }
}

function isWorkbookId(value: unknown): value is WorkbookId {
  return typeof value === "string" && value in WORKBOOKS
}

function isDemoScenarioId(value: unknown): value is DemoScenarioId {
  return typeof value === "string" && value in DEMO_SCENARIOS
}

function isChatEntry(value: unknown): value is ChatEntry {
  if (!value || typeof value !== "object") {
    return false
  }

  const entry = value as Partial<ChatEntry>

  if (typeof entry.id !== "string") {
    return false
  }

  if (entry.kind === "answer") {
    return isDemoScenarioId(entry.scenarioId)
  }

  return (
    (entry.kind === "user" || entry.kind === "agent" || entry.kind === "unsupported") &&
    typeof entry.text === "string"
  )
}

function isSession(value: unknown): value is WorkbookSession {
  if (!value || typeof value !== "object") {
    return false
  }

  const session = value as Partial<WorkbookSession>

  return (
    typeof session.id === "string" &&
    isWorkbookId(session.workbookId) &&
    typeof session.title === "string" &&
    typeof session.createdAt === "string" &&
    typeof session.updatedAt === "string" &&
    Array.isArray(session.entries) &&
    session.entries.every(isChatEntry) &&
    Array.isArray(session.confirmedScenarioIds) &&
    session.confirmedScenarioIds.every(isDemoScenarioId)
  )
}

export function createInitialSessionStore(): SessionStore {
  return {
    version: SESSION_STORAGE_VERSION,
    activeSessionId: null,
    sessions: [],
  }
}

export function createExampleSessions(now = new Date()): WorkbookSession[] {
  const timestamp = now.toISOString()
  const buildSession = (
    workbookId: WorkbookId,
    title: string,
    entries: ChatEntry[],
    confirmedScenarioIds: DemoScenarioId[] = []
  ): WorkbookSession => ({
    ...createSession(workbookId, now),
    title,
    entries,
    confirmedScenarioIds,
    updatedAt: timestamp,
  })

  return [
    buildSession("real-estate", "Listing status follow-up", [
      { id: createId(), kind: "user", text: "Show me a listing status overview." },
      { id: createId(), kind: "answer", scenarioId: "listing-status-overview" },
      { id: createId(), kind: "user", text: "Why should I focus on Sold listings for price analysis?" },
      {
        id: createId(),
        kind: "agent",
        text: "Sold listings have completed Sale Price values. Active and Pending rows are still in progress, so including them would mix finalized transactions with asking prices or incomplete sales.",
      },
    ]),
    buildSession("marketing", "Channel performance review", [
      { id: createId(), kind: "user", text: "Which channel has the highest aggregate ROAS?" },
      { id: createId(), kind: "answer", scenarioId: "channel-roas" },
      { id: createId(), kind: "user", text: "What should I investigate next?" },
      {
        id: createId(),
        kind: "agent",
        text: "Start with the individual Email campaigns behind this aggregate result. Compare their spend, revenue, and conversion mix before reallocating any budget.",
      },
    ]),
    buildSession(
      "marketing",
      "Campaign budget confirmation",
      [
        { id: createId(), kind: "user", text: "Change CMP-8002's Budget Allocated to $30,000." },
        { id: createId(), kind: "answer", scenarioId: "campaign-budget-update" },
        { id: createId(), kind: "user", text: "Confirm the demo change." },
        {
          id: createId(),
          kind: "agent",
          text: "The demo change is confirmed in this chat. The source workbook was not written or changed.",
        },
      ],
      ["campaign-budget-update"]
    ),
  ]
}

export function loadSessionStore(storage: Storage | null = window.localStorage): SessionStore {
  try {
    const rawValue = storage?.getItem(SESSION_STORAGE_KEY)

    if (!rawValue) {
      return createInitialSessionStore()
    }

    const parsedValue = JSON.parse(rawValue) as Partial<SessionStore>
    const sessions = Array.isArray(parsedValue.sessions)
      ? parsedValue.sessions.filter((session): session is WorkbookSession => isSession(session) && session.entries.length > 0)
      : []
    const activeSession = sessions.find((session) => session.id === parsedValue.activeSessionId)

    if (parsedValue.version !== SESSION_STORAGE_VERSION) {
      return createInitialSessionStore()
    }

    return {
      version: SESSION_STORAGE_VERSION,
      activeSessionId: activeSession?.id ?? sessions[0]?.id ?? null,
      sessions,
    }
  } catch {
    return createInitialSessionStore()
  }
}

export function persistSessionStore(store: SessionStore, storage: Storage | null = window.localStorage) {
  try {
    if (store.sessions.length === 0) {
      storage?.removeItem(SESSION_STORAGE_KEY)
      return
    }

    storage?.setItem(SESSION_STORAGE_KEY, JSON.stringify(store))
  } catch {
    // The demo remains usable when browser storage is unavailable.
  }
}

export function sessionTitleForPrompt(prompt: string) {
  const trimmedPrompt = prompt.trim()

  return trimmedPrompt.length > 42 ? `${trimmedPrompt.slice(0, 42).trimEnd()}…` : trimmedPrompt
}
