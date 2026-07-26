# Research: U.S. property listings, campaign performance, and user needs

**Decision in one sentence:** optimize the assistant around a small set of reliable user jobs - find and compare listings, explain property prices and statuses, measure and compare campaign efficiency, and safely perform ID-based workbook changes - with answer-first responses, visible assumptions, exact metric formulas, and deterministic evaluation cases.

This report combines:

- the assignment in [Task - Junior AI Engineer](../task-reqs/Task-%20Junior%20AI%20Engineer.pdf);
- a read-only profile of [Real Estate Listings.xlsx](../task-reqs/Real%20Estate%20Listings.xlsx) and [Marketing Campaigns.xlsx](../task-reqs/Marketing%20Campaigns.xlsx); and
- primary or first-party sources from RESO, HUD, DOJ, FTC, CFPB, Census, NAR, and Google Ads.

The assignment provides no official numeric scoring rubric. Recommendations about "highest score" below are therefore explicit **evaluation hypotheses**, derived from the brief's statement that the assistant should handle any reasonable natural-language request and that easier access to answers earns a higher score.

## Executive findings

1. **Users do not want workbook operations; they want decisions.** Property users ask what matches, what is available, what is typical, and how options compare. Marketing users ask what performed best, why, whether the result is efficient, and what to change. The interface should translate those jobs into filters, comparisons, formulas, and safe write previews.
2. **The two files are clean enough for deterministic tooling but contain important semantic traps.** IDs are unique and numeric fields are usable, but names and labels are not safe identifiers. `Aurora` appears in Colorado and Illinois; 300 campaign names are repeated; campaign-name years and quarters often disagree with actual dates; and every pending property already has a `Sale Price`.
3. **Metric definitions and aggregation rules will determine answer correctness.** For a group of campaigns, CTR, CPC, CPA, conversion rate, and ROAS should normally be calculated from summed numerators and denominators, not by averaging per-campaign ratios.
4. **"Best," "affordable," "available," "conversion," and "ROI" are ambiguous.** The assistant should clarify only when the ambiguity materially changes the answer. Otherwise it should choose a defensible default and state it in one short line.
5. **Answer design is a scoring feature.** Lead with the result, then show scope, filters, formula, row count, and important caveats. For writes, show exact matched IDs and before/after values, then require confirmation.
6. **Fair Housing is a hard product boundary.** The assistant must not steer, filter, rank, suppress, or personalize housing results using protected characteristics or close proxies. It should redirect subjective demographic requests to neutral user-chosen criteria.
7. **The strongest submission will include an evaluation corpus, not only a demo.** A broad, deterministic request matrix proves coverage and makes the architecture defensible during the live call.

## What the supplied data actually contains

### Real Estate Listings workbook

The workbook has one visible sheet, `Real Estate Listings`, with 1,000 data rows and 11 columns. It has a header filter and freezes the first row. It contains no formulas, tables, merged cells, or hidden sheets.

| Dimension | Observed value |
|---|---:|
| Unique listing IDs | 1,000 of 1,000 |
| States | 10 |
| Cities | 49 |
| Property types | House 351; Apartment 272; Condo 194; Townhouse 183 |
| Listing statuses | Sold 473; Active 316; Pending 211 |
| List-price range | $33,000-$1,918,000 |
| Sale prices present | 684 |
| Sale prices missing | 316 |
| Year-built range | 1960-2025 |

Important project-specific semantics:

- `Listing ID` is the only safe row identifier for update or delete.
- `City` is not unique: `Aurora` occurs in both Colorado and Illinois. A city-only request for Aurora needs a state clarification or grouped results by state.
- `Sale Price` is absent for all 316 active rows, but present for all 211 pending and all 473 sold rows. Therefore, `Sale Price is not blank` does **not** mean `Listing Status = Sold`.
- The median sold sale-to-list ratio is 1.00. Among sold listings, 230 sold above list, 8 at list, and 235 below list. This roughly balanced synthetic distribution is a useful deterministic evaluation target, not evidence about the U.S. market.
- The dataset is a 10-state sample with no listing date, update timestamp, street address, ZIP code, coordinates, days on market, amenities, taxes, HOA fee, school, crime, neighborhood, agent, or source fields. The assistant must not invent these facts or describe the file as the whole U.S. market.

The project's `Active`, `Pending`, and `Sold` labels are local workbook values. RESO's standard status is the state of the listing contract and includes values such as Active, Active Under Contract, Pending, and Closed. Preserve the workbook vocabulary in answers and explicitly map it only if the product later imports standardized data. [RESO StandardStatus](https://dd.reso.org/DD2.0/Property/StandardStatus/)

RESO also distinguishes an asking/list price from a completed close price. The assistant should consistently say **list price** for this workbook's asking amount and **sale price** only for the workbook's sale-price field; it should never call either an appraisal or valuation. [RESO Data Dictionary](https://dd.reso.org/)

### Marketing Campaigns workbook

The workbook has one visible sheet, `Marketing Campaigns`, with 1,000 data rows and 11 columns. It also has a header filter and freezes the first row, with no formulas, tables, merged cells, or hidden sheets.

| Dimension | Observed value |
|---|---:|
| Unique campaign IDs | 1,000 of 1,000 |
| Channels | Google Ads 246; Facebook 244; Instagram 188; LinkedIn 174; Email 148 |
| Start-date range | 2024-01-02 to 2025-11-29 |
| End-date range | 2024-01-12 to 2026-01-17 |
| Campaign duration | 8-61 days; median 34 inclusive days |
| Total amount spent | $11,676,846.71 |
| Total revenue generated | $64,943,234.30 |
| Rows over allocated budget | 255 |
| Reused campaign names | 300 names covering 821 rows |

Important project-specific semantics:

- `Campaign ID` is the only safe row identifier. `Campaign Name` is not unique; one name appears as many as seven times.
- All rows have positive spend, impressions, clicks, conversions, and revenue. No row has clicks above impressions or conversions above clicks.
- Amount spent exceeds allocated budget in 255 rows, by at most about 9.9%. Overspend should trigger a warning or be a valid filter; it is not automatically corrupt data.
- Every campaign name can be parsed as a theme, channel, year, and quarter, and the named channel always matches the `Channel` field. However, 505 names disagree with the start-date year and 745 disagree with the start-date quarter. Date questions must use `Start Date` and `End Date`, never the name suffix. The name may encode a planning or creative label rather than the actual flight dates.
- Fifty-four campaigns span two calendar years. "Campaigns in Q4" may mean campaigns that start in Q4 or campaigns active at any time in Q4; the answer changes, so this is a material clarification.
- The data does not identify currency, conversion action, attribution model/window, platform reporting timezone, data freshness, customer acquisition status, profit/margin, qualified leads, or closed sales. These missing semantics limit cross-channel and ROI claims.

## Domain model and vocabulary

Use these terms consistently in prompts, tool schemas, UI labels, tests, and answers.

### Property concepts

| Concept | Project meaning | Do not silently treat as |
|---|---|---|
| Listing | One workbook row identified by `Listing ID` | A complete MLS record or unique physical parcel |
| Active | Workbook status `Active` | Guaranteed real-time availability |
| Pending | Workbook status `Pending` | Sold/closed |
| Sold | Workbook status `Sold` | A current listing |
| List price | Current asking amount stored in `List Price` | Appraised value, market value, or sale proceeds |
| Sale price | Amount stored in `Sale Price` | Proof of closing unless status is also Sold |
| Price per square foot | Price divided by `Square Footage` | A valuation model or apples-to-apples quality adjustment |
| Typical price | Default to median, with the choice stated | Automatically the arithmetic mean |

For future integrations, pin the RESO Data Dictionary version and preserve provider-specific mappings. RESO allows local fields and does not require every standard field, so missing data may mean "not supplied," not "none." [RESO Data Dictionary overview](https://www.reso.org/data-dictionary/)

Market statistics are separate from live listings. NAR's Existing-Home Sales series measures completed transactions using a representative sample and is revised; Census ACS housing values are estimates with a vintage, geography, estimate period, and margin of error. Neither should be presented as current listing availability. [NAR methodology](https://www.nar.realtor/research-and-statistics/housing-statistics/existing-home-sales/methodology), [Census ACS estimate guidance](https://www.census.gov/programs-surveys/acs/guidance/estimates.html), [Census margin-of-error guidance](https://www.census.gov/help/topics/faq.do-i-need-to-consider-the-margins-of-error-when-comparing-acs-estimates.html)

### Campaign concepts and formulas

| Metric | Formula for one row or a filtered group | Answer label |
|---|---|---|
| Budget utilization | `sum(Amount Spent) / sum(Budget Allocated)` | Budget used |
| Budget variance | `sum(Budget Allocated) - sum(Amount Spent)` | Remaining budget; negative means overspend |
| CTR | `sum(Clicks) / sum(Impressions)` | Click-through rate |
| CPC | `sum(Amount Spent) / sum(Clicks)` | Cost per click |
| Conversion rate | `sum(Conversions) / sum(Clicks)` for this dataset | Click-to-conversion rate |
| CPA | `sum(Amount Spent) / sum(Conversions)` | Cost per conversion/action |
| CPM | `sum(Amount Spent) / sum(Impressions) * 1,000` | Cost per 1,000 impressions |
| ROAS | `sum(Revenue Generated) / sum(Amount Spent)` | Return on ad spend, expressed as `x` |
| Revenue per conversion | `sum(Revenue Generated) / sum(Conversions)` | Revenue per recorded conversion |
| Simple ad-spend return | `(sum(Revenue Generated) - sum(Amount Spent)) / sum(Amount Spent)` | A proxy, **not true ROI** |

Google Ads defines CTR as clicks divided by impressions, CPA as cost divided by conversions, conversion rate as conversions divided by eligible interactions, and conversion value per cost/ROAS as value divided by spend. [Google Ads statistics definitions](https://support.google.com/google-ads/answer/2454071?hl=en), [Google Ads conversion metrics](https://support.google.com/google-ads/answer/6270625?hl=en-EN)

The dataset does not say whether every channel's `Conversions` column represents the same action. A conversion is an advertiser-defined valuable action, so campaign comparisons must state that the workbook is being treated as normalized; a production system should require conversion-action and attribution metadata before claiming true cross-platform comparability. [Google Ads glossary](https://support.google.com/google-ads/answer/12851704?hl=en)

Do not call `(Revenue Generated - Amount Spent) / Amount Spent` definitive ROI. True ROI depends on profit and other costs, which are absent. Prefer ROAS and label the alternative as a simple ad-spend return proxy. Google's first-party ROI guidance also defines ROI using net profit and costs rather than revenue and ad spend alone. [Google Ads ROI guidance](https://support.google.com/google-ads/answer/1722066?hl=en)

For grouped results, recompute each ratio from summed inputs. For example, this workbook's overall CTR is about 5.30% using total clicks divided by total impressions, while the unweighted mean of row CTRs is about 3.96%. Both are mathematically valid but answer different questions; the portfolio-level result should default to the weighted calculation.

## Real user jobs and likely requests

### Property listing users

Likely users include a buyer/renter browsing options, an agent or operations user maintaining listings, and an analyst comparing inventory. Their highest-value jobs are:

1. **Find matching inventory.** Filter by status, state, city, property type, bedrooms, bathrooms, price range, square footage, and year built; sort and limit results.
2. **Compare options.** Compare selected IDs, cities, states, or property types in a compact table with differences highlighted.
3. **Understand the market represented by the file.** Counts, medians, ranges, price per square foot, status mix, and sold-to-list differences by location or property type.
4. **Identify exceptions.** Highest/lowest prices, recent builds, unusual price-per-square-foot values, missing sale prices, or possible status/value inconsistencies.
5. **Maintain the workbook.** Add a listing, correct one field, change status, record a sale price, or delete a specific listing with a staged preview.

Representative natural-language requests:

- "Show active houses in Texas with at least 3 bedrooms under $500,000, cheapest first."
- "Compare LST-5001 and LST-5003."
- "Which state has the lowest median list price for condos?"
- "What percentage of sold houses closed above list?"
- "Find listings over 2,000 square feet below the median price per square foot."
- "Change LST-5001 to sold at $360,000, but show me the change first."

The assistant must decline to invent unsupported attributes. Requests such as "best school district," "safe neighborhood," "near my office," "low taxes," or "has a pool" cannot be answered from these columns. It should say which required field is missing and offer a supported alternative.

### Campaign performance users

Likely users include a marketing manager, performance analyst, finance/budget owner, and campaign operations user. Their highest-value jobs are:

1. **See performance quickly.** Spend, revenue, impressions, clicks, conversions, CTR, conversion rate, CPC, CPA, and ROAS for a selected scope.
2. **Compare channels or campaigns fairly.** Rank by an explicit KPI and include the scale/volume metrics that prevent misleading conclusions.
3. **Monitor budget.** Budget utilization, remaining budget, overspend, and campaigns near or above allocation.
4. **Analyze time.** Campaigns starting, ending, or overlapping a date range; performance by month, quarter, or year with a stated date rule.
5. **Diagnose the funnel.** Separate reach, engagement, conversion efficiency, and revenue efficiency rather than collapsing everything into "good" or "bad."
6. **Maintain campaign data.** Add a campaign, correct dates or allocation, update cumulative results, or delete a specific ID with a preview.

Representative requests:

- "Which channel had the best ROAS in 2025? Include spend and revenue."
- "Show campaigns over budget with below-median conversions."
- "Compare Google Ads and Facebook on CTR, CPA, and ROAS."
- "Which campaigns were active at any time in Q3 2025?"
- "Rank campaigns by conversions, but exclude campaigns with less than 100,000 impressions."
- "Increase CMP-8002's budget to $30,000 and preview the change."

"Best campaign" needs a KPI clarification because revenue, conversions, CTR, CPA, and ROAS can produce different winners. If the request says "most profitable," the assistant should explain that profit is unavailable and offer revenue, ROAS, or the simple ad-spend-return proxy.

## Query and operation coverage needed for a high score

The first version should cover the following request grammar without using arbitrary Python, SQL, or spreadsheet formulas from the model:

| Capability | Examples |
|---|---|
| Exact lookup | by Listing ID or Campaign ID |
| Text/category filter | status, property type, city, state, channel, campaign name |
| Numeric comparison | under/over/between, at least/at most, equal/not equal |
| Date comparison | starts, ends, or overlaps before/after/between |
| Multiple conditions | AND, OR, parentheses/nested groups |
| Sort and limit | cheapest, newest, top 5, bottom 10 |
| Projection | return only requested columns plus identifier |
| Aggregation | count, sum, min, max, mean, median, percentage, grouped metrics |
| Derived metric | property price per square foot and campaign KPIs above |
| Comparison | IDs, categories, locations, channels, or periods side by side |
| Data-quality query | missing, duplicate, inconsistent, over-budget, impossible range |
| Insert | validate required fields/types and unique ID; stage one or more rows |
| Update | stable ID match, expected match count, before/after diff |
| Delete | stable ID match, preview complete row, explicit confirmation |
| Follow-up | retain workbook and prior filter context, but show interpreted scope |

The tool layer should implement a typed filter/aggregation AST and a catalog of allowed derived metrics. The model selects operations; deterministic Python performs them. This will make broad language coverage testable without giving the model arbitrary execution.

## Ambiguity policy

Clarifications are useful only when they prevent a materially different answer. Too many questions make the assistant feel obstructive.

| User wording | Recommended behavior |
|---|---|
| "Aurora listings" | Ask Colorado or Illinois, or return grouped sections for both if the request is read-only and small. |
| Campaign name without ID | If one row matches, proceed; if several match, show candidates and ask for ID before mutation. For analysis, aggregate only if clearly requested. |
| "Available listings" | Default to `Listing Status = Active` and state the interpretation. Do not include Pending. |
| "Typical price" | Use median and state it. |
| "Average CTR/ROAS" | For a group, use totals-based weighted calculation and show the formula. |
| "Best campaign/channel" | Ask which KPI unless recent context already defines it. |
| "ROI" | Explain missing profit/cost data; offer ROAS or a labeled proxy. |
| "Campaigns in Q3" | Ask whether start date or any overlap matters; default to overlap only if the wording says active/running. |
| "This year" | Resolve to an explicit date range in the answer. |
| "Affordable" | Ask for a budget or monthly-payment constraint; the file has no income, financing, tax, or HOA data. |
| Destructive request with broad match | Stage and report exact match count; require confirmation. Never infer "all" from vague wording. |

## Answer design: make the result easy to trust

### Read/query response contract

Every analytical answer should contain, in this order:

1. **Direct result in one or two sentences.** Include the decisive number or conclusion.
2. **Interpreted scope.** Workbook, sheet, filters, date rule, and row count; keep this to one compact line or filter chips in the UI.
3. **Evidence.** A small table of the most relevant rows or groups, sorted to match the question. Always include the stable ID for row-level output.
4. **Calculation note.** Show the formula and denominator for derived metrics; state median versus mean and weighted versus unweighted.
5. **Caveat only when material.** Missing fields, null exclusions, repeated names, unavailable profit data, or lack of freshness.
6. **Useful next action.** Offer a relevant refinement, comparison, chart, or safe edit rather than a generic "anything else?"

Example property answer:

> **12 active Texas houses match; the lowest list price is $241,000.** Showing the 10 cheapest.  
> Scope: status Active, type House, Texas, 3+ bedrooms, list price <= $500,000; sorted by list price.  
> [result table with Listing ID]  
> Want all 12, or should I compare price per square foot?

Example campaign answer:

> **Email has the highest aggregate ROAS at 12.99x** on $1.62M spend and $21.02M recorded revenue.  
> Scope: all workbook rows; ROAS = total revenue / total spend for each channel.  
> [channel comparison table with campaign count, spend, revenue, conversions, and ROAS]  
> This compares the workbook's recorded conversions as if they are normalized across channels; conversion action and attribution metadata are not supplied.

### Mutation response contract

1. Restate the requested change and the matched ID/count.
2. Show a before/after diff containing only affected cells, plus warnings for related fields.
3. State that the original workbook remains unchanged.
4. Ask for explicit confirmation before commit.
5. After confirmation, save a new artifact, reopen it, verify postconditions, and report its location.

Cross-field checks should warn when a status change creates an odd state. For example, moving a listing to Sold without a sale price should require the missing value; changing it to Active while retaining a sale price should require confirmation or clearing the value. Because pending rows in the source already contain sale prices, do not impose a universal rule that only Sold may have one.

## Interface implications

The current UI is a generic invoice-oriented scaffold. The domain research suggests these changes when implementation begins:

- Replace invoice sample content with the two real workbook schemas.
- Auto-detect the workbook and show schema-aware starter prompts such as `Find listings`, `Compare prices`, `Campaign overview`, `Check budget`, and `Preview an edit`.
- Display interpreted filters as removable chips so users can verify what the assistant understood.
- Keep the answer in the center and put tool traces behind a collapsible "How this was calculated" disclosure. Raw tool JSON should not dominate the task.
- Use result tables with sticky headers, stable IDs, sort indicators, row counts, and clear truncation (`Showing 10 of 48`).
- For grouped campaign results, show a compact KPI table; add a chart only for a meaningful comparison or time trend.
- Show missing-data and ambiguity warnings next to the affected metric, not as a large generic banner.
- Make confirmation specific: `Update 1 listing`, `Delete 3 campaigns`, or `Insert 2 rows`, followed by the exact IDs.
- Provide a visible `Original file unchanged` guarantee and a link to the verified output artifact after commit.
- Keep follow-up context visible so "now only condos" clearly modifies the prior filter rather than starting a hidden new query.

## Fair Housing, privacy, and legal safety

The Fair Housing Act prohibits making housing unavailable, discriminatory terms or services, false availability, and advertising that indicates a preference based on race, color, religion, sex, familial status, national origin, or disability. Treat this as applying to wording, filtering, ranking, recommendations, and personalization. [42 U.S.C. §3604](https://uscode.house.gov/view.xhtml?req=%28title%3A42+section%3A3604+edition%3Aprelim%29), [DOJ civil enforcement summary](https://www.justice.gov/jm/jm-8-2000-enforcement-civil-rights-civil-statutes)

Product rules:

- Do not rank or recommend listings using a protected characteristic or a close demographic proxy.
- Refuse steering requests such as "best area for [race/religion]," "no children," or other demographic preferences. Offer neutral criteria available in the file: price, location explicitly chosen by the user, property type, bedrooms, bathrooms, square footage, year built, and status.
- Do not infer protected characteristics from names, location, language, photos, or campaign behavior.
- If future data adds school or crime facts, present consistently sourced facts rather than subjective demographic-coded labels such as "good for families." Current HUD policy permits consistent factual information without discriminatory intent. [HUD April 2026 letter](https://www.hud.gov/sites/default/files/hudclips/documents/AS-Trainor%27s-DCL-on-Neighborhood-Crime-Data-and-School-Quality.pdf)
- Housing-ad delivery can create exposure even without an advertiser explicitly selecting a protected class. DOJ's Meta matter is a first-party enforcement example; a production system should keep protected traits/proxies out of optimization and audit eligible versus delivered audiences. [DOJ v. Meta](https://www.justice.gov/crt/case/united-states-v-meta-platforms-inc-fka-facebook-inc-sdny)
- Do not cite HUD's withdrawn April 2024 digital-platform housing-ad guidance as current authority. HUD withdrew it effective September 2025. [Federal Register withdrawal notice](https://www.federalregister.gov/documents/2026/04/06/2026-06624/notification-of-withdrawal-of-fair-housing-and-equal-opportunity-guidance-documents)

The supplied workbooks contain no person-level or tenant-screening data. Preserve that low-risk scope. If later campaign data includes people, devices, precise locations, or audiences, default to aggregated results, minimize collection, restrict access, define retention, and securely dispose of data. [FTC personal-information guidance](https://www.ftc.gov/business-guidance/resources/protecting-personal-information-guide-business)

If the product later produces tenant eligibility scores or recommendations to landlords, those outputs may be consumer reports under the FCRA, bringing accuracy, permissible-purpose, disclosure, dispute, and adverse-action duties. [FTC screening-company guidance](https://www.ftc.gov/business-guidance/resources/what-tenant-background-screening-companies-need-know-about-fair-credit-reporting-act), [FTC landlord guidance](https://www.ftc.gov/business-guidance/resources/using-consumer-reports-what-landlords-need-know)

## Evaluation strategy and scoring hypotheses

### What should count as success

The artifact and tool trace are the authority, not fluent prose. A case passes only when:

- the correct workbook, sheet, rows, columns, filters, and date semantics were used;
- calculations match deterministic expected values with explicit rounding rules;
- grouped ratios use the intended totals-based formula;
- nulls and unavailable fields are handled honestly;
- the final answer includes the important result and scope;
- mutations match the intended stable IDs and no other cells change;
- broad or destructive changes are staged and confirmed;
- no Fair Housing, privacy, path, shell, or arbitrary-code policy is violated.

### Suggested case matrix

Build at least 60-80 cases before prompt tuning:

| Category | Essential cases |
|---|---|
| Property lookup/filter | exact ID, status, city/state ambiguity, multi-filter, ranges, sort/limit, no matches |
| Property analysis | grouped counts, median price, price/sq-ft, sold-to-list, null sale price, unsupported fields |
| Campaign lookup/filter | exact ID, reused name, channel, numeric thresholds, over-budget, no matches |
| Campaign analysis | CTR, CPC, CPA, conversion rate, ROAS, weighted aggregation, channel ranking, KPI ambiguity |
| Dates | starts in range, ends in range, overlaps range, cross-year campaign, name/date mismatch |
| Inserts | valid row, duplicate ID, missing required value, bad date/numeric/category |
| Updates | unique ID, zero match, repeated name, one field, multiple fields, cross-field warning |
| Deletes | unique ID, broad match, confirmation absent/present, original unchanged |
| Follow-ups | refine prior filters, change sort, compare selected rows, switch workbook explicitly |
| Safety | protected-class steering, unsupported neighborhood claim, arbitrary code/path request, prompt-like cell text |
| Robustness | malformed model JSON, invented field/tool, tool error, turn/row limit, output verification failure |

High-value golden checks from the supplied fixtures include:

- 1,000 rows and 1,000 unique IDs in each workbook;
- listing status counts: 473 Sold, 316 Active, 211 Pending;
- sale price missing for exactly the 316 Active listings and present for all Pending and Sold rows;
- `Aurora` requires state disambiguation;
- 255 campaigns have spend above budget;
- 300 campaign names are reused, covering 821 rows;
- 505 campaign names disagree with start year and 745 disagree with start quarter;
- overall weighted CTR is approximately 5.3047%, not the 3.9624% mean of row CTRs;
- overall ROAS is approximately 5.5617x;
- channel-level aggregate ROAS is highest for Email at approximately 12.9884x for the full workbook.

Store expected values at full precision and apply formatting only in the presenter. Tests should compare decimals within an explicit tolerance rather than compare formatted strings.

### Proposed internal scorecard - not the assignment's official rubric

| Dimension | Proposed weight | Evidence |
|---|---:|---|
| Answer and workbook correctness | 40% | deterministic facts, formulas, postconditions, unchanged source |
| Reasonable-request coverage | 20% | pass rate across the query/CRUD matrix |
| Safety and control | 15% | ID precision, confirmation, policy tests, no excessive authority |
| User effort and clarity | 15% | direct answers, minimal necessary clarification, visible scope, useful next step |
| Engineering judgment | 10% | traceability, evaluation design, documented tradeoffs, live-call defensibility |

The best architecture is the simplest one that achieves the highest **safe success rate** on this corpus. Track raw pass counts, mutation precision/recall, invalid-tool rate, recovery rate, turns, latency, and tokens rather than relying on a handful of demos.

## Prioritized implementation implications

### P0 - required to satisfy the task credibly

1. Workbook inspection and schema summary for both supplied files.
2. Typed filters, sorting, selection, limit, grouping, and approved derived metrics.
3. Answer presenter implementing the read/query response contract.
4. ID-based staged insert/update/delete with exact diffs and explicit confirmation.
5. Workbook-specific semantic catalog: categories, null behavior, date rules, campaign formulas, and local status vocabulary.
6. Deterministic evaluation fixtures covering successful, ambiguous, empty, unsafe, and mutation cases.
7. Original-file preservation, verified output artifact, and append-only trace.

### P1 - likely to improve user-ease scoring materially

1. Follow-up context with visible interpreted filters.
2. Schema-aware starter prompts and suggested refinements.
3. Side-by-side property and campaign comparisons.
4. Compact charts for channel comparisons and time trends.
5. Friendly ambiguity resolution that presents candidate IDs/options.
6. Explainable calculation disclosure without exposing raw internal traces by default.

### P2 - only after evaluations justify it

1. External MLS, Census, or ad-platform integrations with source/version/freshness metadata.
2. Saved user views or reusable queries.
3. More advanced anomaly detection, forecasts, or budget recommendations.
4. Cross-source attribution or causal analysis after conversion definitions and identity/privacy controls are established.

## Open product questions

Resolve these before declaring the semantic layer complete:

1. Is `Sale Price` on Pending rows an accepted offer, projected value, or another meaning?
2. What currency applies to both workbooks?
3. Does `Revenue Generated` mean platform-attributed conversion value, booked revenue, or collected revenue?
4. What event does `Conversions` represent, and is it consistent across all five channels?
5. When a user says a campaign is "in" a period, should the default be start date or interval overlap?
6. Are edits expected to overwrite the supplied file, or is a new verified artifact acceptable? The safer product default is a new file.
7. Which writes require confirmation: every mutation or only update/delete? The current architecture correctly proposes confirmation for all writes.
8. Will scoring be manual, scripted, or both? Until known, optimize for deterministic behavior plus a polished live demonstration.

## Recommended next step

Turn this research into a versioned evaluation dataset before implementing the full agent loop. Start with roughly 25 property reads, 25 campaign reads, 15 mutations, and 15 ambiguity/safety/robustness cases. Implement only the tool contracts required to make those cases pass; then use failures to expand the corpus and refine prompts.

## Source-selection note

Primary and first-party sources were preferred: the assignment and workbooks themselves; RESO definitions; U.S. statute and agency material from HUD, DOJ, FTC, CFPB, and Census; NAR's own methodology; and Google Ads' definitions. Sources and policy currency were checked on 2026-07-26. Platform documentation and regulatory guidance can change, so production policy should pin versions and be re-reviewed before adding external data, audience optimization, screening, or credit decisions.
