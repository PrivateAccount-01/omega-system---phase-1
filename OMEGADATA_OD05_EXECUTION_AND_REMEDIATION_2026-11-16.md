# OmegaData OD-05: Owner Gate Closure, Historical Format Contracts and Offline Parser Implementation

**Type:** Strict, repository-specific Codex implementation contract  
**Repository:** `https://github.com/PrivateAccount-01/omega-system---phase-1`  
**Expected branch:** `feature/od01-source-rights`  
**Inspected latest commit:** `98e2a4b656e8f9b81ad5600658981b65750e9645`  
**Preceding reviewed implementation:** `bbc38716d902fe27192f80affaca29c6f51e9890`  
**Latest commit message:** `docs: record gated OD05 source-era audit and implementation plan`  
**Permitted phase:** **OD05-GATE-CLOSURE, then OD05-SYNTHETIC-PARSER-IMPLEMENTATION ONLY if independently authorized**.  
**Date:** 2026-11-16. Recheck live HEAD before every edit.  
**Historical evidence:** OD04R technical re-verification successful; process exception still pending; OD05 audit/plan complete; no OD05 tests or parser implementation yet.

> This contract does **not** itself accept the historical OD-04 process exception, approve market-source rights, authorize a production deployment, or make a legal determination. A Code agent **must not impersonate a human project owner**, invent a decision record, or treat this file's existence as permission. If the required human owner decision and implementation authorization are absent, execute the read-only gate-closure inventory and **STOP**, stating exactly what the owner must supply. If those independent gates are valid, proceed through the bounded offline synthetic parser implementation without asking redundant questions.

## 0. Mandatory operating rules, identity, and preservation

Read, completely and in this order:

1. `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`.
2. `docs/verification/OMEGADATA_OD05_CODEX_MASTER_PROMPT_2026-11-16.md` and `docs/omegadata_v2/implementation/od05/20261115T190654Z/` reports `00` through `11`, plus `reference_registry.json` and `logs/final-qa.json`.
3. The old OD04 Gatekeeper: `docs/omegadata_v2/implementation/od04/20261115T124835Z/09_gatekeeper_verdict.md`.
4. The OD04R Gatekeeper, exception request, independent byte oracle and final acceptance under `docs/omegadata_v2/implementation/od04r/20261115T181120Z/`.
5. `docs/omegadata_v2/plan/09_implementation_phase_plan.md`, especially OD05; the architecture proposal, source-rights audit, reuse matrix and prioritized defects (including D-01, D-02, D-03, D-04, D-08, D-09).
6. Actual current `src/omegadata/track_a/{source_registry,source_rights,acquisition,download_manager,raw_archive}.py`, `src/omegadata/pipelines/sequential_pipeline.py`, `tests/unit/test_od02_acquisition.py`, `tests/unit/test_od04_raw_archive.py`, `tests/unit/test_od04r_adversarial.py`, relevant seed/fixture definitions and direct backfill/probe scripts.

Perform first: `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff --name-status`, `git diff --cached --name-status`, `git merge-base main HEAD`, and inspect `git log -6 --format=fuller`. If HEAD is no longer `98e2a4b656e8f9b81ad5600658981b65750e9645`, inspect the intervening changes. STOP application edits until prior evidence and permitted scope have been reconciled to the new HEAD. Do not stash, reset, clean, force, checkout over user work, rebase, or rewrite Git history. Preserve any existing untracked content and any user edits.

**Non-negotiable exclusions:** no actual market-data requests (including exchange archives, historical bhavcopy endpoints, browser/curl/API/source probes); no installation from untrusted URLs, paid services, or provider credentials; no changes to actual source-rights records (all 13 remain `PENDING_REVIEW`); no production database or SQL/Parquet writes; no changing existing archive object bytes, stored observation/commit schema, legacy data, official-labeled fixtures, trading calendar, corporate actions, universe, release/readiness/promotion, signing, GPG/private keys, warehouse, broker/trading controls or CI. **No commit, push, PR, merge, or deployment without separate instruction.** Keep live egress disabled. Do not open/hash/copy private signing material to prove preservation; metadata-only permitted when existing guard requires it.

Do not copy old test results into a fresh report and label them `RUN`. Use evidence labels: `RUN` actual new execution; `TEST/SYN` synthetic offline fixtures; `ARCH` earlier recorded evidence; `REF-DOC` externally sourced publication reference but not proof of schema/row truth; `UNK` unknown; `CLAIM` assertion not reproduced. Maintain honest filenames, timestamps, versions, command exits, and exact source/test hashes.

## 1. Unambiguous entry-gate sequence

### Gate G0: authentic owner disposition of OD-04's historical process deviation

The original OD04 Gatekeeper was `OD04_BLOCKED` because its entire A01–A28 negative-first suite was not executed before implementation. OD04R separately reverified the implementation, but its latest verdict was `OD04R_TECHNICALLY_REVERIFIED_PROCESS_EXCEPTION_PENDING`. The latest OD05 audit located no human ACCEPT_EXCEPTION decision. These facts must remain in historical evidence, never backdated or edited.

Read the owner-supplied decision stored or passed via an authenticated project-owner channel. The decision must explicitly identify:

- Decision `ACCEPT_EXCEPTION` or `REJECT_EXCEPTION`, human author/role, actual decision date/time, and how owner authority was established.
- The exact OD04 implementation commit `44090a42958869faaab57a42b65f7ad8571d924d`, OD04R remediation commit `bbc38716d902fe27192f80affaca29c6f51e9890`, OD04R run `20261115T181120Z`, and the corresponding reviewed source/evidence hashes or verifiable manifest.
- Acknowledgment that the original test-ordering rule was violated; that independent OS power-loss, remote-filesystem, malicious directory-ownership, legal rights, source authenticity, trusted key custody and release controls remain uncertified.
- Specific rationale and limits: accepting the process **exception only**, not declaring historical tests pre-implementation, not certifying any financial data, legal right or production readiness.

Do not create, pre-fill, approve, sign, or impersonate an owner decision. A blank template, an agent-authored JSON, a commit by the agent, a previous Codex prompt or this instruction is NOT a human decision. If absent, invalid or rejected, record `OD05_GATE_BLOCKED_OWNER_DECISION`, allow only read-only review/documentation, and STOP. An agent may document the condition but cannot grant the exception.

### Gate G1: separate owner authorization to implement OD05

Look for an explicit, independently issued project-owner instruction such as `AUTHORIZE_OD05_SYNTHETIC_PARSER_IMPLEMENTATION` that references the current repository/branch/HEAD, the accepted exception and the exact offline scope in this file. Do **not** infer implementation authorization from the owner's process-exception decision or from a generic request to generate prompts. If missing, status `OD05_GATE_BLOCKED_AUTHORIZATION`; STOP before code/tests/fixtures. On rejection, STOP.

### Gate G2: reference and corpus scope

Build two distinct tracks:

- **Track SYN, executable with approved authorization:** Synthetic NSE cash-equity parser reference profiles. The test producer and independent expected-row oracle are separately authored, hashed and frozen. Their status remains `SYNTHETIC_TEST_ONLY`, or after parse, `PARSED_UNVERIFIED`. These tests prove software behavior for specified contracts only.
- **Track REF, independently gated:** Human-reviewed, lawfully accessible official format documents, exact publisher/date/format version, original publication/document SHA, human reference-use permission and representative lawful raw data with trusted expected row mapping. Without all necessary evidence, mark `SOURCE_REFERENCE_PENDING` and do not count these cases as official-certified successes. No agent may set `OFFICIAL_REFERENCE_VERIFIED` merely from its own interpretation of a webpage or filename.

The absence of Track REF **must not force the agent to pretend it is complete**. Once G0/G1 permit Track SYN, build the pure testable interface and run synthetic cases, but explicitly mark REF-dependent cases `BLOCKED_REFERENCE`. Do not change live source routing or trusted official-format classifications in this partial run. Any change to legacy production-era routes requires a subsequent verified reference gate and separate narrow authorization.

## 2. First priority: historical NSE CM cutover ambiguity

Current code selects modern NSE CM from `2020-01-01` in `source_registry.py` (`2019_present`) and `acquisition.py` (`requested.year < 2020` for legacy). Existing tests prove only synthetic 2019 and 2026 examples, not official 2020–2024 acceptance.

NSE's current official **All Reports** webpage `https://www.nseindia.com/all-reports/` records discontinuation of older `CM - Bhavcopy(csv)` and `CM - Common Bhavcopy(csv)` products effective `2024-07-08`, citing circular no. `62424`, `2024-06-12`; it names the `CM-UDiFF Common Bhavcopy Final(zip)` successor. This is documentation-level evidence of a 2024 transition. It **does not establish** earliest simultaneous file availability, complete historical format compatibility, original row-level semantics, exact BSE formats or source use permission. A separately indexed copy of NSE/MSD/62424 mentions revised UDiFF release date `2024-06-24` and old/new parallel dissemination through `2024-07-05`; do not treat those as fully authenticated row-spec evidence absent direct verified permitted reference material. Do not equate a publication notice with trade-session proof.

Construct a `source_era_evidence_matrix.md` that distinguishes each **format ID** from publication/discontinuation date, market business date, URL route, member name, field list, semantic date fields, permitted sample/reference, and reference confidence. Include four specific boundaries: 2019-12-31/2020-01-01; 2024-06-24; 2024-07-05; 2024-07-08 and neighboring independently confirmed market sessions. Unknown/overlap states must explicitly exist. Do not globally substitute `2024` for `2020` in current code. Never silently relabel legacy fixture values as valid official UDiFF data.

Also audit duplicated era logic in backfill and probe scripts, preserving all direct diagnostics as-is until separately authorized. Distinguish `TRADDT` and `BIZDT` rather than assuming they always equal the requested business date; require real schema evidence before a certified rule. Check modern row identity and series conventions; prevent unverified collapse of different series into a single instrument. Do not modify `PriceRecord` or make the parser perform corporate-action adjustments.

## 3. Frozen contract before tests or code

Design a pure offline parser package under `src/omegadata/parsers/`, using existing stdlib `csv`, `zipfile`, `hashlib`, `datetime`, `decimal` and existing frozen Pydantic patterns. Do not add `pandera`/Arrow or any dependency without measured same-corpus gain, license/runtime/security evaluation, and separate approval. Compare existing stdlib+Pydantic versus Pandera and existing PyArrow in a decision table. Default is `EXTEND_EXISTING` unless independent evidence changes that choice. Pin upstream tag/commit only when verified; do not invent versions or benchmark results.

Freeze these public contracts (names can be adapted to code style, semantics must match):

`ParseRequest`: source_key, requested_business_date, exact_raw_sha256, format_id, parser_version, reference_id/version, observation_id optional, source_mode with explicit SYN designation, optional expected_record_count independently pinned; no implicit latest or date-based unverified promotion.

`ParsedBar`: source_key/exchange/date, original symbol, series optional, ISIN optional, exchange scrip code optional as STRING, source row index, Decimal OHLC, nonnegative exact integer volume, original price lexemes, preserved inert unknown fields, units and source identity. Explicit row identity rule per format; no inferred ISIN or silent series collapse.

`ParseResult`: `PARSED_UNVERIFIED` or `QUARANTINED` unless independently authenticated source reference capability is granted later; frozen rows/quarantine records, full raw SHA, source format, parser/spec versions, evidence/reason codes, semantic hash and source-column manifest. Never encode unverified source terms as `FINANCIALLY_RECONCILED` or `OFFICIAL`.

`ParserError` taxonomy: `ERA_UNKNOWN`, `REFERENCE_PENDING`, `FORMAT_UNSUPPORTED`, `RAW_HASH_MISMATCH`, `ZIP_INVALID`, `ZIP_UNSAFE`, `ZIP_BUDGET`, `CSV_INVALID`, `HEADER_DUPLICATE`, `HEADER_MISSING`, `DATE_MISMATCH`, `ROW_INVALID`, `PRICE_INVALID`, `VOLUME_INVALID`, `IDENTITY_AMBIGUOUS`, `SOURCE_SCOPE_DENIED`, `VERSION_UNSUPPORTED`, `INTEGRITY`, `INTERNAL_PARSER_ERROR`. Public errors include bounded row/field metadata only; no payload, URL tokens or financial raw strings.

Invariants:

- Input hash computed from **original exact bytes** before decoding. Only explicit source+format+parser+reference selection; inferred year, member suffix or header alone cannot grant official trust.
- ZIP: at most one expected member or explicitly documented multi-member rule; reject duplicates, nested archives, traversal, symlinks, encrypted/bomb/malformed entries, unsupported codecs and decompression/row/size ceiling violations. No extracting to existing datasets.
- Strict decoding and CSV lexical correctness; duplicate/case-normalized header collisions, malformed quoting, extra fields, truncated rows, non-finite numeric lexemes, unsupported time formats and unchecked aliases cause typed refusal.
- Exact `Decimal` parsing without float roundtrips; preserve input lexeme separately; bounded exponent/precision and meaningful maximums; distinct series/ISIN/scrip identity; legitimate zero volume allowed where synthetic profile permits it; prices nonnegative and consistent OHLC.
- `business_date`, actual market trade date, source publication time, first observation time and ingestion time are different concepts. Unknown `published_at` remains NULL; never infer PIT availability from file contents or parser success.
- A file with one invalid critical record must not return trusted partial success; quarantine/refusal must be explicit, deterministic, reproducible, and no source/DB/release writes.
- Canonical semantic digest is stable across OS locale, line endings only where format permits normalization, ZIP metadata that should be excluded, and operational clock. Raw SHA must still distinguish changed original bytes. Unknown source columns survive as inert data/manifest, never usable as strategy features automatically.
- Access to existing archive through `RawArchive.read_verified` must remain rights-aware with pinned observation ID and read purpose, and never change PENDING/REVOKED status. Synthetic in-memory entrypoints must be visibly separate from protected archive reads.

## 4. Entire negative-first test matrix: 32 groups

Author `tests/unit/test_od05_era_parsing.py`, auxiliary disposable synthetic factories and a completely separate independent expected-row oracle **before editing any application module**. Freeze a hash of each test file, exact fixture byte SHA, G0/G1 evidence and test expectation. Execute old-code baseline; distinguish: (a) genuine old-behavior assertion failure; (b) missing new API; (c) reference/corpus blocker; (d) bad test/harness. A missing import is NOT a proved old-system failure. Retain exact red evidence without timestamps invented or older tests altered.

Group design and test ID requirements:

- **T01–T03:** input identity and version pinning, deterministic semantic hashes, same-date separate raw bytes and no previous-version overwrite.
- **T04–T07:** separate 2019 synthetic legacy, disputed 2020 dates, 2024 June/July transition and 2026 synthetic UDiFF profiles; cases that require real official format semantics remain `BLOCKED_REFERENCE`, never green by synthetic substitution.
- **T08–T10:** unknown/ambiguous format quarantine, BSE format pending/no masquerade, forged `OFFICIAL` flag refusal.
- **T11–T14:** duplicate/missing headers and aliases, malformed quoted CSV, ZIP traversal/bomb/duplicate/partial, HTML/JSON login/error denial.
- **T15–T18:** strict date field semantics, exact finite Decimal OHLC, legitimate zero volume, signed/overflow/noninteger volume failures, no floats.
- **T19–T22:** row identity and separate series, leading-zero exchange/scrip identities, missing ISIN/series handling, published-vs-known time separation.
- **T23–T26:** wrong full SHA and source observation refusal, synthetic/cache/seed origin non-escalation, rights-revocation refusal, no filesystem/DB/Parquet/release/policy writes on every failure.
- **T27–T30:** deterministic oracle and parsing versions, legacy adapter default OFF, platform/line-ending/path/locale behavior, strict row/byte/archive/CPU resource bounds.
- **T31–T32:** independent numerical and row-field oracle, all three runtime full suites plus Ruff/mypy/pip/coverage/security regression and exact skip pairing.

For **every** T01–T32 record: test IDs, fixture, reference classification, old-code result, new-code result, exact argv/cwd/python/OS/UTC/exit, evidence link, skipped/deselected/blocked counts and whether the test is synthetic or authentic. If a T04/T05/T06/T07/T09/T15/T19/T21/T31 reference-dependent subcase lacks a legally obtained publisher row/spec, mark that subcase `BLOCKED_REFERENCE` while still running its explicitly synthetic analogue. **Do not declare 32 full passes when authoritative cases are absent.** A separate `OD05_SYNTHETIC_TECHNICAL_PASS` gate is possible with all in-scope synthetic cases green and official cases clearly not certified.

The independent comparator must NOT import or call the parser to derive expected values. Use a separately frozen literal fixture, independent scaled-integer calculations for price/volume, source-row numbers and identities, and independently pinned expected semantic hashes. Missing, moved, corrupt or empty expected corpus fails non-vacuously. Distinguish CSV data-record index from physical line number (quoted newlines). All expected legacy/current semantics in synthetic examples are explicitly *assumed contracts*, not independently verified official NSE columns.

## 5. Exact implementation scope after gate, and no more

Allowed new files, if G0/G1 pass:

- `src/omegadata/parsers/__init__.py`
- `src/omegadata/parsers/contracts.py`
- `src/omegadata/parsers/dispatch.py`
- `src/omegadata/parsers/nse_cm.py`
- `src/omegadata/parsers/reference_registry.py` (read-only/provenance validation, no approval authority)
- `tests/unit/test_od05_era_parsing.py` and newly named synthetic/independent-oracle test helpers
- `docs/omegadata_v2/implementation/od05_impl/<UTC-run-id>/` fresh reports/logs only
- `docs/omegadata_v2/decisions/od05_parser_contract.md` additive architecture decision

**Not allowed by default:** edits to `source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `sequential_pipeline.py`, `storage.py`, `models.py`, old tests, existing reference registry, official-labeled fixture data, release manager, signing, existing source policies or backfill scripts. An integration mutation requires a genuine reproduced defect, independently proven reference semantics and a **separate exact-file scope amendment** from the owner; the synthetic-only implementation is intentionally default OFF and produces no production data.

Implementation sequence:

1. Verify G0 owner record, G1 separate implementation authority and G2 corpus classifications; record approved exact code/test paths, input hashes, resource ceilings, no extra permissions.
2. Freeze pure data schema and all 32 case groups before application edits; run old-code baseline and negative assertions in isolated runners. Freeze SHA ledger.
3. Implement a pure, side-effect-free parser for authorized **synthetic** NSE CM profiles, with explicit `format_id` and `parser_version`; reject unsupported BSE, ambiguous 2020 formats, and official-state escalation. Reuse existing validators only where their assumptions are independently understood; never silently inherit the unproven 2020 year dispatch.
4. Compare every output to the separate independent oracle; fix reproduced defects with new negative-first cases **before** corresponding corrections. Retain honest chronology if new tests added after original first implementation.
5. Execute isolated integration: acquire bytes only through mock adapters or pinned rights-authorized local archive fixtures. Assert zero external egress, zero protected file writes and all policy REFUSAL paths.
6. Re-run complete applicable existing unit/integration tests, including OD01 rights, OD02 acquisition, OD02V portability, OD04 archive and OD04R verifier, alongside new OD05 tests. Record actual skip/selected counts rather than assume old totals.
7. Run Ruff, strict mypy, pip check and module compilation. Capture available branch coverage, no suppression. Prefer matrix Windows Python3.14 / Windows3.11 / native Linux3.12 on isolated directories; if a runtime unavailable, Gatekeeper records `BLOCKED_PLATFORM`, not fake success. Guard test collection and execution from DNS, TCP, UDP, subprocess and writes to original paths.
8. Independently audit output hashes, archives, permissions, no-mutation invariants, source provenance, test timestamps, source-file identity and cross-runtime result equality. Retain all prior red/failing commands and new attempts.
9. Issue a narrow Gatekeeper verdict, stop. Do NOT begin OD06 or migrate the old current-state DB.

No supply-chain adoption by default. A planning comparison of Pandera and PyArrow is not permission to add or install them. If no third-party reuse is necessary, record `EXTEND_EXISTING` and show reproducible correctness and measured execution costs before claiming an improvement.

## 6. Output/evidence package: exactly specified

Create, only within permitted fresh directories and only after G0/G1, the following documents. If blocked at gate, create only a new gate inventory/decision-check report, no implementation/test artifacts:

- `00_identity_and_authorizations.md`: verified SHA/branch, human owner decision reference, separate implementation approval, rights/reference scopes, protected paths.
- `01_official_reference_gap_and_cutover.md`: NSE circular/page notice vs exact record evidence, dates and overlap uncertainty, BSE exclusions, semantic blocked cases.
- `02_parser_contract_and_reuse_adr.md`: source/format/parser/reference/version interfaces; exact Decimal semantics; reuse decision, dependency/license/pin proof and unmeasured claims.
- `03_preimplementation_test_matrix.md`: T01–T32, frozen before code, test/fixture hashes, executable red/blocked distinction and actual run chronology.
- `04_code_delta_and_compatibility.md`: every changed file and why; user/pre-existing file preservation; default-OFF behavior, rollback.
- `05_independent_numeric_oracle.md`: separate expected-row source, literal reference vectors, scaled integer lexemes, new measured output comparison.
- `06_security_rights_pit_review.md`: hostile inputs, no-mutation tests, approved synthetic vs pending/blocked official data, publication-time unknowns.
- `07_cross_platform_regression.md`: exact commands/exit codes/skip/coverage/warning and source hashes for every runtime attempted.
- `08_defects_unknowns_and_rollback.md`: all open inherited P0/P1 (private signing custody, release-promotion bypass, temporal corrections, fixed Parquet overwrite) with owners; no silent waivers.
- `09_gatekeeper_verdict.md`: a single honest technical verdict.
- `10_next_phase_request.md`: **one** requested next action, and stop.
- `reference_registry.json`: immutable prior metadata copied by reference, separate newly evidenced documents with provenance; never mutate prior audit records.
- `logs/`: immutable per-command JSON + raw stdout/stderr, evidence hashes, preservation before/after, test/oracle inputs/outputs, blockers and expected errors; no secrets or unapproved data.

Per-command evidence: `{command, python, OS, cwd, start_utc, end_utc, duration_seconds, exit_code, stdout_path, stderr_path, source_sha256, test_sha256, fixture_sha256, test_results, skip_reasons}`. Never claim equal coverage across interpreters unless actually measured. Retain current pending-source counts and actual origin metadata in Gatekeeper.

## 7. Gatekeeper outcomes and stop criteria

Possible outcomes, not merely success/failure:

- `OD05_GATE_BLOCKED_OWNER_DECISION`: no independently human-issued G0 acceptance, or rejection. STOP before code/tests.
- `OD05_GATE_BLOCKED_AUTHORIZATION`: no separate G1 implementation approval. STOP.
- `OD05_DESIGN_ONLY_REFERENCE_PENDING`: authorizes only reference/design planning, no source format certification or production routing.
- `OD05_SYNTHETIC_TECHNICAL_PASS_REFERENCE_PENDING`: source/test hashes and all in-scope synthetic contracts verified; all external semantic claims explicitly BLOCKED_REFERENCE; no official-data certification or consumer rollout.
- `OD05_BLOCKED_TESTS`: negative-first chronology not followed, any unexecuted critical synthetic test, uncontrolled writes or failing new/old regression.
- `OD05_BLOCKED_SECURITY`: policy bypass, unapproved network, source mode escalation, secret leak, mutable archive or unreviewed production file changed.
- `OD05_BLOCKED_PLATFORM`: required OS/runtime gate not executed (or native symlink analogue absent without paired proof).
- `OD05_FULL_REFERENCE_TECHNICAL_PASS`: ONLY if independent official document and representative rows, rights and every mandatory reference-dependent group have been checked and verified by approved reviewers. Never infer from synthetic results or official-page snippets. Still not signing/release/live-production approval.

Stop immediately if initial branch unexpectedly changes, owner authorization fails, no safe disposable test root, source reference rights are inadequate for the attempted action, output would mutate historical data, critical numeric/reference mismatches remain, previous tests weakened, or exact evidence cannot be preserved. **Always stop after OD05**. No OD06, OD10, OD11, OD14, merge, signing, live source request or downstream quant feature work follows automatically.

## 8. Required final message to project owner

Use the following exact structure:

```
REPO:
BRANCH:
START HEAD:
FINAL LOCAL HEAD:
OWNER OD04 EXCEPTION: [accepted/rejected/not supplied; exact human record]
OD05 AUTHORIZATION: [approved/not supplied; exact source]
REFERENCE STATUS: [source/document IDs, confirmed boundaries, missing data/rights]
IMPLEMENTED FILES:
INTENTIONALLY UNCHANGED FILES:
TEST CHRONOLOGY: [pre-code vs post-code, actual red and blocked classes]
TESTS BY OS/PYTHON: [passed/failed/skipped/deselected, true exit codes]
INDEPENDENT ORACLE:
CURRENT RIGHTS COUNT:
EXTERNAL EGRESS:
RAW DATA / RELEASE / SIGNER MUTATIONS:
DEFECTS OPEN:
GATEKEEPER VERDICT:
SINGLE NEXT OWNER ACTION:
```

Do not report a blank human approval as valid. Do not silently switch to building a different repository. Do not call old historical green reports new OD05 results. The goal is to stop at an honest, reproducible, auditable boundary while making maximal progress that is genuinely permitted.
