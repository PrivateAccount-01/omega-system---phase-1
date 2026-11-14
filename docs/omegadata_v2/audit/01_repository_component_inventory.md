# 01 — Repository component inventory

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Maker / architecture reviewer; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure

Read core source, configuration, tests, workflow and repository plans; indexed all 46 Python modules using AST without importing application startup. [Complete module/symbol inventory](logs/module-and-package-inventory.json) records definition line numbers. [Search evidence](logs/component-search.md) and [temporal search](logs/temporal-and-side-effect-search.txt) support the following map. File references point to working-tree source; the inventory supplies precise line numbers.

| Components | Existing code and observed role | Current limitation |
|---|---|---|
| OD-01 | [source_registry.py:21](../../../src/omegadata/track_a/source_registry.py#L21), DataSource/SourceEra | URLs, format eras and budgets; no human rights approval contract |
| OD-02 / 04 | [download_manager.py:93](../../../src/omegadata/track_a/download_manager.py#L93), cache, transport fallback, validation, hashed raw files | Hash recheck on cache hit exists; non-atomic writes and incomplete equity validation |
| OD-03 | Registry direct HTTP is current path | No authorized JS pilot demonstrated; optional and deferred |
| OD-05 | [sequential_pipeline.py:503](../../../src/omegadata/pipelines/sequential_pipeline.py#L503), NSE/BSE/FO/CA/sidefeed loaders | Source normalization co-located with orchestration; edits update current rows |
| OD-06 | [isin_master.py:33](../../../src/omegadata/track_b/isin_master.py#L33), [trading_calendar.py:20](../../../src/omegadata/track_a/trading_calendar.py#L20) | Luhn, dated mappings, delistings, explicit holiday/special sessions; listing identity and knowledge time incomplete |
| OD-07 | [corporate_actions.py:63](../../../src/omegadata/track_b/corporate_actions.py#L63), matching/parser/policies, [adjustment_engine.py:23](../../../src/omegadata/track_b/adjustment_engine.py#L23) | Decimal adjustments and correction links; latest-state recomputation and calendar-day rights lookup |
| OD-08 | [universe_manager.py:44](../../../src/omegadata/track_b/universe_manager.py#L44) | Effective-date membership and five reference snapshots; no strict decision-time availability |
| OD-09 | [cross_source_validation.py:42](../../../src/omegadata/track_b/cross_source_validation.py#L42), confidence, discontinuity, manual review | Policy-backed comparisons and scoped blocks exist; independent comparability calibration still required |
| OD-10 | [storage.py:22](../../../src/omegadata/track_a/storage.py#L22), [models.py:189](../../../src/omegadata/db/models.py#L189) | Fixed daily Parquet path; one current equity row per ISIN/exchange/date |
| OD-11 | [release_manager.py:494](../../../src/omegadata/track_b/release_manager.py#L494), [release_readiness.py:163](../../../src/omegadata/track_b/release_readiness.py#L163), [publication.py:31](../../../src/omegadata/track_b/publication.py#L31) | Per-row API blocking exists; bundle export/promotion is not an equivalent fail-closed contract |
| OD-12 | [api/main.py](../../../src/omegadata/api/main.py), terminal UI | Release metadata and release-backed sidefeed/derivative reads exist; full decision-time equity contract absent |
| OD-13 | [collection_schedule.py](../../../src/omegadata/track_a/collection_schedule.py), orchestration, monitoring, alerting, SLO; Airflow/infra | Offline behavior covered; live services and crash recovery not executed |
| OD-14 | [pyproject.toml](../../../pyproject.toml), [calendar workflow](../../../.github/workflows/trading-calendar-guard.yml) | Floating minimum dependencies; calendar-only CI; signing material tracked |
| OD-15 | [run_full_pipeline.py](../../../scripts/run_full_pipeline.py), historical proofs | Existing replay evidence is not fresh acquisition or full certification |
| OD-16 | News, participant flows, indices, futures/options loaders and exports | Existing breadth does not authorize feed expansion before core correctness |

## Existing tests and operating profiles

111 offline tests selected from 115 collected; four tests in [live-source integration](../../../tests/integration/test_real_data_sources.py#L9) are realdata-marked. [Fixture DB isolation](../../../tests/conftest.py#L12) uses tmp_path. API tests redirect runtime DBs. Warehouse synchronization/signing are mocked in the release test. Full external Postgres, ClickHouse, Kafka, Redis and Airflow profiles were not exercised.

The Track A/B plans are CLAIM design inputs, not proof of current behavior. They prescribe ISIN-only identity, calendar-day pre-rights lookup and latest active actions; the master contract requires stronger listing/version/knowledge semantics. Proposed changes should resolve these differences explicitly rather than copy old plan text.

## Limitations / next action

This is a component audit, not exhaustive execution coverage of every function. No claimed upstream repository or Founder skill was fetched; neither AEF nor a configured Founder skill was verified locally. Maker, Reviewer, Gatekeeper and Historian were separate same-model review checklists, not independent agents or human approval. Next: review the narrowly scoped phase plan and preserve all uncommitted work before any implementation.

