# OmegaData 2.0 | OD-05U: Authentic Market Reference Gate and First Real-Observation Verification

**Task contract for Codex. Prepared 2026-11-16.**  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Branch:** `feature/od01-source-rights`  
**Last remotely inspected HEAD:** `0d43a43a7df2a997b394269d6a9ebf1e64a00de1`  
**Starting state:** OD-05T `OD05T_METADATA_TOOL_TECHNICAL_PASS_REAL_DATA_PENDING`; six real-reference groups blocked.  
**Permitted execution mode:** `OD05U_REAL_REFERENCE_EVIDENCE_GATE_THEN_BOUNDED_OFFLINE_VALIDATION_ONLY`.  
**Fundamental rule:** never generate artificial market OHLC, volume, instrument identity, corporate action, date or return data and never substitute prior synthetic-engineering results for real financial validation.

## 0. The objective, decision gates and a hard stop

Deliver the **first defensible, independently replayable, real historical NSE Capital Market bhavcopy verification**, using an actual, lawfully usable historical publisher-format document, a matching real market-data file and separately reviewed literal expectations. Do not produce a staged-data marketing claim, a fictional dataset, an empty-success report or another metadata-only feature for its own sake.

There are two modes, mutually exclusive:

- **GATE / READ-ONLY:** If an independently nominated authentic source pack or its use permissions are missing, conduct one concise inventory of the missing fields and relevant existing candidate metadata, produce exactly one owner handoff, and STOP. Do not make application changes, execute real-data parsing, fabricate source material or create another large repetitive documentation dossier. You may inspect publisher *documentation* via permitted manual or read-only access, but do not download market-data feeds without their permission. A live publisher documentation URL alone is not permission to use a historical market-data file.
- **VERIFICATION / APPROVED:** Only where a named accountable human supplies the exact bounded pack, actual permitted-use evidence, independent pins and explicit authority to inspect the nominated local market payload, write new verification code/tests as needed in a narrow additive scope and execute the true real-data exercise. Separate authorization is needed for production routing, backfill, data migration or further OD phases.

Do not interpret this prompt, any previous G0/G1 exception approval, copied review strings, old cache hashes, a website URL, or `PENDING_REVIEW` policies as authorization for real-data payload use. No paid API or vendor purchase; never bypass a site's access terms or commercial-license requirements.

## 1. Required repository preflight

Read in full: `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, and the phase plan OD-05 in `docs/omegadata_v2/plan/09_implementation_phase_plan.md`.

Inspect the actual latest branch HEAD, `git status --porcelain`, index and merge base; review Git changes beyond the recorded `0d43a43...`. Read the source and tests, not only commit messages:

- `src/omegadata/parsers/archive_candidate_inventory.py`
- `scripts/audit_existing_market_archive.py`
- `src/omegadata/parsers/reference_evidence.py`, `era_matrix.py`, `nse_cm.py`, `dispatch.py`, `contracts.py`
- `src/omegadata/track_a/source_registry.py`, `acquisition.py`, `raw_archive.py`, `download_manager.py`, `source_rights.py`
- `tests/unit/test_od05t_archive_inventory.py`, `od05t_metadata_oracle.py`
- Latest OD-05T run `docs/omegadata_v2/implementation/od05t/20261116T100613Z/`, Gatekeeper `10_gatekeeper_verdict.md`, scorecard, frozen pins and original-scan metadata.
- Prior OD-05, OD-05R, OD-05S provenance reports and historic OD-04/OD-04R Gatekeepers.

Preserve current original data, signing material, secret paths, caches, evidence, fixture classifications, DB, warehouse, Parquet, release bundles, source-rights configuration, Git history and existing tests exactly. Do not run reset, clean, stash, history rewrite, large automatic formatting, installer, migration, collection, release or trading commands. The project remains `feature/od01-source-rights`. Commit/push/PR/merge only under an independent explicit Git-lifecycle instruction.

## 2. What the evidence already proves, and what it does NOT

OD-05T has a read-only manifest inventory. The committed scorecard found **3,596 NSE CM seed-import manifests and 30 NSE CM versioned-cache manifests** (3,626 within this selected scope; OD-05S's earlier 3,676 was a broader tree). The stored metadata oracle had no mismatches. This is metadata identity evidence, not market truth.

Existing recorded engineering tests: Windows 3.14 and 3.11 each 678 passed/13 skipped/4 realdata excluded; WSL Linux 3.12 687 passed/4 skipped/4 realdata excluded. The new metadata suite counted 46 pass/2 skip on Windows and 47 pass/1 skip on Linux. These are archived author-generated results on one physical host, not fresh tests, hosted CI or independent financial certification. Any future claim must cite newly executed evidence.

Real publisher-authenticated documents = **0 established**. Real sample payloads independently authenticated = **0 established**. Real OHLCV rows parsed = **0**. Independent real-row reconciliations = **0**. Actual session completeness, PIT availability, mismatch rate and performance are unknown, NOT 0% error or 100% accuracy. Thirteen actual policies remain `PENDING_REVIEW` and none approved; do not modify or impersonate their policy owners.

## 3. Select the first actual evidence pack, without assuming truth

First nominate a **small, bounded real NSE CM corpus** by referring to pre-existing private files only, without opening the payload while rights remain pending. Start from the actual metadata roots inventoried by OD-05T:

- `data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/` (seed-labeled, origin UNVERIFIED)
- `data/raw/nse_equity_bhavcopy/` (versioned-cache-labeled, origin UNVERIFIED)

Prefer one post-transition control and, only if lawful and available, one reference around the disputed 2019/2020 or June–July 2024 boundaries. Example *candidate dates* visible in existing versioned-cache metadata include 2024-07-23 through 2024-07-29. They are **not** independently verified market sessions or real files. Never synthesize an observation for a missing date; record missing or unknown.

For each nominated file freeze before interpretation: private local path, exact SHA-256 and byte length independently read from actual bytes *only after rights approval*, original publisher receipt or other authenticated provenance, collection/availability evidence, declared source/format, date/era, file/member naming, kind of original source evidence, applicable usage-rights record, immutable reviewer reference, and an independent expected-row reference. The issuer string in a manifest is not authentication.

### Minimal pack: four separately identifiable roles

**A. Original publisher schema/circular/annexure:** exact document/version/URL, file bytes (where permitted), independent SHA/size, retrieved-at, scope (NSE CM only), relevant fields and effective applicability. Approved to consult and retain only as rights allow.

**B. Actual real market-data sample:** exactly nominated original ZIP/CSV/member bytes, exchange date, independently frozen SHA/size, original receipt chain and sample-use permission, stored privately outside Git. No seed promotion without evidence.

**C. Independent reviewed literal expectations:** field-by-field values derived by an accountable human or a genuinely separate independently sourced verifier, bound to exact row ordinal and security identity, including symbol, series, ISIN, trading date, business date, OHLC as original lexical strings and exact Decimal values, volume as original text and integer, unknown/optional fields, units and publication/PIT fields only where evidenced. Must not be generated by the parser under test.

**D. Independent pins and rights decision:** immutable external hash/length manifest, named authorized reviewer/owner and actual decision time; permission separated into documentation consultation, local parsing/research, retention, derived output, commercialization/trading use, redistribution and publication. Unknown is NOT permission. Keep any data-provider contract and secret credentials private, outside Git.

Use `docs/omegadata_v2/implementation/od05t/20261116T100613Z/owner-pack-manifest-template.json` as an unsigned template, not as evidence. Distinguish a bona-fide publisher-original from a locally copied sample whose original receipt chain is missing. If only the latter is provided, classify `LOCALLY_HASHED_UNVERIFIED_SOURCE` and block official financial certification.

## 4. Public documentary research, bounded and honest

These are **starting points**, not approved market-data endpoints:

- NSE forms and formats: `https://www.nseindia.com/static/resources/forms-formats-members` (UDiFF guidance, catalogues v1–v4, CM bhavcopy file format and test-file links).
- NSE reports: `https://www.nseindia.com/all-reports/` (July 8, 2024 CM bhavcopy discontinuation notice and reference to circular 62424).
- NSE data policy: `https://www.nseindia.com/static/market-data/nse-data-policy` (intended use, subscription/usage restrictions, commercial terms and redistribution). If the canonical page differs, resolve it via NSE's own domain and record access evidence.

A guidance note says harmonization work began in 2020; it does NOT establish CM UDiFF routing from January 1, 2020. Reconcile announcement dates, release and parallel-availability dates, format versions, file splitting, exact sample schema, calendar sessions and validity intervals from true originals. Do not assume a universal 2020→2024 replacement or borrow F&O/BSE format evidence for CM. Where official annexures cannot be authenticated, leave the transition/field semantics unknown.

Public documentation research must respect publisher terms; no scraping, endpoint probing, anti-bot circumvention, credential reuse, login bypass, automated provider feed access or invented availability. If source access to *actual real rows* requires a paid agreement, report that plainly instead of silently substituting an unapproved third party.

## 5. Technical implementation, conditional on GATE approval

If an authorized pack is available, implement a small **offline, read-only, opt-in real reference verification adapter** that consumes the existing pinned `read_verified` / reference-evidence contracts without loosening them. Prefer a new narrow module, e.g. `src/omegadata/parsers/real_reference_validation.py`, a new explicit CLI `scripts/verify_nse_cm_real_reference_pack.py`, and a new test module under `tests/unit/` or `tests/integration/` for authorized private fixtures. Paths are illustrative; do not create anything until gates pass. No default production route, schedule, live-fetch, database writer or release integration.

Before any real-payload open, check independently authorized rights, exact user-specified scope, permitted operation, expected filename/corpus count/byte length/sha, source and business-date binding, external human review evidence and private root controls. Source-rights `PENDING_REVIEW` cannot be overridden by the new adapter; if a separate lawful reference-inspection approval is used, its nature and non-equivalence to acquisition/redistribution approval must be explicitly recorded and narrowly enforced.

Compare the real bytes with the separately pinned input SHA; validate allowed container form and exact member count/path/size, strict decoding, file-level row count and source-specific field semantics, never a guessed generic schema. Produce exact-Decimal financial observations with row identity, original lexemes, unknown columns, explicit parser/reference versions, issuer/provenance and a deterministic content digest. Reject/hold on ambiguity instead of coercion. Keep provenance, schema interpretation, numeric comparison, rights and PIT as distinct states.

Never output old protected raw prices or proprietary full payloads to logs, Git, dashboards or prompts. Logs may contain redacted counts, hashes, bounded mismatch categories and masked identifiers subject to the agreement. No current-state `PriceRecord` writes, Parquet overwrite, canonical release promotion, adjustment or backfill. Missing publication time remains `null` and blocks PIT validation.

## 6. Negative-first plan and honest test accounting

Freeze the exact **real** reference pack and expected-row file *outside code under an approved private root*, then write tests for the following **20 distinct acceptance checks before real adapter edits**. For every test, save command, executor, UTC, hashes, expected count, genuine observed old behavior (if any), new behavior and whether source evidence suffices:

1. Authorized original publisher document and exact version-bound schema.
2. Document SHA and byte-length identity.
3. Authenticated sample-source receipt chain; a valid SHA alone is not enough.
4. Separate permitted-use scope for sample and reference.
5. Mismatched source key, market segment, instrument series, date and expected format refusal.
6. Exact ZIP/member inventory and safe decompression, no implicit extraction.
7. Raw input SHA, original archive observation ID and authorized consumer purpose.
8. Historical era boundaries with independent publisher evidence; otherwise blocked.
9. Header schema versus exact official catalogue; benign unknown fields retained inert.
10. Literal symbol, series, ISIN, leading-zero security codes and identity multiplicity.
11. Trade/business/publication date meanings; no datetime guessing.
12. Full-field OHLC exact Decimal and lexical value comparison.
13. Volume exact integer/original lexeme/units comparison; legitimate zero if documented.
14. Independently pinned row ordinal/order and non-vacuous expected record count.
15. File-wide failure/quarantine on critical malformed/duplicate or inconsistent rows.
16. Independent alternative reading of same real bytes, with no parser-under-test oracle dependency.
17. Same real bytes reproducibly yield same content hash; revisions have separate lineage.
18. Real permission revoked, absent, restricted or mismatched: fail before payload open.
19. Explicit no-write, no-network, secret-safe logging and protected-root confinement.
20. Full three-runtime regression, actual result hashes, quality checks, warning and skip accounting.

No invented fake OHLC rows to make these green. For refusal/property tests, non-financial malformed metadata probes may remain engineering-only and must not enter real-data acceptance; inherited synthetic engineering tests can run for regression but are strictly excluded from real-data numerator and denominator. If some checks cannot execute because a real source sample, reference or right is missing, mark them `BLOCKED_REAL_REFERENCE` with an exact missing input. Do not claim '20 passed' from a mixture of blocked and synthetic cases. Missing a new API is not proof of an old-data financial defect.

## 7. Independent real financial oracle

An oracle is not independent merely because it lives in a separate Python file. It must use **separately established expected real market fields** reviewed independently of the implementation and pinned before parser execution. Compare each real row's identity, date, OHLC Decimal, volume, units and exact source ordinal, with sensible field-specific typed refusal codes. Reject missing or empty expected corpora, changed expected hashes, missing required source rows and a changed raw source without refreshed approval. Do not compute expected values from the implementation itself.

Where only some rows can be independently certified, report the **exact numerator and denominator** of those sampled rows and define the sampling frame. Do not extrapolate sampling accuracy to all trading days or the entire 3,626-manifest inventory. If an independent second reading or human reviewer is absent, label comparison `SELF_REVIEWED_ENGINEERING_ONLY`, not certified financial truth. No fabricated market accuracy, P&L, Sharpe, win rate or backtest results.

## 8. Evidence, scorecard and two separate verdicts

If the pack is supplied and permission is valid, create a new immutable run folder `docs/omegadata_v2/implementation/od05u/<UTC-run-id>/` with:

- `00_repo_and_authority.md` (exact HEAD, clean/dirty worktree, owner permission, scope and limits).
- `01_real_pack_and_provenance.md` (pinned issuer/original/sample metadata, without raw sensitive bytes).
- `02_schema_era_and_calendar.md` (actual proved dates and unresolved 2020/2024 intervals).
- `03_negative_first_tests.md` (all 20 groups with red-first chronology and blocked subcases).
- `04_implementation_diff_and_compatibility.md` (minimal additive changes only).
- `05_independent_real_field_oracle.md` (human-reviewed expectation proof/independence).
- `06_security_rights_and_no_write.md` (exact permission and protected path evidence).
- `07_runtime_regression.md` (Windows 3.14/3.11, Linux 3.12; exact tests, skips, warnings, exits, coverage, identity).
- `08_real_data_scorecard.json` (actual source files/payloads/rows verified; actual mismatches, rejected, missing sessions, coverage denominator, PIT unknown and synthetic count fixed zero).
- `09_remaining_defects_and_rollback.md` (D-01 private signing custody P0, D-04 release bypass P0, and other P1/P2 risks unchanged).
- `10_gatekeeper.md` with **TWO DISTINCT** conclusions: `REAL_REFERENCE_ENGINEERING` and `REAL_FINANCIAL_VERIFICATION`.
- `11_one_next_request.md` and hashed, redacted command/evidence manifests.

Possible verdicts: `OD05U_REAL_REFERENCE_VERIFIED_LIMITED_SCOPE`, `OD05U_TECHNICAL_PASS_REAL_FINANCIAL_PENDING`, `OD05U_BLOCKED_SOURCE_RIGHTS`, `OD05U_BLOCKED_REFERENCE`, `OD05U_FAILED_REAL_MISMATCH`, `OD05U_BLOCKED_PLATFORM`. NEVER declare the first without authentic source, permitted use and independent real-row comparison. A synthetically correct decoder remains only an engineering pass. Do not assert PIT/research-release/trading readiness.

## 9. Practical owner input and stop behavior

If no real pack is available, **DO NOT** start a new round of application code or claim financial validation. Return this exact type of concise action:

`OD05U_INPUT_REQUIRED: one authorized NSE CM publisher spec/circular, matching genuine local market ZIP/CSV, separately independently pinned raw files, permission for this use, and independently reviewed literal expected OHLCV row values. No real payload was opened; no real-data tests were executed.`

For the owner, point to the existing file-by-file template above. Do not auto-complete the owner's identity, permission, file hashes, approval dates, reviewed values or actual status. Do not require a new global OD-04 G0/G1 loop. If the repository now contains new evidence/HEAD beyond the reviewed SHA, inspect it and preserve it rather than resetting it. Only the real source pack and scoped rights are the current external dependency. The user's insistence on real data forbids synthetic substitution. Stop after the gate or this bounded verification; no OD-06/production changes.

## 10. Required completion response

In a short auditable report, provide: actual branch+SHA, identified new source/evidence files, whether a genuine owner-approved pack exists, actual samples/documents/rows independently checked, exact old/new tests executed, source/hash comparisons, Windows/Linux quality exits, file changes, all remaining P0/P1/P2 risks, and exactly one owner action. If blocked, do not bury the blocker in a thousand lines of repetitive logs.
