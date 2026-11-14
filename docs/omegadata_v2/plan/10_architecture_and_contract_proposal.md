# 10 — Architecture and contract proposal

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Maker / architect; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Evidence and procedure

Map the target contracts to [current ORM](../../../src/omegadata/db/models.py), [downloader](../../../src/omegadata/track_a/download_manager.py), [storage](../../../src/omegadata/track_a/storage.py), [universe](../../../src/omegadata/track_b/universe_manager.py), [adjustments](../../../src/omegadata/track_b/adjustment_engine.py) and [release builder](../../../src/omegadata/track_b/release_manager.py). Source definitions and lines are in the [AST inventory](../audit/logs/module-and-package-inventory.json). This is a proposal; no schema, API, database or file-layout change has been applied.

## Proposed bounded flow

Approved rights policy → bounded acquisition → immutable raw bytes + acquisition observation → era parser → versioned listing/session observations → versioned action chains and PIT membership → reconciliation/quarantine → immutable typed snapshot → independent release verification → atomic promotion → pinned read-only consumer.

The minimal local profile uses filesystem + SQLite + Parquet and existing typed Python modules. Keep the full service integration profile available. Current release policy requires warehouse sync; a local profile must be a separately reviewed policy rather than silently waiving that requirement.

## Actual-to-target contract map

| Target | Existing representation | Minimal additive proposal / compatibility |
|---|---|---|
| Rights policy | DataSource URL/era/budgets at source_registry.py:21 | SourcePolicy v1, separate permission state and human evidence; old registry facade still renders technical routes |
| Raw envelope | DownloadArtifact/checksum + raw manifest, download_manager.py:42/963 | Full SHA-256 identity, response/transport/requested date/policy/schema/parser/source-mode references; separate immutable acquisition observations from byte identity |
| Event / effective / known times | trade_date, membership effective dates, CA announcement/ex_date/fetched_at | Preserve market dates; add published_at nullable, first_observed_at evidenced, known_from/to revision intervals; never invent original publication |
| Canonical equity | PriceRecord, models.py:189 | Observation/bar revisions linked to raw hash/parser/listing/session/currency/units; retain legacy current-row read facade during migration |
| Identity | InstrumentMaster ISIN PK, SymbolMap dated mappings at models.py:38/58 | Internal instrument/listing IDs; ISIN optional only with explicit verified identity policy; exchange/series distinctions retained |
| Calendar | Config year coverage, holidays/special sessions at trading_calendar.py:20 | Hash/versioned session records with local exchange zone and open/close details; official reference evidence |
| Corporate actions | ConfirmedCorporateAction supersedes flag/link at models.py:138 | Append revisions plus availability and original source wording; immutable chain IDs; separate price-return/total-return/execution conventions |
| Universe | UniverseMembership business dates at models.py:248 | Observation revisions and decision-time predicate; quarantine unavailable identity; strict unknown-time refusal |
| Reconciliation | PASS/WARN/FAIL, review policies and PublicationService | Add UNCOMPARABLE and economic/session/basis key; retain independent hard blocks and evidence-bound overrides |
| Dataset | Fixed daily part filename at storage.py:40 | Full snapshot/revision ID namespace, exclusive staging and atomic commit; full file hashes |
| Release | Date_profile ID + generated metadata at release_manager.py:92/524 | Opaque immutable revision ID and input digest; code/config/parser/calendar/rights/CA/universe/policy hashes and verifier decision; no machine path as identity |
| Consumer | Equity current-row API, metadata and release-backed sidefeed routes | Explicit release+decision+basis request and provenance/refusal response; no implicit replacement mid-research |

## ADR-OD-001 — Rights before acquisition

Status: **PROPOSED**. Problem/evidence: D-07, registry has no enforced human approval. Alternatives: extend current dataclasses with a policy reference; adopt a general ingestion engine; build a standalone policy service. Proposed decision: small validated, versioned policy register and shared guard around every transport, including cache reuse/redistribution where policy requires. Finance/legal implication: approved personal research does not imply commercial redistribution. Complexity/cost: lowest new dependency burden, no service assumed. Reversible migration: technical registry remains, missing policy fails closed; no historical data relabeling. Acceptance authority: user-appointed rights owner plus explicit OD-01 approval. No decision accepted yet.

## ADR-OD-002 — Append observation history and query knowledge explicitly

Status: **PROPOSED**. Problem/evidence: D-02/D-08; effective dates and updated current values cannot reconstruct what was known. Alternatives: reuse current tables unchanged with warning; additive observation/revision tables with a compatibility view; external temporal database. Proposed decision: additive immutable observations and known intervals; require decision_at and source availability policy. Preserve unknown published_at as null; first_observed_at is evidence, not retroactive publication. Known-from uses timezone-aware UTC semantics, with exchange-local sessions separately defined. Finance implication: revised demerger/CA/membership data cannot leak into earlier research. Legal condition: metadata and old raw retention must comply with source rights. Complexity/cost: migration and storage overhead must be measured. Rollback: old read facade plus backup/restore rehearsal; never drop old history. Independent verifier must check retroactive corrections and unknown availability. Human policy approval pending.

## ADR-OD-003 — Content-addressed raw bytes and versioned datasets

Status: **PROPOSED**. Problem/evidence: D-03, direct raw writes and fixed canonical partition names. Alternatives: minimally wrap existing pathlib/PyArrow; adopt DVC; use a transactional lake format. Proposed decision: full-hash raw namespace plus immutable snapshot namespace, atomic stage/publish and provenance observations; avoid new engine until concurrency evidence demands it. Equal bytes can share identity without losing separate fetch/seed observations. Financial implication: corrections create new versions while old research pins retain exact bytes. Legal condition: retention and redistribution flags travel with observations. Cost/complexity: disk growth, garbage-collection design and lock semantics unmeasured. Rollback: old namespaces read-only, new namespace additive; test same-day versions/concurrency/disk faults first. No automated deletion approved.

## ADR-OD-004 — Separate generation, verification and promotion

Status: **PROPOSED**. Problem/evidence: D-04; current builder exports all current rows and updates latest irrespective of readiness result. Alternatives: reuse generation with manual distribution control; small staged release state machine; external catalog/lake platform. Proposed decision: STAGED → VERIFIED/BLOCKED → APPROVED → PROMOTED with explicit authority, content hashes and atomic pointer transition. Every consumer validates immutable manifest/file identities and allowed use; required warehouse failure remains blocking under existing policy. Financial implication: row, forward-series, instrument and global blocks must survive export and direct reads. Security condition: trusted public root and external signer custody; signing is not certification. Cost: no external catalog assumed. Rollback: atomically restore prior verified pointer, never overwrite an old release. Refusal/rollback tests and human publication owner required; no acceptance yet.

## ADR-OD-005 — Reuse current components before adopting infrastructure

Status: **PROPOSED**. Problem/evidence: current module breadth and a green offline baseline coexist with missing invariants; changing frameworks alone will not fix financial semantics. Alternatives: retain current components with narrow wrappers; adopt dlt/Pandera/DuckDB per pilot; wholesale rewrite. Proposed decision: keep existing tested modules, compare candidates on a frozen authorized corpus, and record exact upstream pin/license/advisory/API/correctness/resource cost before adoption. Financial implication: any tool that silently normalizes values or loses provenance is rejected. Legal/model-weight condition: separately review all relevant licenses; no model dependencies needed. Reversibility: optional adapters and versioned interfaces, preserve full integration profile. No measured speedup or cost saving asserted.

## Universal component contract

Every approved component must freeze: ID/owner/module; typed inputs and validation; output schema/version; permitted mutations; external calls/rights scope; deterministic inputs and explicitly nonsemantic timestamps; shared bounded retry/idempotency key; failure taxonomy; secret-safe metrics/logs; unit/property/integration/independent reference tests; measured performance/cost budget; rollback and stop gate. The [phase plan](09_implementation_phase_plan.md) supplies component-specific proposals. Exact numerical budgets, approved publication-time defaults, named owners and legal permissions remain open decisions; they cannot be filled with invented confidence.

## Limitations and next action

No ADR is ACCEPTED. Full schema migrations, backward-compatible APIs and numeric resource budgets require phase-specific design reviews and disposable experiments. First actionable proposal is ADR-OD-001 under OD-01; subsequent ADRs do not grant implementation scope.

