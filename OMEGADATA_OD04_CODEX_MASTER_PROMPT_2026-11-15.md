# OMEGADATA OD-04: IMMUTABLE RAW ARCHIVE & PROVENANCE

**Status:** IMPLEMENTATION PROMPT, NOT A PRE-APPROVED RELEASE OR SOURCE ACCESS AUTHORIZATION  
**Repository:** `https://github.com/PrivateAccount-01/omega-system---phase-1`  
**Working branch:** `feature/od01-source-rights`  
**Reviewed starting HEAD:** `d24e9cfd29c8a59e590aaee85983babe9e8bf182`  
**Reviewed change:** `fix: verify OD-02 portability and redact acquisition evidence` (2026-11-15)  
**Mode:** `OD-04 IMPLEMENT_IMMUTABLE_RAW_ARCHIVE_ONLY`  
**Out of scope:** OD-03 browsers, OD-05+ parser/financial research, OD-10 analytical Parquet revisions, OD-11 release promotion, OD-14 signing/security custody, live external data acquisition.

## 0. COMMAND AUTHORITY AND MANDATORY STOP RULES

You are an engineering agent operating in the **existing** OmegaData Phase 1 repository. DO NOT initialize a replacement project or wholesale-rewrite the application. Use the best available Codex reasoning model, with sufficient reasoning effort for architecture review, adversarial tests, and careful integration. Model choice does not waive verification.

**Before changes:**

1. Read this file **completely**, root `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, and applicable deeper instructions. If some referenced file is absent, record that; do not invent or silently recreate it.
2. Record `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain=v1`, `git diff --stat`, `git log -5 --oneline`, and current `main` SHA. If HEAD differs from `d24e9cfd29c8a59e590aaee85983babe9e8bf182`, **STOP application edits**, inspect the difference, and write a conflict/risk assessment. Do not apply this prompt blindly to another commit.
3. Read OD-00 audit and plan, OD-01, OD-01R, OD-02, OD-02V complete Gatekeeper and next-phase reports, including:
   - `docs/omegadata_v2/plan/09_implementation_phase_plan.md`
   - `docs/omegadata_v2/plan/10_architecture_and_contract_proposal.md`
   - `docs/omegadata_v2/audit/08_prioritized_defects.md`
   - `docs/omegadata_v2/implementation/od02/20261115T084441Z/08_gatekeeper_verdict.md`
   - `docs/omegadata_v2/implementation/od02v/20261115T114445Z/07_gatekeeper_verdict.md`
   - `docs/omegadata_v2/implementation/od02v/20261115T114445Z/08_next_phase_request.md`
4. Preserve existing user edits, Git history, tracked and untracked material, historical data, evidence, root databases, release bundles, and signing material. **No** `git reset --hard`, `git clean`, broad `git restore`, mass format, blanket deletion, rebase, forced push, automatic merge, change to signer/key artifacts, or rewriting prior proof directories.
5. Keep all **13 source policies PENDING_REVIEW** and **0 APPROVED**. Do not invoke real NSE/BSE/GDELT/other provider traffic; do not weaken `BLOCKED_EXTERNAL_EGRESS`, source policy guards, terminal HTTP denial handling, or resource ceilings. No provider/browser/network smoke, paid service or production release.
6. Work only in **fresh disposable directories** for storage experiments, crash simulations, recovery and test artifacts. Never run experiments on original `data/`, `artifacts/`, production database paths, or source cache trees. Read original source/fixtures only as needed for audit and strictly controlled compatibility tests; avoid opening any private signing material.
7. Do **not** call OD-04 complete based solely on a same-model Gatekeeper statement or passing mock tests. Differentiate executed proof, inferred design, synthetic fixture, historical evidence and independent review. A non-zero command, skipped required test, missing executable or failed contract remains visible.
8. This prompt authorizes **OD-04 only**. Stop after producing OD-04 evidence and Gatekeeper results. Do not begin OD-05, OD-10, signing, release or deployment.

## 1. VERIFIED STARTING POINT; DO NOT DISCARD IT

The inspected feature-branch commit `d24e9cfd29c8a59e590aaee85983babe9e8bf182` follows `eaedac1bddc35867f9089486beffa3bb38cb11f4` and adds OD-02V evidence and a small confidentiality fix in `acquisition.py` and `download_manager.py`. Archived logs report:

- Windows Python 3.14.3: 393 offline full-suite passes, 10 platform-specific skips, 4 real-data exclusions.
- Windows Python 3.11.15: 393 passes, 10 platform-specific skips, 4 real-data exclusions.
- WSL Linux Python 3.12.3: 401 passes, 2 Windows-only junction skips, 4 real-data exclusions.
- The three previously blocked real file-symlink cases execute and pass on Linux (outside-data reads reported as zero). Source-acquisition egress is still disabled.
- Ruff, mypy and `pip check` pass on all three recorded environments. OD-02V reports combined statement/branch coverage approximately 81%; an acquisition module measure approximately 93.67%. These are **archived developer-produced logs**, not an independently rerun measurement in this new OD-04 session.

Outstanding issues still exist: D-01 signing private-key custody **P0**, D-04 promotion/export bypass **P0**, D-02 point-in-time universe and D-08 mutable observation history **P1**, D-06 adjustment convention **P1**, D-09 official source provenance **P1**, D-11 supply-chain/CI **P2**, and SQLite ResourceWarnings. **Do not modify these unrelated components.** The storage overlap in D-03 is the target of this phase **only for raw acquisition objects**; canonical Parquet overwrite remains assigned to OD-10.

### Existing storage behavior to inspect closely

- `src/omegadata/track_a/download_manager.py`: currently derives `artifact_stem = date + digest[:12]`, conditionally does `output.write_bytes(payload)`, conditionally writes a manifest, and writes `YYYYMMDD.latest.json` directly. A per-`DownloadManager` `RLock` is **not** a cross-process transaction or crash-atomic publication guarantee.
- `src/omegadata/track_a/acquisition.py`: bounded offline transport, strict response/ZIP/CSV validation, full raw SHA-256, sanitized URL and evidence contracts. Reuse them; do not copy or recalculate financial fields unnecessarily.
- `src/omegadata/track_a/source_rights.py`: versioned approval/refusal; gate cache reads, derivation and storage as applicable.
- `src/omegadata/track_a/storage.py`: `ParquetStorage.store_daily` currently writes a fixed `part-00000.parquet`. **OD-10 owns canonical analytical versioning.** Do not silently change this output schema during OD-04; document D-03 partial closure accurately.
- `src/omegadata/track_a/orchestration.py`, source-probe scripts, source registry, tests and existing API clients must keep their contracts or have intentionally designed backward-compatible adapters.

## 2. EXACT OD-04 SCOPE AND DELIVERABLE

Build and integrate a **transactionally published, append-only, full-content-addressed raw acquisition archive** with immutable observation records, safe reads, deterministic replays and documented legacy compatibility. It must work locally on disposable file storage and not require cloud services, paid data vendors, a distributed database, a browser or an LLM.

### In scope

A. Immutable raw object identity and exact-byte preservation.  
B. Immutable per-acquisition observation identity and provenance.  
C. Exclusive and crash-recoverable commit protocol, safe cross-process concurrency, atomic visibility for readers, and failure injection.  
D. Cache/seed/source_mode distinction, rights-aware reads, non-escalation on cache miss, and exact legacy compatibility.  
E. Typed errors, bounded resources, strict schema/version and input/path validation.  
F. Opt-in integration with the existing `DownloadManager` at an explicitly scoped, tested boundary; legacy bytes and pointers remain unchanged.  
G. Offline replay verifier, integrity scan and deterministic evidence reports.  
H. Unit/property/fault/concurrency/cross-platform tests and independent reference verification using stdlib hash checks.

### Explicitly out of scope

- Building a new tradeable market-data feed, granting exchange permissions or converting historical fixture files into officially certified market data.
- Backfilling all historical instruments, scraping live URLs, enabling browser acquisition, modifying policy records to APPROVED.
- Replacing the ORM, restructuring warehouse tables, changing corporate-action math, adjusting prices, changing point-in-time universe semantics.
- Replacing `ParquetStorage` canonical analytical dataset contract or `part-00000.parquet` path; that is OD-10.
- Creating a production release, updating any release latest pointer, signing data or fixing exposed signing keys without a separately approved security plan.
- Adopting Delta Lake, lakeFS, DVC, DuckDB or other infrastructure merely for appearance.

## 3. REPOSITORY-FIRST CHOICE, DOCUMENT BEFORE CODING

Research and compare **exactly relevant** implementation options to avoid rewriting solved infrastructure:

| Candidate | Source | Check |
|---|---|---|
| Existing Python/`pathlib`/`os`/`hashlib`/`tempfile`/`json` and PyArrow | Existing repo + https://github.com/apache/arrow | Lowest dependency cost; prove crash/process semantics rather than assume `os.replace` is a transaction |
| DVC | https://github.com/iterative/dvc | Dataset/content versioning, object store and cache semantics; assess adaptation overhead, daemon needs and license |
| lakeFS | https://github.com/treeverse/lakeFS | Commit/versioned object-lake semantics; assess substantial service/object-store overhead |
| delta-rs | https://github.com/delta-io/delta-rs | Table transaction/log model, not necessarily a raw-byte acquisition envelope; evaluate actual fit |
| DuckDB | https://github.com/duckdb/duckdb | Useful future verification and analytical readers, but not a transactional replacement for raw-file storage by itself |

For every examined candidate record repo URL, exact tag/commit (only if verified), license **from the checked version**, language/runtime/platform support, dependency footprint, suitability, mismatch, rollback cost, existing tests and actual local benchmark (or `UNMEASURED`). If network research is unavailable, do not invent metadata: mark `UNVERIFIED` and continue with stdlib baseline. The default recommendation to challenge is **EXTEND_EXISTING** using Python's standard filesystem APIs and existing application dependencies. Only add a new dependency if a measured capability gap makes it necessary and an explicit license/review gate is met. Do not install tools without permission or fetch third-party code into production.

Deliverable: `docs/omegadata_v2/decisions/od04-raw-archive-reuse.md` (new, with acceptance conditions).

## 4. REQUIRED DATA CONTRACTS

First propose and freeze a versioned schema such as `raw-object/v1`, `raw-observation/v1`, `raw-commit/v1`, with names adjusted only after evidence-backed review. Use immutable typed models (existing Pydantic/dataclass pattern). Never conflate object identity, observation identity, or research release identity.

**Raw object**: full `sha256` (64 lowercase hex), byte length, format/media hints, stored relative object path derived only from SHA-256, optional original registry checksum, and verification state. The exact original bytes define identity; source/date/URL/receipt time must **not** be part of content identity. A 12-digit hash prefix is inadequate as the sole identity.

**Observation**: separate immutable ID (unique even when two collection events retrieve identical bytes); source key, requested business date, acquisition/observation UTC time, object SHA and size, requested source era, source mode (`SYNTHETIC_TEST_ONLY`, `SOURCE_CACHED_RAW`, `SOURCE_SEED_IMPORTED`, `PROVIDER_OBSERVED_UNVERIFIED` or an explicitly versioned equivalent), parser/schema state (`HTTP_RECEIVED` versus structural validity), transport, final sanitized request/response URL fields, policy ID/revision/hash and decision scope, immutable provenance references, observable errors/warnings and acquisition attempt numbers. Store `published_at` as null if unknown. `first_observed_at` must not masquerade as historical public availability. No secrets in manifests, exception context or paths.

**Commit record**: unique commit/observation ID, raw object identity, schema version, state, complete cryptographic link to immutable object and observation, commit timestamp (nonsemantic), verified reader-visible commit marker, and optionally a transaction/journal reference. Fields used for deterministic replay must have explicitly defined semantic vs nonsemantic roles.

**Source rights**: caching, reading, storing and deriving require the correct operation/consumer scope at the appropriate boundary. New storage interfaces are **not** a bypass around OD-01/01R. A synthetic APPROVED fixture is allowed inside tests only. All real sources remain PENDING. Applying legal retention restrictions remains a separate owner-controlled policy; do not introduce unapproved garbage collection.

**Data status**: differentiate `RAW_BYTES_CAPTURED`, `PAYLOAD_STRUCTURALLY_VALID`, `SOURCE_REFERENCE_PENDING`, and `RELEASE_APPROVED` as relevant states; raw archival success must **never** be promoted automatically to official historical or financial correctness.

**Identity validation**: reject invalid source keys, traversal, absolute/drive/UNC injection, symlink escapes, malformed hashes, duplicate JSON fields, inconsistent byte lengths, wrong source/date, unsupported schema, suspicious metadata/path or unacceptable source-mode relabels before any trusted read/write. The archive root must be private, disposable during tests and owned by the process. No claim of race-safe hostile-directory security without descriptor-based evidence.

## 5. REQUIRED FILESYSTEM AND TRANSACTION PROPERTIES

Design the protocol as a small finite-state machine such as:

`CANDIDATE → STAGED → VERIFIED → COMMITTED` and `CANDIDATE/STAGED → QUARANTINED`, with `RECOVERY_REQUIRED` after interrupted operations. Exact states may differ; record them in an ADR before coding.

Mandatory invariants:

1. A returned `COMMITTED` observation references an existing, fully written, byte-hash-verified object and immutable observation. No reader sees a half-written successful object.
2. A crash before commit leaves **no reader-visible committed observation**; recovery can identify and safely reprocess/discard abandoned temporary objects using an explicitly reviewed retention policy. Do not delete originals, even if a fault test suggests cleanup.
3. A second observation of the same exact bytes can share an object, but must not erase its distinct acquisition event. The distinct same-day **different-byte** observation creates a new immutable object and a new immutable observation; earlier reads remain byte-identical.
4. A replay pinned to an observation/commit ID returns the same bytes and provenance regardless of later observations, new source data, or legacy `latest` changes.
5. Two independent processes racing to publish the same or different digests cannot overwrite published bytes or return a successful commit whose identity belongs to another candidate.
6. On an existing destination, validate byte length and full digest (do not trust a matching filename alone). Never overwrite a mismatched object. Exclusively create final immutable records, detect conflicting ID reuse.
7. Staging must occur in the same filesystem as the target. Flush and `fsync` written bytes where supported; document OS-specific directory durability (POSIX dir fsync; Windows limitations). Atomic rename **alone** does not provide cross-file transactionality; a commit marker or equivalent validated protocol must define successful visibility. Record actual tested guarantees and explicitly defer unsupported power-loss guarantees.
8. Prevent/close checksum mismatch, incomplete writes, permission loss, disk-full, abrupt termination, stale lock, malformed commit marker and parent-path attacks. Do not build a speculative complicated lock service: test at least two viable exclusive-publish strategies and select the smallest reliable one for Windows and Linux. If a filesystem cannot meet an invariant, fail closed and block the gate.
9. Idempotent retry uses an explicit immutable operation/attempt identity and cannot change the payload of a prior committed ID; identical bytes alone do not establish identical provenance or legal scope.
10. Maintain a *bounded* and inspectable archive size, concurrency and fault-test budget. Report disk bytes, duplicates avoided, verified read latency and recovery timing from actual tests; do not fabricate performance claims.

Suggested local namespace (illustrative, not mandatory):

```text
<DISPOSABLE_RAW_ARCHIVE_ROOT>/
  objects/sha256/ab/cd/<FULL_SHA256>
  observations/<SOURCE_KEY>/<YEAR>/<MONTH>/<OBSERVATION_ID>.json
  commits/<OBSERVATION_ID>.commit.json
  staging/<EPHEMERAL_TRANSACTION_ID>/
  quarantine/<TRANSACTION_ID>/
```

Never use the final object hash in a way that implies official provenance, and never write archive files by using unvalidated components from a URL.

## 6. COMPATIBILITY AND INTEGRATION DESIGN

Implement the archive as a small, well-typed service, likely `src/omegadata/track_a/raw_archive.py` and focused new contracts or tests. Avoid circular imports with `download_manager.py` and `acquisition.py`. Prefer a clean API such as `put_candidate()`, `commit_observation()`, `read_verified()`, `inspect_commit()` and `recover_staging()`; choose exact names after review.

Integrate through **a deliberate opt-in archive mode/interface** at the existing downloader's validated candidate-to-storage boundary. The default runtime must not silently switch storage behavior, rewrite prior manifests, mutate historical `YYYYMMDD.latest.json`, or allow pending sources to be fetched. The opt-in mode must use the new transaction system rather than writing a second unaudited copy in legacy directories.

Preserve public `DownloadManager.download`, `DownloadArtifact`, `IngestionOrchestrator.ingest_raw_source` and tests where possible. If extending the artifact with `observation_id`, `object_sha256`, `commit_id` or `archive_state`, use additive optional fields and never replace source policy/error provenance. Source modes from OD-02 must remain distinguishable in cached/seed/fixture reads and new observations. Cached legacy data may be read through a strictly **read-only compatibility facade** with unchanged checks; label it `LEGACY_UNVERIFIED` until verified, not `COMMITTED`/`OFFICIAL`.

No in-place upgrade or migration of existing user data is authorized. Prepare a dry-run-only **migration manifest/specification** containing source path, observed length/hash, desired object identity, origin, conflicting pointers and reversible mapping. Do not execute migration on the real dataset. Test migration solely on synthetic disposable copies. Do not change analytical Parquet paths: OD-10 will handle that.

## 7. NEGATIVE-FIRST TEST PLAN (MANDATORY)

Create `tests/unit/test_od04_raw_archive.py` and, if justified, a separate offline multiprocessing fault test. Test names must map to actual requirements, not decorative placeholders. Author failing tests against unchanged implementation **before writing production changes**. Preserve raw red and green evidence; never claim a pre-change failure if the failure arose only from an import or broken test harness. At minimum cover:

| Test | Expected result |
|---|---|
| A01 | Exact original payload bytes produce correct full SHA-256 and immutable address |
| A02 | Same payload twice shares physical object without collapsing two observations |
| A03 | Different bytes for same date produce two separate retrievable historical versions |
| A04 | Repeating a verified operation ID is idempotent only when payload and metadata identity match |
| A05 | Conflicting reuse of operation/observation ID refuses, no overwrite |
| A06 | Complete commit marker references validated object and observation; partial staged file never visible |
| A07 | Crash injection before staging, after staging, after object commit, after observation, and before final commit marker |
| A08 | Restart/recovery precisely detects and handles each interrupted state without rewriting committed observations |
| A09 | Two threads writing same hash do not corrupt it |
| A10 | **Two independent processes** writing same hash do not corrupt it (not only same-manager `RLock`) |
| A11 | Independent processes writing different hashes on same date both retain history |
| A12 | Read-back checks length, full hash, record-link integrity, and refuses corruption |
| A13 | No path traversal / absolute / UNC / drive / symlink / junction escape on raw and metadata paths |
| A14 | Duplicate JSON fields, malformed manifests and unknown versions fail closed |
| A15 | No unsupported source mode or `SYNTHETIC_TEST_ONLY` label can be silently changed to real-source provenance |
| A16 | Pending/revoked/missing source rights stop before archive write and, where required, before read |
| A17 | Cache-only miss causes no fetch and no new artifact; legacy cache reads remain read-only and labeled |
| A18 | Legacy latest pointers, original bytes, manifests, release files, database and signer paths retain pre-test hashes/metadata |
| A19 | Zero-length, large/oversized input and bounded disk/metadata budget behavior |
| A20 | File flush failure, permission error, space exhaustion and atomic-publish failure are typed; no committed partial output |
| A21 | Concurrent reader never observes a partially published commit |
| A22 | Safe URL redaction, no secret in manifest, logs or structured errors |
| A23 | Deterministic replay pinned to observation/commit ID remains identical after later versions |
| A24 | Exact registry/origin/era/date/schema/policy references, no invented published-at |
| A25 | Cross-platform Windows and Linux success using actual filesystem semantics, with explicit genuine skips and paired coverage |
| A26 | Existing OD-01/01R/02/02V offline security tests and the full suite still run unchanged |
| A27 | Lint, strict mypy, `pip check`, import, collection and package metadata; no hidden warnings |
| A28 | A compact benchmark reports archive bytes, duplicate-object savings, per-operation elapsed time and peak memory on recorded fixture sizes |

For process/crash tests: prior OD-02V guarded pytest runner intentionally blocks arbitrary subprocesses. **Do not weaken its global egress or protected-file guard to make test numbers green.** Build a second, explicitly scoped local process-test runner using only a documented trusted executable and disposable IPC/filesystem root; enforce no network in each child. Prefer independent CI-capable OS tests. If this is impossible, record the exact blocker and return `BLOCKED` rather than relabel as success.

Use real filesystem fault tests on Windows and Linux where supported, plus injected deterministic failures for hard-to-force timing conditions. `kill -9` or forced process termination must target **only** a disposable test worker never any user process. Do not claim power-failure durability based on an exception mock.

## 8. IMPLEMENTATION ORDER AND REVIEW GATES

**Gate 0: Preflight and inventory**  
- Record exact repository identity and current HEAD, working-tree changes, protected paths and environment. Distinguish prior user edits from phase edits.  
- Execute fresh offline baseline tests on a protected disposable profile. Confirm the reviewed previous Gatekeeper remains applicable to the new HEAD, and do not erase old verdicts.

**Gate 1: Design and repo-first decision**  
- Map actual call graph from `DownloadManager.download` through `_fetch_candidate`, `_validate_payload`, policy checks, cache/seed, raw writes, observations and legacy callers.  
- Write an ADR with invariants, alternative publish protocols, exact APIs, schema samples, failure taxonomy, compatibility changes and rollback.  
- Reject unnecessary new infra. Record any unresolved choice rather than implement multiple storage stacks.

**Gate 2: Negative-first proofs**  
- Implement A01–A28 test families, record failing assertions on the old code. Exclude harness/import errors from defect proof.  
- Include independent full SHA-256 and byte-for-byte verification from stdlib, not just methods under test.

**Gate 3: Core raw archive**  
- Add minimal typed models and transaction writer/reader/recoverer using local filesystem and deterministic serialization. Add strictly validated provenance and full-content hashes.  
- Ensure no privileged writes outside a new configured, disposable root; safe symlink semantics. No storage redesign elsewhere.

**Gate 4: Narrow downloader integration**  
- Implement the opt-in boundary and read-only legacy facade. Retain all OD-02 resource, policy and egress controls.  
- Assert `SourcePolicyError` and terminal resource/provider denials cannot be swallowed by storage wrappers.

**Gate 5: Adversarial verification**  
- Rerun targeted unit, integration, concurrency/crash/recovery tests with an independent reference implementation and both operating-system filesystems; report exact genuine skips.  
- Re-run `pytest -q -m 'not realdata'`, Ruff, strict mypy, package check and collect-only under protected fixture/environment. No new `realdata` tests or source contact.

**Gate 6: Evidence and Gatekeeper**  
- Provide exact dated command argv, working directory, interpreter versions, exit codes, source SHA, test identities, failed attempts, source hashes and coverage deltas.  
- A purported pass requires no required failure/blocked case, no changed source-rights status, no mutation of existing historical files, and no unsupported external access. Otherwise `OD04_BLOCKED` with next single scoped request.

Do not auto-commit, merge, push, or open a PR unless specifically authorized after review. If the existing user workflow expects a local commit, seek explicit authority rather than treating the presence of a file as permission.

## 9. PERMITTED AND FORBIDDEN FILE EDITS

**Normally permitted, subject to prior design gate:**

```text
src/omegadata/track_a/raw_archive.py                    NEW
src/omegadata/track_a/download_manager.py               NARROW INTEGRATION ONLY
src/omegadata/track_a/orchestration.py                   ONLY IF ESSENTIAL TO API
src/omegadata/track_a/acquisition.py                     ONLY IF REQUIRED AND RED-PROVEN
config/raw_archive_policy.v1.json                       NEW, DISPOSABLE/OFFLINE DEFAULT
scripts/verify_raw_archive.py                            NEW, READ-ONLY VERIFIER
scripts/plan_legacy_raw_import.py                        NEW, DRY-RUN ONLY
tests/unit/test_od04_raw_archive.py                      NEW
<new narrow integration/process test modules>           NEW
docs/omegadata_v2/decisions/od04-raw-archive-reuse.md    NEW
docs/omegadata_v2/implementation/od04/<UTC_RUN_ID>/**   NEW EVIDENCE
```

These are proposals, not mandatory file churn. If a design proves an additional specific file is essential, record the reason and explicit change scope **before** touching it. Do not edit existing tests solely to weaken assertions or improve a green percentage. Preserve all existing reports as archive evidence, including their former `BLOCKED` status.

**Forbidden without new scoped authorization:**

```text
artifacts/** (especially GnuPG, signing, released proofs)
data/** (original market-data corpus)
existing release bundles or latest release pointers
src/omegadata/track_b/release_manager.py
src/omegadata/track_b/publication.py
src/omegadata/track_b/adjustment_engine.py
src/omegadata/track_b/universe_manager.py
src/omegadata/db/models.py
src/omegadata/track_a/warehouse.py
historical verification reports
source policy records transitioning to APPROVED
.github/workflows/**, dependency pins or lock files, unless separately approved
```

## 10. TEST EXECUTION RECIPES (ONLY IN VERIFIED DISPOSABLE ENVIRONMENT)

Choose an actual existing interpreter based on the new preflight. Use the **existing protected verification approach** from OD-02V and allocate **fresh run IDs** so old logs are not overwritten. Never run a destructive command on original corpus paths.

```powershell
# Windows example: choose a VERIFIED disposable interpreter and guard/harness.
$py = '.venv/Scripts/python.exe'
& $py -m pytest -q tests/unit/test_od04_raw_archive.py
& $py -m pytest -q -m 'not realdata'
& $py -m ruff check --no-cache src/omegadata tests scripts
& $py -m mypy src/omegadata
& $py -m pip check
```

```bash
# Linux/WSL example: choose the VERIFIED isolated Python executable.
python -m pytest -q tests/unit/test_od04_raw_archive.py
python -m pytest -q -m 'not realdata'
python -m ruff check --no-cache src/omegadata tests scripts
python -m mypy src/omegadata
python -m pip check
```

**IMPORTANT:** These illustrate the effective commands; *do not* execute them unguarded if they could create repository-local outputs or contact services. In this project they must be run by a new protective runner or isolated copy with the same enforced DNS/socket/child-process/data-write restrictions as the reviewed OD-02V runner. In process-specific fault tests, use only the narrowly reviewed test worker and disposable storage root. No skipped-required test may be declared passed. Collect-only and full suite must share the same tested source identity.

If cross-platform dependencies are missing, record the exact block. Do not install packages or alter dependency constraints without a separate explicit permission and a license/security review. Cache-only setup first; any allowed official-index dependency installation must be confined to a newly isolated environment and independently logged.

## 11. EXACT EVIDENCE DELIVERABLES

Create a **new**, isolated directory `docs/omegadata_v2/implementation/od04/<UTC_RUN_ID>/` with:

```text
00_preflight.md
01_existing_callgraph_and_repo_reuse.md
02_architecture_and_contracts.md
03_negative_first_matrix.md
04_implementation_ledger.md
05_concurrency_crash_recovery.md
06_cross_platform_and_compatibility.md
07_security_and_rights_review.md
08_metrics_and_reproducibility.md
09_gatekeeper_verdict.md
10_next_phase_request.md
logs/                       # New, bounded sanitized command evidence
```

Every acceptance row includes: test ID; test function/node; exact command; environment; actual exit; red/green proof; run timestamp; source hash; relevant output artifact/digest; reason for any skip; final PASS/FAIL/BLOCKED. Do not print or commit credentials, key metadata that is unnecessary, absolute private local paths, or massive indiscriminate snapshots of customer data. Trim reports to *useful evidence* while preserving underlying critical failures in separate bounded log files.

### Required final response format

Produce **one** unambiguous status:

- `OD04_OFFLINE_RAW_ARCHIVE_TECHNICAL_PASS` **only** if every mandatory safety/correctness/portability/concurrency/recovery gate was actually executed with the specified evidence, and zero out-of-scope mutations occurred.
- `OD04_BLOCKED` if any critical test is skipped/failed, a required platform unavailable, cross-process atomicity unproven, unauthorized filesystem changes are found, or source rights/egress protections fail.

Then report: exact branch and HEAD; changed-file list; component and repo decision; 10 most consequential tests and outcomes; entire test matrix summary; live source count = 0; immutable raw object and observation count on test corpus; performance *measured or unmeasured*; proof locations; open risks; one next-phase proposal. The previous release readiness remains **BLOCKED** regardless of OD-04 result because D-01 and D-04 P0 remain unresolved.

## 12. STOP AND FUTURE HANDOFF

STOP after OD-04. An accepted OD-04 result permits only an **approval request** for OD-05 schema/semantic validation or another explicitly chosen next phase. It must not trigger live scraping, automated data migration, release signing, historical reprocessing, analytical Parquet rewrites, or Qlib/LLM strategy development. Future OD-10 work may build an immutable analytical store on top of these raw object/observation IDs.

**Engineering standard:** No success claim without reproducible evidence; no information-time inference without evidence; no historical proof rewrite; no paid or unauthorized source calls; no guaranteed trading profit claims. OmegaData is the trustworthy input substrate, not a generator of earnings by itself.
