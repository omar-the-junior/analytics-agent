import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import App from "@/App"

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
    class EventSourceMock {
      static readonly instances: EventSourceMock[] = []
      readonly readyState = 1
      onerror: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null

      constructor(_url: string) {
        EventSourceMock.instances.push(this)
      }

      close() {}
    }

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
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("EventSource", EventSourceMock)
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
    class EventSourceMock {
      static readonly instances: EventSourceMock[] = []
      readonly readyState = 1
      onerror: ((event: Event) => void) | null = null
      onmessage: ((event: MessageEvent) => void) | null = null

      constructor(_url: string) {
        EventSourceMock.instances.push(this)
      }

      close() {}
    }

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
    vi.stubGlobal("fetch", fetchMock)
    vi.stubGlobal("EventSource", EventSourceMock)
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

    await act(async () => {
      EventSourceMock.instances.at(-1)?.onmessage?.({
        data: JSON.stringify({
          type: "assistant_message",
          data: { message: "## Summary\n\n- **Stable ID:** `Listing ID`" },
        }),
      } as MessageEvent)
    })

    expect(await screen.findByRole("heading", { name: "Summary" })).toBeInTheDocument()
    expect(screen.getByRole("listitem")).toHaveTextContent("Stable ID: Listing ID")
    expect(screen.getByText("Listing ID")).toHaveProperty("tagName", "CODE")
  })
})
