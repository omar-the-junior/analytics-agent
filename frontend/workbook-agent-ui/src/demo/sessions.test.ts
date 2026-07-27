import { describe, expect, it } from "vitest"

import {
  SESSION_STORAGE_KEY,
  createExampleSessions,
  createSession,
  createInitialSessionStore,
  loadSessionStore,
  persistSessionStore,
} from "@/demo/sessions"

describe("workbook chat sessions", () => {
  it("creates an empty store when storage is empty", () => {
    const storage = new Map<string, string>()
    const store = loadSessionStore({
      getItem: (key: string) => storage.get(key) ?? null,
    } as unknown as Storage)

    expect(store.sessions).toEqual([])
    expect(store.activeSessionId).toBeNull()
  })

  it("recovers safely from an invalid saved value", () => {
    const store = loadSessionStore({
      getItem: () => "not json",
    } as unknown as Storage)

    expect(store.sessions).toEqual([])
    expect(store.activeSessionId).toBeNull()
  })

  it("does not persist an empty draft store", () => {
    const values = new Map<string, string>([
      [SESSION_STORAGE_KEY, "legacy draft"],
    ])
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => values.set(key, value),
    } as unknown as Storage

    persistSessionStore(createInitialSessionStore(), storage)

    expect(values.has(SESSION_STORAGE_KEY)).toBe(false)
  })

  it("writes only started chats to the versioned session store", () => {
    const values = new Map<string, string>()
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      removeItem: (key: string) => values.delete(key),
      setItem: (key: string, value: string) => values.set(key, value),
    } as unknown as Storage
    const store = createInitialSessionStore()
    const session = createSession("real-estate")
    session.entries.push({
      id: "entry-1",
      kind: "user",
      text: "Show me a listing status overview.",
    })
    store.activeSessionId = session.id
    store.sessions.push(session)

    persistSessionStore(store, storage)

    expect(JSON.parse(values.get(SESSION_STORAGE_KEY) ?? "{}")).toMatchObject({
      version: 1,
      activeSessionId: store.activeSessionId,
    })
    expect(loadSessionStore(storage)).toEqual(store)
  })

  it("creates three populated example chats that can be persisted", () => {
    const sessions = createExampleSessions(new Date("2026-07-26T12:00:00.000Z"))

    expect(sessions).toHaveLength(3)
    expect(sessions.every((session) => session.entries.length > 0)).toBe(true)
    expect(sessions[0]).toMatchObject({
      workbookId: "real-estate",
      title: "Listing status follow-up",
    })
    expect(sessions[2].confirmedScenarioIds).toEqual(["campaign-budget-update"])
  })
})
