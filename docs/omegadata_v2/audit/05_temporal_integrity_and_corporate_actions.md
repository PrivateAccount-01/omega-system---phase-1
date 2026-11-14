# 05 — Temporal integrity and corporate actions

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Quantitative data-integrity reviewer; evidence classes: RUN / TEST / SYN / CMP / ARCH / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure

Inspected ORM, universe queries, loader updates, corporate-action corrections/adjustments, calendar, fixture references and selected test semantics. Ran in-memory/disposable diagnostic commands only; [results](logs/disposable-integrity-experiments.txt). The successful suite verifies existing expectations, not a complete PIT contract.

## Verified temporal findings

- [Universe query](../../../src/omegadata/track_b/universe_manager.py#L74) checks effective/removal dates and current instrument delisting; it does not check added_date or knowledge/publication timestamps. A synthetic membership added in 2026 and effective in 2019 is returned for 2020 (observed 1, strict expected 0). This is a concrete availability gap, not proof that all existing memberships leaked.
- [Membership model](../../../src/omegadata/db/models.py#L248) has business dates/source/confidence but no known_from/known_to or original publication evidence. Missing master rows silently disappear in get_universe; quarantine is preferable.
- [Price model](../../../src/omegadata/db/models.py#L189) has unique ISIN/exchange/date and no series/listing/release/raw artifact/parser/knowledge version. [Loaders](../../../src/omegadata/pipelines/sequential_pipeline.py#L600) update existing values. Historical corrections therefore cannot reconstruct all prior knowledge states from this table.
- [Adjustment recomputation](../../../src/omegadata/track_b/adjustment_engine.py#L23) selects non-superseded current actions, writes adjusted history, and has no decision timestamp. [Corrections](../../../src/omegadata/track_b/corporate_actions.py#L394) retain a supersedes link, which is useful, but as-known querying is missing. Demerger actual listing prices can later replace preliminary inputs.

## Adjustment mathematics and calendars

Decimal precision is 28 with explicit rounding; split/bonus price and reciprocal volume factors exist; raw fields remain separate. Cash dividends are intentionally not price-adjusted in this implementation. That behavior must be named as price-return semantics, not total return.

Rights calculation at [factor code](../../../src/omegadata/track_b/adjustment_engine.py#L218) looks up ex_date minus one **calendar** day. A synthetic Monday event with the last supplied bar on Friday returns None; independent TERP with P=100, N=4, R=1, S=50 gives (400+50)/5=90 and factor 0.9. The dates illustrate a missing preceding row; they do not assert an actual official session calendar. Missing issue price falls back to zero and adds metadata; downstream strict publication must reject unsupported assumptions.

[Calendar](../../../src/omegadata/track_a/trading_calendar.py#L153) explicitly supports special sessions and strict year coverage. It is **not simply weekday-only**. Source authenticity, session open/close boundaries, delayed corrections and complete historical coverage remain unverified. Preserve strict versus diagnostic behavior.

## Official versus synthetic reference integrity

The corpus currently contains 23 labeled official cases and 11 transformational cases, plus 14 manual cases. Tests check path existence and expected adjusted values. For example, [20MICRONS extract](../../../tests/fixtures/official_source/circular_extracts/20microns_reverse_split_2025-06-24.json#L1) claims an official reverse split but supplies no circular identifier, official URL, retrieval timestamp or original document hash. The [demerger extract](../../../tests/fixtures/official_source/circular_extracts/21stcenmgm_demerger_final_2025-06-24.json#L1) has the same provenance weakness. These are unverified official claims; this audit does not establish that the events are false. File existence and arithmetic agreement cannot authenticate an exchange event.

Five PIT snapshots do not establish complete membership changes or original information availability. Unknown publication times must not be backfilled with effective/ingested times. No fresh official reference was obtained.

## Limitations / next action

OD-06/07/08 owners must obtain independent source-backed event/session/membership evidence and a conservative unknown-availability policy; this requires human source-rights approval. Before publication, add immutable observation revisions and decision_at queries, calendar-aware rights lookback with maximum staleness, and return-basis-specific chains. Roll out through new versions with disposable migration/restore rehearsal. Same-model review here is not independent verification.

