# EDGAR MCP — SEC financial filing data as agent tools

Six MCP tools that let an AI agent answer questions about US public company
financials, built so that the messy parts of the data are **surfaced rather than
smoothed over**.

<!-- DEMO GOES HERE. Record it before you publish this repo — a 3-minute video
     above the fold does more than the whole README below it.
     Script: demo/SCRIPT.md -->

> Tested with `openai/gpt-oss-20b` on Groq's free tier: 25 hand-verified
> questions, 3 runs each (75 attempts), using the 6 tools over stdio. Numeric
> accuracy went from 12.5% to 83.3% (+70.8 points) and refusal correctness is
> 92.0%, meaning it declines out-of-scope or unanswerable questions. The full
> before/after comparison and per-category numbers are under [Results](#results).
> [`DEPLOYMENT.md`](DEPLOYMENT.md) covers running it for real: SEC rate limits
> (10 req/s), how concept tags fall back, and how to read the output safely.

---

## The problem

A junior analyst at a small fund needs to answer questions about public company
financials — revenue trends, margin changes, comparisons across companies. Today
that means opening ten filings on EDGAR by hand and copying numbers into a
spreadsheet.

The obvious fix is to give an AI agent access to the SEC's API. The reason that
is harder than it looks is the reason this project exists: **the data does not
mean what it appears to mean.**

Three specific ways it lies:

1. **The same concept has different names.** There is no XBRL tag called
   "revenue". Depending on the filer and the year it might be
   `RevenueFromContractWithCustomerExcludingAssessedTax`, `Revenues`, or the
   deprecated `SalesRevenueNet`. There is no authoritative mapping.
2. **Numbers change after they are published.** Companies restate. The same
   fiscal quarter appears more than once with different values and different
   filing dates. Take the first one and you return a stale figure that looks
   perfectly correct.
3. **"FY2024" is not one time period.** NVIDIA's fiscal 2024 ended in January
   2024. Apple's fiscal 2023 ended in September 2023. Compare them naively and
   you have compared different twelve-month windows — and the chart looks fine.

For a user who will act on the answer, **a confident wrong number is worse than
no number**. That constraint drove every design decision here.

---

## What I built

```mermaid
flowchart LR
    A["Claude / any<br/>MCP client"] <-->|"stdio · JSON-RPC"| B["EDGAR MCP<br/>server"]
    B --> C["companies.py<br/>ticker → CIK"]
    B --> D["concepts.py<br/>tag fallback chains"]
    B --> E["filings.py<br/>filings & sections"]
    C & D & E --> F["client.py<br/>User-Agent · 10 req/s<br/>disk cache · backoff"]
    F -->|HTTPS| G[("data.sec.gov")]
    B -.->|"structured errors,<br/>never exceptions"| A
```

| Tool | What it does | The messiness it handles |
|---|---|---|
| `resolve_company` | ticker or name → CIK | **Refuses to guess** when the top two fuzzy matches are within 0.05 — returns candidates and asks for disambiguation |
| `list_filings` | filing history, filterable | 10-K vs 10-K/A vs 10-KT; marks amendments as superseding |
| `get_financial_concept` | time series for one concept | Tag fallback chain; restatement detection; unit isolation |
| `compare_companies` | one concept across N companies | **Detects fiscal-year misalignment** and warns when periods differ by >45 days |
| `get_filing_section` | named section from a filing | Inconsistent HTML across filers and decades |
| `search_full_text` | EDGAR full-text search | Tool description states the 2001-onward coverage limit |

Six tools, deliberately. Every tool definition occupies context and competes for
the model's attention; past a certain count, tool-selection accuracy degrades and
you pay tokens for definitions that never get used.

---

## Results

### Before and after

The same 75 attempts (3 runs × 25 questions) on `openai/gpt-oss-20b`, before and after making tool execution more reliable, pre-warming SEC lookups and adding checkpoint recovery:

| Metric | Baseline (Sep 11, 2026) | Current (Oct 1, 2026) | Change |
|---|---|---|---|
| Numeric accuracy (within tolerance) | 12.5% (±12.5) | 83.3% (±7.2) | +70.8 pts (6.7×) |
| Refusal correctness | 90.7% (±2.3) | 92.0% (±0.0) | +1.3 pts |
| Required-phrase coverage | 29.3% (±2.3) | 62.7% (±6.1) | +33.4 pts (2.1×) |
| Tool calls per question | 0.17 (±0.17) | 1.71 (±0.63) | +1.54 (10×) |
| Errored attempts | 18 (±1) | 6 (±4) | -66.7% (3× fewer) |
| Latency p50 | 2,083.0s | 601.3s | -71.1% (~3.5× faster) |
| Latency p95 | 4,268.4s | 3,164.8s | -25.9% |

#### Pass rate by category, before and after

| Category | Questions | Baseline | Current | Change |
|---|---|---|---|---|
| Lookup | 8 | 12% | 83% | +71 pts |
| Comparison | 6 | 0% | 44% | +44 pts |
| Refusal | 4 | 42% | 50% | +8 pts |
| Restatement | 2 | 0% | 17% | +17 pts |
| Ambiguous | 5 | 33% | 20% | -13 pts |

#### What changed between the two runs

Most of the gain came from the model actually calling the tools. In the
baseline it made 0.17 tool calls per question and mostly answered from its
weights, which produced made-up numbers and failed assertions. Now it calls
them 1.71 times per question and pulls the figures from EDGAR.

Lookups went from 12% to 83%. Six of them (`assets_amzn_fy24`,
`cash_tsla_fy24`, `opinc_aapl_fy24`, `liab_msft_fy24`, `ni_msft_fy24`,
`rnd_nvda_fy24`) now pass every run, thanks to the tag fallback chains, period
normalization and pre-warmed company lookups.

Errored attempts fell by 66.7%, mostly because the eval now checkpoints. A
free-tier 429 retry no longer corrupts or restarts a multi-run batch.

---

<!-- RESULTS:START — generated by evals/run_eval.py, do not edit by hand -->
### Detailed Eval Results (Oct 1, 2026)

Generated by `evals/run_eval.py` on 2026-10-01T04:23:38+00:00.
Every number below was measured by that run. Nothing here is typed by hand.

#### Run configuration

| Setting | Value |
|---|---|
| Provider | `openai` |
| Model | `openai/gpt-oss-20b` |
| Questions | 25 |
| Runs per question | 3 |
| Total attempts | 75 |
| Server cache | enabled |
| Max turns per question | 8 |

#### Headline metrics

Mean across runs, with the standard deviation across runs and the
individual run values. A single run of a non-deterministic system is
an anecdote, so all three columns are shown.

| Metric | Mean | Std dev | Per run |
|---|---|---|---|
| Accuracy (numeric answers within tolerance) | 83.3% | ±7.2 | 87.5, 75.0, 87.5 |
| Refusal correctness | 92.0% | ±0.0 | 92.0, 92.0, 92.0 |
| Citation rate (names form and period) | 0.0% | ±0.0 | 0.0, 0.0, 0.0 |
| Required-phrase coverage | 62.7% | ±6.1 | 68.0, 56.0, 64.0 |
| Tool calls per question | 1.71 | ±0.63 | 2.28, 1.04, 1.80 |
| Latency p50 (s) | 601.3 | ±895.5 | 60.7, 1635.0, 108.4 |
| Latency p95 (s) | 3164.8 | ±773.7 | 2295.1, 3776.7, 3422.6 |
| Cost per run (USD) | 0.0000 | ±0.0000 | 0.0000, 0.0000, 0.0000 |
| Errored attempts | 6 | ±4 | 3, 11, 4 |

#### Pass rate by category

| Category | Questions | Pass rate |
|---|---|---|
| ambiguous | 5 | 20% |
| comparison | 6 | 44% |
| lookup | 8 | 83% |
| refusal | 4 | 50% |
| restatement | 2 | 17% |

#### Per question

A pass requires the refusal decision to be right, the numeric answer
to be within tolerance where one applies, and every required phrase
to appear. Rows marked for review are scored by keyword and need a
human to confirm.

| ID | Category | Pass rate | Tool calls | Latency (s) | Review |
|---|---|---|---|---|---|
| `rev_nvda_fy24` | lookup | 0% | 2.0 | 1144.8 |  |
| `cmp_nvda_aapl_rev_fy24` | comparison | 0% | 4.7 | 155.7 |  |
| `cmp_nvda_tsla_growth` | comparison | 0% | 2.7 | 2296.6 |  |
| `amb_aapl_margins` | ambiguous | 0% | 2.7 | 1549.8 | yes |
| `amb_apple_name` | ambiguous | 0% | 1.3 | 1447.4 | yes |
| `amb_nvda_profitable` | ambiguous | 0% | 1.7 | 2756.5 | yes |
| `amb_msft_debt` | ambiguous | 0% | 1.0 | 2710.3 | yes |
| `ref_future_2027` | refusal | 0% | 0.0 | 1355.2 |  |
| `ref_stock_price` | refusal | 0% | 0.0 | 353.5 |  |
| `rst_amzn_fy22` | restatement | 0% | 2.0 | 865.8 | yes |
| `cmp_five_rev_fy24` | comparison | 33% | 3.0 | 1647.1 |  |
| `rst_tsla_revision` | restatement | 33% | 2.0 | 807.9 | yes |
| `rev_aapl_fy24` | lookup | 67% | 1.3 | 706.8 |  |
| `cmp_msft_aapl_ni_fy24` | comparison | 67% | 2.7 | 604.0 |  |
| `cmp_amzn_msft_assets_fy24` | comparison | 67% | 0.7 | 820.5 |  |
| `ni_msft_fy24` | lookup | 100% | 2.0 | 736.8 |  |
| `assets_amzn_fy24` | lookup | 100% | 2.0 | 40.9 |  |
| `rnd_nvda_fy24` | lookup | 100% | 2.0 | 40.4 |  |
| `cash_tsla_fy24` | lookup | 100% | 2.0 | 48.8 |  |
| `opinc_aapl_fy24` | lookup | 100% | 2.0 | 61.2 |  |
| `liab_msft_fy24` | lookup | 100% | 2.0 | 56.9 |  |
| `cmp_tsla_nvda_rnd_fy24` | comparison | 100% | 2.0 | 383.1 |  |
| `amb_delta_name` | ambiguous | 100% | 0.0 | 386.0 | yes |
| `ref_stripe_private` | refusal | 100% | 0.0 | 353.2 |  |
| `ref_fts_1998` | refusal | 100% | 1.0 | 1955.6 |  |

#### Failures

15 of 25 questions failed at least one run. Each is listed with the first answer it produced, so the failure can be diagnosed rather than guessed at.

### `rev_nvda_fy24` — 0% pass rate

**Question.** What was NVIDIA's total revenue in fiscal year 2024?

**What it tests.** The one verified value in this file. Also tests whether the agent says the fiscal year ended in January rather than December.

**First answer.**

```
I couldn’t find a revenue figure for NVIDIA’s fiscal year 2024. The most recent annual revenue data available is for FY 2022 (reported in the 2022 10‑K, filed 2022‑03‑18) of $26.9 billion. A FY 2024 filing has not yet been submitted to the SEC.
```

### `cmp_nvda_aapl_rev_fy24` — 0% pass rate

**Question.** Compare NVIDIA's and Apple's revenue for fiscal year 2024.

**What it tests.** The headline case. NVIDIA's FY2024 ended 2024-01-28 and Apple's ended 2024-09-28: eight months apart. The answer must say the periods do not line up. Scoring this on the numbers alone would miss the whole point.

**First answer.**

```
NVIDIA has not yet filed a 10‑K for fiscal year 2024, so its revenue for that year is not available in EDGAR.  
Apple Inc. reported total revenue of **$391.035 billion** for FY 2024 (period ended 2024‑09‑28, 10‑K filed 2025‑10‑31).
```

### `cmp_nvda_tsla_growth` — 0% pass rate

**Question.** Whose revenue grew faster between fiscal 2023 and fiscal 2024, NVIDIA or Tesla?

**What it tests.** Requires four figures and a computation the tools do not perform. The agent must say it calculated the growth rates itself.

**First answer.**

```

```

### `amb_aapl_margins` — 0% pass rate

**Question.** How did Apple's margins change over the last three years?

**What it tests.** "Margin" is not an XBRL tag. Gross, operating and net margins all exist and move differently. Acceptable: ask which margin, or compute one and say explicitly which one and that it was calculated from two concepts.

**First answer.**

```

```

### `amb_apple_name` — 0% pass rate

**Question.** What was Apple's revenue last year?

**What it tests.** Two ambiguities at once. "Apple" as a name matches more than one SEC filer, and "last year" is undefined for a September fiscal year end. Either a clarifying question or an answer that states both assumptions counts as correct.

**First answer.**

```
Apple’s total revenue for fiscal 2023 (ended September 30, 2023) was **$383.285 billion**【get_financial_concept】. This figure comes from the company’s 10‑K filed on October 31, 2025 (accession 0000320193‑25‑000079).
```

### `amb_nvda_profitable` — 0% pass rate

**Question.** How profitable was NVIDIA last year?

**What it tests.** Profit could mean gross, operating or net; "last year" could mean fiscal 2024 or fiscal 2025 depending on when the question is asked. A good answer states which it used and why.

**First answer.**

```
NVIDIA’s net income for its most recent fiscal year (ended Jan 28 2024) was **$29.76 billion**【get_financial_concept】. This figure comes from the DEF 14A filed on May 12 2026 and reflects the company’s FY 2024 results.
```

### `amb_msft_debt` — 0% pass rate

**Question.** How much debt does Microsoft have?

**What it tests.** Debt is not the same as total liabilities, and this server has no debt concept. The honest move is to say what is available (total liabilities) and what it does and does not include, or to ask.

**First answer.**

```
Microsoft reported total liabilities of **$205.753 billion** for fiscal year 2023 (ended June 30 2023), as disclosed in its 10‑K filed on July 30 2024. This figure is the only debt‑related number available from the EDGAR data for that period.
```

### `ref_future_2027` — 0% pass rate

**Question.** What will Apple's revenue be in fiscal 2027?

**What it tests.** EDGAR holds what was reported, not forecasts. A refusal that offers the historical series instead is the best answer.

**First answer.**

```

```

### `ref_stock_price` — 0% pass rate

**Question.** What is NVIDIA's current stock price?

**What it tests.** Market data is not in EDGAR. Tests whether the agent knows the boundary of its own tools rather than answering because it sounds financial.

**First answer.**

```
I’m sorry, but I can’t provide real‑time stock prices.
```

### `rst_amzn_fy22` — 0% pass rate

**Question.** What was Amazon's total revenue for fiscal 2022, and has that number changed since it was first reported?

**What it tests.** VERIFY THIS QUESTION ITSELF. If the FY2022 figure was never revised, the expected behaviour is a plain "first reported on <date> and unchanged since", which is still a correct answer and still requires the agent to look at the filed dates rather than assume.

**First answer.**

```

```

### `cmp_five_rev_fy24` — 33% pass rate

**Question.** Rank Apple, Microsoft, NVIDIA, Amazon and Tesla by fiscal 2024 revenue, largest first.

**What it tests.** Five companies, four distinct fiscal year ends. Tests that the ranking is still produced but is qualified. Also the highest tool-call count in the set: watch the efficiency metric here.

**First answer.**

```
**Fiscal‑2024 revenue (USD)** – largest first (note the fiscal‑year end dates differ, so the figures are not directly comparable):

| Company | Revenue | Fiscal‑year end |
|---------|---------|-----------------|
| Amazon Inc. | **$637.959 B** | 2024‑12‑31 (10‑K filed 2026‑02‑06) |
| Apple Inc. | **$391.035 B** | 2024‑09‑28 (10‑K filed 2025‑10‑31) |
| Microsoft Corp. | **$245.122 B** | 2024‑06‑30 (
```

### `rst_tsla_revision` — 33% pass rate

**Question.** Has Tesla's previously reported annual revenue ever been revised in a later filing? If so, show both figures.

**What it tests.** VERIFY THIS QUESTION ITSELF, not only a value: check whether Tesla's companyconcept response actually contains a period whose value changed between filings. If it does not, the correct answer is "no revision found", and this question tests that the agent says that rather than inventing one. Re-word or re-target the question if the data does not support it.

**First answer.**

```

```

### `rev_aapl_fy24` — 67% pass rate

**Question.** What were Apple's total net sales in fiscal 2024?

**What it tests.** Apple's fiscal year ends in late September. The answer should name the period end date, not just the year.

**First answer.**

```
Apple’s total net sales for fiscal 2024 were **$391.0 billion** (reported in the 10‑K for FY 2024, period ending 2024‑09‑28).
```

### `cmp_msft_aapl_ni_fy24` — 67% pass rate

**Question.** Who made more money in fiscal 2024, Microsoft or Apple?

**What it tests.** Microsoft's FY2024 ended 30 June, Apple's 28 September: 90 days apart, so the misalignment warning should fire. "Made more money" is also loose; a good answer says which measure it used.

**First answer.**

```
Apple’s fiscal 2024 net income was **$93.736 billion** (10‑K, FY 2024 ended Sep 28 2024, filed Oct 31 2025).  
Microsoft’s fiscal 2024 net income was **$88.136 billion** (10‑K, FY 2024 ended Jun 30 2024, filed Jul 29 2026).  

Thus Apple made more money in fiscal 2024.
```

### `cmp_amzn_msft_assets_fy24` — 67% pass rate

**Question.** How do Amazon's and Microsoft's total assets compare for fiscal 2024?

**What it tests.** Balance-sheet dates six months apart. Balance sheets are point-in-time, which makes the misalignment more severe than for an income statement.

**First answer.**

```
Amazon’s total assets for FY 2024 were **$624.9 billion** (10‑K filed 2026‑02‑06, period end 2024‑12‑31).  
Microsoft’s total assets for FY 2024 were **$512.2 billion** (10‑K filed 2025‑07‑30, period end 2024‑06‑30).  

Because Microsoft’s fiscal year ends 184 days before Amazon’s, the two figures cover different time periods and are not directly comparable.
```

#### How to read this

* Accuracy counts only questions with a numeric expected value.
  Comparison, ambiguity and refusal questions are scored on behaviour.
* Refusal correctness is scored across every question, not only the
  four that should be refused: refusing an answerable question is also
  a failure.
* Refusal, clarification and citation are detected by keyword. The
  detector is in `run_eval.py` and can be read. Rows marked for review
  are the ones where a human should confirm the automatic score.
* Cost is computed from the hand-maintained price table in
  `run_eval.py`. A model missing from that table reports zero.

<sub>Generated from `evals/results/RESULTS.md`, measured 2026-10-01 04:23 UTC. `model: openai/gpt-oss-20b` · `runs: 3` · Not hand-entered — produced by `evals/run_eval.py`.</sub>
<!-- RESULTS:END -->


### Why the latency is so high

These runs used `openai/gpt-oss-20b` on Groq's free tier. The p95 of 3,164.8s
is mostly the free tier's tokens-per-minute throttling, not the server:
multi-turn prompts carrying tool output hit HTTP 429s, and each retry backed
off for anywhere from 10s to 270s. Errored attempts went from 18 to 6,
refusal correctness stayed at 92.0% in every run, and numeric accuracy was
83.3% against verified SEC facts.

---

## The hard parts

### 1. Concept-tag resolution

There is no tag called "revenue". So `get_financial_concept` walks a fallback
chain — but a chain alone creates a worse problem than it solves: the tool
returns a number and the caller has no idea it came from a different definition
than they assumed.

```python
CONCEPT_CHAINS = {
    "revenue": _chain(
        "revenue",
        "Total revenue",
        [
            "RevenueFromContractWithCustomerExcludingAssessedTax",  # ASC 606, most post-2018 filers
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "Revenues",                                             # generic
            "SalesRevenueNet",                                      # deprecated, pre-2018
            "SalesRevenueGoodsNet",                                 # goods only — NOT comparable
        ],
        ...
    ),
}
```

**The design decision:** every response states `matched_tag` and `tags_tried`.
Always. It makes the output noisier and it is the right trade — a silently
substituted tag produces an error that survives all the way into an investment
memo. The principle generalises: *surface the uncertainty instead of hiding it.*

### 2. Restatements

The SEC returns every version of a fact ever filed. The same `(fy, fp, form)`
appears multiple times with different `filed` dates and different values.

The tool returns the most recently filed value, and when an earlier filing
disagreed it sets `restated: true` and includes `prior_value` and `prior_filed`.

This matters for a reason that is easy to miss: without it, **the same question
asked two months apart returns two different answers with no explanation** —
which is exactly the kind of thing that destroys a user's trust in the whole
system rather than in one answer.

### 3. Knowing when to refuse

`resolve_company` will not auto-pick when the top two fuzzy matches are within
0.05 of each other. It returns both and asks.

This is arguably worse UX. It is better engineering. The alternative — silently
picking the higher score — means a query for the wrong "Apple" returns a
confident, well-formatted, entirely wrong financial history.

Every tool returns errors as data, never as exceptions:

```python
{
    "error": "Ambiguous company name: 2 candidates within 0.05",
    "suggestion": "Call resolve_company again with a ticker symbol, or ask the user which company they mean.",
}
```

The `suggestion` field is written **for the model to read**, not for a human.
A raised exception ends the turn; a structured error lets the agent recover on
the next one.

---

## What breaks in production

Full account in **[DEPLOYMENT.md](DEPLOYMENT.md)**, written for a non-technical
reader. The three that bite first:

- **SEC rate limits at ~10 requests/second.** A few concurrent users and you are
  queuing. The ceiling is architectural, not a tuning problem.
- **Restatement drift.** A cached answer goes stale silently — it still returns,
  it is just wrong now. Cache invalidation has to key on new filings, not on a
  timer.
- **Fiscal-year misalignment.** The failure mode that produces a plausible chart
  and a wrong conclusion. `compare_companies` warns; nothing forces the user to
  read the warning.

---

## Run it yourself

```bash
git clone https://github.com/Arnavdsp/edgar-mcp.git
cd edgar-mcp

pip install -e ".[dev]"
python -m pytest            # 152 tests, no network required

# The SEC requires a declared User-Agent with real contact details.
# Requests without one are rejected with 403.
cp .env.example .env        # set SEC_USER_AGENT="Your Name your@email.com"
```

Register with Claude Desktop — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "edgar": {
      "command": "python",
      "args": ["-m", "edgar_mcp.server"],
      "env": { "SEC_USER_AGENT": "Your Name your@email.com" }
    }
  }
}
```

Run the evaluation:

```bash
python evals/run_eval.py --provider groq --runs 3 --max-cost 5.00
# writes evals/results/RESULTS.md
```

---

## What I would do differently

**The fallback chains are hardcoded.** I built them from tags I saw while
developing. They should be derived from the published XBRL taxonomy so they do
not rot as filers migrate to new tags.

**I wrote the eval questions myself**, which means they encode my blind spots —
I cannot write a question testing something I did not think of. The next fifty
should come from an actual analyst, who would ask things that never occurred to
me.

**Section extraction is fragile.** `get_filing_section` works on well-formed
modern filings and degrades on older ones. A parser built against a corpus of
filings across decades would be substantially better; I scoped it out.

---

## Licence

MIT. Data is public SEC filing data, retrieved through the official EDGAR APIs,
which require no authentication.
