import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

class EventSourceMock {
  static readonly instances: EventSourceMock[] = []
  readonly readyState = 1
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  constructor() {
    EventSourceMock.instances.push(this)
  }

  close() {}
}

function stubSessionAndRun() {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: "session-123" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ run_id: "run-123" }),
      })
  )
  vi.stubGlobal("EventSource", EventSourceMock)
}

async function startListingsRun(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: /real estate listings/i })
  )
  await user.type(
    screen.getByRole("textbox", { name: "Ask the workbook assistant" }),
    "Show listings"
  )
  await user.click(screen.getByRole("button", { name: "Send" }))
  await waitFor(() =>
    expect(EventSourceMock.instances.at(-1)?.onmessage).toBeTypeOf("function")
  )
}

async function emit(event: { type: string; data: Record<string, unknown> }) {
  await act(async () => {
    EventSourceMock.instances.at(-1)?.onmessage?.({
      data: JSON.stringify(event),
    } as MessageEvent)
  })
}

function renderApp() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <App />
    </QueryClientProvider>
  )
}

describe("workbook assistant", () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    EventSourceMock.instances.length = 0
  })

  it("creates a backend session when a workbook is selected", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: "session-123" }),
    })
    vi.stubGlobal("fetch", fetchMock)
    const user = userEvent.setup()

    renderApp()
    await user.click(
      screen.getByRole("button", { name: /real estate listings/i })
    )

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/sessions",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ workbook: "listings" }),
      })
    )
    expect(
      await screen.findByRole("heading", { name: "Real Estate Listings" })
    ).toBeInTheDocument()
    expect(screen.queryByText(/load 3 example chats/i)).not.toBeInTheDocument()
  })

  it("keeps the composer editable while a run is in progress", async () => {
    stubSessionAndRun()
    const user = userEvent.setup()

    renderApp()
    await user.click(
      screen.getByRole("button", { name: /real estate listings/i })
    )
    const composer = screen.getByRole("textbox", {
      name: "Ask the workbook assistant",
    })
    await user.type(composer, "Count active listings")
    await user.click(screen.getByRole("button", { name: "Send" }))

    await screen.findByRole("button", { name: "Cancel" })
    expect(composer).not.toBeDisabled()
    await user.type(composer, " and sold listings")
    expect(composer).toHaveValue(" and sold listings")
    await user.click(screen.getByRole("button", { name: "Queue" }))
    expect(composer).toHaveValue("")
    expect(await screen.findByText("1 message queued.")).toBeInTheDocument()
  })

  it("renders Markdown received in an assistant event", async () => {
    stubSessionAndRun()
    const user = userEvent.setup()

    renderApp()
    await user.click(
      screen.getByRole("button", { name: /real estate listings/i })
    )
    await user.type(
      screen.getByRole("textbox", { name: "Ask the workbook assistant" }),
      "Summarize the workbook"
    )
    await user.click(screen.getByRole("button", { name: "Send" }))
    await waitFor(() =>
      expect(EventSourceMock.instances.at(-1)?.onmessage).toBeTypeOf("function")
    )

    await emit({
      type: "assistant_message",
      data: { message: "## Summary\n\n- **Stable ID:** `Listing ID`" },
    })

    expect(await screen.findByRole("heading", { name: "Summary" })).toBeInTheDocument()
    expect(screen.getByRole("listitem")).toHaveTextContent("Stable ID: Listing ID")
    expect(screen.getByText("Listing ID")).toHaveProperty("tagName", "CODE")
  })

  it("renders a structured workbook table without relying on assistant Markdown", async () => {
    stubSessionAndRun()
    const user = userEvent.setup()
    renderApp()
    await startListingsRun(user)

    await emit({
      type: "workbook_result",
      data: {
        result: {
          kind: "table",
          columns: ["Address", "List Price", "Listing ID"],
          rows: [["123 Example Ave", 850000, "LST-5017"]],
          row_count: 2,
          truncated: true,
          stable_id_field: "Listing ID",
          calculation_source: "tool_computed",
        },
      },
    })

    expect(await screen.findByText("123 Example Ave")).toBeInTheDocument()
    expect(screen.getByRole("columnheader", { name: "Listing ID" })).toBeInTheDocument()
    expect(screen.getByText("850,000")).toBeInTheDocument()
    expect(screen.getByText(/2 matching rows; showing 1/i)).toBeInTheDocument()
    expect(screen.getByText(/one or more matching rows are not shown/i)).toBeInTheDocument()
  })

  it("renders selection and metric result kinds from structured events", async () => {
    stubSessionAndRun()
    const user = userEvent.setup()
    renderApp()
    await startListingsRun(user)

    await emit({
      type: "workbook_result",
      data: {
        result: {
          kind: "selection",
          column: "List Price",
          value: 850000,
          row: { "Listing ID": "LST-5017", "List Price": 850000 },
          stable_id_field: "Listing ID",
          stable_id: "LST-5017",
          calculation_source: "tool_computed",
        },
      },
    })
    await emit({
      type: "workbook_result",
      data: {
        result: {
          kind: "metric",
          metric: "count",
          value: 2,
          column: null,
          row_count: 2,
          unavailable: false,
          reason: null,
          calculation_source: "tool_computed",
        },
      },
    })

    expect(await screen.findByText("Workbook selection")).toBeInTheDocument()
    expect(screen.getByText(/Stable ID: Listing ID LST-5017/)).toBeInTheDocument()
    expect(screen.getByText("Workbook metric")).toBeInTheDocument()
    expect(screen.getByText("count: 2")).toBeInTheDocument()
  })

  it("uses the same typed field-diff preview and exact stage id for confirmation", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ session_id: "session-123" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ run_id: "run-123" }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) })
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("EventSource", EventSourceMock)
    const user = userEvent.setup()
    renderApp()
    await startListingsRun(user)

    await emit({
      type: "confirmation_required",
      data: {
        stage_id: "stage-exact-123",
        operation: "update",
        stable_id_field: "Listing ID",
        stable_id: "LST-5001",
        warnings: [],
        preview: {
          kind: "field_diff",
          columns: ["Field", "Before", "After"],
          rows: [["List Price", 351000, 351001]],
        },
      },
    })

    expect(await screen.findByText("List Price")).toBeInTheDocument()
    expect(screen.getByText("351,001")).toBeInTheDocument()
    expect(screen.queryByText('"before"')).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /review and confirm/i }))
    expect(screen.getAllByText(/stage-exact-123/)).toHaveLength(2)
    expect(screen.getAllByRole("columnheader", { name: "After" })).toHaveLength(1)
    await user.click(screen.getByRole("button", { name: "Confirm change" }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenLastCalledWith(
        "/api/sessions/session-123/runs/run-123/confirmation",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ stage_id: "stage-exact-123" }),
        })
      )
    )
  })
})
