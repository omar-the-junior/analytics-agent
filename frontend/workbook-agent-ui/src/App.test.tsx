import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { cleanup, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import App from "@/App"
import { ThemeProvider } from "@/components/theme-provider"
import { SESSION_STORAGE_KEY } from "@/demo/sessions"

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

async function startMarketingChat(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Start a new chat with Marketing Campaigns.xlsx" }))
}

async function startRealEstateChat(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Start a new chat with Real Estate Listings.xlsx" }))
}

async function submitPreparedPrompt(user: ReturnType<typeof userEvent.setup>, prompt: string) {
  await user.click(screen.getByRole("button", { name: prompt }))
}

describe("workbook assistant demo", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => configuration }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    localStorage.clear()
  })

  it("shows a source chooser before creating an unsaved chat draft", async () => {
    const user = userEvent.setup()
    renderApp()

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Choose a source to begin")
    expect(screen.getByRole("button", { name: "Start a new chat with Real Estate Listings.xlsx" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Start a new chat with Marketing Campaigns.xlsx" })).toBeInTheDocument()

    await waitFor(() => expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull())

    await startRealEstateChat(user)
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Real Estate Listings.xlsx")
    expect(screen.getByRole("button", { name: "Show me a listing status overview." })).toBeInTheDocument()
    expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()
  })

  it("loads three populated, deletable example conversations on demand", async () => {
    const user = userEvent.setup()
    renderApp()

    await user.click(screen.getByRole("button", { name: "Load 3 example chats" }))

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Real Estate Listings.xlsx")
    expect(screen.getByText("Why should I focus on Sold listings for price analysis?")).toBeInTheDocument()
    expect(
      screen.getByText(/Sold listings have completed Sale Price values/i)
    ).toBeInTheDocument()
    await waitFor(() => expect(localStorage.getItem(SESSION_STORAGE_KEY)).not.toBeNull())
    expect(screen.getByRole("button", { name: "Delete chat titled Channel performance review" })).toBeInTheDocument()
  })

  it("lets the user choose a workbook, then start a new source-specific chat", async () => {
    const user = userEvent.setup()
    renderApp()

    await startMarketingChat(user)

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Marketing Campaigns.xlsx")
    expect(screen.getByRole("button", { name: "Which channel has the highest aggregate ROAS?" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Change CMP-8002's Budget Allocated to $30,000." })).toBeInTheDocument()
  })

  it("deletes a saved chat after confirmation and keeps an unsaved replacement draft", async () => {
    const user = userEvent.setup()
    renderApp()

    await startRealEstateChat(user)
    await submitPreparedPrompt(user, "Show me a listing status overview.")
    await screen.findByText("316 Active · 211 Pending · 473 Sold")
    await user.click(screen.getByRole("button", { name: "Start a new chat" }))
    await user.click(screen.getByRole("button", { name: "Delete chat titled Show me a listing status overview." }))

    const dialog = await screen.findByRole("alertdialog", { name: "Delete this chat?" })
    expect(within(dialog).getByText(/will be removed from this device/i)).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Delete chat" }))

    await waitFor(() => {
      expect(localStorage.getItem(SESSION_STORAGE_KEY)).toBeNull()
    })
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Choose a source to begin")
  })

  it("returns the verified listing-status overview", async () => {
    const user = userEvent.setup()
    renderApp()

    await startRealEstateChat(user)
    await submitPreparedPrompt(user, "Show me a listing status overview.")

    expect(await screen.findByText("316 Active · 211 Pending · 473 Sold")).toBeInTheDocument()
    expect(screen.getByText("473 listings")).toBeInTheDocument()
    expect(screen.getByText(/sale price is meaningful only for sold listings/i)).toBeInTheDocument()
  })

  it("returns the aggregate channel ROAS formula and value", async () => {
    const user = userEvent.setup()
    renderApp()

    await startMarketingChat(user)
    await submitPreparedPrompt(user, "Which channel has the highest aggregate ROAS?")

    expect(await screen.findByText("Email has the highest aggregate ROAS at 12.99×.")).toBeInTheDocument()
    expect(screen.getByText("$21,021,486.18")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "How this was calculated" }))
    expect(screen.getByText(/total revenue ÷ total amount spent/i)).toBeInTheDocument()
  })

  it("previews and confirms the single campaign budget demo change without writing a workbook", async () => {
    const user = userEvent.setup()
    renderApp()

    await startMarketingChat(user)
    await submitPreparedPrompt(user, "Change CMP-8002's Budget Allocated to $30,000.")

    expect((await screen.findAllByText("CMP-8002")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("$24,500").length).toBeGreaterThan(0)
    expect(screen.getAllByText("$30,000").length).toBeGreaterThan(0)

    await user.click(screen.getByRole("button", { name: "Review demo change" }))
    const dialog = await screen.findByRole("alertdialog", { name: "Confirm this demo change?" })
    expect(within(dialog).getByText(/frontend demo state only/i)).toBeInTheDocument()

    await user.click(within(dialog).getByRole("button", { name: "Confirm demo change" }))
    expect(await screen.findByText("Demo change confirmed; no workbook was written.")).toBeInTheDocument()
  })

  it("explains unsupported prompts and remains usable while the API is offline", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")))
    const user = userEvent.setup()
    renderApp()

    await waitFor(() => expect(screen.getByText("API offline")).toBeInTheDocument())
    await startRealEstateChat(user)
    await user.type(screen.getByRole("textbox", { name: "Ask the workbook assistant" }), "Summarize every city")
    await user.click(screen.getByRole("button", { name: "Send" }))

    expect(await screen.findByText(/agent endpoint is not connected for arbitrary prompts/i)).toBeInTheDocument()
    expect(screen.getByText("Demo mode")).toBeInTheDocument()
  })
})
