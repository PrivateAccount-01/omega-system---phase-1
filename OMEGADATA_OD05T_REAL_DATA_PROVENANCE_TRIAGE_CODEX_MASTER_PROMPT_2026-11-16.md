# OmegaData OD-05T: Real-Archive Provenance Triage, Reference-Pack Readiness, and Evidence-Bound Validation

**Codex execution contract | Prepared 2026-11-16**  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Existing branch:** `feature/od01-source-rights`  
**Latest reviewed HEAD:** `db087fb9ee12887d3d9c787b797bb6968ad45440`  
**Immediate predecessor:** `25fb5aa4a2f4312e7bfafb9084c29aa95ee2bd48`  
**Execution mode:** `OD05T_REAL_DATA_PROVENANCE_TRIAGE_AND_PACK_READINESS_ONLY`  
**Permitted technical outcome:** `OD05T_METADATA_TOOL_TECHNICAL_PASS_REAL_DATA_PENDING` or `OD05T_BLOCKED`.  
**Financial outcome:** `BLOCKED_REAL_DATA` until real source bytes, lawful usage, and independent expected values are actually verified.  
**Do not start OD-06 or alter live/production routing.**

## 00. Governing rule: actual market evidence, never synthetic financial acceptance

The user specifically requires **actual, independently verifiable market data** to judge OmegaData's financial success. The last OD-05S execution legitimately stopped with `OD05S_BLOCKED`, because no authentic, permitted NSE CM reference pack was identified; the report did not execute the 24 planned OD-05S tests or open real market payload bytes. Do not misreport this stop as an implementation pass.

1. **Do not generate, substitute or label artificial OHLC/volume/instrument/corporate-action/return observations as actual market data.** Do not invent exchange sessions, historical continuity, dividends, or numerical expectations. New phase acceptance must use existing real manifest metadata for metadata capabilities and genuine publisher data for financial capabilities.
2. Existing synthetic tests are preserved as **legacy software-regression evidence only**. Their counts never contribute to measured real-data accuracy or official-reference acceptance. No new synthetic market dataset is needed in this phase.
3. Existing seed-cache data is **not automatically synthetic and not automatically authentic**. Classify as `EXISTING_CACHED_OR_SEEDED_UNVERIFIED` until independent provenance, applicable permissions and values are established. An HTTPS URL in a manifest is not an original publisher receipt.
4. Do not bypass any provider's access restrictions, scrape blocked exchange endpoints, use unapproved credentials, or assume public download availability equals commercial research rights. The 13 real source policies currently remain `PENDING_REVIEW`, zero approved.
5. No source-data payload read/parse/backtest or data copying until the **specific file's permissible use and scoped review authority** are established. Metadata-only `read/stat` of an explicit allowlisted repository tree may proceed within these limits. If a protected manifest itself is disallowed, stop that subset as `BLOCKED_RIGHTS`.
6. Do not let an LLM, a self-signed JSON record, a repository file name, a SHA-256 checksum, a web citation, or an `approved` string self-issue provider authenticity or lawful-use approval.
7. Maintain strictly distinct classifications: `SOFTWARE_ENGINEERING_CHECK`, `METADATA_ONLY_INVENTORY`, `REAL_BYTES_HASH_VERIFIED`, `PUBLISHER_ORIGIN_VERIFIED`, `REFERENCE_SCHEMA_VERIFIED`, `REAL_ROW_VALUES_INDEPENDENTLY_MATCHED`, `PIT_ELIGIBILITY_VERIFIED`, `RELEASE_ELIGIBLE`. Never infer one from a weaker stage.
8. The task is to deliver useful **code and evidence from existing real manifests**, not another repeated no-code gate report. Implement the bounded metadata tool even when a full authentic reference pack is absent, provided the allowed paths and metadata authority are sound. When permissions prohibit even that work, make only the minimal blocker report and stop.

## 01. First, verify the actual checkout and preserve everything

Read completely: root `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, `docs/omegadata_v2/plan/09_implementation_phase_plan.md`, the OD-05, OD-05R, OD-05S Gatekeeper reports, and relevant rights policy. Read only required code modules before editing: `src/omegadata/parsers/{contracts,dispatch,nse_cm,reference_evidence,era_matrix}.py`, `src/omegadata/track_a/{source_registry,source_rights,raw_archive,download_manager,acquisition}.py` and the existing tests/fixtures. Do not trust old logs as current execution.

Check exact `git branch --show-current`, `git rev-parse HEAD`, full tracked `git diff`, `git diff --cached`, `git status --short`, `git merge-base main HEAD`, source-policy SHA, and source/tests/evidence hashes. Base reviewed version is `db087fb9ee12887d3d9c787b797bb6968ad45440`; if the branch has moved, inspect the actual new diff before proposing any patch. Preserve all owner changes. No reset, clean, stash, force push, history rewrite, merge, commit/push without separately explicit instruction. Never touch the existing GnuPG private/revocation files or read/hash/copy their contents. Preserve every existing raw archive, seed import, SQLite/Parquet DB, generated release/pointer, report and test.

Specific latest evidence: `docs/omegadata_v2/implementation/od05s/20261116T094756Z/`. That run inspected **3,676 manifests**: 3,596 described seed-cache imports, 79 immutable versioned-cache entries, one undeclared. It opened **zero payload bytes and zero rows**; verified **zero** publisher-origin packs and **zero** real values; executed **zero** OD-05S tests. These are report claims to reconcile, not numbers to reuse in future outputs without fresh actual commands.

## 02. Deliver a useful first-party real-archive metadata tool

Within exact reviewed scope, implement an **additive, read-only** library + CLI, not a new downloader or a staging/migration mechanism. Proposed files, adapt to conventions after inspecting repo:

- `src/omegadata/parsers/archive_candidate_inventory.py`: pure, bounded metadata parser, explicit candidate classifications, immutable index rows and stable canonical output.
- `scripts/audit_existing_market_archive.py`: CLI with `--manifest-root`, `--source-key`, `--business-date-start`, `--business-date-end`, `--output-dir` (must be fresh, disposable, outside protected data paths), and `--metadata-only` mandatory by default.
- `tests/unit/test_od05t_archive_inventory.py`: test-first functional cases over real existing manifest structures and adversarial malformed *metadata* inputs; no generated market observations.
- A separate stdlib-only metadata-count and SHA oracle under `tests/unit/` or phase evidence, using independently frozen real manifest paths/counts and hash pins; it must not call application inventory functions to compute expected results.
- Fresh evidence directory `docs/omegadata_v2/implementation/od05t/<UTC_RUN_ID>/`, with no historical overwrite.

Program requirements:

A. Inventory **only a narrow, explicit, approved metadata directory**. Do not descend into untracked environments, GnuPG paths, raw payloads or arbitrary drives. Never auto-search a user's entire home directory. Validate realpath/relative confinement, symlink/junction/reparse and device rules, bounded recursion/file counts/size, and no destructive operations. Never use manifest-provided paths to open another file in this metadata phase. Reject malformed/binary/non-JSON manifests with typed, redacted reasons; record counts, not file contents.

B. Record source_key, business date, storage mode, manifest metadata SHA, declared payload checksum **as an unverified claim**, declared relative artifact path **as untrusted metadata**, transport/origin classification, and whether the manifest contains a declared reference, permission or reviewed-value field. Mark missing vs present vs independently validated distinctly. Untrusted URL strings must be redacted; never emit raw URLs with tokens, credentials or identifiable local absolute paths.

C. Deduplicate only repeated **manifest identities**, not distinct market observations. Retain multiple same-date revisions and same-byte separate observations. Distinguish `SEED_IMPORT_UNVERIFIED`, `VERSIONED_CACHE_UNVERIFIED`, `TRANSPORT_CLAIM_UNVERIFIED`, `RIGHTS_PENDING`, `MALFORMED_METADATA`, `REFERENCE_PACK_ELIGIBLE_PENDING_PROOF`, `DOCUMENT_IDENTITY_PINNED` (only when genuinely independently pinned), and `MISSING_INFORMATION`.

D. Produce **candidate triage ordered by evidence readiness**, not fabricated accuracy or provider trust. For the source `NSE_EQUITY_BHAVCOPY`, identify actual manifest coverage around dates (as metadata **only**) 2019-12-31, 2020-01-01/02, 2024-06-21/24/25, 2024-07-04/05/08/09 and independent controls. Do not call these trading days or official sessions merely because a file says so. Count duplicates, revisions, missing metadata, unresolved integrity and rights states.

E. If existing manifest records are too sensitive to commit, keep raw records and absolute paths in the private environment, write **aggregated and redacted** summaries only. Do not introduce a public `data/` export or a sanitized-looking but actually authentic market payload fixture into tests. All output must be source-identity-aware and reproducible with canonical SHA of metadata inputs.

F. Every output must report `payload_bytes_read=0`, `market_rows_parsed=0`, `market_rows_independently_verified=0`, `official_reference_verified=0` unless actual authorized later-stage evidence proves otherwise. Never count metadata SHA matches as payload hash verification. Counts must be derived from actual scan, not hardcoded from the prior report.

G. CLI `--help`, `--dry-run`, invalid argument, protected destination, unexpected source, duplicate manifest, mixed namespaces, Windows/Linux path syntax and termination/error behavior require actual tests. The CLI should exit nonzero for untrustworthy or incomplete acceptance requests, even if a metadata inventory itself succeeds.

## 03. Owner-supplied authentic reference-pack contract

The **single external unblocker** is an independently supported, legally permitted NSE CM reference pack, rather than a new synthetic test corpus. If the owner has already placed one locally, use only the exact authorized allowlisted path. If not, issue one concrete owner handoff request; do not repeatedly create blocked dossiers.

Required pack contents, preferably private and NOT committed to Git:

1. Original publisher document or dated schema/UDiFF catalogue/annexure; verifiable publisher/edition/version, canonical publisher URL and acquisition provenance; full original SHA-256 and byte length independently supplied and freshly rechecked.
2. A bounded number of **actual** historical CM cash-equity rows/files dated near the disputed 2019/2020 and June-July 2024 boundaries, with exact original bytes, source file name, source key, appropriate rights/use evidence and immutable SHA/length. A positive count is required for real acceptance. Avoid assuming every target calendar date is a trading session.
3. Separately authored, human-reviewed expected source-field list, member names, date meanings, series/ISIN/scrip identity, price units/Decimal precision, volume units, source row order, and **literal expected values from independently verified original rows**. No expectations derived from the parser-under-test; no LLM invented target rows.
4. Scoped right-to-use record that distinguishes **documentation consultation**, **read/parse existing data locally for financial research**, **data retention**, **derived usage**, **publication**, and **redistribution**. A student or no-fee use case is not a blanket exemption for commercial/trading use. Do not alter global policy or authorize live egress in this phase.
5. A true independent pin manifest outside the pack, owned by the accountable human/reference reviewer: full filename + SHA + length + publisher origin + review identity and actual review date. A checksum generated at the moment a pack is discovered proves integrity only, not external authenticity.
6. Reference version and claimed applicability interval; explicitly track potential overlapping formats and uncertainty. Distinguish source publication date, exchange session/trade date, file generation, observed/ingested time and research decision time.

Use existing `src/omegadata/parsers/reference_evidence.py` and `era_matrix.py` as foundations. They currently **do not confer official approval automatically** (`official_eligible=False`), which is correct. Design a **separate reviewed-attestation trust path** but do not implement automatic final approval or promote a reference while the owner pack is missing. Do not let a self-reported `OWNER_SUPPLIED_REFERENCE_USE` string authorize itself.

Suggested source-document discovery references (metadata only; not permission to download market feeds):
- NSE official forms/UDiFF catalogues: `https://www.nseindia.com/static/resources/forms-formats-members`.
- NSE official reports: `https://www.nseindia.com/all-reports/`.
- NSE data policy: `https://www.nseindia.com/static/market-data/nse-data-policy` (recheck exact live URL/terms; approval must be separately documented).

**Publisher documents and authentic market observations are not interchangeable.** A genuine schema PDF can establish a format specification only in its scope; it cannot prove every row, a trading session, or whether a particular legacy cache originated with the exchange.

## 04. Source-eligible payload verification is a later, gated substep

Only when a real pack and scoped owner authorization are physically present and independently pinned may Codex perform the following in a **private disposable sandbox**:

- First verify checksum and byte length of every authentic file. Verify provenance of original receipt against independent publisher evidence; do not invent missing receipt facts.
- Confirm rights for this operation. If not explicitly granted, do not open payload bytes; report `BLOCKED_RIGHTS` instead.
- Invoke the existing rights-aware `RawArchive.read_verified` for a pinned observation where allowed. The user must not need to enable all 13 pending source policies. Explicit off-pipeline reference-review authority should be separately scoped and cannot masquerade as provider collection approval.
- If a parser for that actual, authenticated format does not exist, write failing **real-byte, real-expected-row** tests first and implement only a versioned opt-in parser for that one proven format. Preserve the synthetic illustrative parser as a separate regression path, not evidence of market correctness.
- Independent oracle checks every row/field of the bounded owner-pinned sample. Compare dates, symbols/series/ISIN, OHLC exact decimals, volume units, member/header/schema, unknown fields, row order and file-wide failure behavior. Record expected vs actual and full mismatch categories, without placing raw licensed rows or confidential URLs in public logs.
- Missing/empty/corrupted/moved pack or mismatched external pins must refuse non-vacuously. Wrong-date/wrong-format/overlap must quarantine; no year-only dispatch. Never overwrite historical raw or canonical Parquet, modify PriceRecord, or silently recalculate the old releases.

**If the pack is absent, this entire payload substep is `NOT_RUN_BLOCKED_REFERENCE` rather than a software pass.** Completion of a correct metadata CLI is a separate technical achievement, not financial validation. Real trading performance, signal profitability and production readiness remain unassessed.

## 05. Complete test-first acceptance matrix, no generated financial corpus

Freeze executable tests, real metadata fixture identity hashes, independent oracle and intended outputs **before any new application file**. Execute the baseline against existing code; classify missing new API imports as `NEW_FEATURE_ABSENT`, NOT old-behavior defects. Retain each later adversarial addition with its true chronology. The final test suite must cover at least:

**M01–M06: Current real-manifest intake**
- M01 correct scan count from existing metadata manifests, with independent count source.
- M02 deterministic canonical metadata digest across Windows/Linux and file enumeration order.
- M03 exact source/date/storage/source-mode classification; missing vs present provenance.
- M04 malformed real manifest, duplicate JSON keys, non-JSON, size/entry budget, mixed source identities.
- M05 same-date revisions and same-byte observations remain separate, no silent overwrite.
- M06 no payload opens; denied/protected path and symlink/junction refusal.

**M07–M12: Integrity, rights and privacy**
- M07 untrusted path/UNC/drive/`..`/reparse/outside-root refusal.
- M08 URL redaction, no tokens/credentials/private absolute paths in user-visible reports.
- M09 fail-closed on `PENDING_REVIEW`, revoked/unknown scope and absent permission evidence.
- M10 stated manifest payload checksum is *not* labeled independently byte verified.
- M11 no network call, no signing content access, no source archive modification, no releases.
- M12 missing, moved, empty, tampered expected metadata corpus fails independently; zero actual rows is never accepted financial success.

**M13–M18: Reproducibility, portability and scorecard**
- M13 exact expected metadata count must be independently pinned; can't derive pass threshold from scan output.
- M14 2019/2020 and June-July 2024 candidate metadata matrix is explicit, not trading calendar proof.
- M15 reproducible scorecard separates parsed manifests and verified actual observations.
- M16 memory/time/row/byte limits measured under multiple real metadata volumes without generating fake market rows.
- M17 Windows 3.14, Windows 3.11 and Linux 3.12 target actual execution with platform skip pairing and protected disposable roots.
- M18 old OD01/OD02/OD04/OD05/OD05R/OD05S evidence and default production paths remain unchanged.

**R01–R06: Genuine reference-pack acceptance, conditionally executable**
- R01 independently pinned publisher document bytes present and legal read permitted.
- R02 actual sample bytes present, full SHA/length match external owner pins.
- R03 independently reviewed source format and representative expected-row values exist.
- R04 correct source-era/date/field mapping against actual rows, with exact Decimal/integer/identity checks.
- R05 deliberate tampered real sample and bad date/version refused, no silent fallback.
- R06 reference rights, scoped purpose and PIT meanings verified independently before any financial acceptance.

R01–R06 must report `NOT_RUN_BLOCKED_REFERENCE` if required inputs are missing; they are NEVER green through synthetic substitution. No generated OHLC/volume/security fixture should fill these cases. Non-market malformed metadata negative probes are engineering safeguards only, not market-data examples.

## 06. Quality controls and independent oracle

For every actually supported runtime, in protected disposable copies with network egress blocked, execute and record:

- Fresh import/collection and targeted tests (metadata tool + inherited archive/rights tests).
- `python -m pytest -q -m "not realdata"` or repo-equivalent, with all realdata exclusions explicit and never called verified.
- Ruff, strict mypy, `pip check`, compilation and coverage, with exact executable/version/argv/cwd/time/exit.
- Real local metadata scan (no payload bytes), independent read-only count/hash oracle, checksum of new source/tests and separately pinned expected subset, and preservation diff.
- Actual OS-specific symlink and Windows junction tests where feasible; skipped test names must have named passing peer on another OS, not a generic assertion.
- Test the CLI in both empty and populated candidate metadata roots; **empty corpus is failure for actual market validation**. Do not invent a positive corpus by copying synthetic price records.

Guard DNS/TCP/UDP/subprocess where appropriate; allow only the exact trusted test worker commands. Avoid weakening guardrails to get green tests. No package installations or changes to lockfiles merely to make tests pass. Do not conceal warnings, skip real tests or count missing data as 100% accuracy.

Report actual observed metadata processing rates and resource budgets, but no market-price accuracy unless real rows and independently reviewed expected values were processed. Dedicated missing-source and malicious path cases are security assertions, not price predictions.

## 07. Human-access and rights workflow, one unblocker

If no valid reference pack is supplied, provide a *specific* single owner request with a bounded list of exact needed artifacts. Include a plain file-by-file manifest template containing `file_role`, `local_private_path`, `publisher`, `publisher_url`, `document_id`, `publication_date`, `format_id`, `data_date`, `sha256_independent_pin`, `byte_length`, `acquired_at`, `permission_scope`, `permission_evidence`, `reviewer_identity`, `reviewed_at`, `expected_fields`, `expected_values_ref`, and `PIT_publication_evidence` (nullable). **Do not fill unverifiable items.**

If no fee-free permissible market-data access can be established, report that fact and evaluate an owner-approved alternative authentic source without pretending that it is NSE official. The requirement of no paid vendors does not erase provider terms. Never switch to unverified public GitHub CSV dumps or generated data as a 'solution'. NSE Data's published policy describes special subscription/usage arrangements; the data owner or compliance reviewer must determine scope and cost. Prioritize a small legally permitted real sample before broader ingestion.

## 08. Strict scope and exclusions

Allowed existing files to **read**: manifest metadata under a narrow authorized data directory; existing source code and evidence. Allowed new files: narrowly named first-party metadata inventory module, CLI, new tests/helpers over existing manifest metadata, docs and aggregates. Additive only.

**Forbidden without separate explicit authorization and authentic reference proof:** modifying existing `source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `sequential_pipeline.py`, `storage.py`, DB models, release manager, GnuPG files, source-rights policy, `.github/workflows/`, data payloads, existing fixtures and tests, and all historical evidence. No live exchange requests, real broker actions, source-scraping tools, browser access bypass, data export, signing, merge, push or commit.

No OD-06, OD-07, OD-10 or Phase 2 implementation. No automatic trading, P&L claims or backtesting in this scope. No use of new synthetic price test data as an alternative path. Preserve the real-data-only policy in all outputs.

## 09. Mandatory deliverables

Under `docs/omegadata_v2/implementation/od05t/<UTC_RUN_ID>/` create:

- `00_identity_scope_and_rights.md`: branch, HEAD, exact permissions, protected files.
- `01_existing_archive_manifest_inventory.md`: actual read-only results, source/month/date counts, declared modes and unknowns; no raw data.
- `02_candidate_era_and_sample_readiness.md`: 2019/2020/2024 candidate matrix, explicitly not verified trading dates.
- `03_metadata_contract_and_implementation.md`: source-level code diff, purpose, performance and dependency decision.
- `04_negative_first_and_honest_chronology.md`: M01–M18 baseline/red/green, real-pack R01–R06 blocked/executed states.
- `05_independent_metadata_oracle.md`: separately frozen existing-manifest counts/pins and actual mismatches.
- `06_real_data_acceptance_scorecard.md` and machine `real-data-scorecard.json`: independent real file/row evidence, unknown denominators, accepted/rejected, zero synthetic acceptance contribution.
- `07_security_rights_and_source_authenticity.md`: permission risks, path/URL security, provider verification and no payload opens.
- `08_cross_platform_quality_matrix.md`: actual executed commands/results/warnings/exclusions, distinct archived vs new evidence.
- `09_remaining_defects_and_rollback.md`: still-open signing/release P0, 2020 source-era P1, PIT and canonical Parquet versioning.
- `10_gatekeeper_verdict.md`: ONE accurate verdict.
- `11_owner_reference_pack_handoff.md`: ONE concrete artifact/permission request if reference pack missing.
- `logs/`: fresh immutable command/environment/OS/input SHA/test/coverage/preservation evidence, including intentionally failing runs, redactions, no raw licensed payloads or signing material.

Gatekeeper decision:

- `OD05T_METADATA_TOOL_TECHNICAL_PASS_REAL_DATA_PENDING` **only** when metadata inventory implementation and all in-scope M01–M18 tests truly run and pass; it **must retain `BLOCKED_REAL_DATA`** if no authenticated permitted sample has passed independent real-row comparison.
- `OD05T_REAL_REFERENCE_SAMPLE_VERIFIED_SCOPED` only when actual R01–R06 real-byte, rights and independent-field evidence pass for a narrowly stated corpus; no blanket NSE historical or production certification.
- `OD05T_BLOCKED` if the metadata implementation or required scoped authority cannot safely proceed, or essential tests fail.

A `PASS` on one dimension cannot erase blockers on another. Owner review and upstream reference-rights approval are external to the agent.

## 10. STOP AND REPORT

Stop at the OD-05T gate. Provide (i) actual changed-file list, (ii) fresh tests with exact pass/skip/blocked counts, (iii) number of authentic market files and rows independently verified, (iv) exact unresolved financial/publisher/legal blockers, (v) evidence paths and SHA, and (vi) one next owner input. Do not silently initiate later phases or change source policies.

**Nonnegotiable definition of success:** An engineering CLI that lists 3,676 manifests is useful, but it is not yet a verified market-data engine. The first real financial milestone is an appropriately permitted, authentic, independently checked source sample with exact source-field and numeric agreement, followed by era/session/revision coverage. Synthetic financial examples never substitute for that evidence.
