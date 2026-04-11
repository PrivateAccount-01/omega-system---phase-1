Before you start vibe-coding this, one critical thing to establish first.

---

## Do Not Vibe-Code OmegaData

This is the one project in the entire system where vibe-coding will cost you more time than it saves.

**Here is exactly why:**

The corporate action adjustment engine has edge cases that an LLM will not know about unless you explicitly describe every one of them. A vibe-coded adjustment engine will look correct, pass basic tests, and silently produce wrong adjusted prices for the 15-20% of edge cases that require India-specific handling. You will not discover this until you are building OmegaSignal and your IC numbers do not make sense. At that point you trace back, find the data error, and rebuild the adjustment engine anyway — except now you also have to rebuild every signal that was trained on wrong data.

The 30-year historical dataset with wrong corporate action adjustments is worse than no dataset at all. Wrong data that looks right is the most dangerous possible state for a trading system.

**What vibe-coding is safe for in this project:**

The boilerplate — Airflow DAG scaffolding, ClickHouse table creation scripts, FastAPI/gRPC server setup, Docker configuration, Kafka consumer templates, monitoring dashboard setup, the download manager for bhavcopy files. All of this is generic engineering that any capable LLM handles correctly.

---

## The Correct Approach for OmegaData

**Split the project into two tracks:**

**Track A — Vibe-code freely:**
Infrastructure, boilerplate, generic pipeline components, API server setup, database connections, monitoring, logging, testing framework, the download manager, the Kafka setup, the Redis caching layer, the Airflow orchestration.

**Track B — Design precisely before any code is written:**
The corporate action engine, the adjustment chain logic, the price discontinuity detector, the cross-source validation logic, the confidence scoring system, the point-in-time universe management. These require a written specification so detailed that the LLM is essentially transcribing your design, not inventing its own.

---

## What You Need to Produce Before Track B Code Is Written

A specification document for OmegaData. Not a system design — a precise behavioral specification. It answers: given this exact input, what is the exact expected output, and why.

This document has seven sections:

---

### Section 1 — Data Source Registry

Every data source documented completely before the pipeline is built.

```
SOURCE: NSE Equity Bhavcopy
  URL pattern (Era 1, pre-2010): [exact URL pattern]
  URL pattern (Era 2, 2010-2019): [exact URL pattern]
  URL pattern (Era 3, 2019-present): [exact URL pattern]
  File format Era 1: fixed-width, column positions documented
  File format Era 2: CSV, exact column names documented
  File format Era 3: CSV, exact column names documented
  Changes between eras: documented field by field
  Download rate limit: what is safe without IP ban risk
  Retry policy: how many retries, what backoff
  Checksum: how to verify file integrity after download
  Storage: exact Parquet partition structure

SOURCE: NSE F&O Bhavcopy
  [same structure]

SOURCE: NSE FII/DII Activity
  [same structure]

SOURCE: India VIX
  [same structure]

SOURCE: NSE Corporate Action Calendar
  [same structure]

SOURCE: BSE Corporate Action Announcements
  [same structure]

SOURCE: GDELT
  [same structure]

SOURCE: RBI DBIE
  [same structure]

SOURCE: MOSPI
  [same structure]

SOURCE: AMFI Monthly Portfolios
  [same structure]

SOURCE: NSE Bulk/Block Deals
  [same structure]

SOURCE: NSE/BSE Insider Trades (PIT)
  [same structure]
```

This section is written once. It is the permanent reference for everyone who touches the data pipeline. When NSE changes a URL or format, this document is updated first, then the code.

---

### Section 2 — ISIN Master and Symbol Mapping Specification

Precise rules for every mapping scenario:

```
RULE 1: ISIN is the only primary key
  Every record in every table has an ISIN field
  Symbol fields are always nullable — some instruments have no symbol
  ISIN is validated against the ISIN check digit algorithm before storage

RULE 2: Symbol changes
  When a company changes its trading symbol,
  a new record is created in the symbol_map table
  The old record's end_date is set to the day before the change
  Queries by symbol on a historical date must return
  the symbol that was active on that date, not the current symbol

RULE 3: Same ISIN, multiple exchanges
  HDFC Bank trades on both NSE and BSE
  Two records exist in symbol_map, one per exchange
  Prices from both exchanges are stored separately
  The NSE record is the primary for signal computation
  unless NSE data is missing for a specific date

RULE 4: Company mergers
  When company A merges into company B:
  Company A's ISIN has end_date set to merger effective date
  A merger_map record links company A ISIN to company B ISIN
  Historical signals computed on company A are NOT transferred
  Signal computation starts fresh for company B on merger date
  This is a hard break, not a continuation

RULE 5: Demergers
  When company A spins off subsidiary B:
  Company B gets a new ISIN from the issue date
  Company A continues with its existing ISIN
  A demerger_map record documents the relationship
  Price adjustment for company A is computed from
  the ex-date theoretical price

RULE 6: Face value changes without price change
  Some corporate events change face value without
  affecting the share price (rare but documented cases exist)
  These must be identified and NOT treated as splits
  Cross-source validation with BSE catches these cases
```

---

### Section 3 — Corporate Action Adjustment Specification

The most critical section. Every adjustment type has exact formulas.

```
ADJUSTMENT TYPE: BONUS ISSUE

  Definition: Company issues free additional shares to existing shareholders
  
  Trigger: ex_date in corporate action calendar, type = 'BONUS'
  
  Formula:
    ratio = bonus_shares / existing_shares
    adjustment_factor = 1 / (1 + ratio)
    
    Examples:
      1:1 bonus (1 bonus for every 1 held): ratio=1.0, factor=0.5
      1:2 bonus (1 bonus for every 2 held): ratio=0.5, factor=0.6667
      3:1 bonus (3 bonus for every 1 held): ratio=3.0, factor=0.25
  
  Application:
    All prices BEFORE ex_date are multiplied by adjustment_factor
    Prices ON and AFTER ex_date are stored as-is (unadjusted)
    Volume adjustment: all volumes BEFORE ex_date divided by adjustment_factor
    (volume × shares outstanding must be consistent)
  
  Validation:
    Price on (ex_date - 1) × adjustment_factor must equal
    approximately price on ex_date (within 5% for market moves)
    If outside 5%: flag for manual review
    Do not apply adjustment: flag record in audit log
  
  Edge cases:
    Multiple bonus issues in the same year:
      Apply adjustments in chronological order
      Each adjustment multiplies the cumulative factor
      
    Bonus issue announced but not reflected in bhavcopy:
      Price discontinuity detector will catch this
      Manual review queue receives the record
      Adjustment applied manually after confirmation

ADJUSTMENT TYPE: STOCK SPLIT

  Definition: Face value reduced, share count increased proportionally
  
  Trigger: ex_date in corporate action calendar, type = 'SPLIT'
  
  Formula:
    adjustment_factor = new_face_value / old_face_value
    
    Examples:
      FV ₹10 to ₹5: factor = 0.5
      FV ₹10 to ₹2: factor = 0.2
      FV ₹10 to ₹1: factor = 0.1
  
  Application: identical to bonus issue
  
  Edge case — reverse split:
    FV ₹1 to ₹2: factor = 2.0
    Prices BEFORE ex_date multiplied by 2.0
    Volume BEFORE ex_date divided by 2.0
    Extremely rare in India but must be handled

ADJUSTMENT TYPE: RIGHTS ISSUE

  Definition: Company offers existing shareholders the right to buy
  new shares at a discount
  
  Trigger: ex_date in corporate action calendar, type = 'RIGHTS'
  
  Formula:
    TERP (Theoretical Ex-Rights Price):
    TERP = (N × P + R × S) / (N + R)
    
    Where:
      N = existing shares per lot (from ratio denominator)
      P = pre-rights closing price on (ex_date - 1)
      R = rights shares per lot (from ratio numerator)
      S = subscription price (from corporate action record)
    
    adjustment_factor = TERP / P
    
    Example:
      Rights ratio 1:4 (1 new share for every 4 held)
      Pre-rights price: ₹100
      Subscription price: ₹60
      N=4, P=100, R=1, S=60
      TERP = (4×100 + 1×60) / (4+1) = 460/5 = ₹92
      adjustment_factor = 92/100 = 0.92
  
  Critical: subscription price is required for correct computation
    If subscription price is missing from NSE record:
      Check BSE record
      If still missing: use 0 as subscription price
      (conservative — assumes rights are worthless)
      Flag record in audit log for manual review

ADJUSTMENT TYPE: DIVIDEND

  Policy decision (documented here, not in code):
  OmegaData stores BOTH dividend-adjusted and
  price-only-adjusted series
  Signal factory uses price-only-adjusted by default
  Dividend-adjusted available on request
  This matches the convention used in Indian academic
  factor research for comparability
```

---

### Section 4 — Price Discontinuity Detection Specification

```
ALGORITHM: Idiosyncratic Return Filter

  Step 1: Compute overnight return for every stock every day
    overnight_return = (close_today - close_yesterday) / close_yesterday

  Step 2: Compute Nifty50 overnight return for the same day
    market_return = (nifty_close_today - nifty_close_yesterday) / nifty_close_yesterday

  Step 3: Compute idiosyncratic return
    idiosyncratic = overnight_return - beta × market_return
    (beta computed from rolling 252-day regression, minimum 60 observations)
    (if insufficient history: use beta = 1.0)

  Step 4: Flag if idiosyncratic return exceeds threshold
    THRESHOLD_BONUS_SPLIT: idiosyncratic < -0.35
      (likely bonus or split — price dropped significantly)
    THRESHOLD_RIGHTS_DEMERGER: idiosyncratic < -0.10
      (possible rights or demerger)
    THRESHOLD_SUSPICIOUS_POSITIVE: idiosyncratic > 0.25
      (possible data error or rare event — investigate)

  Step 5: Cross-reference with corporate action calendar
    If flagged date matches a known corporate action ex_date:
      Check whether adjustment has been applied
      If not applied: add to adjustment queue
    If flagged date has no corporate action record:
      Add to manual review queue
      Do NOT apply any adjustment automatically

  Exclusions (do not flag these):
    Dates within 2 days of Nifty circuit breaker events
    Dates of confirmed market-wide crises (COVID crash dates, etc.)
    Stocks suspended from trading (zero volume days)

  Output: daily discontinuity report
    Count of flags by category
    List of stocks requiring review
    List of adjustments applied automatically
    List of records sent to manual review queue
```

---

### Section 5 — Confidence Score Specification

```
CONFIDENCE LEVELS

  1.00: Gold standard
    Source: NSE official bhavcopy
    Cross-validated: matches BSE within 0.05%
    Corporate actions: all adjustments verified
    Discontinuity check: passed
    Use: all computations

  0.90: High confidence
    Source: NSE official bhavcopy
    Cross-validation: BSE not available for this date/instrument
    Corporate actions: adjustments applied, not cross-validated
    Discontinuity check: passed
    Use: all computations

  0.80: Acceptable
    Source: NSE bhavcopy
    Cross-validation: minor disagreement with BSE (0.05-0.5%)
    Reason documented in audit log
    Use: signal computation, not regime classification

  0.70: Low confidence — use with caution
    Source: yfinance or secondary source
    Primary source unavailable for this date
    Use: backtesting only, not live signal computation

  0.50: Imputed
    Source: linear interpolation between valid surrounding dates
    Used for: filling single missing trading days
    Maximum consecutive imputed days: 1
    If 2+ consecutive days missing: do not impute, leave as null
    Use: continuity only, flag in all output

  0.00: Invalid
    Failed schema, range, or continuity validation
    Never used in any computation
    Stored in audit log only
    Triggers alert if count exceeds 0.1% of daily records

THRESHOLD ENFORCEMENT (hardcoded, not configurable):
  Signal computation: minimum confidence 0.75
  Regime classification: minimum confidence 0.85
  Live trading signals: minimum confidence 0.90
  Backtesting: minimum confidence 0.70
```

---

### Section 6 — Point-in-Time Universe Specification

```
PRINCIPLE: The universe on any historical date reflects
  what was KNOWN on that date, not what we know today

TABLE STRUCTURE:
  isin          — the stock
  index_name    — which index (NIFTY50, NIFTY200, NIFTY500, etc.)
  added_date    — date the stock joined the index
                  (the date NSE announced the change, not effective date)
  effective_date — date the change took effect
  removed_date  — date the stock left the index (null if current member)
  removal_effective — date removal took effect (null if current member)
  source        — NSE press release reference

QUERY CONTRACT:
  get_universe(index_name, as_of_date) returns the list of ISINs
  that were members of the index on as_of_date
  
  CORRECT behavior:
    A stock added effective 2020-03-27 is NOT in the universe
    for as_of_date = 2020-03-26
    A stock removed effective 2019-08-30 IS in the universe
    for as_of_date = 2019-08-29

CONSTRUCTION:
  Primary source: NSE press releases (index reconstitution announcements)
  These are publicly available on NSE website
  All Nifty50 reconstitution announcements since 2004 are documented
  Nifty500 reconstitution announcements since 2010 are documented
  Pre-2010 Nifty500: reconstruct from academic datasets and
  historical bhavcopy (stocks appearing in bhavcopy on each date)
  
VALIDATION:
  Five reference dates have been manually verified:
    Current composition: matches NSE published list exactly
    March 2020: verified against academic research papers
    June 2022: verified against NSE announcements
    December 2019: verified against NSE announcements
    December 2015: verified against NSE announcements
  Any code change must reproduce these reference compositions exactly
```

---

### Section 7 — 24/7 News Pipeline Specification

```
EVENT CLASSIFICATION TAXONOMY

  Level 1 — Market-wide events:
    MONETARY_POLICY_CHANGE: RBI rate decision
    MONETARY_POLICY_GUIDANCE: RBI statement (hawkish/neutral/dovish)
    FISCAL_POLICY_BUDGET: Union budget announcement
    MARKET_CIRCUIT_BREAKER: Index halt event
    GLOBAL_RISK_OFF: Defined as US VIX > 30 and EM fund outflow > $2B daily
    CURRENCY_STRESS: USD/INR move > 1% in single session

  Level 2 — Sector-wide events:
    REGULATORY_CHANGE: SEBI circular affecting a sector
    COMMODITY_SHOCK: Oil move > 5% (affects auto, airlines, paints)
    CREDIT_EVENT: NBFC stress, bank NPA announcement
    POLICY_ANNOUNCEMENT: Government policy affecting specific sector

  Level 3 — Company-specific events:
    EARNINGS_RELEASE: Quarterly results
    PROMOTER_TRANSACTION: PIT disclosure filed
    BULK_BLOCK_DEAL: Institutional transaction above threshold
    CORPORATE_ACTION: Announced but not yet ex-date
    REGULATORY_ACTION: SEBI enforcement against specific company
    MANAGEMENT_CHANGE: CEO/CFO change announcement

IMPACT SCORE FORMULA:
  impact_score = magnitude_score × relevance_score × recency_weight
  
  magnitude_score: 0.0 to 1.0
    Calibrated per event type from historical event-return relationships
    RBI surprise rate cut: magnitude = 0.9
    RBI as-expected decision: magnitude = 0.2
    Oil spike 10%: magnitude = 0.7
    Bulk deal by Tier 1 institution: magnitude = 0.5
  
  relevance_score: 0.0 to 1.0
    For market-wide events: 1.0 for all instruments
    For sector events: 1.0 for sector stocks, 0.1 for others
    For company events: 1.0 for that company, 0.0 for others
  
  recency_weight: exponential decay
    weight = exp(-λ × hours_since_event)
    λ = 0.1 (half-life approximately 7 hours)
    Events older than 48 hours: weight < 0.01, effectively zero

PRECOMPUTED OUTPUT FORMAT (stored in Redis):
  key: signal:event_impact:{isin}:current
  value: {
    score: float (-1.0 to +1.0),
    dominant_event: event_id,
    event_type: string,
    event_timestamp: ISO8601,
    confidence: float,
    expires_at: ISO8601
  }
  TTL: 4 hours (recomputed continuously as new events arrive)

PROCESSING LATENCY REQUIREMENTS:
  Level 1 events: processed within 2 minutes of publication
  Level 2 events: processed within 10 minutes
  Level 3 events: processed within 30 minutes
  GDELT events: processed within 20 minutes of GDELT update
```

---

## Now You Are Ready to Vibe-Code

With this specification document complete, hand it to ChatGPT o3/Codex section by section.

**The prompt structure that works:**

"I am building OmegaData, a Bloomberg-quality financial data infrastructure for Indian equity markets. Here is the complete specification for [Section X]. Build the [specific component] according to exactly this specification. Do not make design decisions — all design decisions are in the specification. Your job is to implement the specification precisely."

This produces code that is correct because the decisions have already been made correctly. The LLM is transcribing your design, not inventing its own.

**The review discipline:**

Every generated component is reviewed against the specification before it is merged. Not reviewed for code quality — reviewed for specification compliance. Does this code produce exactly the output the specification requires for every input the specification defines?

Track A components can be merged after passing tests.
Track B components must pass specification compliance review before any tests are written.

**One final thing:**

Build the test suite for Track B components before the implementation. Write the tests directly from the specification — what input goes in, what output must come out. Then give the LLM both the specification and the tests and ask it to implement code that passes them. This is specification-driven development and it is the only way to build a financial data layer that you can genuinely trust.

OmegaData built this way will be the foundation that makes every other project in the system trustworthy. It is worth doing correctly.