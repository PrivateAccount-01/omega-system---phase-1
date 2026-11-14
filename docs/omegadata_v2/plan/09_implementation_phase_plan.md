# 09 — Implementation phase plan (all PROPOSED)

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Maker / implementation planner; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Scope, ordering and shared contract

This plan is an OD-00 deliverable, not authority to implement. Proposed order: **01 → 02 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15**, with OD-03 optional and OD-16 separately gated after core certification. Signing exposure must be contained before any signed-release work. Moving security implementation earlier requires an explicit reviewed phase-order decision; no phase automatically begins when a predecessor ends.

All paths below are proposed implementation scopes, not changed files. New acceptance files named below **do not yet exist**; commands are future acceptance specifications, never claimed executed. Existing tests to retain are in [test inventory](../audit/02_test_execution_matrix.md). Each phase also runs the full offline baseline, ruff and mypy commands recorded there; a targeted pass alone is insufficient. Source/network/service tests require separate source-specific authorization.

For every phase: inputs must validate against a versioned contract; output is immutable/versioned or a reason-coded refusal. Write only newly approved isolated namespaces during rehearsal; no existing data deletion, proof overwrite or production DDL. Retry budget must be finite and shared across nested fallbacks, with exact numeric limits approved at design gate rather than guessed. Log source, stage, versions, start/end UTC, attempts, outcome and counts without secrets. Measure correctness first; throughput/RSS/disk/time/cost budgets remain UNMEASURED and block performance claims. Phase owner is the relevant component engineer; independent verifier below is a proposed role requiring a named person before signoff. [Architecture ADRs](10_architecture_and_contract_proposal.md) are PROPOSED.

Common rollback: code/config change reversible in a dedicated implementation diff; old bytes/releases retained; DB changes only after disposable backup/restore rehearsal. Gate failure stops the current phase. No commit, push, PR, live source collection or paid service is implied.

## OD-01 — Source rights and canonical registry

- Entry / dependencies: OD-00 reviewed; explicit OD-01 approval; source-rights owner appointed.
- Existing module status: source_registry.py; Technical registry only; D-07. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current dataclasses/Pydantic; no new library initially; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Extend registry with versioned policy record, approved/pending/denied/revoked state; shared pre-fetch guard. No live access until separately approved.
- Proposed code/config scope: `src/omegadata/track_a/source_registry.py; src/omegadata/track_a/download_manager.py; src/omegadata/config.py; proposed versioned source-policy file`.
- Inputs / validation / outputs / side effects: source request + policy version → authorized envelope/refusal; no network in offline acceptance.
- Determinism, retries and failure taxonomy: policy_block / policy_revoked; idempotent by source+policy version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Mock approved/pending/denied/revoked source; zero-request spy; no real market prices.
- Future acceptance command: `python -m pytest -q tests/unit/test_od01_source_rights.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Human source-rights steward + a reviewer independent of implementation. Same-model self-review cannot fill this role.
- Confidence / budget: High confidence in technical gap; legal status unknown. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Prior registry/config preserved; deploy policy schema alongside legacy view; fail closed on missing approval.
- Stop condition: Terms/owner/use-case unresolved; unknown source cannot fetch.

## OD-02 — Deterministic direct acquisition

- Entry / dependencies: OD-01 gate; approved source/corpus; explicit OD-02 authorization.
- Existing module status: download_manager.py; Transport/cache support; D-05/D-12 and non-atomic raw writes. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Existing httpx 0.28.1 vs pinned dlt pilot; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Retain transport but propagate terminal denial; cap total attempts/body/time; identify payload/date before success; classify cache/seed/live explicitly.
- Proposed code/config scope: `src/omegadata/track_a/download_manager.py; src/omegadata/track_a/source_registry.py`.
- Inputs / validation / outputs / side effects: request+policy → verified raw candidate; network only separately approved; attempt/duration/body metrics.
- Determinism, retries and failure taxonomy: access_denied / payload_invalid / transient_timeout; source+requested date+payload hash; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Authorized normal/wrong-date/HTML/truncated ZIP/403/429 fixtures; no provider traffic in offline suite.
- Future acceptance command: `python -m pytest -q tests/unit/test_od02_acquisition.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent archive bytes/hash comparator and source-policy steward. Same-model self-review cannot fill this role.
- Confidence / budget: High gap confidence; source availability unverified. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Feature flag new validator; retain old artifacts unchanged; no success downgrade.
- Stop condition: Denied access, unapproved live endpoint, unbounded retries or unknown format.

## OD-03 — Optional browser pilot

- Entry / dependencies: OD-01/02; proven JS necessity; explicit source/network/browser isolation approval.
- Existing module status: download_manager.py; No approved pilot; optional component. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Pinned Obscura vs Playwright vs direct HTTP; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Defer unless direct permitted path cannot satisfy a narrow source. Isolated adapter, no general stealth browser.
- Proposed code/config scope: `Proposed src/omegadata/track_a/browser_adapter.py; bounded isolated runner config`.
- Inputs / validation / outputs / side effects: approved URL/task → evidence-bearing extraction; bounded browser process; p50/p95/RSS/CPU metrics.
- Determinism, retries and failure taxonomy: browser_denied / extraction_mismatch / resource_limit; source+task+document hash; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Approved pages with known fields and original-document references; denied-page/resource-limit cases.
- Future acceptance command: `python -m pytest -q tests/unit/test_od03_browser_adapter.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent direct/manual field extraction + security reviewer. Same-model self-review cannot fill this role.
- Confidence / budget: Low; no corpus, pin, license or measurements. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Remove optional adapter/feature flag; direct route preserved.
- Stop condition: License/rights/isolation unavailable; access denial; no measured benefit.

## OD-04 — Immutable raw archive

- Entry / dependencies: OD-01/02 contracts; explicit archive approval; disposable storage budget.
- Existing module status: download_manager.py; Versioned names/hash validation exist; atomicity/races unproven. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current pathlib/hashlib vs DVC; simplest sufficient wrapper; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Full-hash content addressing, atomic exclusive publish, immutable provenance observations, safe seed classification.
- Proposed code/config scope: `src/omegadata/track_a/download_manager.py; src/omegadata/track_a/storage.py; proposed raw-manifest contract`.
- Inputs / validation / outputs / side effects: validated raw candidate → immutable artifact+observation; disk mutations only bounded namespace.
- Determinism, retries and failure taxonomy: hash_mismatch / collision / disk_incomplete; full raw SHA-256 + provenance observation ID; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Same bytes twice/different bytes same day; corrupted hash; concurrent writers; disk failure; seed manifests.
- Future acceptance command: `python -m pytest -q tests/unit/test_od04_raw_archive.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Separate hash/read utility + fault-injection reviewer. Same-model self-review cannot fill this role.
- Confidence / budget: Medium; current atomic failure behavior not stress-tested. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: New archive namespace; preserve legacy import read facade and all old bytes.
- Stop condition: Existing archive mutation, ambiguous seed origin, missing backup or disk budget.

## OD-05 — Era-aware parser/schema

- Entry / dependencies: OD-02/04 raw envelope; approved era corpus; explicit parser authorization.
- Existing module status: sequential_pipeline.py; Multiple loaders with implicit branches and current-row updates. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current typed checks/Pydantic vs pinned Pandera; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Extract pure source-era parsers; keep valid loader behavior; no silent coercion; retain unknown columns and quarantine reason codes.
- Proposed code/config scope: `src/omegadata/pipelines/sequential_pipeline.py; proposed src/omegadata/parsers/; schema contracts`.
- Inputs / validation / outputs / side effects: raw hash+parser version → typed observations/quarantine; deterministic; row/error metrics.
- Determinism, retries and failure taxonomy: schema_unknown / row_invalid / date_mismatch; raw hash+parser version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Golden raw bytes per supported era; wrong date/encoding/NaN/duplicate/negative/legitimate zero-volume cases.
- Future acceptance command: `python -m pytest -q tests/unit/test_od05_era_parsing.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent source field/row calculation. Same-model self-review cannot fill this role.
- Confidence / budget: Medium; historical era validity unverified. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Parser version pin; new output namespace; old release bytes unchanged.
- Stop condition: Missing official era bytes/rights; unknown semantics.

## OD-06 — Identity and historical calendar

- Entry / dependencies: OD-01/04/05; authoritative mapping/session evidence; explicit authorization.
- Existing module status: isin_master.py; trading_calendar.py; Dated symbols and special sessions exist; listing identity/knowledge gaps. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current calendar vs pinned exchange_calendars; official references authoritative; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Add immutable internal instrument/listing IDs without dropping ISIN interface; version historical mappings/session metadata; quarantine missing identity.
- Proposed code/config scope: `src/omegadata/track_b/isin_master.py; src/omegadata/track_a/trading_calendar.py; src/omegadata/db/models.py; config/trading_holidays_india.json`.
- Inputs / validation / outputs / side effects: source identity/session facts → versioned mappings/sessions; no implicit weekday strict fallback.
- Determinism, retries and failure taxonomy: identity_ambiguous / calendar_missing; source fact hash+mapping/calendar version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Symbol rename/collision, same ISIN series/listings, IPO/delisting, exceptional weekend, early close and missing calendar.
- Future acceptance command: `python -m pytest -q tests/unit/test_od06_identity_calendar.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent identifier list/session circular reviewer. Same-model self-review cannot fill this role.
- Confidence / budget: Medium; mapping completeness and session source truth unknown. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Disposable schema migration, backup/restore and dual-read facade; no production DDL.
- Stop condition: Unverified master or authoritative calendar gap.

## OD-07 — Corporate actions/adjustment chains

- Entry / dependencies: OD-04/05/06; independently verified events; explicit math/basis approval.
- Existing module status: corporate_actions.py; adjustment_engine.py; Decimal math/correction links exist; D-06/D-08/D-09. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current engine + hand Decimal reference; external finance comparator only if conventions match; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Calendar-aware preceding session; strict required parameters; separate price-return/total-return/execution basis; append chain revisions and decision availability.
- Proposed code/config scope: `src/omegadata/track_b/adjustment_engine.py; src/omegadata/track_b/corporate_actions.py; src/omegadata/db/models.py; reference fixtures`.
- Inputs / validation / outputs / side effects: raw bars+known action revisions+decision+basis → versioned adjusted series; factor/unknown counters.
- Determinism, retries and failure taxonomy: action_unverified / prior_session_missing; input release+chain/basis version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Official split/bonus/rights/dividend/demerger/correction cases; independent manual weekend/suspension/multi-action vectors.
- Future acceptance command: `python -m pytest -q tests/unit/test_od07_adjustment_integrity.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent quant + original circular/hand math. Same-model self-review cannot fill this role.
- Confidence / budget: High on reproduced rights gap; low on unverified official extracts. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: New chain versions; pin old factors/releases; no destructive recomputation.
- Stop condition: Unknown action parameters/availability, missing original source or undecided basis.

## OD-08 — PIT universe

- Entry / dependencies: OD-06/07 contracts; availability policy approved; explicit OD-08 authorization.
- Existing module status: universe_manager.py; Effective-date filtering; D-02; only five archived snapshots. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Extend existing ORM/query; no index library required; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Bitemporal membership revisions, strict decision_at, listing status and actual constituent comparisons; unknown availability rejects.
- Proposed code/config scope: `src/omegadata/track_b/universe_manager.py; src/omegadata/db/models.py; reference fixtures; backfill script`.
- Inputs / validation / outputs / side effects: membership observations+decision/session → eligible IDs/refusals; knowledge exclusions counted.
- Determinism, retries and failure taxonomy: availability_unknown / transition_incomplete; membership version+decision_at; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Complete bounded transition identifiers, late publication/correction, delisted/renamed/unknown master and non-survivor cases.
- Future acceptance command: `python -m pytest -q tests/unit/test_od08_pit_knowledge.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent historical constituent/announcement reviewer. Same-model self-review cannot fill this role.
- Confidence / budget: High on missing filter; completeness unverified. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Version new memberships; retain effective-only audit query explicitly labeled; restore rehearsal.
- Stop condition: Unavailable publication evidence or silent current-survivor inference.

## OD-09 — Reconciliation and reviews

- Entry / dependencies: OD-05/06/07/08; comparable authorized source pairs; explicit approval.
- Existing module status: cross_source_validation.py; manual_review.py; Policy tolerances, confidence and blocks exist. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Keep existing validator + independent matched-row calculation; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Define comparable source/session/basis pairs and UNCOMPARABLE; retain hard-block independence; calibrate FP/FN without threshold fitting.
- Proposed code/config scope: `src/omegadata/track_b/cross_source_validation.py; src/omegadata/track_b/confidence.py; src/omegadata/track_b/manual_review.py; policy configs`.
- Inputs / validation / outputs / side effects: comparable observations → PASS/WARN/FAIL/UNCOMPARABLE + review; per-category rates.
- Determinism, retries and failure taxonomy: uncomparable / hard_disagreement; matched input hashes+policy version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Legitimate NSE/BSE last-trade differences, parser errors, sparse series, hard review/reprocess cases.
- Future acceptance command: `python -m pytest -q tests/unit/test_od09_reconciliation.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent sample/quant review with labeled positives and negatives. Same-model self-review cannot fill this role.
- Confidence / budget: Medium. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Version policy and review evidence; replay new release only; preserve prior audit facts.
- Stop condition: Unmatched identity/basis, uncalibrated tolerances, undocumented override.

## OD-10 — Versioned analytical store

- Entry / dependencies: OD-04/05/06/07/08/09; approved data migration and explicit authorization.
- Existing module status: storage.py; models.py; D-03/D-08; fixed path and mutable canonical rows. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current PyArrow 23.0.1 vs pinned DuckDB/Arrow; lake format only if necessary; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Immutable snapshot namespaces, file hashes and atomic partition commit; read facade preserves older consumers until migrated.
- Proposed code/config scope: `src/omegadata/track_a/storage.py; src/omegadata/db/models.py; src/omegadata/track_b/release_manager.py; proposed migrations`.
- Inputs / validation / outputs / side effects: typed observations+versions → immutable snapshot manifest; bytes/throughput/duration metrics.
- Determinism, retries and failure taxonomy: snapshot_collision / commit_incomplete; complete input/version digest; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Two revisions same day, concurrent writers, schema evolution, crash/restore, deterministic semantic hash corpus.
- Future acceptance command: `python -m pytest -q tests/unit/test_od10_snapshot_store.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent Parquet reader/hash verifier. Same-model self-review cannot fill this role.
- Confidence / budget: High on overwrite; concurrency feasibility unmeasured. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Backup/restore rehearsal and old snapshot read byte-for-byte; no DROP/reset on existing paths.
- Stop condition: Any old release byte changes, unsafe migration or collision.

## OD-11 — Publication and release gate

- Entry / dependencies: OD-01–10 required contracts (03 optional); P0 signing custody resolved; explicit authorization.
- Existing module status: release_manager.py; release_readiness.py; publication.py; D-04; row API controls exist but exports/promotion differ. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Reuse current services; small staging/promotion adapter; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Separate build/verify/promote, immutable revision IDs, row/series/instrument/release eligibility, fresh policy-bound hashes/signatures and current warehouse requirement.
- Proposed code/config scope: `src/omegadata/track_b/release_manager.py; src/omegadata/track_b/release_readiness.py; src/omegadata/track_b/publication.py; scripts/build_release_bundle.py; policy configs`.
- Inputs / validation / outputs / side effects: snapshot+rights/reference/policy versions → blocked/approved manifest; no latest update on failure.
- Determinism, retries and failure taxonomy: promotion_blocked / signature_invalid / warehouse_failed; immutable release input digest; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Blocked row/series, stale/missing/corrupt evidence, bad signature, failed warehouse, interrupted promotion and rollback.
- Future acceptance command: `python -m pytest -q tests/unit/test_od11_release_promotion.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent Gatekeeper command execution + human publication owner. Same-model self-review cannot fill this role.
- Confidence / budget: High on static gap; full integration unverified. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Atomic latest pointer restore to prior verified ID; old bundle immutable; staged failures quarantined.
- Stop condition: Any P0/P1, failed/unknown critical check, unknown rights/trust root.

## OD-12 — Research consumer contract

- Entry / dependencies: OD-11 approved release; explicit downstream/read-only scope.
- Existing module status: api/main.py; Existing release metadata/sidefeed pinning; equity decision contract incomplete. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Minimal independent Arrow client; Qlib only after gate; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Require release/basis/decision/schema, enforce row refusal and hash verification; paginate/filter; no strategy/broker integration.
- Proposed code/config scope: `src/omegadata/api/main.py; proposed consumer contract/client`.
- Inputs / validation / outputs / side effects: pinned release+decision/query → rows/provenance/refusal; latency/page/error metrics.
- Determinism, retries and failure taxonomy: release_unavailable / basis_unsupported; release ID+query+decision; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Tiny exact release corpus, known/unknown availability, blocked rows, stale/untrusted release and changed underlying bytes.
- Future acceptance command: `python -m pytest -q tests/unit/test_od12_consumer_contract.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent read-only client reproduces sample rows. Same-model self-review cannot fill this role.
- Confidence / budget: Medium. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Version API contract; preserve clearly labeled audit-only legacy surface; no silent fallback to latest.
- Stop condition: Unpinned data access, unknown basis/knowledge or unauthorized consumer.

## OD-13 — Scheduling/operations

- Entry / dependencies: Core release path stable; workload evidence; explicit service scope.
- Existing module status: collection_schedule.py; orchestration.py; Scheduling/monitoring wrappers exist; live distributed stack unverified. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Current local runner vs current Airflow/Kafka/Redis/ClickHouse profiles; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Use minimal local orchestration by default; preserve full profile; add bounded job state/idempotency/alerts and crash resume.
- Proposed code/config scope: `src/omegadata/track_a/collection_schedule.py; src/omegadata/track_a/orchestration.py; src/omegadata/track_a/warehouse.py; monitoring/alert modules; airflow`.
- Inputs / validation / outputs / side effects: approved window+policy → bounded job/result; attempt/duration/freshness/resource metrics.
- Determinism, retries and failure taxonomy: job_retry_exhausted / dependency_unavailable; source+session+stage+version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Duplicate jobs, crash mid-write, service outage, calendar gap, source denial; no operational endpoints.
- Future acceptance command: `python -m pytest -q tests/unit/test_od13_job_recovery.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent fault/restart operator. Same-model self-review cannot fill this role.
- Confidence / budget: Medium-low; actual load/service behavior unmeasured. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Disable new scheduler path; replay state from immutable inputs; preserve queues/data.
- Stop condition: Unbounded retries, partial promotion, unapproved service or real alert destination.

## OD-14 — Security/CI/supply chain

- Entry / dependencies: Explicit security scope and owner; existing signing incident classified; network approval for advisory checks.
- Existing module status: pyproject.toml; .github/workflows/trading-calendar-guard.yml; D-01/D-11; filename scan only; no current advisory clearance. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Pinned existing tooling; evaluate scanner/SBOM utilities before adoption; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: External secret custody/public trust, pinned compatibility/lock/SBOM, archive/URL/path bounds, CI negative gates and restore drill.
- Proposed code/config scope: `pyproject.toml; .github/workflows/; src/omegadata/config.py; downloader/release manager; infra config`.
- Inputs / validation / outputs / side effects: code/dependencies/config → verifiable security evidence; scan/error/resource metrics.
- Determinism, retries and failure taxonomy: secret_detected / dependency_blocked / untrusted_signature; commit+lock+policy hashes; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Malicious archive/path/redirect fixtures, secret detection, forged signatures, no credential fixtures.
- Future acceptance command: `python -m pytest -q tests/unit/test_od14_security_boundaries.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent security reviewer + approved advisory/license evidence. Same-model self-review cannot fill this role.
- Confidence / budget: High on tracked-key paths; current vulnerabilities unknown. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Reversible tool/config rollout; separately approved key changes; never silently rewrite Git history.
- Stop condition: Unknown code/license compatibility, detected secret, unsafe egress or no trusted signer.

## OD-15 — Bounded vertical-slice certification

- Entry / dependencies: All necessary OD-01–14 gates; no P0/P1; explicit source window/rights and user OD-15 authorization.
- Existing module status: run_full_pipeline.py; release proof scripts; Historical replay exists, not current certification. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Reuse tested pipeline + independent read-only hash/financial client; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: Fresh isolated source-to-release rehearsal; clearly label live vs verified cached replay; corrupted input must block promotion; second clean replay compares hashes.
- Proposed code/config scope: `scripts/run_full_pipeline.py; approved audit-only verifier scripts; reference corpus and isolated runbook`.
- Inputs / validation / outputs / side effects: approved corpus+frozen code/config → certified bounded release or reject; correctness then measured cost.
- Determinism, retries and failure taxonomy: certification_failed; complete provenance/version digest; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Authorized cash-equity window, preferably 30+ sessions once valid; real action if in window else separate official corpus.
- Future acceptance command: `python -m pytest -q tests/unit/test_od15_vertical_slice.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent environment/operator; human Gatekeeper accepts evidence. Same-model self-review cannot fill this role.
- Confidence / budget: Low until prerequisites close. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Discard only newly created disposable environment; preserve all prior released versions; demonstrate promotion rollback.
- Stop condition: Any unknown rights/time/provenance, missing independent reproduction, failed negative case.

## OD-16 — Optional feed expansion

- Entry / dependencies: OD-15 core milestone; separate human source/product approval for one feed.
- Existing module status: news_pipeline.py; sequential_pipeline.py; Broad feed code already exists; source rights/semantics remain unresolved. See [component inventory](../audit/01_repository_component_inventory.md) for current links and line references.
- Candidate / reuse: Scrapy/trafilatura for news; other candidates only per feed; pin, official license/advisory and fair measured pilot before adoption, per [reuse register](../audit/07_repo_reuse_candidate_matrix.md).
- Least-change strategy: One feed at a time with its own registry, bitemporal contract/profile; no automatic derivatives/news onboarding.
- Proposed code/config scope: `Feed-specific modules, parser/schema/model/API and policies only after scope selection`.
- Inputs / validation / outputs / side effects: feed raw+policy → versioned independent dataset/profile; feed-specific quality/cost metrics.
- Determinism, retries and failure taxonomy: feed_policy_block / contract_unknown; feed+source hash+schema version; common bounded retry/security/logging rules above apply.
- Fixtures / experiments: Per-feed official timestamp/revision/corporate/contract metadata corpus; synthetic tests separate.
- Future acceptance command: `python -m pytest -q tests/unit/test_od16_selected_feed.py`, followed by `python -m pytest -q -m "not realdata"`, `python -m ruff check src/omegadata tests scripts`, `python -m mypy src/omegadata`. Use explicit configured interpreter, disposable state and offline guard as appropriate; the proposed test module must first be authored and meaningful negative cases fail before implementation.
- Independent verifier: Independent domain reviewer + rights owner. Same-model self-review cannot fill this role.
- Confidence / budget: Low until feed selected. No benchmark or cost saving measured; set resource/time/cost limits at design gate before external/service pilots.
- Rollback: Feature/profile isolation; remove new feed from consumers without mutating core releases.
- Stop condition: No selected feed, rights, timestamp semantics, cost or budget approval.

## Limitations / next action

None of these implementation commands was executed as phase work. Current code may require refining path scope after preflight; any added scope must be explicit. First concrete human decision: review OD-00 and authorize **only OD-01** with the rights owner and offline enforcement scope; do not infer approval for OD-02 or key rotation. Existing uncommitted warehouse/release work needs owner disposition before edits touching it.

