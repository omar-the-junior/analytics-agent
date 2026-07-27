export type WorkbookId = "real-estate" | "marketing"

export type DemoScenarioId =
  "listing-status-overview" | "channel-roas" | "campaign-budget-update"

export type EvidenceRow = {
  label: string
  value: string
  detail?: string
}

export type AnswerPayload = {
  directResult: string
  scope: string[]
  evidence: EvidenceRow[]
  calculation?: string
  caveat?: string
  nextActions: string[]
}

export type MutationPreview = {
  workbook: WorkbookId
  operation: string
  matchedIds: string[]
  changes: Array<{
    field: string
    before: string
    after: string
  }>
  requiresConfirmation: boolean
}

export type DemoScenario = {
  id: DemoScenarioId
  workbookId: WorkbookId
  prompt: string
  answer: AnswerPayload
  mutationPreview?: MutationPreview
}

export type Workbook = {
  id: WorkbookId
  name: string
  rowCount: number
  description: string
  columns: string[]
  starterPrompts: DemoScenarioId[]
}

export const WORKBOOKS: Record<WorkbookId, Workbook> = {
  "real-estate": {
    id: "real-estate",
    name: "Real Estate Listings.xlsx",
    rowCount: 1000,
    description:
      "US property listings across Active, Pending, and Sold statuses.",
    columns: [
      "Listing ID",
      "Property Type",
      "City",
      "State",
      "Bedrooms",
      "Bathrooms",
      "Square Footage",
      "Year Built",
      "List Price",
      "Sale Price",
      "Listing Status",
    ],
    starterPrompts: ["listing-status-overview"],
  },
  marketing: {
    id: "marketing",
    name: "Marketing Campaigns.xlsx",
    rowCount: 1000,
    description:
      "Campaign performance across paid social, search, and email channels.",
    columns: [
      "Campaign ID",
      "Campaign Name",
      "Channel",
      "Start Date",
      "End Date",
      "Budget Allocated",
      "Amount Spent",
      "Impressions",
      "Clicks",
      "Conversions",
      "Revenue Generated",
    ],
    starterPrompts: ["channel-roas", "campaign-budget-update"],
  },
}

export const DEMO_SCENARIOS: Record<DemoScenarioId, DemoScenario> = {
  "listing-status-overview": {
    id: "listing-status-overview",
    workbookId: "real-estate",
    prompt: "Show me a listing status overview.",
    answer: {
      directResult: "316 Active · 211 Pending · 473 Sold",
      scope: ["1,000 listings", "Listing Status"],
      evidence: [
        { label: "Active", value: "316 listings" },
        { label: "Pending", value: "211 listings" },
        { label: "Sold", value: "473 listings" },
      ],
      calculation: "Counted every row, grouped by Listing Status.",
      caveat:
        "Sale Price is meaningful only for Sold listings; Active and Pending listings do not represent completed sales.",
      nextActions: ["Compare status by state", "Inspect Sold listing prices"],
    },
  },
  "channel-roas": {
    id: "channel-roas",
    workbookId: "marketing",
    prompt: "Which channel has the highest aggregate ROAS?",
    answer: {
      directResult: "Email has the highest aggregate ROAS at 12.99×.",
      scope: ["1,000 campaigns", "Complete workbook", "Email channel"],
      evidence: [
        { label: "Total revenue", value: "$21,021,486.18" },
        { label: "Total amount spent", value: "$1,618,335.15" },
        { label: "Aggregate ROAS", value: "12.99×" },
      ],
      calculation:
        "Aggregate ROAS = total revenue ÷ total amount spent, grouped by Channel.",
      nextActions: ["Compare every channel", "Inspect Email campaigns"],
    },
  },
  "campaign-budget-update": {
    id: "campaign-budget-update",
    workbookId: "marketing",
    prompt: "Change CMP-8002's Budget Allocated to $30,000.",
    answer: {
      directResult: "I prepared one budget change for your review.",
      scope: ["1 matched campaign", "CMP-8002", "Budget Allocated"],
      evidence: [
        { label: "Matched ID", value: "CMP-8002" },
        { label: "Current budget", value: "$24,500" },
        { label: "Proposed budget", value: "$30,000" },
      ],
      calculation:
        "Matched Campaign ID exactly, then staged a single field-level change.",
      caveat:
        "This is a frontend demo preview. No workbook data has been changed.",
      nextActions: ["Confirm demo change", "Keep reviewing"],
    },
    mutationPreview: {
      workbook: "marketing",
      operation: "Update Budget Allocated",
      matchedIds: ["CMP-8002"],
      changes: [
        {
          field: "Budget Allocated",
          before: "$24,500",
          after: "$30,000",
        },
      ],
      requiresConfirmation: true,
    },
  },
}

export function starterPromptsFor(workbookId: WorkbookId) {
  return WORKBOOKS[workbookId].starterPrompts.map(
    (scenarioId) => DEMO_SCENARIOS[scenarioId]
  )
}

export function findScenario(prompt: string, workbookId: WorkbookId) {
  const normalizedPrompt = prompt.trim().toLocaleLowerCase()

  return starterPromptsFor(workbookId).find(
    (scenario) => scenario.prompt.toLocaleLowerCase() === normalizedPrompt
  )
}
