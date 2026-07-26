import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"
import { ThemeProvider } from "@/components/theme-provider"

const configuration = {
  provider: "local",
  model: "demo-model",
  write_confirmation_required: true,
  available_tools: [],
}

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <ThemeProvider defaultTheme="light" storageKey="test-theme">
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  )
}

async function submitPreparedPrompt(user: ReturnType<typeof userEvent.setup>, prompt: string) {
  await user.click(screen.getByRole("button", { name: prompt }))
}

describe("workbook assistant demo", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => configuration }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it("switches workbooks with keyboard navigation and shows source-specific prompts", async () => {
    const user = userEvent.setup()
    renderApp()

    const realEstateTab = screen.getByRole("tab", { name: /real estate listings/i })
    realEstateTab.focus()
    await user.keyboard("{ArrowRight}")

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Marketing Campaigns")
    expect(screen.getByRole("button", { name: "Which channel has the highest aggregate ROAS?" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Change CMP-8002's Budget Allocated to $30,000." })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Show me a listing status overview." })).not.toBeInTheDocument()
  })

  it("returns the verified listing-status overview", async () => {
    const user = userEvent.setup()
    renderApp()

    await submitPreparedPrompt(user, "Show me a listing status overview.")

    expect(await screen.findByText("316 Active · 211 Pending · 473 Sold")).toBeInTheDocument()
    expect(screen.getByText("473 listings")).toBeInTheDocument()
    expect(screen.getByText(/sale price is meaningful only for sold listings/i)).toBeInTheDocument()
  })

  it("returns the aggregate channel ROAS formula and value", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("tab", { name: /marketing campaigns/i }))
    await submitPreparedPrompt(user, "Which channel has the highest aggregate ROAS?")

    expect(await screen.findByText("Email has the highest aggregate ROAS at 12.99×.")).toBeInTheDocument()
    expect(screen.getByText("$21,021,486.18")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "How this was calculated" }))
    expect(screen.getByText(/total revenue ÷ total amount spent/i)).toBeInTheDocument()
  })

  it("previews and confirms the single campaign budget demo change without writing a workbook", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("tab", { name: /marketing campaigns/i }))
    await submitPreparedPrompt(user, "Change CMP-8002's Budget Allocated to $30,000.")

    expect((await screen.findAllByText("CMP-8002")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("$24,500").length).toBeGreaterThan(0)
    expect(screen.getAllByText("$30,000").length).toBeGreaterThan(0)

    await user.click(screen.getByRole("button", { name: "Review demo change" }))
    const dialog = await screen.findByRole("alertdialog", { name: "Confirm this demo change?" })
    expect(within(dialog).getByText(/frontend demo state only/i)).toBeInTheDocument()
    expect(document.activeElement).toBeInTheDocument()

    await user.click(within(dialog).getByRole("button", { name: "Confirm demo change" }))
    expect(await screen.findByText("Demo change confirmed; no workbook was written.")).toBeInTheDocument()
  })

  it("explains unsupported prompts and remains usable while the API is offline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")))
    const user = userEvent.setup()
    renderApp()

    await waitFor(() => expect(screen.getByText("API offline")).toBeInTheDocument())
    await user.type(screen.getByRole("textbox", { name: "Ask the workbook assistant" }), "Summarize every city")
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText(/agent endpoint is not connected for arbitrary prompts/i)).toBeInTheDocument()
    expect(screen.getByText("Demo works while API is offline")).toBeInTheDocument()
  })
})
