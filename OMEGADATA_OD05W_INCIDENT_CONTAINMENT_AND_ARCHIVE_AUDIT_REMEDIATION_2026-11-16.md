# OmegaData 2.0 | OD-05W
## Contain the OD-05V setup deviation, repair archive-presence classifications, and restore honest cross-platform engineering verification

**Execution prompt for Codex / IDE coding agent**  
**Reviewed repository:** `PrivateAccount-01/omega-system---phase-1`  
**Reviewed branch:** `feature/od01-source-rights`  
**Reviewed remote HEAD:** `c8e7ff974e6c4a471a002d4807f268dc5d0044b1`  
**Date:** 2026-11-16 (Asia/Kolkata)  
**Execution mode:** `OD05W_SAFE_HARNESS_REMEDIATION_AND_ARCHIVE_PRESENCE_CORRECTION_ONLY`  
**Boundary:** No new real market-data read, no online acquisition, no source-policy promotion, no OD-06, no release, no trading, no Git lifecycle action without explicit separate instruction.

### 0. Mission: produce a working correction, not another report-only permission loop

OD-05V added a real read-only archive-presence scanner and evidence, but its Gatekeeper correctly concluded `OD05V_FILE_PRESENCE_BLOCKED` / `BLOCKED`. Execute the **allowed engineering repairs in this task** without stopping for a publisher-permission response. Stop only if an operation would require market payload bytes or permissions that have not been established. A finished **safe engineering component** can legitimately be accepted with the separate **financial-data gate blocked**. Neither replaces the other.

Do not reopen historic G0/G1 approvals. Do not fabricate an OD-05V process-exception acceptance. The OD-05V setup deviation must remain a formally pending human review even when code-level containment is completed. Do not make a docs-only commit as a substitute for the implementation. If branch or source code differs from reviewed HEAD, conduct a precise diff and adjust; do not force-reset.

### 1. Required reading and inspected baseline

Read completely:

- `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, and the existing OD-05V master prompt.
- `docs/omegadata_v2/implementation/od05v/20261116T172401Z/00_scope_reuse_and_chronology.md` through `05_next_owner_action.md`.
- The adjacent `gatekeeper.json`, `real-data-scorecard.json`, `runtime-matrix.json`, `full-regression-failures.json`, `logs/setup-deviation.json`, `command-index.json`, `logs/phase2-git-lineage.json`, `logs/original-presence-scan.json`, accepted source identity and preservation records. If a file has a different path, discover it, and cite the actual path.
- `src/omegadata/parsers/local_archive_presence.py`, `src/omegadata/parsers/archive_candidate_inventory.py`, `src/omegadata/parsers/reference_evidence.py`, `scripts/audit_local_archive_presence.py`, `tests/unit/test_od05v_local_presence.py`, `tests/unit/od05v_presence_oracle.py`.
- Test-fixture and consumer dependencies: `tests/unit/test_adjustment_reference_corpus.py`, `tests/unit/test_universe_manager.py`, `src/omegadata/track_b/universe_manager.py`, the reference-corpus fixture, source-rights contracts, RawArchive, acquisition, and any historical fixture-copy helpers.

Verify `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain=v1`, working and staged diff, and merge base. Record the actual branch/HEAD. Do not discard, reset, stash, clean, delete, rehash, copy or open retained prior raw-data copies, key material, environments, or user files. Historical Gatekeeper findings are immutable.

#### Exact observations to reconcile, not blindly restate as current executions

| Observed OD-05V datum | Status / interpretation |
| --- | --- |
| NSE cash-equity manifest candidates | 3,626 total: 3,596 `seed`, 30 `cache` |
| Filesystem ZIP paths | 3,626 present regular-file paths, zero missing |
| Filesystem length | 3,626 stat-reported lengths match manifest claims |
| Singly linked paths | 866 |
| Hardlinked paths | 2,760, currently labeled `HARDLINK_REFUSED` |
| Setup boundary deviation | 39 raw market files read/hashed/copied, 6,135,515 bytes, before guards; additional disposable regression reads not measured |
| Windows 3.14 / 3.11 OD-05V focused | 40 pass / 1 skip per runtime |
| Windows full | 714 pass / 4 fail / 14 skip / 4 realdata deselected per runtime |
| Linux focused | 35 pass / 5 fail (`BUDGET`) / 1 skip |
| Linux full | 718 pass / 9 fail / 5 skip / 4 realdata deselected |
| Rights | 13 source policies pending / zero approved at the last reviewed gate |
| Real row correctness | zero independently verified rows; no authenticated publisher/usage-rights approval |
| Historical format | 2020-01-02 legacy filename claim conflicts with default modern 2020 registry rule; not yet a verified schema correction |
| GitHub hosted branch CI | no matching branch workflow run in previous remote inspection |

These numbers are historical OD-05V evidence and **must be refreshed by actual OD-05W commands** wherever the task permits it. No real-data metric may inherit software-pass counts.

### 2. Mandatory incident containment before any test runner starts

The immediate P1 engineering issue is **copy helper execution before a raw-data-access guard**. The previous script copied 39 market files into a disposable environment. Implement a new `OD05W` guarded-runner/preflight contract that prevents this class of mistake **by construction**.

1. Identify the exact OD-05V helper and its call graph that selected original data paths. Record the exact old source lines, input manifest and all 39 affected path identities from `logs/setup-deviation.json`, but **do not open or rehash those files** to audit them. Prior byte identities must be labeled `ARCHIVE_OBSERVATION`, not newly approved or independently authenticated evidence.
2. Create a **fresh phase-owned clean-room runner** with a deny-by-default file manifest: copy only version-controlled `.py`, static configuration required by the data-free tests, `.md` as needed, and **specific non-market metadata** (`*.manifest.json`, pinned JSON) under explicit bounded roots. Treat generic `data/` copying, recursive globbing of source data, and old helper reuse as fatal. Deny `.zip`, `.csv`, `.gz`, `.parquet`, `.db`, `.sqlite`, `.bin`, raw market ZIP names, secret/certificate material, real snapshots, and all other data-bearing files unless separately authorized and classified. Unknown extensions fail closed. Do not assume an extension alone proves absence of sensitive data.
3. **Guard before copy, not after**: preflight the complete intended path/size/extension list and its symlinks/reparse points, then verify the guard covers the copy routine itself. Enforce no subprocess, network, raw-payload reads, and protected writes during the sensitive steps using host-supported controls; demonstrate a blocked adversarial copy attempt. Python monkeypatch/audit-hook restrictions are useful additional evidence, **not** a kernel-level sandbox. A separate process can bypass Python instrumentation unless the OS restriction also applies.
4. Make it impossible for a test-runner fallback to reuse old unrestricted copies. Distinguish a newly created empty destination from an old retained copy. Never delete or reuse existing incident directories automatically.
5. Capture source and destination allowlist hashes, copied metadata path list, byte counts, file counts, UTC invocation, effective guard, and denial probes **before executing pytest**. No logging of secrets or disallowed raw bytes.
6. If incident data were committed into public Git, do not attempt Git-history rewriting. Record the existing exposure separately for owner/legal review. Keep older setup deviation visible and unapproved. No retroactive approval or claim that the original read was compliant.

**Done condition:** a deliberately injected market file cannot enter a disposable runner **at any time**, even when it is placed in a folder otherwise allowed for test setup. A clean-room test runner can run pure code/metadata tests without even transient market-data payload access. No original archived raw payload byte read is allowed in OD-05W.

### 3. Fix the presence/state model without weakening content security

Inspect `local_archive_presence.py` and its current `_info`, `_row`, `scan_presence`, `ledger` and CLI. In OD-05V, 2,760 hardlinked regular files have correct `st_size` but `HARDLINK_REFUSED` is treated as not present in the simple `present` count, and the `size_matches_manifest` counter currently counts only the 866 singly linked files.

Implement an additive, versioned classification that separates **facts** from **eligibility**:

- `path_exists`: path resolves lexically to a final file whose metadata was inspected without following forbidden symlinks.
- `regular_file`: true/false.
- `filesystem_size_matches_manifest`: true/false/unknown. This is permitted for hardlinked files using `lstat` metadata; never require opening them.
- `link_class`: `SINGLE_LINK`, `HARDLINKED`, `SYMLINK_OR_REPARSE`, `UNKNOWN`.
- `metadata_discovery_state`: `PRESENT_SIZE_MATCHED`, `PRESENT_HARDLINK_SIZE_MATCHED`, `SIZE_MISMATCH`, `MISSING`, `UNSAFE_PATH`, `WRONG_TYPE`, etc.
- `content_inspection_eligibility`: independently determined and **false** under current source rights. A hardlink observation is not automatically approval or a reason to silently open the content.
- `raw_sha_verified`, `zip_structure_verified`, `publisher_origin_verified`, `row_financial_verified`: distinct false/unknown states unless actually measured with appropriate evidence.

Preserve original SHA/size provenance and revisions. `st_nlink != 1` is an audit/security marker, not proof of missing payload. Do not break existing callers: prefer a `v2` report or backwards-compatible additive schema with explicit migration/evidence justification. Refactor the current CLI exit semantics so it reports whether stat-level physical discovery completed separately from whether **every file is eligible for content inspection**; never return `0` if the caller requested content integrity but no content check ran. Retain the refusing rights-gated `--payload-integrity` path. Do not change production acquisition, RawArchive or source policies.

Strengthen adversarial cases for wrong ancestors, casing aliases, inaccessible directories, device boundaries, junctions/symlinks, hardlinked **final files**, hardlinked **metadata**, size mismatch on hardlinks, count mismatch and changing inode/stat values. For an attacker concurrently mutating directory ownership/mounts, refuse/mark unsupported; do not claim race immunity from a single `lstat`. Source roots are treated as trusted-owner controlled, with explicit limitation.

### 4. Resolve Linux `BUDGET` failures based on measured filesystem behavior

The five Linux failures are `test_p01_p03_real_candidates[P01]`, `[P02]`, `test_p04_full_independent_count_oracle`, `test_p15_2020_conflict_no_route_change`, and `test_p16_lineage_claims_not_authentication`. They use repeated bulk scans of 3,596 seed manifests on `/mnt/e`, which exceeds the 30-second wall budget. This is distinct from a logical schema failure.

1. Measure and log the actual per-stage costs of enumeration, pinned JSON reads, ancestor inspection and repeated test calls on both Windows and WSL. Do not assume exact performance or silently relax `ScanLimits.max_seconds=30`.
2. Optimize repeated `lstat` and directory enumeration with a **single bounded scan** per requested root and reuse the frozen read-only result in tests that do not mutate inputs; do not re-scan thousands of files within five separate tests. Ensure no stale results are reused across malicious mutation tests.
3. Avoid an untrusted path cache that could conceal a changed symlink. If caching ancestor stats for performance, bind metadata to source-owned immutable snapshot assumptions, revalidate required identity on the actual final path, and explicitly document race limitations. A one-time OS-level secure directory-handle traversal is preferable when supported. Do not weaken link or traversal refusal to win a benchmark.
4. For portable security/unit tests, construct a **native Linux disposable metadata-only corpus** and zero-byte/sparse non-market file canaries. Such files verify path/state logic, **not** historical financial validity. Full original `E:`-mounted archive stats remain a separate measured Windows/on-host evidence class. Never label a copied sparse canary as a real market-data payload.
5. If a fresh full WSL scan can truly meet 30 seconds after optimization, retain its actual success. If not, keep `LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED` with wall-clock evidence, and run the native-Linux portability suite completely. Do not mark five failing tests skipped, xfailed or passed without a valid documented contract change and executed proof.
6. Use CLI selection scopes and explicit fully pinned small manifest subsets for focused WSL tests if needed. Those subsets must not be described as full original-corpus verification. Keep one canonical full-corpus stat inventory on the supported host.

### 5. Repair the regression **harness**, not the business expectations

OD-05V's deliberately empty data tree caused 4 existing regression failures on Windows and Linux. They are:

- `tests/unit/test_adjustment_reference_corpus.py::test_reference_corpus_official_nse_source_pack_cases`: missing corporate action source snapshot `data/raw/nse_corporate_actions/year=2026/month=03/20260319.bin` in the clean-room copy.
- `tests/unit/test_universe_manager.py::test_seed_pack_backfill_reproduces_reference_snapshots`: no permitted cached input to resolve NIFTY50 symbol→ISIN mappings.
- `tests/unit/test_universe_manager.py::test_seed_pack_preserves_knowledge_vs_effective_date_semantics`: data-dependent seed validation fails in the payload-free test environment.
- `tests/unit/test_universe_manager.py::test_seed_pack_backfill_works_with_production_autoflush_setting`: the same missing approved raw mapping path affects its PIT/autoflush coverage.

Record all four exact node IDs as observed in the OD-05V ledger. Independently verify each actual root cause in the new clean-room run; do not assume the same symptom always has the same cause or label the tests defective without evidence.

Implement explicit suite segmentation with a **machine-readable test dependency inventory**, not substring hacks that silently deselect tests. Separate:

- `A`: code-only and nonfinancial metadata regression suite, including OD-05W tests. This must run with a payload-deny guard.
- `B`: existing source-dependent regression tests requiring real market bytes/snapshots. Preserve their names/assertions; under rights pending report `BLOCKED_INPUT` with exact dependencies and **do not count as passed or as a test that was run**.
- `C`: genuinely `realdata`-marked tests, still not run without authorization.

Demonstrate a controlled full collection/list of all tests; reconcile cardinalities `A+B+C` with the exact collection manifest and known skips. Continue to run the actual unchanged full command in a disposable clean-room copy once as diagnostic evidence; expected failures remain `FAIL` and must not be rewritten as green. Then run `A` as an explicitly scoped required engineering gate and report its PASS/FAIL separately. Never weaken/remove/mutate production tests or fabricate OHLC/ISIN data to make B pass. No silent skip markers, `pytest -k not ...` passed off as full regression, or environment-specific suppression.

If a specific B test can be reworked to use existing non-market fixture data *without changing its economic meaning or claiming financial certification*, propose separately, and retain proof of semantic equivalence. Do not do it silently in this scope.

### 6. Implement tests negative-first; reproduce and fix real defects

Add targeted tests before changing implementation. Freeze individual test file hashes before application changes and record the **actual** failed baseline. If failure is due only to absent new APIs, label `NEW_FEATURE_ABSENT`, not a reproduced old bug. Maintain chronological logs for later additions.

**W01–W24 minimum test groups:**

- **W01**: rejected old raw-payload copy helper and disallowed glob; no file-open happens.
- **W02**: copy allowlist permits exact source/manifest/config subset only and rejects unknown extensions.
- **W03**: denied ZIP/CSV/Parquet/DB/secret payloads even if disguised inside allowed tree.
- **W04**: guard active before all copies; adversarial read/write/network subprocess attempts actually denied.
- **W05**: preflight detects unsafe link/junction/hardlink and cross-volume/private path; no disallowed copy.
- **W06**: immutable historical incident ledger remains intact, previous evidence hashes match, no auto-owner-waiver.
- **W07**: `PRESENT_HARDLINK_SIZE_MATCHED` for a hardlinked sparse non-market canary, no payload open.
- **W08**: hardlink wrong size reported `SIZE_MISMATCH` with link warning; never missing.
- **W09**: regular-file present count independent of content eligibility.
- **W10**: original 3,626 stat-count ledger reconciles, source-root 3,596/30 split and zero missing only if freshly observed.
- **W11**: 2011, 2020, 2024 date candidates retain format and lineage flags; 2020 conflict remains unresolved.
- **W12**: mutated relative path, case alias, UNC, ADS, traversal, wrong ancestor, reparse/symlink refusal.
- **W13**: deterministic digest/JSON across directory enumeration orders and supported runtimes; no secret path leakage.
- **W14**: time/size/count/depth budgets enforced on a native disposable dataset.
- **W15**: targeted original/canary scan operation count and timing vectors; no undocumented 30-second relaxation.
- **W16**: repeated test access uses one immutable observation when inputs unchanged; mutation invalidates it.
- **W17**: Linux-native metadata scanner and sparse-canary cases pass actual POSIX link tests.
- **W18**: original Windows stat inventory remains a distinct status; native Linux canary is not market-data proof.
- **W19**: explicit test inventory A/B/C includes all collected node IDs; unclassified tests fail the harness audit.
- **W20**: B missing snapshots/mappings remain `BLOCKED_INPUT` and do not enter A acceptance totals.
- **W21**: full unrestricted diagnostic still records actual failures; restricted engineering PASS is clearly named.
- **W22**: `--payload-integrity` never returns success while rights pending; no RawArchive bypass.
- **W23**: output only in fresh external path, does not overwrite originals, no incident-copy cleanup.
- **W24**: source-file preservation, accepted code hashes, command/exit/skip pairing and machine Gatekeeper reconciled.

No generation of synthetic market prices, securities, returns, volumes, corporate actions or financial reference values. Empty/sparse OS-file canaries are allowed for filesystem engineering tests; explicitly label them `NON_MARKET_CANARY` and never include them in market accuracy metrics.

### 7. Execution and verification matrix

After implementing, use the actual configured Windows 3.14, Windows 3.11 and native Ubuntu/WSL Python 3.12 runtimes already present. Do not install paid dependencies or download provider payloads. Use temporary, newly created **data-free** test worktrees and a pinned, inspectable input manifest.

For each platform record exact executable/argv/cwd/UTC/exit, source and fixture SHA-256 (of **code and metadata only**), package identity, stdout/stderr, warnings, file-denial probes, elapsed time, total copied file/bytes list, tests passed/failed/skipped/deselected and reason for each exclusion. Actual test command patterns can be chosen from existing repo configuration, but use these quality checks where available:

```text
python -m pytest --collect-only -q
python -m pytest -q tests/unit/test_od05w_*.py
python -m pytest -q <explicit-engineering-suite-node-list-from-machine-inventory>
python -m pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing   # Diagnostic; record nonzero honestly
python -m ruff check --no-cache src/omegadata scripts tests
python -m mypy src/omegadata
python -m pip check
python -m compileall -q src/omegadata scripts
```

The broad full diagnostic may have missing-data failures. Do not claim that every test passes while full diagnostics exit nonzero. The goal is a **valid reproducible green data-free A suite**, independently verified counts, and a **truthful B/C blocked matrix**. If any A test fails, overall engineering verdict is blocked. WSL mount original full-scan performance may stay separately blocked if true; native Linux code safety still must pass.

### 8. Gatekeeper output and evidence package

Create a fresh, append-only directory:

`docs/omegadata_v2/implementation/od05w/<UTC_RUN_ID>/`

Deliver at minimum:

- `00_identity_and_preservation.md`: SHA/branch/status, unchanged originals, exact scope.
- `01_incident_root_cause_and_pre_guard_containment.md`: old helper defect, timeline, protected copy boundaries, non-approval of historical deviation.
- `02_hardlink_presence_correction.md`: actual pre/post counters and v1/v2 semantics.
- `03_linux_runtime_optimization.md`: measured bottleneck and legitimate original-vs-native corpus distinction.
- `04_regression_dependency_inventory.md` plus machine JSON: precise A/B/C test node IDs, missing snapshot and ISIN dependencies, no hidden exclusions.
- `05_negative_first_W01_W24.md`: every group, timestamps, pre-code/post-code classification, exact test IDs.
- `06_cross_platform_execution.md` plus exact JSON/text command/exit/coverage/skip pairing.
- `07_real_data_scorecard.json`: original candidate count, metadata-only results, zero newly authorized hashes/rows unless separately proven, publisher and rights states.
- `08_security_risks_rollback.md`: unresolved P0 signing/release risks, P1 setup deviation and rights, Linux performance, controlled rollback plan.
- `09_gatekeeper_verdict.md` and `gatekeeper.json`, with **two independent axes**:
  - `safe_engineering_verdict`: `OD05W_SAFE_ENGINEERING_PASS` only if W01–W24 and A suite pass on required runtimes with no new prohibited reads; else BLOCKED.
  - `financial_data_verdict`: `BLOCKED_REAL_DATA` until genuine separately permitted file/row validation is actually executed and independently compared.
- `10_one_next_owner_input.md`: specific incident-review and source permission action, but **do not block safe engineering implementation while awaiting them**.

All evidence must distinguish `RUN`, `ARCH`, `NON_MARKET_CANARY`, `LOCAL_META`, `AUTHENTIC_REFERENCED`, `NOT_RUN`, `BLOCKED`, `UNKNOWN`. Preserve old reports. A recent commit SHA is not an accepted current-run test identity. No signing, publishing, trading, OD-06, deployment, auto-merge, push or commit.

### 9. Scope boundaries and anti-failure checklist

**DO NOW:** inspect and repair the OD-05V runner/copy guard, precise file-presence model, Linux performance, test-dependency segmentation, negative-first coverage and preservation. Reuse existing code and project conventions. Make narrow reversible code/test changes.

**DO NOT:**

- Treat `st_size` agreement, Git blob ID, manifest checksum or historical filename as proof of financial accuracy or official NSE origin.
- Read/rehash/copy the 39 affected original payloads or examine their contents to reproduce the incident. The previous recorded incident counts suffice.
- Delete or clean the retained copies, rewrite historical Gatekeeper decisions, fake retroactive authority or blame Windows/WSL without measurements.
- Turn the four data-dependent regressions into silent passes by tampering tests, marking them skipped, adding fictional financial rows or hiding them from collection.
- Increase the 30-second scanner budget just to make Linux pass; optimize or report an explicitly bounded real limitation.
- Modify `source_rights_policy.v1.json`, `source_registry.py` era cutover, acquisition logic, RawArchive semantics, PIT, corporate actions, DB, signing, CI, releases or production routes in this phase.
- Use external NSE endpoints, paid vendors, bypasses, or temporary permissions invented by the coding agent.
- Claim that multiple AEF agent personas equal independent human or legal review.

### 10. Exact final response contract

Respond with:

1. **Current branch/HEAD and patch paths.**
2. **The actual technical root causes fixed**, with code locations and before/after evidence.
3. **Current 3,626-candidate discovery stats** with hardlinks counted accurately as physically present, but blocked from content use.
4. **Fresh W01–W24 results**, including negative-first chronology and all runtime summaries.
5. **B/C test block table** and explicitly nonzero full diagnostic outcomes if they remain.
6. **Process-incident status**: containment completed vs retrospective owner/legal review still pending; report any new prohibited access as immediate STOP.
7. **Financial correctness status**: zero independent real OHLC comparisons unless actual permitted file/row verification occurred, which is not part of OD-05W.
8. **Two-axis Gatekeeper and one actionable owner handoff.**
9. **Explicit STOP after OD-05W.**

A technical PASS is conditional on executed evidence. Code is not deployed or committed merely because a Markdown instruction exists.
