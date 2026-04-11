# OmegaData — Track B Complete Ideation & Planning

## What Track B Is and Why It Exists Separately

Track B is every component where a wrong design decision made during coding produces data that looks correct but is wrong. The damage is invisible until months later when a signal's IC collapses and you trace it back to a price that was adjusted incorrectly in 2019.

Track B has zero tolerance for design ambiguity. Every decision is made here, in writing, before a single line of code exists. The vibe-coding session for Track B is then a precise transcription exercise — not a design exercise.

Track B has six components. They build in strict dependency order.

---

## The Dependency Order

```
COMPONENT 1: ISIN Master & Identifier System
        ↓
COMPONENT 2: Corporate Action Database & Classification
        ↓
COMPONENT 3: Price Adjustment Engine
        ↓
COMPONENT 4: Price Discontinuity Detector
        ↓
COMPONENT 5: Point-in-Time Universe Manager
        ↓
COMPONENT 6: Confidence Scoring & Data Trust System

All six feed into:
COMPONENT 7: Cross-Source Validation Framework
(runs across all of the above)
```

---

## Component 1 — ISIN Master & Identifier System

### What It Is

The single source of truth for every financial instrument that has ever traded on NSE or BSE. Every other component in OmegaData asks this component: "what do I know about this instrument?" It answers definitively.

### The Core Problem It Solves

Indian markets have three overlapping identifier systems that are all unreliable individually. NSE uses trading symbols that change. BSE uses scrip codes that are BSE-specific. The international standard is ISIN. A system built on any one of these three will break when that identifier changes. ISIN is the only identifier that persists across all corporate events except a full delisting.

### Design Decisions — Every Single One

**Decision 1: ISIN validation**

Every ISIN that enters the system is validated against the ISIN check digit algorithm before storage. ISIN is a 12-character string: 2-character country code (IN for India), 9-character alphanumeric identifier, 1-character check digit. The check digit is computed using the Luhn algorithm adapted for alphanumeric characters. An ISIN that fails this validation is rejected and logged — it never enters the master table.

**Decision 2: The instrument type taxonomy**

Every instrument is classified into exactly one type from this closed list: EQUITY, EQUITY_PREFERENCE, DEBENTURE, BOND, ETF, INDEX_FUTURES, STOCK_FUTURES, INDEX_OPTIONS_CE, INDEX_OPTIONS_PE, STOCK_OPTIONS_CE, STOCK_OPTIONS_PE, CURRENCY_FUTURES, COMMODITY_FUTURES. No instrument has two types. No instrument has an unclassified type. If a new instrument type appears that does not fit this taxonomy, the taxonomy is updated first, then the instrument is classified.

**Decision 3: Temporal validity — the active period model**

Every identifier mapping has an active period defined by valid_from and valid_to dates. Valid_to is null for currently active mappings. This applies to: symbol-to-ISIN mappings, exchange listings, index memberships, liquidity tier classifications, and sector classifications. A query for "what is the symbol for ISIN X" without a date parameter is invalid and rejected — the date context is mandatory because the answer changes over time.

**Decision 4: The symbol change protocol**

When NSE changes a stock's trading symbol, the following happens in this exact order, never varied:

First: A new record is inserted into the symbol_map table with the new symbol and valid_from set to the effective date of the change.

Second: The existing record's valid_to is set to the day before the effective date.

Third: An entry is created in the symbol_change_log table recording: old symbol, new symbol, effective date, reason for change, and the NSE circular reference that authorized the change.

Fourth: A data quality check runs to verify that bhavcopy files before the change date use the old symbol and files after use the new symbol. Discrepancies are flagged.

What does NOT happen: the historical bhavcopy data is not modified. The raw data stores whatever symbol NSE used on that date. The ISIN master is the translation layer.

**Decision 5: Handling ISINs that appear in BSE but not NSE**

Some instruments trade only on BSE. They are stored in the ISIN master with exchange marked as BSE_ONLY. They are excluded from all signal computations (signals are NSE-focused) but are included in the corporate action database because their corporate actions can affect NSE-listed group companies.

**Decision 6: The delisting protocol**

When a stock is delisted, the following happens:

The ISIN master record gets delisted_date populated.

The symbol_map record gets valid_to set to the delisting date.

A delisting_record is created with: reason (voluntary, regulatory, merger, insolvency), last trading date, last recorded price, delisting_type.

The stock is removed from all point-in-time universe queries with as_of_date after the delisting date.

Historical data is preserved permanently. The stock existed. The data is real. It is simply excluded from forward computations.

The delisting record is the survivorship bias correction mechanism. Without it, a backtest that excludes delisted stocks overstates returns because it only includes survivors.

**Decision 7: Instrument creation — the IPO protocol**

When a new stock is listed:

The ISIN master record is created on the listing date.

The symbol_map record valid_from is set to the listing date.

The IPO price and issue size are stored in a separate IPO_registry table.

The stock is NOT added to any index membership until NSE formally announces its inclusion. An IPO listing date and an index inclusion date are always different events.

**Decision 8: Cross-listing handling**

Some Indian companies have ADRs or GDRs listed overseas. The ISIN master stores the primary NSE ISIN as the canonical identifier. Foreign listing identifiers are stored in a cross_listing_map table that links the NSE ISIN to the foreign identifier. Foreign price data is not used in signal computation but is stored for cross-asset analysis.

---

## Component 2 — Corporate Action Database & Classification

### What It Is

The authoritative record of every corporate event that has affected or could affect the price, share count, or identity of any instrument in the ISIN master. It is the input to the price adjustment engine. Its accuracy directly determines the accuracy of every adjusted price in the system.

### The Core Problem It Solves

NSE publishes corporate action data in a format that is inconsistent across time periods, missing fields in older records, and occasionally wrong when cross-referenced against BSE. A naive implementation that trusts NSE's corporate action feed will silently produce wrong adjustments for a predictable set of edge cases. This component standardizes, validates, and cross-validates every corporate action before it is used.

### Design Decisions

**Decision 1: The corporate action taxonomy — complete and closed**

Every corporate action is classified into exactly one type. The complete closed list:

BONUS: Free shares issued to existing shareholders in a fixed ratio.

SPLIT: Face value reduction with proportional share count increase.

SPLIT_REVERSE: Face value increase with proportional share count decrease. Rare but exists.

RIGHTS: Shares offered to existing shareholders at a fixed price below market.

RIGHTS_RENOUNCE: A rights issue where shareholders can renounce their rights. Treated identically to RIGHTS for price adjustment purposes.

DIVIDEND_CASH: Cash dividend. Stored but not used in price adjustment by default.

DIVIDEND_SPECIAL: One-time special dividend. Stored and flagged as potentially significant.

MERGER_ACQUIRER: This company absorbed another company. No price adjustment needed — the acquirer continues trading.

MERGER_TARGET: This company was absorbed into another. Price series ends on merger date.

DEMERGER_PARENT: This company spun off a subsidiary. Requires price adjustment on ex-date.

DEMERGER_SPINOFF: The new entity created by a demerger. Price series begins on listing date.

BUYBACK_OPEN_MARKET: Company buying back shares from open market. No price adjustment — market mechanism handles this.

BUYBACK_TENDER: Company buying shares via tender offer at fixed price. Potential price impact on ex-date.

RECLASSIFICATION: Change in series type (EQ to BE or similar). No price adjustment but affects universe membership.

SUSPENSION: Trading suspended by regulator. Price series gap begins.

REINSTATEMENT: Trading resumed after suspension. Price series gap ends.

DELISTING_VOLUNTARY: Company chose to delist.

DELISTING_REGULATORY: Regulator required delisting.

DELISTING_MERGER: Delisting due to merger completion.

Any corporate action that cannot be classified into one of these types is stored as UNCLASSIFIED with a mandatory notes field and is routed to manual review before any adjustment is applied.

**Decision 2: The dual-source collection protocol**

Every corporate action is collected from both NSE and BSE independently. Collection happens on a defined schedule: NSE corporate action calendar is checked at 07:00 IST and 19:00 IST daily. BSE corporate action calendar is checked at 07:30 IST and 19:30 IST daily.

The results are stored in two separate staging tables: nse_ca_staging and bse_ca_staging. A matching algorithm runs at 20:00 IST daily to cross-validate. The matching algorithm is:

Step 1 — Match by ISIN and ex_date. If both sources have an event with the same ISIN and ex_date, compare the action type and key parameters.

Step 2 — If action type matches and parameters agree within tolerance: create a confirmed_ca record with confidence HIGH. Mark both staging records as matched.

Step 3 — If action type matches but parameters disagree: create a confirmed_ca record with confidence MEDIUM. Flag for review. Use the NSE parameters as primary (NSE is the primary exchange for most instruments). Log the discrepancy.

Step 4 — If NSE has a record but BSE does not: create a confirmed_ca record with confidence MEDIUM. This is expected for some corporate action types where BSE disclosure is not required.

Step 5 — If BSE has a record but NSE does not: create a confirmed_ca record with confidence LOW. Flag for urgent review. This should be rare for NSE-listed stocks and may indicate a data collection failure.

Step 6 — Unmatched records from either source after 48 hours: escalate to manual review queue.

**Decision 3: Required fields per action type**

Every corporate action type has a defined set of required fields. A record without all required fields for its type is not processed — it is held in staging until the missing fields are obtained or the record is manually overridden.

For BONUS: isin, ex_date, record_date, bonus_ratio_numerator, bonus_ratio_denominator, board_meeting_date.

For SPLIT: isin, ex_date, old_face_value, new_face_value.

For RIGHTS: isin, ex_date, record_date, rights_ratio_numerator, rights_ratio_denominator, issue_price, issue_type (fully paid or partly paid), subscription_close_date.

For MERGER_TARGET: isin, merger_effective_date, acquirer_isin, swap_ratio (shares of acquirer per share of target), cash_component (if any).

For DEMERGER_PARENT: isin, ex_date, spinoff_isin, demerger_ratio.

**Decision 4: The immutability rule**

Once a corporate action record is in the confirmed_ca table with confidence HIGH, it is never modified. If an error is discovered, a correction record is created with a reference to the original and the original is marked as superseded. The adjustment engine always uses the most recent non-superseded record. The full history of corrections is preserved permanently.

This immutability rule exists because the adjustment chain for every price record references specific corporate action record IDs. If those records change, the adjustment chain becomes inconsistent. By making records immutable, the adjustment chain is always reproducible.

**Decision 5: Announcement date versus ex-date — both matter**

The corporate action database stores both the announcement date and the ex-date for every event. These are different dates with different uses.

Announcement date is used by the signal factory for event-driven signals. A promoter buying stock after a bonus announcement but before the ex-date is a different signal than buying after the ex-date.

Ex-date is used by the adjustment engine. Price adjustment is always applied on the ex-date, never the announcement date.

Recording both dates enables the signal factory to compute how markets react to announcements before they take effect — a significant source of event-driven alpha.

---

## Component 3 — Price Adjustment Engine

### What It Is

The mathematical transformation engine that converts raw traded prices into adjusted prices comparable across all corporate action events. It is the most mathematically precise component in OmegaData.

### The Core Problem It Solves

A raw price series for a stock that has had a 1:1 bonus issue shows an overnight price drop of 50% on the ex-date. This is not a loss — it is a mathematical artifact. Any signal computed on unadjusted prices will generate a massive false negative signal on every bonus ex-date. The adjustment engine eliminates these artifacts.

### Design Decisions

**Decision 1: Adjustment direction — backward only**

All price adjustments are applied backward from the ex-date. Prices on and after the ex-date are stored as raw traded prices. Prices before the ex-date are adjusted to be comparable to the current price level.

This decision is consistent with the Bloomberg convention and with the convention used in every major academic study of Indian equity returns. It ensures that the most recent price is always the actual traded price.

**Decision 2: Adjustment chain — the complete audit trail**

Every adjusted price record stores its adjustment_chain: the ordered list of every corporate action that has been applied to produce the adjusted value. The chain is stored as a structured array:

Each element contains: corporate_action_id (reference to confirmed_ca table), action_type, ex_date, adjustment_factor_applied, and cumulative_factor_at_this_point.

This chain allows any adjusted price to be un-adjusted back to its original raw value by dividing by the cumulative factor. It allows the system to recompute any adjusted price from scratch if a correction is applied.

**Decision 3: Separate adjustment factors for price and volume**

Price and volume are adjusted with different factors because they represent different economic quantities.

For a 1:1 bonus issue: price factor = 0.5, volume factor = 2.0. Post-adjustment, the price is halved and the volume is doubled. This preserves the total traded value (price × volume) across the ex-date, which is the economically correct behavior.

If volume is not adjusted: a volume signal comparing pre and post-bonus volume will see a doubling that is entirely artificial.

**Decision 4: The four adjustment formulas — exact**

BONUS adjustment:
Price factor = existing / (existing + bonus) where existing and bonus are from the ratio.
Volume factor = 1 / price_factor.
Both factors are stored to 8 decimal places.

SPLIT adjustment:
Price factor = new_face_value / old_face_value.
Volume factor = old_face_value / new_face_value.

RIGHTS adjustment:
TERP = (N × P + R × S) / (N + R)
Price factor = TERP / P
Where P is the closing price on (ex_date - 1), not a fixed reference price.
This means the rights adjustment factor is computed using the actual market price, not a theoretical price. It must be recomputed each time from the actual historical price.
Volume factor = 1.0 for rights issues (share count increase is gradual as rights are subscribed, not instantaneous).

DEMERGER adjustment:
Price factor = 1 - (spinoff_value / parent_value_pre_demerger)
Spinoff value is estimated from the first day of trading of the spinoff entity.
This is an approximation — the exact demerger adjustment requires the actual first-day price of the spinoff.
The demerger adjustment is therefore computed in two stages: a preliminary adjustment on ex-date using theoretical values, and a final adjustment after the spinoff begins trading using actual prices.

**Decision 5: Cumulative factor computation — precision rules**

Cumulative factors are computed using Python's Decimal type with 28 significant figures, not floating point. Floating point arithmetic accumulates errors across 30 years of corporate action adjustments. A stock with 15 corporate actions over 30 years will have a cumulative factor computed as the product of 15 individual factors. Using float64 for this computation introduces errors of 0.001-0.01% per factor application — which becomes significant across 15 applications.

The final adjusted price is stored as a float32 (sufficient precision for prices) but the intermediate cumulative factor is always computed in Decimal.

**Decision 6: The rights issue special case — subscription price is zero**

When the subscription price for a rights issue is unavailable (missing from both NSE and BSE records), the adjustment uses subscription price = 0. This is the conservative assumption: it treats the rights as worthless, which maximizes the price adjustment factor and produces the smallest adjusted historical price. This is preferable to using an estimated subscription price because underestimating the adjustment is less dangerous than overestimating it for signal computation.

All records where subscription price = 0 was used as a fallback are flagged in the adjustment chain. The flag allows the system to identify and recompute these adjustments if the actual subscription price is later recovered from alternative sources.

**Decision 7: What the adjustment engine does not adjust**

Dividends are not adjusted by default. The unadjusted-for-dividends convention is used for all signal computation. This matches the convention in Indian academic research and ensures signals are comparable to published research benchmarks.

Buyback events are not adjusted. The price impact of buybacks is captured through normal market price movements.

Suspension and reinstatement events create gaps in the price series. The adjustment engine does not fill gaps. Gaps are preserved as null values. Signal computation handles nulls according to its own missing data policy (defined in OmegaSignal, not OmegaData).

---

## Component 4 — Price Discontinuity Detector

### What It Is

The automated quality control layer that identifies price series where a corporate action adjustment has not been applied, has been applied incorrectly, or where a non-corporate-action event has created an apparent discontinuity.

### Design Decisions

**Decision 1: The three categories of detected discontinuities**

Category A — Probable unadjusted corporate action:
Idiosyncratic overnight return below -35% with no market-wide event.
Action: Automatic lookup in corporate action database.
If a matching confirmed_ca record exists: add to adjustment queue, apply adjustment in next batch run.
If no matching record exists: add to manual review queue, do not apply adjustment.

Category B — Probable partial adjustment or data error:
Idiosyncratic overnight return between -35% and -10% (downward) or above +25% (upward).
Action: Flag for review. Do not automatically adjust. Log in discontinuity report.

Category C — Probable data collection error:
OHLC integrity failure (high below close, low above open, etc.) or price outside 20% circuit limit without a corresponding circuit breaker event.
Action: Mark record confidence as 0.0. Do not include in any computation. Log in data quality report.

**Decision 2: The beta estimation fallback hierarchy**

Beta is required to compute idiosyncratic returns. For stocks with insufficient history, the following fallback hierarchy applies:

Level 1 (preferred): Rolling 252-day beta with minimum 60 valid observations.

Level 2: Rolling 126-day beta with minimum 40 valid observations.

Level 3: Sector median beta computed from all stocks in the same sector classification with sufficient history.

Level 4: Beta = 1.0 (market assumption). This is the fallback of last resort and is flagged in the discontinuity record.

**Decision 3: Exclusion dates — events that look like discontinuities but are not**

The detector maintains an exclusion_dates table. On these dates, the discontinuity detection thresholds are relaxed or suspended entirely because market-wide events legitimately cause large idiosyncratic moves:

Index circuit breaker halt dates.
Dates when Nifty moved more than 5% intraday.
Dates of confirmed global financial crises (defined by a curated list of events updated annually).
Dates immediately following a trading halt or suspension for a specific stock.

On exclusion dates, the Category A threshold is moved from -35% to -50% and the Category B thresholds are widened proportionally. The exclusion date list is stored in the database and updated as new significant market events occur.

**Decision 4: Detection runs twice — intraday and end-of-day**

The detector runs at two points in the daily pipeline:

End-of-day run: Comprehensive detection against the full bhavcopy data after normalization. This is the primary detection run. Results feed into the adjustment queue and manual review queue.

Historical audit run: Runs weekly against the full historical dataset. Catches cases where a corporate action record was added to the database after the affected dates had already been processed. When a new corporate action is added retroactively, the historical audit run ensures all affected historical prices are re-adjusted.

---

## Component 5 — Point-in-Time Universe Manager

### What It Is

The system that answers the question: what stocks were members of index X on date Y, using only information that was available on date Y?

### The Core Problem It Solves

Using the current Nifty500 composition for all historical backtesting overstates returns by 2-4% annually due to survivorship bias. Stocks that were removed from the index because they performed poorly are excluded from the historical analysis. Their poor returns are not counted. This inflates every historical signal IC and every historical backtest return. The point-in-time universe manager eliminates this bias completely.

### Design Decisions

**Decision 1: The knowledge date versus effective date distinction**

Every index change has two dates that must both be stored:

Knowledge date: when NSE announced the change. This is the date the market learned about the upcoming change.

Effective date: when the change took effect for index calculation purposes.

Signal computations use effective_date for determining universe membership.
Event-driven signals (signals based on the announcement of index additions/removals) use knowledge_date.
These are always different dates and the difference is always significant — NSE typically announces index reconstitution 2-4 weeks before the effective date.

**Decision 2: The four universe tiers and their data sources**

NIFTY50:
NSE announces every constituent change via press release.
Every constituent change since 2000 is documented in NSE press releases.
These press releases are the primary source.
Coverage: complete from 2000-present.

NIFTY200:
Constituent changes are announced via NSE circulars.
Coverage: complete from 2010-present from NSE records.
Pre-2010: reconstructed from bhavcopy trading data (stocks that regularly appear in the bhavcopy with sufficient volume) combined with academic data sources.

NIFTY500:
Same construction methodology as NIFTY200.
Coverage: complete from 2010-present.
Pre-2010: reconstructed with lower confidence (flagged as RECONSTRUCTED in the source field).

SECTOR INDICES (NiftyBank, NiftyIT, NiftyAuto, etc.):
Constituent changes are published with sector index methodology documents.
Coverage: complete from 2010-present for major sector indices.

**Decision 3: The reconstruction methodology for pre-2010 data**

For periods where NSE press releases are not available:

Step 1: Extract all ISINs that appear in bhavcopy EQ series data for the target period.

Step 2: Apply market capitalization filter (approximate Nifty500 inclusion threshold using available data).

Step 3: Apply liquidity filter (minimum 20-day average trading volume).

Step 4: Cross-reference with any available academic datasets that document index composition for that period.

Step 5: Mark all reconstructed records with source = RECONSTRUCTED and confidence = 0.70.

Reconstructed records are used in long-horizon backtests but flagged in all output. Research that depends on pre-2010 universe composition is explicitly marked as subject to survivorship bias uncertainty.

**Decision 4: Index reconstitution as a signal input**

Index additions and removals are stored in a way that makes them queryable as event signals:

Upcoming additions (announced but not yet effective) are stored with a flag indicating pre-effectiveness status. The signal factory can query: what stocks are scheduled for index addition in the next 30 days?

Recent removals are stored with removal reason where available. Stocks removed due to corporate events (mergers, delistings) are distinguished from stocks removed due to declining market capitalization or liquidity.

The MSCI rebalancing effective dates are stored in a separate MSCI_rebalancing table. These dates are used to suppress the FII conviction signal during mechanical rebalancing flows.

---

## Component 6 — Confidence Scoring & Data Trust System

### What It Is

The system that attaches a quantitative trust score to every record in OmegaData and enforces that downstream components only use records above the appropriate confidence threshold for their use case.

### Design Decisions

**Decision 1: Confidence is computed, not assigned**

Confidence scores are not manually assigned. They are computed from a defined algorithm applied to every record. The algorithm is deterministic — the same inputs always produce the same confidence score. The algorithm is versioned — when the algorithm changes, all confidence scores are recomputed.

**Decision 2: The confidence computation algorithm — complete definition**

Every price record starts with a base confidence of 1.00. Deductions are applied for specific conditions. The final confidence is the base minus all applicable deductions, floored at 0.00.

Deduction -0.10: Primary source is a secondary provider (yfinance, reconstructed) rather than NSE official bhavcopy.

Deduction -0.10: Cross-source validation unavailable (BSE data not present for this ISIN/date combination).

Deduction -0.05: Cross-source validation present but shows discrepancy between 0.05% and 0.5%.

Deduction -0.25: Cross-source validation shows discrepancy above 0.5%. (Large discrepancy — one source is likely wrong.)

Deduction -0.15: Adjustment chain contains a corporate action with confidence MEDIUM (cross-source discrepancy on the corporate action record).

Deduction -0.30: Adjustment chain contains a corporate action with confidence LOW.

Deduction -0.05: Rights issue adjustment where subscription price was unavailable (zero used as fallback).

Deduction -0.20: Record is a gap-fill (imputed value between two valid records).

Deduction -0.10: Record is from a reconstructed point-in-time universe period (pre-2010).

Deduction -0.50: Discontinuity detector flagged this record as Category B (probable partial adjustment or data error). (This record is suspicious but not definitely wrong.)

Deduction -1.00: Discontinuity detector flagged this record as Category C (probable data collection error). (Confidence floors to 0.00 — record is invalid.)

**Decision 3: Threshold enforcement — hardcoded at the API level**

The OmegaData API enforces confidence thresholds automatically based on the query context. These thresholds are not configurable by the caller — they are built into the API:

Endpoint /prices/{isin} with context=LIVE_SIGNAL: Returns only records with confidence ≥ 0.90. Records below this threshold are excluded from the response. The response includes a metadata field indicating how many records were excluded and the date range of exclusions.

Endpoint /prices/{isin} with context=BACKTEST: Returns records with confidence ≥ 0.70. Records below this threshold are excluded.

Endpoint /prices/{isin} with context=RESEARCH (no downstream trading): Returns all records with confidence ≥ 0.50 and includes confidence scores in the response for the caller to apply their own filtering.

Endpoint /prices/{isin} with context=AUDIT: Returns all records including those with confidence 0.00, for data quality investigation purposes only. This endpoint requires explicit authentication and is not available to the signal factory.

**Decision 4: The monthly confidence report**

A monthly report is automatically generated on the first day of each month for the previous month. The report contains:

Total records processed in the month.
Distribution of confidence scores (histogram by 0.10 bucket).
Percentage of records below each threshold (0.90, 0.80, 0.70, 0.50).
Records with confidence 0.00: complete list with reasons.
Trend: comparison of confidence distribution to the previous three months.
Most common deduction reasons: ranked list of what is causing confidence reductions.
Corporate action coverage: percentage of detected events that were confirmed from dual sources.

This report is the operational equivalent of Bloomberg's data quality team's monthly review. It makes data quality trends visible and drives improvement prioritization.

---

## Component 7 — Cross-Source Validation Framework

### What It Is

The systematic comparison of every data point that appears in multiple sources. It is the quality control layer that catches errors that individual source validation cannot catch.

### Design Decisions

**Decision 1: The validation pairs — complete list**

NSE bhavcopy vs BSE bhavcopy: Daily OHLCV for dual-listed stocks. Agreement tolerance: 0.10% on close price (small differences exist due to exchange-specific auction mechanisms).

NSE corporate action calendar vs BSE corporate action calendar: All event types. Agreement required on: action type, ex_date, key ratio or price parameter. Tolerance: zero for action type and date (these must match exactly), 1% for numeric parameters (subscription prices may be reported with minor differences).

NSE FII data vs RBI external sector data: Monthly aggregates should be consistent. Discrepancies above 5% on monthly net flow trigger a review.

OmegaData computed IV vs Opstra/alternative sources (where available): Spot-checked quarterly on a sample of 20 ISIN/date/strike combinations. Validates the IV surface construction methodology.

yfinance adjusted prices vs OmegaData adjusted prices: For a reference set of 50 stocks, yfinance-adjusted prices are compared quarterly. Expected differences exist (yfinance adjustment methodology differs from OmegaData's). Differences above 5% on any date trigger investigation.

**Decision 2: Disagreement handling — by severity**

Disagreement below tolerance: Both sources agree within the acceptable range. The NSE source is used as primary. The agreement is recorded in the validation log as PASS.

Disagreement above tolerance but below 2×tolerance: A review record is created. The NSE source is used with confidence deduction applied. The discrepancy is included in the monthly quality report.

Disagreement above 2×tolerance: A high-priority review record is created. The record is held at confidence 0.50 until the discrepancy is resolved. An alert is generated immediately.

Systematic disagreement (same direction across 5+ consecutive dates for the same ISIN): Treated as a potential methodology error or data collection failure. Escalated immediately. The affected ISIN is flagged for comprehensive review.

**Decision 3: The validation audit log structure**

Every validation comparison is recorded permanently. The audit log stores: validation_date, source_1, source_2, isin, data_date, field_compared, source_1_value, source_2_value, difference_absolute, difference_pct, tolerance_applied, result (PASS/WARN/FAIL), resolution_status, resolution_notes.

The audit log is never deleted. It is the permanent record of OmegaData's data quality history. Queries against the audit log enable: trend analysis of data quality over time, identification of sources that consistently disagree, and documentation of data quality for downstream users.

---

## The Track B Testing Specification

Before vibe-coding Track B, the test specification is written for every component. The vibe-coding session is then: "implement code that passes these tests."

### Corporate Action Reference Cases — The Non-Negotiable Test Set

These 12 reference cases are hand-computed from publicly available historical data. Every implementation must produce exactly these results. They run on every code change.

```
REFERENCE CASE 1: Infosys 1:1 Bonus (2018)
  ISIN: INE009A01021
  Ex-date: June 14, 2018
  Pre-adjustment close on June 13, 2018: ₹1,270.45 (verify from NSE)
  Expected adjustment factor: 0.5
  Expected adjusted price on June 13, 2018: ₹635.225
  Expected adjusted prices for all dates before June 14, 2018:
    raw_price × 0.5

REFERENCE CASE 2: TCS Stock Split FV ₹1 to ₹1 (no split needed)
  [Document a TCS corporate action that did occur]

REFERENCE CASE 3: [Rights issue — identify a specific NSE stock with
  complete publicly available rights issue data]

REFERENCE CASE 4 through 12:
  [Eight additional reference cases covering: reverse split,
  multiple sequential corporate actions on same stock,
  rights issue with known subscription price,
  demerger with known spinoff listing price,
  merger target,
  corporate action on stock that was subsequently delisted,
  bonus issue immediately followed by split,
  corporate action during market-wide stress period]
```

The actual values for these reference cases are computed manually from NSE historical data before any code is written. They are the ground truth against which every implementation is measured.

### Discontinuity Detector Reference Cases

Five reference cases where the correct detection outcome is known:

A date where a bonus issue occurred and the bhavcopy price is unadjusted: the detector must classify this as Category A and route it to the adjustment queue.

A date where a market-wide crash caused a large idiosyncratic move: the detector must NOT classify this as a corporate action (the date is in the exclusion list).

A date with a data collection error (price clearly wrong based on OHLC integrity): the detector must classify this as Category C.

A date where the corporate action was correctly pre-applied in the bhavcopy: the detector must find no discontinuity.

A date where a rights issue created a partial discontinuity (smaller than bonus): the detector must classify this as Category B.

### Universe Manager Reference Cases

Five reference dates where the exact Nifty500 composition is known and independently verifiable:

Current date: composition matches the live NSE published list exactly.

March 23, 2020 (COVID crash peak): composition matches NSE records for that date.

Two additional reference dates from NSE announcements.

One pre-2010 date: composition matches the best available academic source with a note that this is reconstructed data.

---

## The Vibe-Coding Instructions for Track B

When Track B vibe-coding begins, the session structure is:

**Session 1: Component 1 — ISIN Master**
Prompt: "Here is the complete design specification for the ISIN Master component of OmegaData [paste Component 1 design decisions]. Here are the tests this implementation must pass [paste Component 1 tests]. Implement the database schema, the ISIN validation function, the symbol change protocol, and the delisting protocol exactly as specified. Make no design decisions — all decisions are in the specification."

**Session 2: Component 2 — Corporate Action Database**
Prompt: "Here is the complete design specification for the Corporate Action Database [paste Component 2]. The ISIN Master is already implemented [paste relevant interface]. Implement the corporate action taxonomy, the dual-source collection protocol, and the required fields validation exactly as specified."

**Sessions 3-7: One session per remaining component, same structure.**

**Session 8: Integration**
Prompt: "All six Track B components are implemented. Here are their interfaces [paste interfaces]. Implement the integration layer that connects them in the dependency order specified. The integration layer must pass these end-to-end tests [paste integration tests]."

**The review discipline for each session:**
Before merging any Track B output, verify against the specification. Not code review — specification compliance review. Does the code produce the exact output the specification requires for every reference case? Run the reference case tests. If any reference case fails, the session output is not merged. The specification is not changed to match the code — the code is changed to match the specification.

---

## What You Hand to the Vibe-Coding Session

One document. Seven sections. Complete design decisions for every component. Reference cases with hand-computed expected outputs. Test specifications written before any code exists.

The vibe-coding session for Track B is then fast and precise. The LLM is not making decisions — it is implementing decisions you have already made correctly. The output is reviewable against a written standard, not against intuition.

This is how OmegaData achieves Bloomberg-quality data trust. Not because the code is perfect. Because the design is precise and the tests verify compliance with that precision.