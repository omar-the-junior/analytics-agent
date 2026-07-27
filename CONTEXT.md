# Workbook Agent

The shared language for a framework-free assistant that answers questions about and safely changes the two supplied workbook artifacts.

## Language

**Safe Task Success**:
An evaluation case in which the required answer or workbook outcome is correct and none of the case's forbidden actions or safety conditions occur.
_Avoid_: Fluent success, apparent success, task completion rate

**Baseline Evaluation Corpus**:
The fixed initial set of 72 deterministic workbook-agent cases used to measure Safe Task Success; it grows only in response to observed failures.
_Avoid_: Official rubric, score target

**Workbook Parity**:
Equal primary evaluation coverage for the property-listings and marketing-campaigns workbooks, with results reported separately.
_Avoid_: Blended workbook score

**Baseline Release**:
The workbook-agent build that has zero hard-gate failures across the baseline corpus and at least 65 Safe Task Success cases out of 72.
_Avoid_: Assignment passing score, official rubric

**Independent LLM Judge**:
A model different from the evaluated agent's model that reviews response quality and interaction behavior alongside deterministic graders.
_Avoid_: Self-grading model, sole correctness authority

**Recorded Sale Price**:
A source-provided `Sale Price` value for a listing, including a Pending listing whose business meaning is unknown.
_Avoid_: Final sale price, closed sale price (for Pending listings)

**Finalized Sale Price**:
The Recorded Sale Price of a listing whose `Listing Status` is `Sold`.
_Avoid_: Sale price without a status qualifier when finalized-sale analysis is intended

**USD Amount**:
A monetary value in either supplied workbook, expressed in United States dollars.
_Avoid_: Unspecified currency amount

**Recorded Campaign Revenue**:
The source-provided `Revenue Generated` amount for one or more campaigns; it is not profit, collected cash, or a defined attribution measure.
_Avoid_: Profit, collected revenue, attributed revenue

**Conversion Count**:
The source-provided `Conversions` count for a campaign; its underlying event and cross-channel consistency are unverified.
_Avoid_: Customers, purchases, leads, or another asserted conversion event

**Campaign Interval**:
The inclusive period from a campaign's `Start Date` through its `End Date`; a campaign is active in a period when the two intervals overlap.
_Avoid_: Campaign date when a start, end, or overlap rule is needed

**Totals-Based Campaign Metric**:
A group-level campaign ratio calculated from the group's total numerator and denominator, rather than an average of row-level ratios.
_Avoid_: Average CTR, average conversion rate, average CPC, average CPA, or average ROAS when a group result is intended

**List Price per Square Foot**:
The list price divided by square footage for a listing, and the default meaning of “price per square foot.”
_Avoid_: Sale price per square foot unless the user explicitly requests a finalized-sale measure

**Finalized Sale Price per Square Foot**:
The Finalized Sale Price divided by square footage for a Sold listing.
_Avoid_: Price per square foot without a finalized-sale qualifier

**Stable ID**:
A workbook row's `Listing ID` or `Campaign ID`, which is the canonical identity for a staged mutation.
_Avoid_: Campaign name, city, property type, or another non-unique attribute as a mutation identity

**Staged Mutation**:
A proposed insert, update, or deletion that names its Stable ID targets and exact changes but has not altered a workbook.
_Avoid_: Completed edit before explicit confirmation

**Mutation Authorization**:
An explicit user confirmation given after reviewing one unchanged Staged Mutation; it authorizes that stage only and is required for every insert, update, and delete.
_Avoid_: Initial natural-language request as commit authority, risk-based write bypass

**Verified Output Artifact**:
A new workbook artifact produced from a confirmed Staged Mutation, reopened to prove its exact authorized cell diff while its source workbook remains unchanged.
_Avoid_: Overwritten source workbook, unverified export

**Neutral Listing Criterion**:
A property-listings field that can be used for a housing query without inferring or acting on protected characteristics: city/state chosen by the user, property type, price, bedrooms, bathrooms, square footage, year built, or listing status.
_Avoid_: Demographic preference, protected characteristic, or demographic proxy

**Available Listing**:
A listing whose `Listing Status` is `Active`.
_Avoid_: Pending listing as available unless the user explicitly includes it

**Property Type**:
The canonical listing-category field. A natural-language house, apartment, condo, or townhouse request respectively requires `Property Type` equal to `House`, `Apartment`, `Condo`, or `Townhouse`, in addition to every other requested scope filter.
_Avoid_: Treating a property type as a description-only term or replacing it with a geographic filter

**Typical Price**:
The median of the relevant price field within the stated listing scope.
_Avoid_: Average price unless the user requests a mean

**Campaign KPI**:
The explicitly chosen measure used to judge campaign or channel performance, such as Recorded Campaign Revenue, Conversion Count, CTR, CPA, or ROAS.
_Avoid_: Best campaign or best channel without a stated measure

**City Scope**:
A city paired with its state when the workbook contains that city name in more than one state.
_Avoid_: City name alone when it matches multiple states

**Unavailable Metric**:
A requested calculation that cannot be produced because every applicable input is missing or its ratio denominator is zero.
_Avoid_: Zero, imputed value, or invented ratio

**Session Workbook**:
A temporary, chat-scoped copy of a supplied source workbook. Both reads and staged mutations for that chat operate on this copy; the supplied source workbook remains unchanged.
_Avoid_: Source workbook, shared working file, or a mutation-only copy

**WorkbookSession**:
The bounded chat-scoped service that validates requests and operates on that chat's Session Workbook. It uses pandas for approved calculations and openpyxl for verified committed versions; neither library determines what is permitted.
_Avoid_: Arbitrary workbook executor, model-controlled file access, or a query-only session

**Workbook Key**:
The backend-owned identifier for one supplied source workbook: `listings` or `campaigns`. It binds a newly created WorkbookSession; uploads are not part of this API.
_Avoid_: Filename, client-selected path, uploaded workbook

**Confirmed Mutation**:
A Staged Mutation whose unchanged `stage_id` was explicitly authorized and then committed directly into a verified output artifact without another model invocation.
_Avoid_: Chat-text authorization, post-confirmation agent action

**Cancelled Run**:
A terminal backend run whose cancellation revokes any staged change and which cannot produce an artifact or later accept confirmation.
_Avoid_: Paused run, reversible cancellation

**Backend Session**:
The in-memory API record that owns one WorkbookSession and its bounded runs. It expires when the API process restarts, so the browser must not present local demo history as server state.
_Avoid_: Persisted browser chat, demo session

**Inspectable Execution Trace**:
The ordered, user-visible account of an agent run: concise agent-step labels plus approved tool inputs and bounded output summaries. It is not hidden reasoning and never carries workbook result rows.
_Avoid_: Chain of thought, raw tool transcript, second result table
