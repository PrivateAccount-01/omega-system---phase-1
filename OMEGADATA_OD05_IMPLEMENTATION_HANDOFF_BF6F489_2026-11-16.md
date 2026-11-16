# OmegaData 2.0 — OD-05 Implementation Handoff (Exact Next Codex Prompt)

**Document ID:** OD05-CODEX-HANDOFF-BF6F489  
**Prepared:** 2026-11-16  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Feature branch:** `feature/od01-source-rights`  
**Reviewed HEAD:** `bf6f4894c9e5237e8c1a44b625c66b8a420b4aad`  
**Last implementation:** OD-04R technical verification at `bbc38716d902fe27192f80affaca29c6f51e9890`  
**Required human decision references:** OD-04 implementation `44090a42958869faaab57a42b65f7ad8571d924d`, OD-04R `bbc38716d902fe27192f80affaca29c6f51e9890`, OD-04R run `20261115T181120Z`.  
**Mode:** `OWNER_DISPOSITION_THEN_OD05_SYNTHETIC_ONLY`, with no implicit exception, no automatic later phase.

---

## 0. Non-negotiable: stop making report-only commits

The latest `bf6f489` commit **adds two Markdown documents only**:

1. `OMEGADATA_OD05_EXECUTION_AND_REMEDIATION_2026-11-16.md`.
2. `docs/omegadata_v2/implementation/od05_impl/20261115T194705Z/00_gate_inventory_and_decision_check.md`.

It **does not implement** OD-05, add executable OD-05 tests, repair source-era routing, obtain real-source permissions, or resolve the OD-04 owner exception. The prior `98e2a4b` OD-05 commit was likewise audit/plan-only. These are genuine states, not invitations to regenerate essentially identical reports indefinitely.

**Your first action:** inspect the current user task and any owner-authored authorization presented with it. If human disposition G0 or explicit implementation authorization G1 is missing, **STOP WITHOUT CREATING NEW FILES, COMMITS, OR DUPLICATE AUDIT REPORTS**. Respond in the terminal with exactly which user-supplied decision/authorization is absent and the existing link to the owner decision request. Never write an `ACCEPT_EXCEPTION` yourself, insert a human name, backdate a test, fill an owner template, or infer acceptance from the user's desire for progress or from this document being committed.

**If and only if G0 and G1 are genuine and separately explicit**, proceed to the authorized implementation sequence below. An actual project owner may provide both as two distinct, clearly labeled authorizations in the same direct instruction, but Codex must not author either clause itself. G0 accepts only the historical process deviation; G1 authorizes only synthetic-only OD-05 implementation. Neither certifies exchange rights, schema correctness, live acquisition, production datasets or releases.

## 1. Owner gate contract (G0/G1/G2)

- **G0, historical process exception:** Obtain a genuine decision by the accountable human owner: `ACCEPT_EXCEPTION` or `REJECT_EXCEPTION`, referring to the OD-04 Gate-2 ordering deviation, exact OD-04/OD-04R SHA and run IDs above, current reviewed source/evidence ledger, acknowledged residual risks and a real date/time. The original Gatekeeper `OD04_BLOCKED` must remain immutable. `REJECT_EXCEPTION` means stop OD-05. Missing/invalid decision also means stop.
- **G1, explicit implementation authorization:** Obtain a separately stated owner directive: `AUTHORIZE_OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY`, identifying this feature branch, approved SHA or reconciled successor, exact new file scope, offline synthetic-only data, preserved source rights, and permission to run safe disposable tests. A G0 acceptance alone does not supply G1.
- **G2, reference permission and classification:** The absence of an authenticated exchange-format corpus does **not** prevent an explicitly G1-authorized *synthetic-only* parser vertical slice. It **does** block `OFFICIAL_REFERENCE_VERIFIED`, real NSE/BSE historical-era certification, changes to production `source_registry.py`/`acquisition.py`, and any actual provider access. Keep `SOURCE_REFERENCE_PENDING` for unverified formats. Source-policy register must remain 13 `PENDING_REVIEW`, zero `APPROVED` unless separately changed through a real rights-owner process outside this phase.

If G0/G1 is missing, stop immediately; do not perform another wide audit. If the user asks solely for a gate report, provide the concise textual missing-gate answer rather than a new repository documentation tree.

## 2. Required read set and baseline

Before edits, read and honor:

- Root `AGENTS.md` and `OMEGADATA_AGENTS.md`; controlling `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`.
- OD-00 architecture and defect register: `docs/omegadata_v2/audit/08_prioritized_defects.md`, `docs/omegadata_v2/plan/09_implementation_phase_plan.md` (OD-05), and `docs/omegadata_v2/plan/10_architecture_and_contract_proposal.md`.
- OD-04's original blocked Gatekeeper, OD-04R's technical Gatekeeper and owner request, and their **current evidence hashes**, not merely their conclusions.
- Existing OD-05 planning dossier under `docs/omegadata_v2/implementation/od05/20261115T190654Z/` and last blocked gate inspection under `docs/omegadata_v2/implementation/od05_impl/20261115T194705Z/`.
- Existing `src/omegadata/track_a/{source_registry.py,acquisition.py,download_manager.py,raw_archive.py,source_rights.py}`, `src/omegadata/pipelines/sequential_pipeline.py`, historical scripts, and tests in `tests/unit/`.
- `pyproject.toml`, actual working tree/index and user-owned untracked files. Check the current feature HEAD against `bf6f4894c9e5237e8c1a44b625c66b8a420b4aad` before a single implementation edit. If different, compare the diff with this scope and get reconciliation rather than overwrite new work.

**Preserve everything:** historical raw/seed/cache/archive files, existing DBs, signed releases and pointers, untracked development environments, private signing artifacts (do not open or hash them), policy files, prior evidence and user edits. Do not `reset --hard`, `git clean`, `stash` user work, auto-delete, rewrite Git history, or write to canonical output folders. Do not commit, push, merge, create a PR, edit workflows, install packages, or switch branches without separate permission.

## 3. Precise build target

Deliver **one new, default-OFF, pure and versioned NSE cash-equity parser** that is testable entirely with synthetic bytes and explicit, non-authoritative format profiles. Its result is `PARSED_UNVERIFIED` or `QUARANTINED`, never an officially authenticated data release. Existing production ingest, broker access, raw archive, SQL and Parquet writes must behave exactly as before by default.

Expected new package (adjust names only with evidence and documentation):

```text
src/omegadata/parsers/
    __init__.py
    contracts.py                # frozen models, typed reasons, no DB
    dispatch.py                 # explicit format/ref/version choice
    nse_cm.py                   # strict bounded synthetic NSE-CM parser
    reference_registry.py      # read-only evidence classifications

tests/unit/test_od05_era_parsing.py
# New synthetic factories and independent oracle files within tests, as needed.
docs/omegadata_v2/implementation/od05_impl/<NEW_UTC_RUN_ID>/
```

Existing code can be read but not edited by default: `source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `sequential_pipeline.py`, `track_a/storage.py`, database ORM, current tests, current fixtures, policy, release, signing or CI. If you believe any existing file requires a change, **demonstrate a real failing integration test on existing behavior and obtain a separate exact-file scope amendment before editing**. A new missing API/import is a planned feature, not an old-code defect.

No requirements/dependency change. Prefer Python standard `csv`, `zipfile`, `hashlib`, `datetime`, `decimal` and existing Pydantic patterns. Record Pandera and PyArrow as `DEFER` unless a reproducible, license-checked same-corpus experiment and explicit approval justify adoption. Do not invent upstream pins, benchmarks or security clearance.

## 4. Actual source-era problem: preserve uncertainty

The current `source_registry.py` selects modern NSE cash-equity format starting `2020-01-01` (`2019_present`) and `acquisition.py` uses `requested.year < 2020` as a legacy cutoff. The prior OD-05 research dossier cites an official NSE page announcing withdrawal of older CM bhavcopies and the UDiFF final ZIP transition effective `2024-07-08`, with circular 62424 dated `2024-06-12`. These statements are **not** sufficient proof of the full 2020–2024 historical format timeline, simultaneous delivery periods, complete sample schema, exact member names, calendar sessions, or legally reusable row data.

Therefore:

1. Treat the `2020-01-01` boundary as `UNVERIFIED_ROUTING_ASSUMPTION`, not an accepted financial fact.
2. Treat `2024-07-08` as a **documented discontinuation/transition lead**, not blanket evidence that UDiFF did not exist earlier. Record June 24 and July 5 as candidate overlap/transition milestones, not authenticated parser contracts.
3. Do **not** replace 2020 with 2024 globally. Do not edit the original registry, backfill scripts, existing dataset labels or historical raw bytes in this phase.
4. Test synthetic `legacy-illustrative`, `udiff-illustrative`, `unknown`, `ambiguous` profiles with **explicit format IDs**, synthetic profile labels and versioned parsers; format IDs alone never confer official trust.
5. Reject unknown or disputed source/date/profile combinations unless a separately approved reference contract proves them. Never infer an official format solely from a filename, year, header aliases or a user-provided `official=true` flag.
6. BSE reference formats, F&O, indices, corporate actions, ISIN temporal identity, PIT universe, calibrated exchange calendars, and financial adjustments are out of this implementation scope.
7. Actual publisher schema/row verification remains a later OD-05 reference-completion subgate requiring lawful source documents with provenance and independent field-by-field review.

## 5. Type-level contracts

Use frozen validated contracts or equivalent types:

- `ParseRequest`: exact `source_key`, `requested_business_date`, full `raw_sha256`, `source_mode`, `format_id`, `parser_version`, `reference_id`, optional pinned raw `observation_id`, optional independently pinned row count. Explicit `SYNTHETIC_TEST_ONLY`; no implicit wall-clock or latest pointer.
- `ParsedBar`: source, exchange, source record ordinal, market trade date if actually supplied, original case-preserved symbol, optional series/ISIN/exchange scrip code as TEXT, original numeric lexemes, exact `Decimal` O/H/L/C and integer volume, inert unknown columns, schema/format lineage. Preserve leading zeros and distinguish series. No inferred ISIN or adjusted prices.
- `ParseResult`: explicit `PARSED_UNVERIFIED` or `QUARANTINED`, immutable rows and quarantines, input SHA, parser/format/reference versions, original field manifest, deterministic semantic digest, concrete reason code(s).
- `ParserError`: stable reason codes `ERA_UNKNOWN`, `REFERENCE_PENDING`, `FORMAT_UNSUPPORTED`, `RAW_HASH_MISMATCH`, `ZIP_INVALID`, `ZIP_UNSAFE`, `ZIP_BUDGET`, `CSV_INVALID`, `HEADER_DUPLICATE`, `HEADER_MISSING`, `DATE_MISMATCH`, `ROW_INVALID`, `PRICE_INVALID`, `VOLUME_INVALID`, `IDENTITY_AMBIGUOUS`, `SOURCE_SCOPE_DENIED`, `VERSION_UNSUPPORTED`, `INTEGRITY`, `INTERNAL_PARSER_ERROR`. Public errors must never contain raw confidential bytes, tokens or arbitrary payload excerpts.

**Hash semantics:** SHA-256 identifies *original bytes* before decoding. Semantic digest identifies the explicit format+parser version+row identities+exact numeric content+reference classification; exclude wall-clock and host paths, but do **not** erase semantically important changes. Same-day distinct raw versions must coexist as separate identities.

**CSV invariants:** strict configurable encoding; no `errors="ignore"`; canonical header checks with case-fold collision rejection; no missing/extra fields; fail file-wide on malformed quoting and unsupported line endings, unless explicitly specified. Quoted-newline CSV record ordinals must not be confused with physical line numbers. Unknown source fields preserved inertly, not dropped silently or made trading features.

**Numeric invariants:** no `float`; exact Decimal values, bounded digits/scale/exponent, no NaN/Infinity, no `"" -> 0`, prices nonnegative under synthetic contract and `high >= max(open,close,low)`, `low <= min(open,close,high)`; exact integer nonnegative volume, including legitimate zero, no fractional/comma/overflow guessing. Explicitly document unknown source-specific exceptions instead of falsely rejecting or accepting real data.

**ZIP invariants:** bounded compressed/uncompressed sizes, member count, compression ratio and total input budget; no extraction to disk, traversal, symlink, absolute/drive paths, duplicate target members, nested archive, encryption, truncated stream or wrong member. Reuse existing OD-02 limits after inspection, not silently copy unsafe assumptions. Strict early rejection and reason codes.

**Temporal / rights invariants:** market trade date != business/report date != publication time != first observation time != ingest time != decision time. Unknown `published_at` stays null. Parsing success never establishes PIT knowledge. In-memory synthetic parsing must be separate from protected archived data; optional archive adapter can only obtain bytes through existing `RawArchive.read_verified()` with the exact observation/source/date/consumer policy, never bypass a pending or revoked policy.

**Side effects:** zero provider network, zero DB/Parquet/warehouse/release/pointer/signing mutations, zero existing raw/archive writes, zero new source approvals. Output of the pure parser is in-memory typed data or a documented local disposable test artifact.

## 6. Mandatory T01–T32 tests: complete all before production code

Author all 32 named **groups** in `tests/unit/test_od05_era_parsing.py` and a separate independent expected-value oracle **before** creating/editing application parser files. Freeze exact test/fixture SHA and red/blocked classification. Run baseline with an offline write/network guard. Distinguish real legacy behavior failures from `ModuleNotFoundError` for new API, test-harness mistakes and missing official references. Missing new API is **NOT** proof the old implementation is defective. Record test chronology honestly; if later new cases are needed, label them as later, never retroactively pre-code.

| Group | Required synthetic or evidence-backed proof |
|---|---|
| T01 | Pinned source, format, parser version and exact full raw hash determine result |
| T02 | Repeated bytes produce identical semantic digest; operational time excluded |
| T03 | Different bytes on same date retain separate revision identities |
| T04 | Clearly synthetic 2019-like legacy profile fields map exactly, no official claim |
| T05 | Disputed 2020 profile cannot be force-routed through presumed UDiFF by year |
| T06 | 2024 June/July cutover ambiguities refuse; only reference-backed assertions certify |
| T07 | Synthetic newer-style ZIP member/header and extra-field preservation |
| T08 | Unknown, overlapping and unsupported format/ref/version return typed refusal |
| T09 | BSE historical profile not accidentally accepted as verified NSE |
| T10 | Misleading `OFFICIAL` label/name cannot elevate reference status |
| T11 | Required/unknown/duplicate/colliding headers and aliases handled explicitly |
| T12 | Bad CSV quotes, wrong field count, malformed encoding reject file-wide |
| T13 | ZIP traversal, duplicate entries, symlink, nested archive, ratio/budget violations |
| T14 | HTML/JSON access denial and empty payload never produce trusted rows |
| T15 | Trade/business/date mismatch and ambiguous date semantics refuse |
| T16 | Volume zero accepted; negative, fractional, missing and overflow rejected |
| T17 | Exact Decimal lexemes, scale, bounds, no float round-trip |
| T18 | Finite/nonnegative and consistent O/H/L/C checks and documented exceptions |
| T19 | Unique row identity includes exchange, symbol, series, ISIN and date as applicable |
| T20 | Leading-zero scrip/symbol/ISIN text preserved exactly |
| T21 | Missing optional vs required series/ISIN follows explicit synthetic format rules |
| T22 | Trade/business/published/observed timestamps not conflated; null publication retained |
| T23 | Raw SHA mismatch, missing pinned observation or wrong source/date refuse |
| T24 | Synthetic/cache/seed origins cannot be relabeled as provider-official |
| T25 | Pending/revoked/wrong-purpose archive read stops before parsing |
| T26 | Each failure has zero external, database, Parquet, archive, release or policy writes |
| T27 | Independent semantic hashes stable across duplicate runs and parser revisions |
| T28 | Default-OFF adapter and all existing OD-01/02/04/04R behaviors unchanged |
| T29 | Windows/Linux paths, case, locale, newlines and ZIP metadata controlled |
| T30 | Row/byte/member/decompression/CPU work budgets bounded and measured |
| T31 | Separate oracle compares every input→row numeric/date/text field, not just counts |
| T32 | Complete guarded Windows 3.11/3.14 + native Linux 3.12 matrix; lint/type/package |

Each T-group must be explicitly classified `PASS_SYNTHETIC`, `BLOCKED_REFERENCE`, `FAIL`, `NOT_RUN` or `NOT_APPLICABLE_WITH_REASON`. One group may contain a passing synthetic analogue **and** an authentic-reference subcase blocked; do not flatten to full PASS. No 32/32 official-validation claim when the reference corpus remains absent. Use exact, nonempty, **independently frozen** expected source rows/hashes/counts; missing or moved oracle files must cause explicit failure rather than vacuous pass.

## 7. Execute code only after test freeze

1. **Preflight:** verify G0+G1 human-authored decisions, HEAD, config, protected paths, runtime capabilities, references, and a fully enumerated test matrix. Stop on missing gate without writing a duplicate report.
2. **Freeze contract and tests:** independently write exact literal expected row mapping, record digests, and execute negative-first baseline. Identify real fail/blocked/new-feature categories.
3. **Implement:** create `contracts.py`, `dispatch.py`, `nse_cm.py` and `reference_registry.py`. Strict bounded pure function `parse(bytes, ParseRequest, ExplicitFormatProfile)`; no I/O/network for parser core. Reject unsupported profiles, pending official certification and BSE by default.
4. **Verify data fidelity:** compare price lexemes, scaled integers, text identity, source row ordinals, date, hash, profile/ref version with independent oracle. Intentionally perturb a price, source index, SHA and reference classification, proving each invalidates the match.
5. **Integrate only a disposable facade:** if permitted, test existing source-rights-gated pinned archive read and pass returned bytes to pure parser, without changing existing downloader/storage/loader. Do not introduce a new implicit latest route.
6. **Adversarial review:** repeat ZIP/CSV/identity/resource and rights failures; require zero writes to protected locations. Fix only actually reproduced defects. Every subsequent test addition is chronologically labeled.
7. **Regression:** three actual Python/OS runtimes where available; run guarded collection, targeted OD-05+prior rights/archive tests, complete offline regression, Ruff, mypy, pip check, module compilation and source SHA/preservation comparisons. No tests silently xfailed/removed/suppressed. If a platform is unavailable, Gatekeeper is `BLOCKED_PLATFORM` not success. Historical suites never counted as fresh runs.
8. **Quality:** independent stdlib expected-value comparator does not import production parser; verify actual output row counts and hashes; include case where expected corpus missing so oracle must fail.
9. **Gatekeeper:** issue `OD05_SYNTHETIC_TECHNICAL_PASS` only if all authorized synthetic gates have actual passing commands on required runtimes, while explicit official reference cases remain `BLOCKED_REFERENCE`. Else issue `OD05_BLOCKED_*`, with exact technical or approval cause. This status **does not** mean official data accuracy, PIT compliance or production permission.
10. **STOP:** no OD-06, no release/signing/publisher contact, no broker trading, no branch merge/commit/push without separate instruction.

Suggested command shapes, adapted to **inspected safe runners and disposable locations**:

```bash
python -m pytest --collect-only -q -m 'not realdata'
python -m pytest -q tests/unit/test_od05_era_parsing.py -m 'not realdata'
python -m pytest -q -m 'not realdata'
python -m ruff check src/omegadata tests scripts
python -m mypy src/omegadata
python -m pip check
```

Do not invoke these commands against production state blindly; first inspect fixture and import side effects and apply the existing OD-02V/OD-04R guarded isolated-test mechanism. No `scripts/run_full_pipeline.py --reset-sqlite-db`. No realdata network tests, no mutation of canonical report paths. Record exact executable, versions, CWD, start/end UTC, exit code, full summaries, selected/deselected/skipped cases, coverage, hashes and original-byte protection, not only terminal green labels.

## 8. Required implementation dossier (only after actual G0+G1)

Write new documents under `docs/omegadata_v2/implementation/od05_impl/<UTC_RUN_ID>/` (never replace old reports):

- `00_authorization_and_branch_identity.md` — externally supplied G0/G1 text/reference, accountable owner, exact HEAD, scope, no agent-authored approval.
- `01_format_reference_and_unknowns.md` — source-era and rights matrix, uncertainties, July 2024 documentary lead, zero false official evidence.
- `02_frozen_contract_and_test_hashes.md` — contracts, pre-code test/fixture hashes, 32-group mapping and actual chronological red/blocked status.
- `03_reuse_and_design_adr.md` — stdlib/Pydantic versus Pandera/PyArrow measured or deferred, license/check provenance.
- `04_exact_implementation_diff.md` — all changed paths/line ranges and reasons, preserved legacy defaults, migration none.
- `05_independent_numerical_oracle.md` — frozen literal expectations, negative tamper/missing cases, per-field comparisons.
- `06_security_source_rights_and_pit.md` — policy state, parser origin limits, privacy/no-write/network and temporal unknowns.
- `07_cross_platform_test_matrix.md` — original raw command logs, counts, exits, coverage, source hashes and warnings/skips.
- `08_defects_and_rollback.md` — actual unresolved P0/P1 and safety limits, reversible feature disable procedure.
- `09_gatekeeper_verdict.md` — only one of the honest verdicts; every claim supported by executable evidence.
- `10_next_phase_request.md` — one follow-up (likely OD-05 official reference completion or OD-06 after separate approval) and STOP.

Attach machine-readable hashes/fixtures/raw stdout in a **new** run-specific `logs/` directory. Never put private signing key bytes, API secrets, customer data or purported real market price datasets into the evidence bundle. Use typed `RUN`, `TEST/SYN`, `ARCH`, `CLAIM`, `UNK` evidence labels. A Maker/Reviewer/Gatekeeper chain is a review *procedure*, not independent human signoff.

## 9. Existing open blockers must survive untouched

- `D-01` P0 private signing-key custody/exposure, unresolved by parser implementation.
- `D-04` P0 release export/promotion eligibility bypass, unresolved; do not build releases.
- `D-03` canonical Parquet fixed `part-00000.parquet` overwrite, assigned OD-10, not OD-05.
- Historical PIT universe/corrections/identity/calendar/source-era and official fixture reference gaps remain uncertified.
- SQLite ResourceWarning in some past Python 3.14 runs; do not suppress or reinterpret.
- Source rights: 13 pending, zero approved, provider egress OFF. Approved synthetic fixture policy is not permission for real exchange data.
- No hosted feature-branch GitHub Actions result was found at review time; local WSL shares physical host with Windows. Honest platform and independence limitations apply.

## 10. Final output to owner

If G0/G1 missing, respond concisely and **create no further repo files**:

```text
OD05_NOT_STARTED — owner gate pending.
Reviewed feature branch/HEAD: <actual>.
G0: ACCEPT_EXCEPTION or REJECT_EXCEPTION not supplied by owner for OD04/OD04R.
G1: separate OD05 synthetic-only implementation authorization not supplied.
No parser/tests altered, no commit/push, no live access.
Owner action: provide a genuine decision on historical OD04 deviation and separate explicit synthetic-only OD05 authorization.
```

If both are supplied, produce a concrete implementation ledger, new-test counts/actual exits, code paths, source rights status, independent numerical match summary, Gatekeeper verdict and only the next appropriate approval. Never self-certify market-source truth or conceal genuine deviations.

**Never advance to OD-06 merely because this handoff file exists.**
