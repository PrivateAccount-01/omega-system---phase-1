# OmegaData 2.0 | OD-05V: Local Historical Archive Recovery and Real-Data-First Verification

**Execution contract:** Read-only local archive inventory and lineage implementation, followed by *separately authorized* offline content integrity / real-row verification. **Do not repeat OD-05U/OD-05U2 documentation-only gate loops.**

**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Branch:** `feature/od01-source-rights`  
**Reviewed remote HEAD:** `0d43a43a7df2a997b394269d6a9ebf1e64a00de1`  
**Phase-2 origin lead:** `PrivateAccount-01/omega-system---phase-2` (`master`), specifically `data/raw/bhavcopy/` and `renaissance/data/bhavcopy_ingestor.py`.  
**Execution mode:** `OD05V_LOCAL_ARCHIVE_DISCOVERY_AND_RIGHTS_GATED_REAL_DATA_DIAGNOSTICS_ONLY`.  
**Owner objective:** Put existing historical data to productive use. No new fabricated securities, prices, volume, returns, calendars, OHLC rows or backtest performance. No paid service, vendor or source bypass. No production feed promotion.

## 0. Read first; preserve original evidence and rules

Read the actual `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, current `src/omegadata/track_a/source_rights.py`, `src/omegadata/track_a/raw_archive.py`, `src/omegadata/track_a/source_registry.py`, `src/omegadata/track_a/acquisition.py`, `src/omegadata/parsers/archive_candidate_inventory.py`, `scripts/audit_existing_market_archive.py`, all accepted OD-05T reports, and the current OD-05U/OD-05U2 blocker notes. Verify branch, clean/staged/untracked changes and actual HEAD, then preserve all existing data, secrets, environments and historical evidence. Never overwrite, reset, clean, stash, delete, edit private keys, or modify source rights, data, DBs or release/signing paths.

**Interpretation of user's direction:** User wants to actually evaluate the extensive *locally held* historical archive rather than declare it nonexistent. Their request is authorization to investigate its *existence, layout, metadata, source lineage and build safe diagnostics*. It is NOT an NSE data license, an authorization to scrape, or proof that commercial research/trading use is permitted. Do not change `PENDING_REVIEW` source policies or create a backdoor to `READ_CACHED`, `DERIVE`, `RESEARCH`, `TRADE_DECISION_USE` or `REDISTRIBUTE`.

## 1. What is already confirmed, not hypothetical

In the reviewed GitHub repository, the following actual versioned GitHub files exist **alongside their manifests** (local run must verify its own worktree; GitHub listing alone is not content validation):

| Layer | Day | Actual ZIP | GitHub-reported size | Manifest/source lead |
|---|---|---|---:|---|
| Phase-2 seed import | 2011-06-22 | `data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/year=2011/month=06/20110622__1eba7f9259b5.zip` | 53,301 | `cm22JUN2011bhav.csv.zip`; `seed://omega_phase2_repo/...` |
| Phase-2 seed import | 2020-01-02 | `data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/year=2020/month=01/20200102__b3cdc49a3f68.zip` | 69,955 | `cm02JAN2020bhav.csv.zip`; **legacy-style naming in 2020** |
| Versioned cache | 2024-07-23 | `data/raw/nse_equity_bhavcopy/year=2024/month=07/20240723__6e7b99b88b17.zip` | 165,041 | `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240723_F_0000.csv.zip` is a **manifest URL claim**, not independently proven origin |

OD-05T recorded **3,596 seed manifests + 30 versioned-cache manifests = 3,626 metadata records**, **zero market ZIP payloads opened and zero verified financial rows**. Prior broad OD-05S counted 3,676 manifests across more scope. These numbers must not be confused. The historical 2011 and 2020 seed manifests identify `source_repo_url` of `https://github.com/PrivateAccount-01/omega-system---phase-2` and `source_repo_relative_path` in `data/raw/bhavcopy/`. The Phase-2 source contains the named original ZIP files, and its `bhavcopy_ingestor.py` constructs an NSE historical EQUITIES archive URL. This is **cross-repository provenance evidence, not NSE receipt/permission**.

**P1 discrepancy:** The 2020-01-02 manifest claims original filename `cm02JAN2020bhav.csv.zip` while the Phase-1 source registry/acquisition uses a modern-era routing assumption from `2020-01-01` / `requested.year < 2020`. Freeze as `ERA_CONFLICT_2020_REFERENCE_PENDING`; do not silently replace the switch year with 2024 or silently reinterpret source format from a filename.

## 2. Mandatory decision-lane separation; no circular blockers

Build and report four separate lanes. **Never use one lane's approval to imply another.**

**Lane A, `LOCAL_FILE_DISCOVERY`** (start immediately, no market payload opening): enumerate the two named directories with `lstat`/directory entry metadata only. Match original ZIP file to its existing manifest and expected size, date, path, source claim, parent project relationship. Count `manifest_present`, `payload_path_exists`, `regular_file`, `size_matches_manifest`, `missing_payload`, `wrong_type`, `duplicate_candidate`, `symlink_or_reparse_refused`, `claim_format`, source mode and date. Flag ZIP existence *without* claiming checksum match or content validity. For the first three named files, produce exact read-only preflight rows in a machine-readable report. Avoid echoing absolute private paths, credentials, signed URLs or all raw lines. This is a new *payload-presence* extension, not another duplicate metadata-only counter.

**Lane B, `OFFLINE_PAYLOAD_INTEGRITY`** (conditional): read byte content, compute SHA-256, check header/magic, bound ZIP structure and compare internal member names ONLY after a scoped determination that this private local inspection is permitted for these files under applicable terms, and actual operator authorization has been recorded. If authorization/evidence is absent, implement the safe opt-in code and its security tests but do not execute it against market ZIP payloads. Record `NOT_EXECUTED_RIGHTS_PENDING`; do not suppress or downgrade source policy. A local SHA proves *consistency* with the manifest, not publisher authenticity, legal reuse, valid OHLC, session truth or point-in-time correctness.

**Lane C, `REAL_ROW_FINANCIAL_COMPARISON`** (conditional, only after permitted byte inspection): independently review original exchange-source rows and a historically applicable schema first. Freeze exact row ordinals, header/member identity, source date, series/ISIN/symbol, OHLC lexemes, decimal values, integer volume, units, real source provenance and reviewer/date. The independent reviewer must not use the candidate parser's output as the expected oracle. Run a versioned, opt-in decoder against that frozen real-row reference, report actual matches and mismatches, all critical columns, rejected rows and denominators. No fabricated expected values, no synthetic profit claims. Separate `INTERNAL_INDEPENDENT_ROW_REVIEW` (human review of source bytes) from `CROSS_PUBLISHER_AUTHENTICATED` (original publisher receipt/independent source).

**Lane D, `SOURCE_RIGHTS_AND_RELEASE`**: independent source-origin proof, historical source applicability, `READ_CACHED`, `RESEARCH`, `DERIVE`, `COMMERCIAL_PRODUCT` and distribution permissions are individually decided from actual applicable terms/agreement and by authorized humans. Keep all existing 13 policies unchanged in this phase, unless a separately approved exact-file rights update is supplied. No real trading, autonomous model training, release promotion or publication from unapproved data.

If B/C/D is blocked, **complete A, the relevant safe code, tests, executable CLI, and one concise factual blocker output**. Do not create a third nearly identical preflight with no new implementation.

## 3. Implement the missing functionality, scoped and reversible

Reuse `archive_candidate_inventory.py` and safe file-access code rather than introducing a new downloader or overriding the source-rights gate. Add a separate additive `src/omegadata/parsers/local_archive_presence.py` library and `scripts/audit_local_archive_presence.py` CLI (names can be adapted to repository naming conventions after audit).

1. `--source-key NSE_EQUITY_BHAVCOPY`, explicitly allowlisted roots `data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy/` and `data/raw/nse_equity_bhavcopy/`, no arbitrary filesystem roots, no network.
2. Accept existing independently frozen manifest metadata pins. Read only those pinned manifests (already permitted and verified by OD-05T), not market payload bytes. Resolve the *claimed* corresponding relative `artifact_path` safely, including Windows separators from manifests. Only perform `lstat`/size/type on the candidate payload, refusing symlinks, junctions/reparse points, hardlinks, path traversal, UNC, alternate streams, case aliases, nonregular files and forbidden parents.
3. `lstat` may identify archive existence. Avoid calling `read_bytes`, `open`, zipfile, memory-map, hash/file magic or reading byte streams in the default no-content lane. Do not inadvertently open payload through a helper or dependency. Negative security tests must prove zero payload read attempts.
4. All counts/gates explicit. Provide concise aggregate and separate first-three-candidate rows; no path leakage or raw data dump.
5. Add optional guarded `--payload-integrity` mode only as an independently authorized future execution path; it must invoke appropriate rights operation checks and fail closed if pending, absent, revoked, expired or unknown. No direct file-open bypass of `RawArchive` / source rights. Implement refusal tests now without executing data reads.
6. If the existing rights layer has no correct operation for independent file-presence `lstat`, **do not extend `READ_CACHED` permission implicitly**. This metadata-only scope must never expose market values.
7. `--dry-run` default; outputs only to fresh external disposable report directory, never to an existing `data/`, source, signing or archived evidence path.
8. Bounded: max 5,000 manifest pairs per root, directories max depth 12, explicit caps, per-file `lstat`, deterministic ordering, resource limits. Root confinement and refusal codes; no paid services, new packages or credentials.
9. Add a cross-repository lineage ledger that compares original names, path structures and repository Git blob IDs or file hashes only when such comparisons do not require unauthorized payload reads. Git blob metadata can show byte identity between two committed objects without reinterpreting their contents, but does not prove publisher origin. The evidence must state whether this check was actually run.
10. Build a quarantine-candidate matrix for 2011, 2019, January 2020, June/July 2024, 2025 and 2026 based on actual present files only. If date has no present archive, say `ABSENT_OR_UNCHECKED`; don't infer trading holiday or generate it.

## 4. Required proof-first test groups (minimum P01-P18)

Freeze and run negative tests before production-module authoring. No new synthetic market rows/prices are permitted; malformed file metadata and OS filesystem canaries are fine as engineering tests, clearly separated. `P01` real 2011 manifest+ZIP existence; `P02` real 2020 manifest+ZIP existence; `P03` real July 2024 ZIP existence; `P04` exact manifest/payload pair counts vs independent `os.scandir`/`lstat` oracle; `P05` missing payload; `P06` manifest says wrong size; `P07` wrong extension/regular-file type; `P08` path traversal, absolute/path escaping; `P09` symlink/reparse/junction/hardlink trap; `P10` wrong root, mixed exchange/feed; `P11` no payload bytes opened under default dry run (monkeypatch/audit-hook canary); `P12` `--payload-integrity` denied while rights pending, no byte read; `P13` permission or credential text redaction; `P14` duplicate dates/revisions/nonvacuous corpus; `P15` current 2020 era contradiction included and never auto-fixed; `P16` Phase-2 lineage cross-check (metadata/Git identity); `P17` deterministic reports across Windows/WSL, no protected writes; `P18` actual CLI invocation, exit codes, preserved original files.

On a real rights-cleared pack only, additional `Q01-Q12`: open/read bounded original ZIP; recompute actual SHA and length; inspect actual ZIP member names + CRC; compare timestamp/date; inspect actual header and schema; freeze independently reviewed real values; compare Decimal OHLC/quantity/identity/date/units; compare independent counts/revisions; output discrepancy vectors and real denominators; cross-run repeatability; no PIT eligibility if publication/observation time absent; preserve original. **Do not execute Q-cases against unauthorized market bytes** and do not create invented substitutes. Mark unavailable cases `NOT_EXECUTED_RIGHTS_PENDING` or `BLOCKED_REFERENCE`, not pytest PASS/SKIP success.

## 5. Source-era conflict investigation (important)

The Phase-1 `source_registry.py` and `acquisition.py` have January-2020 modern-mode assumptions, but the 2020-01-02 manifest and Phase-2 original file name are `cm02JAN2020bhav.csv.zip` (legacy-style). At minimum file-format policy cannot simply be chosen from calendar year. Produce an exact conflict record using metadata alone, and a separate *conditionally executable* real-file-header proof for when content inspection is authorized. Review official historical circular `NSE/MSD/62142` May 22 2024 annexures and subsequent 62424 changes; distinguish **document publication date**, **file delivery/format availability**, **format-specific change type**, **actual file date**, and **trading session**. Do not infer all NSE CM data switched formats 2020 or universally on a particular 2024 date. `ERA_CONFLICT_2020_REFERENCE_PENDING` stays until proven by authenticated material.

Do not change any production route, trade date, calendar, price, PIT, DB, parquet, loader, validator or backfill code in this phase.

## 6. Runtime and evidence expectations

Run code/test import, pre-code red (new API absent, not legacy defect), new module focused suite, full guarded `pytest -m 'not realdata'`, Ruff, strict mypy, pip check, compilation in disposable roots. On Windows Python 3.14 and 3.11, Linux Python 3.12 (WSL), pairing actual counterpart for privilege skips. Guard denies DNS/TCP/UDP, subprocess, credential/secret reads and protected writes; preserve old tests and evidence. Report exact commands, exit codes, run times, file hash identities, before/after preservation, and independent oracle comparison. WSL is same physical host, not independent hardware proof. No hidden test omissions or fabricated test totals.

**Real-data scorecard** must include separate columns:
- Candidate manifests enumerated; payloads present by `lstat`; bytes actually *read*; manifest-claimed vs filesystem actual length; missing/not regular; duplicate dates/revisions; raw SHA matches *only if executed*; ZIP structurally valid *only if inspected*; financial rows parsed/verified; publisher-origin state; permit-use state; real-field mismatches & coverage with non-null denominator only after genuine row validation.
- Engineering PASS never equals `REAL_FINANCIAL_PASS`; all 6 prior official reference gates remain blocked unless real evidence clears them. No synthetic financial observations count.

## 7. Exact Gatekeeper language and stopping behavior

Accepted when safe only:
- `OD05V_FILE_PRESENCE_TECHNICAL_PASS` if actual stat-level existence/correlation tests pass.
- `OD05V_FILE_PRESENCE_BLOCKED` if failed code or unable to inspect allowed paths.
- `PAYLOAD_INTEGRITY_NOT_RUN_RIGHTS_PENDING` whenever no applicable right to read files established.
- `REAL_ROW_VALIDATION_NOT_RUN_RIGHTS_PENDING` until content and reference authority supplied.
- `PUBLISHER_ORIGIN_UNVERIFIED` if there is no authentic original receipt, even if SHA matches.
- `FINANCIAL_CORRECTNESS_NOT_PROVEN` unless separately reviewed real source rows compare successfully.

No error in one lane is allowed to erase successful and honest progress in another lane. Keep existing rights policies pending; source permission must not be self-granted by Codex. Do not treat user's desire to inspect their archive as a publisher commercial license. Do not acquire, redistribute, train, trade, release, reconfigure production routing or start OD-06.

## 8. Nonnegotiable deliverables

1. Executable library and CLI for **actual payload-presence checks** (not a repeat manifest-only counter).
2. Negative-first tests P01-P18 and evidence files with exact input identities.
3. Precise `2011/2020/2024` sample matrix, and any additional actually present date groups.
4. Cross-repository Phase-2 lineage ledger and concrete 2020 source-era contradiction report.
5. Distinct engineering and financial Gatekeeper verdicts, actual runtime cross-platform matrix, preservation record.
6. One-page next owner action containing only the smallest genuine rights/provenance information needed for **the next, separately approved payload-byte inspection**, without another long prompt-loop and without asking the owner to hand-transcribe thousands of prices.
7. STOP. Do not commit/push/merge, modify data/old evidence/policies, or begin a later OD phase without user instruction.

## 9. Note on NSE rights: actionable, not invented

Official NSE market-data usage policy: `https://betanseapi.nseindia.com/static/market-data/nse-data-policy`; NSE EOD/historical subscription: `https://betanseapi.nseindia.com/static/market-data/eod-historical-data-subscription` (contact `marketdata@nse.co.in`). Academic **noncommercial** research program: `https://betanseapi.nseindia.com/static/research/initiatives-data-for-research` (`nseri@nse.co.in`). These have different purposes. Do not invent blanket personal/commercial permission or equate website accessibility with a data license. Owner can provide an actual existing agreement, permission or legally applicable basis for private local inspection. If absent, execute every safe Lane-A task now, leave B/C/D blocked, and do not pressure user to sign fictitious evidence.
