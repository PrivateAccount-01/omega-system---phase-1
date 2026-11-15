# Source-era audit and disputed transition

Run20261115T190654Z @bbc38716d902fe27192f80affaca29c6f51e9890. RUN=static inspection/indexed research; ARCH=stored fixtures/reports; TEST/SYN=synthetic; CLAIM=unsupported attribution; UNK=unverified. Audit/plan only; no executable defect reproduction or official financial certification.

## Evidence-supported distinction

The indexed official [NSE reports page](https://www.nseindia.com/all-reports/) describes withdrawal of two earlier cash-equity bhavcopy products and migration to the UDiFF final ZIP on2024-07-08, citing circular62424 dated2024-06-12. This is independent documentation evidence for the announced discontinuation/switch, **not** proof of earliest UDiFF availability, exclusive format use, every historical row or all overlap periods. Original document bytes, exact PDF/schema catalogue version and human reference permission were not obtained. Format interpretation remains SOURCE_REFERENCE_PENDING. See [reference registry](reference_registry.json).

| Source/period | Current repository routing and columns | Reference/rights status | Proposed treatment, not applied |
|---|---|---|---|
| NSE through2009 | pre_2010; legacy cm{DDMONYYYY}bhav.csv.zip; SYMBOL,SERIES,OHLC,TOTTRDQTY,ISIN,TIMESTAMP expected by later validator | ARCH implementation hypothesis; no authenticated era specification | Reference-specific versioned legacy decoder only after verified coverage |
| NSE2010–2019 | 2010_2019; same legacy member pattern |2019 synthetic positive exists, not official corpus | Retain old behavior; no certification upgrade |
| NSE2020-01-01 to pre-transition2024 | registry2019_present starts2020; validator year>=2020 selects modern member and TradDt/BizDt/ISIN/TckrSymb/OHLC/TtlTradgVol mapping | **P1 unsupported year cutover**;2020 start has no supporting reviewed reference; not proven universally impossible | Disputed/unknown interval; require format+reference-specific dispatch; no global2020→2024 replacement |
| NSE2024 transition/overlap | Current code has no distinct June/July transition or parallel-format model | July8 switch documented at page level; June24 boundary/catalogue/parallel coverage UNK | Freeze dated format identities from authentic specs/rows, quarantine ambiguity |
| NSE2024-07-08 onward | Same current modern route;2026 synthetic modern positive | Page supports named successor, not exact field semantics/first available date | Prospective parser version once schema/row proof exists; current source rights remain pending |
| BSE all dates | One unbounded all era: BhavCopy_BSE_CM_0_0_0_{YYYYMMDD}_F_0000.CSV; EQ_ISINCODE and dated ZIP fallbacks; old_bse plus modern column branches | ARCH mapping only; separate dated specification/representative sample/human permission absent | SOURCE_REFERENCE_PENDING; no independent BSE certification |

There is **no** basis here to mark2020-01-01 as a verified UDiFF introduction date. Conversely a2024 discontinuation notice alone does not disprove every earlier pilot/parallel file. Proposed support boundaries remain provisional; no source table was changed and contested historical behavior is excluded from certification, not silently disabled by edits.

## Boundary/session audit

The indexed official [NSE/CMTR/59722,2023-12-12](https://nsearchives.nseindia.com/content/circulars/CMTR59722.pdf) supplies an annual2024 capital-market closure list. July17 appears as a holiday; the queried June/early-July dates are absent from that list. Absence is only corroboration, not a positive proof of a normal session or absence of later amendments/special sessions. No real bhavcopy/session endpoint was queried. The local calendar supplies dates but has prose attribution without per-date original-document hashes; it is not an independent oracle.

| Boundary | Candidate adjacent dates for future frozen tests | Current independent session status |
|---|---|---|
|2020-01-01 |2019-12-31,2020-01-01,2020-01-02 |2020 official CM calendar not authenticated; search returned2021 circulars, which were explicitly rejected as wrong-year proof |
|2024-06-24 |2024-06-21,06-24,06-25 | Not listed as closures in initial annual2024 excerpt; exact sessions and amendments PENDING |
|2024-07-05 |2024-07-04,07-05 | Same limited annual-calendar corroboration, not confirmed sessions |
|2024-07-08 |2024-07-05,07-08,07-09 | Product switch date supported; calendar/session and row-level boundary proof PENDING |
| Later2024 control |2024-07-16,07-17,07-18 | July17 closure supported by annual calendar; neighboring actual-session proof PENDING |

These are explicitly **candidate dates**, not weekday-derived trading-day assertions. No inference from unrelated commodity/F&O reports was used to certify NSE CM. Circular64667 about trade-modification reports and a2021 holiday circular were irrelevant to cash-bhavcopy schema/session certification and excluded.

## Current call-path reconciliation

| Existing path | Observed assumption/side effect | Future controlled change scope |
|---|---|---|
| [source_registry.py](../../../../../src/omegadata/track_a/source_registry.py) | NSE modern route from2020, both modern/legacy failovers; F&O has its own2024-07-08 split | Separate CM format references, avoid borrowing F&O evidence |
| [acquisition.py](../../../../../src/omegadata/track_a/acquisition.py) | year<2020 toggles required header/member; both TradDt/BizDt required equal requested date; modern dedupe key omits series | T05/T06/T15/T19 semantic tests before any authorized correction; business-vs-trade date semantics require exact specs |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | Registry era+fallback URL candidates; actual payload validation and rights before archive put | Read-only now; reproduced integration defect and explicit scope amendment needed to edit |
| [sequential_pipeline.py](../../../../../src/omegadata/pipelines/sequential_pipeline.py) | First CSV member, UTF8 errors ignored, alias normalization, skips incomplete/non-EQ rows; adds/updates PriceRecord keyed by ISIN/day | New pure parser must not call this writer. Optional default-OFF compatibility adapter only when authorized; no DB changes |
| [backfill_nse_equity_history.py](../../../../../scripts/backfill_nse_equity_history.py) | Duplicated year-era classification; permissive either-header archive check; writes historical report | Inventory only; script modification outside current narrow approved slice, no execution |
| [generate_source_probe_report.py](../../../../../scripts/generate_source_probe_report.py) | Modern NSE URL renderer independent of date-era; writes artifacts | No probes/execution; scope expansion needed for a later correction |
| [test_od02_acquisition.py](../../../../../tests/unit/test_od02_acquisition.py) | Explicit positive eras2019 and2026, not transition interval | Add future disputed-year/boundary cases without weakening inherited assertions |
| [test_pipeline_and_api.py](../../../../../tests/unit/test_pipeline_and_api.py) |2024-01-02 seed fixture uses a modern-named member | TEST/SYN/legacy-cache fixture, not proof UDiFF was officially used then; preserve unchanged |

Official-reference-verified representative files: **0 established**. No legacy raw objects, cached data, historic prices, policy records or existing fixture labels were rewritten. Missing documents/permissions are blockers, not passing tests.
