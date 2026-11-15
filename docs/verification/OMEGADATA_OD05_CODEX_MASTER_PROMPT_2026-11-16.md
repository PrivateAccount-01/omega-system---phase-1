# OMEGADATA OD-05: Historical Source-Era Parsing, Financial Schema Correctness and Provenance

**Document type:** Execution contract for Codex / engineering agents  
**Prepared:** 2026-11-16  
**Existing repository:** `https://github.com/PrivateAccount-01/omega-system---phase-1`  
**Target branch:** `feature/od01-source-rights`  
**Reviewed feature HEAD:** `bbc38716d902fe27192f80affaca29c6f51e9890`  
**Previous feature HEAD:** `44090a42958869faaab57a42b65f7ad8571d924d`  
**Phase:** `OD05_ERA_AWARE_PARSER_AND_REFERENCE_VERIFICATION`  
**Execution mode:** **OWNER_GATE_THEN_OD05_ONLY**. No later phase authorization.  
**Trust level:** Existing technical evidence is local/same-model, not independent financial certification.

> **CRITICAL:** There are TWO independent gates. (1) The historic OD-04 Gate-2 process-order exception requires an explicit, authenticated decision by a named human project owner. (2) OD-05 implementation requires a separately explicit user instruction and a verified, legally permitted source-reference corpus. Neither can be inferred from earlier green tests, from a code-generation prompt or from this Markdown file. If either gate is absent, perform bounded read-only OD-05 planning/evidence inventory and **STOP before changing application code**. Never manufacture a decision record or source approval.

---

## 00. Source of truth and immediate operating rules

Read the following before proposing changes:

1. Root `AGENTS.md`, `OMEGADATA_AGENTS.md`, and `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`.
2. `docs/omegadata_v2/plan/09_implementation_phase_plan.md`, especially OD-05; `docs/omegadata_v2/plan/10_architecture_and_contract_proposal.md`; `docs/omegadata_v2/audit/08_prioritized_defects.md` including D-09; source-rights audit and reuse register.
3. OD-02/OD-02V reports and tests; OD-04 Gatekeeper `docs/omegadata_v2/implementation/od04/20261115T124835Z/09_gatekeeper_verdict.md`; OD-04R Gatekeeper and owner request under `docs/omegadata_v2/implementation/od04r/20261115T181120Z/`.
4. Current actual code, not claims in old reports: `src/omegadata/track_a/source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `src/omegadata/pipelines/sequential_pipeline.py`, existing loaders/tests/fixture manifests and `pyproject.toml`.
5. Exact latest Git HEAD, branch, worktree status/index, `main` merge-base and all existing user changes. Never assume the SHA in this file is still HEAD. If HEAD changed, inspect the new diff and **STOP before editing application code** until the scope is reconciled.

The system is an upgrade of the EXISTING OmegaData Phase-1 repository. **No rewrite, reset, clean, stash, force push, cherry-pick, merge, history rewrite, deletion of raw/seed/archive/history, or broad reformatting.** No direct modifications to source policies, signing files, production databases, warehouse, release bundles, pointer state, or old evidence. No actual market-data HTTP/browser/curl/API requests. All real policies remain `PENDING_REVIEW` unless an actual human rights owner changes them under a different approved phase; **never modify them in OD-05**. No paid services or vendor APIs.

## 01. GATE ZERO: human disposition of OD-04 chronology

Current verified GitHub commit `bbc38716...` includes OD-04R remediation and a local Gatekeeper finding `OD04R_TECHNICALLY_REVERIFIED_PROCESS_EXCEPTION_PENDING`. The older OD-04 `OD04_BLOCKED` was not retroactively converted into PASS. The historic A01–A28 negative-first tranche was not fully run prior to OD-04 application code; that chronology cannot be repaired by reordering log files or replaying tests after the fact.

Before OD-05 implementation:

- Locate a distinct **human-supplied**, authenticated owner decision explicitly referring to the two exact commits and evidence package. Use the blank `OMEGADATA_OD04R_OWNER_DECISION_TEMPLATE.md` only as a template; it is NOT itself approval.
- Check named owner, role, timestamp, exact `ACCEPT_EXCEPTION` or `REJECT_EXCEPTION`, rationale, reviewed hashes, and acknowledgment of residual risks. Never create the decision yourself or assume that the user asking for a prompt constitutes approval.
- If `ACCEPT_EXCEPTION` is authenticated: preserve the original OD-04 Gatekeeper unchanged; record the exception as an ADDITIVE, versioned process decision. It waives only the historic ordering deviation, not any product, source, security, legal or financial gate.
- If absent, incomplete, unauthenticated, or `REJECT_EXCEPTION`: status `OD05_GATE_BLOCKED_OWNER_DECISION`. Read-only OD-05 inventory/proposal is allowed; **NO application, parser, loader, registry or test-source modification**. Record exactly why and stop.
- Even if accepted, require a **separate express user instruction** to execute `OD05_IMPLEMENT_ONLY` on the verified SHA. If missing, produce plan only and stop.

## 02. Severity P1 investigation: NSE cash-equity historic format transition

**Evidence observed on 2026-11-16:** Current `src/omegadata/track_a/source_registry.py` declares the modern NSE equity era `2019_present` starting `date(2020, 1, 1)`, with a modern UDiFF-style filename. `src/omegadata/track_a/acquisition.py` determines legacy parsing using `requested.year < 2020`. Existing synthetic tests cover a 2019 legacy case and a 2026 newer case, **not the 2020–2024 transition boundary**.

NSE's official reports page independently states **CM Bhavcopy (csv)** and **CM Common Bhavcopy (csv)** discontinued effective **2024-07-08**, with a direction to use **CM-UDiFF Common Bhavcopy Final (zip)**; it points to Circular 62424 (2024-06-12). This is evidence of a mismatch in currently assumed dates, not blanket proof that no parallel, transitional or historical variant existed.

Official reference starting points (documentation links only; not automatic permission to download market feeds):

- NSE All Reports: `https://www.nseindia.com/all-reports/`
- NSE Forms & Formats, UDiFF guidance/catalogue and example filenames: `https://www.nseindia.com/static/resources/forms-formats-members`
- NSE Circular identifier to verify through an official domain: `NSE/MSD/62424`, date 2024-06-12.
- If BSE documents or era samples cannot be lawfully authenticated, mark `SOURCE_REFERENCE_PENDING` and do not claim independent BSE certification.

**Mandatory actions:**

1. Assemble a dated per-format transition matrix for `NSE_EQUITY_BHAVCOPY`: legacy formats, pre-transition formats, new UDiFF final format, overlap periods, public availability vs source of truth, filename conventions, CSV columns, official schema/catalogue version, dates and rights status. Separately record whether `2020-01-01` is supported or disproven.
2. Identify exact boundary and adjacent exchange sessions around `2020-01-01`, `2024-06-24`, `2024-07-05`, `2024-07-08` and later 2024 sessions using independently verified exchange calendar references. Do **not** assert each is a trading day without checking; date arithmetic is not an exchange calendar.
3. Reconcile `source_registry.resolve_era`, `acquisition.validate_payload`, ZIP expected members, `download_manager._candidate_urls`, source fallbacks, `_load_bhavcopy_prices`, and any direct script or test that assumes a modern NSE format from 2020.
4. Produce **failing semantic tests before changing any code**: valid older-era bytes in a disputed year must not be forced through the wrong UDiFF reader; correct UDiFF bytes must not be accepted under unsupported historical conditions; unknown/ambiguous era should refuse or quarantine with typed reason codes.
5. **Do not globally replace 2020 with 2024 without verifying all relevant formats**. If documentation and lawful fixture evidence are insufficient, output a proposed era table and `BLOCKED_REFERENCE`, leaving the contested behavior disabled from certification.
6. Do not silently rewrite old raw archive objects, recalculate stored prices, or regenerate any historical release. Any schema correction is prospective and versioned.

## 03. OD-05 exact scope and strict exclusions

The first implementation vertical slice is **NSE CM/cash-equity bhavcopy** across supported, evidenced eras; **BSE CM/cash-equity bhavcopy** only for separately authenticated historical formats. Design pure parser dispatch contracts that other feeds can use later, but do not pretend to implement F&O, cash-vs-futures reconciliation, corporate-action interpretation, index feed semantics or broker/portfolio work here.

Permissible new code, when gated: `src/omegadata/parsers/` (pure source-era parsers, schema/version/error types, references), `tests/unit/test_od05_era_parsing.py` and scoped synthetic/reference fixtures; narrow backwards-compatible changes to `src/omegadata/track_a/source_registry.py`, `src/omegadata/track_a/acquisition.py` and `src/omegadata/pipelines/sequential_pipeline.py` only if proven necessary. Existing `download_manager.py` and `raw_archive.py` may be read/reviewed but not modified without a reproduced integration defect and a documented minimal scope amendment. Never modify `track_a/storage.py`, database models, release, signing, source policy, live acquisition transports, CI or dependencies without a separate owner-approved scope.

No mutations of legacy `PriceRecord` in this phase's primary path. The parser's primary output is a deterministic **typed immutable observation** or a typed quarantine/refusal. If an existing loader must accept the new parser, keep it behind an **explicit default-OFF adapter** with regression-tested old behavior; reject any loss of source identity/rights/version. Production writer and market-row publication are OUT OF SCOPE.

## 04. Repository-first selection, with evidence

Compare at least:

- `EXTEND_EXISTING`: stdlib `csv`, `decimal`, `datetime`, `zipfile` + existing Pydantic/validator and frozen typed models.
- `PANDERA`: `https://github.com/unionai-oss/pandera`, data-frame validation if needed for post-parse quality constraints; inspect exact version/tag/SHA, MIT license, supported runtime, dependencies, actual benchmark/cost, implications of any auto-coercion.
- Optional `PYARROW` already installed for typed batches; no direct raw-byte provenance loss.

For every candidate record version, pinned SHA, license and transitives, Python 3.11/3.12/3.14 compatibility, execution time/RSS, deterministic behavior, semantic fidelity, maintenance/test health, security and integration cost. Evaluate on the **same frozen, authorized synthetic/reference corpus**. A public repo's badges and benchmark claims are L1 only until reproduced. Do not install or vendor a dependency merely to fill the comparison table. A bespoke tiny parser may be superior if it is independently testable and keeps raw bytes exact.

Decide `ADOPT`, `ADAPT`, or `DEFER`, backed by observed results. **No claim of speedup, license clearance, official source certification or commercial-use entitlement without verified evidence.**

## 05. Provenance hierarchy and corpus policy

Every case MUST be visibly one of:

- `OFFICIAL_REFERENCE_VERIFIED`: source publisher and document ID, canonical URL, retrieved-at UTC, immutable document/raw SHA-256, human review/reference permission, format/era coverage and sample-to-spec alignment. The agent cannot assign this status based on the filename, previous JSON assertion, or page existence alone.
- `ARCHIVED_UNVERIFIED`: existing checked-in/cached/seed data with hash/provenance, not official permission or truth; never rewrite/relabel.
- `SYNTHETIC_TEST_ONLY`: deterministic self-generated bytes for boundary/error testing, synthetic prices and dates clearly flagged.
- `SOURCE_REFERENCE_PENDING`: no sufficient lawful source document/actual sample semantics.

Official NSE document **read-only research** is different from fetching exchange data; do not request market/source files from pending-rights endpoints. For reference documents, comply with site terms; do not scrape automatically. Preserve reference metadata without embedding copied full documents or commercial datasets. If the only information is a reference-page statement but the exact schema/real rows are unverified, classify schema interpretation as PENDING and do not claim `OFFICIAL_REFERENCE_VERIFIED`.

Build `docs/omegadata_v2/implementation/od05/<UTC-run-id>/reference_registry.json` describing documents and proof IDs; synthetic fixtures under the test root, not `data/raw`, and hashed. No secret, authentication token, signing material or source API response in logs.

## 06. Proposed typed interface and invariant set

Design (names illustrative, do not force if existing design supports equivalent contract):

```python
@dataclass(frozen=True)
class ParseRequest:
    source_key: str
    business_date: date
    raw_sha256: str
    raw_observation_id: str | None
    requested_parser_version: str
    source_reference_id: str | None

@dataclass(frozen=True)
class ParsedBar:
    source_key: str
    exchange: str
    market_date: date
    symbol: str
    series: str | None
    isin: str | None
    source_row_index: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    # Other exchange-native fields: optional and PROVENANCED, never inferred.

@dataclass(frozen=True)
class ParseResult:
    state: Literal["PARSED_UNVERIFIED", "SCHEMA_REFERENCE_VERIFIED", "QUARANTINED"]
    raw_sha256: str
    parser_version: str
    schema_version: str
    source_reference_id: str | None
    rows: tuple[ParsedBar, ...]
    quarantines: tuple[object, ...]
    original_field_manifest: tuple[str, ...]
```

Contracts must explicitly distinguish **raw-byte capture** vs **structural validation** vs **source-reference-verified semantics** vs **financially reconciled truth**. Structural validation can pass while official status remains PENDING. No `OFFICIAL` promotion by string renaming. `published_at` is optional/unknown, never manufactured from `observed_at` or market date. Downstream PIT eligibility is separate, not inferred by parser acceptance.

Required invariants:

- Input raw byte SHA must match the independently computed exact original bytes. Pinned archive observation ID must correspond to the same source/date and currently permitted read purpose; no implicit latest, no policy bypass.
- Versioned parser selection is an explicit function of **source key, format identifier and verified era reference**, not a guessed year, URL suffix or header alone. Unknown/ambiguous formats quarantine; duplicate headers, extra CSV fields and format drift fail closed.
- All money/price/volume parses exact with `Decimal`/integers. No silent float coercion, locale guessing, comma stripping, unit rescaling, `NaN`/`Infinity`, empty-to-zero or negative prices. Check OHLC invariants, legitimate zero volume and no inferred adjusted prices. If negative/zero prices have a source-specific legitimate meaning, document and test the exception before supporting it.
- Dates retain exchange session and meaning. Trade date, business/settlement date, observation/publication date and ingestion timestamp are not interchangeable. Ambiguous date formats are rejected or validated against explicit era rules.
- Preserve ISIN/series/symbol/scrip code exactly as text, including leading zeros. Do not collapse BSE scrip code into a number or assume identical symbol == identical instrument. No future ISIN substitutions or delisted-entity erasure.
- Preserve **unknown source columns** in an inert raw-field map or manifest. Never silently drop fields while claiming full schema coverage; validate required columns and record optional/unknown ones. Do not propagate unknown fields into trading features without approval.
- Treat correct schema but wrong requested date, duplicated security/series/date row, incomplete archive, malformed CSV quoting, corrupt ZIP and HTML denial as a typed failure or quarantined file. Avoid partial file-success if consistency cannot be guaranteed.
- Keep canonicalization byte-hash deterministic. Do not include nondeterministic wall-clock values in semantic content hashes; separate operational timestamp metadata.
- No parser writes to existing source archive, database, fixed Parquet path, release/latest pointer, or source policy. All experimentation uses disposable tests and proposed outputs.

Define a table of typed errors: `ERA_UNKNOWN`, `REFERENCE_PENDING`, `SCHEMA_UNKNOWN`, `HEADER_DUPLICATE`, `DATE_MISMATCH`, `CSV_INVALID`, `ZIP_INVALID`, `ROW_INVALID`, `PRICE_INVALID`, `VOLUME_INVALID`, `IDENTITY_AMBIGUOUS`, `RAW_HASH_MISMATCH`, `SOURCE_SCOPE_DENIED`, `VERSION_UNSUPPORTED`, `INTERNAL_PARSER_ERROR`. The error location (row/field) may be included; no raw confidential fields or raw payload excerpts in public errors.

## 07. Mandatory negative-first acceptance matrix (write ALL tests before application edits)

**Hard rule learned from OD-04:** Before modifying any application file, freeze interfaces and write the COMPLETE OD05-T01–T32 unit/property/integration matrix, execute against old code, and classify each failure as **real old-behavior defect**, **new API not yet present**, **missing official reference/rights**, or **test/harness error**. Only the first category counts as genuine defect reproduction. Preserve timestamped red logs and test SHA; never claim a missing import proves defective old behavior. Do not add tests afterward and call them pre-implementation. Newly discovered cases may be added with their true chronology and a scope amendment, but original Gate 2 status must remain honest.

| Group | Test and required assertion |
|---|---|
| T01 | Valid source/date/raw-SHA+parser version produces reproducible typed rows on synthetic corpus. |
| T02 | Two identical byte inputs have identical semantic parse hash (operational times excluded). |
| T03 | Same day with different raw bytes yields separate version identities, no overwrite. |
| T04 | Valid legacy NSE 2019 file with documented schema maps accurately. |
| T05 | Valid disputed 2020 file must not be forced to 2024 UDiFF solely on year. |
| T06 | Boundary adjacent to 2024-07-08 chooses only evidence-supported format. |
| T07 | Post-transition UDiFF schema/ZIP membership and header tests. |
| T08 | Unknown/intermediate/parallel era refuses with `ERA_UNKNOWN` or `REFERENCE_PENDING`, no guessing. |
| T09 | BSE supported modern format obeys exact doc/filename/date identity. |
| T10 | BSE historical format lacking proof remains quarantined, not fabricated official. |
| T11 | Unknown/missing/duplicate/header-collision columns refuse; benign extra columns preserved. |
| T12 | Bad quote, malformed escape, extra field or truncated CSV refuses. |
| T13 | Zip-slip, directory/absolute/symlink entry, nested/archive-bomb/duplicate candidate refuse. |
| T14 | HTML/JSON access denial and empty bytes never become trusted market rows. |
| T15 | Wrong market date, mismatched filename date and unsupported date encoding refuse. |
| T16 | Valid zero-volume row retained with zero; empty, negative, fractional or overflow volume rejected. |
| T17 | Decimal prices exact; precision preserved without float round trips. |
| T18 | NaN/Infinity/negative and OHLC-inconsistent prices rejected. |
| T19 | Duplicate identity keys (exchange, symbol, series, ISIN, date as appropriate) detected. |
| T20 | Leading-zero BSE scrip code and ISIN/symbol text retain identity. |
| T21 | Missing ISIN/series handled by explicitly verified era policy; not silently synthesized. |
| T22 | Source request dates vs publication/observed times never confused. |
| T23 | Raw hash mismatch/ref missing/byte tamper rejects before parse. |
| T24 | Archived-unverified/seed/synthetic inputs cannot become official by setting a flag. |
| T25 | Policy pending/revoked or wrong consumer scope prohibits reads/parsing of protected bytes. |
| T26 | Parser failures cause zero database, Parquet, source/archive or release mutation. |
| T27 | Repeated replay pinned same input/parser version produces bit-for-bit canonical evidence. |
| T28 | Old loader/OD02 parser and synthetic tests regress without assertion weakening. |
| T29 | Cross-platform mixed path separators, case, CRLF/LF, ZIP metadata and locale do not misparse. |
| T30 | Size, row-count, ZIP expansion and operation resource budgets are enforced before allocation. |
| T31 | Independent reference calculation compares every numeric field and source row index in golden subset. |
| T32 | Full Windows/Python3.14 + Windows/Python3.11 + native Linux/Python3.12 suites, Ruff/mypy/pip, no covert skips. |

All **T01–T32 tests must be meaningful**; group a test only when all listed assertions truly execute. Any blocked official-reference test is `BLOCKED`, not skipped green; do not invent official values. Keep tests parameterized across supported formats and exact boundaries. A negative-first run is meaningful only if it reaches the assertion, not just an import exception or test fixture error.

## 08. Implementation sequence after BOTH gates pass

**Sequence is strict; no monolithic one-shot rewrite.**

1. `OD05-PREFLIGHT`: Record exact feature SHA, branch, source tree SHA, old test results, inherited limitations, rights status; create a *new* UTC evidence directory without overwriting prior logs. Protect historical/seed/release/signing paths; signing material is never opened or hashed. Capture baseline and source/reference inventory in read-only mode.
2. `OD05-DESIGN`: Produce `01_reference_and_era_matrix.md`, `02_contracts_and_adr.md`, `03_repo_reuse_decision.md` and precise module/scope plan. Freeze supported formats and official-vs-pending statuses.
3. `OD05-RED`: Create and run all T01–T32 tests against the exact old code, record red reasons, blocked references, timestamped pre-edit file hashes. Fix harness mistakes before treating an error as a business defect.
4. `OD05-PARSER`: Implement pure `src/omegadata/parsers/` typed modules with explicit dispatch, strict decimal/date/archive/identity checks and deterministic canonical outputs. Keep compatibility entry points and canonical raw bytes unchanged.
5. `OD05-INTEGRATE`: Apply only reviewed narrow changes to registry/OD02 validation/selected sequential-pipeline adapter. Any changed source-era routing must have a specific signed reference and passing boundary tests. Default live fetch remains OFF.
6. `OD05-ORACLE`: Implement a separate stdlib-based reference comparator that does **not** import the parser under test; validate independently pinned raw rows/fields/expected values/hashes. A source documentation claim alone is not a row-level oracle.
7. `OD05-GREEN`: Run targeted and full offline tests via controlled disposable-root runner; run Windows 3.14, Windows 3.11 and Linux 3.12. Run adversarial archive/date, rights and crash regression. Retain actual exit codes and warnings.
8. `OD05-REVIEW`: Same-model Maker/Reviewer/Implementer/Gatekeeper/Historian ledger, explicitly disclose lack of independent human review. Compare exact test-source hashes/line endings, original file preservation, zero source approvals and forbidden action audit.
9. `OD05-STOP`: Write Gatekeeper and next-phase request; do not begin OD-06, OD-07, browser, markets, production backfill, migration, releases or strategies.

Do not weaken old OD02 validation to make new parsing pass. If the new parser and old validator conflict due to proven era issue, solve it behind versioned compatibility/refusal semantics, not by accepting arbitrary files. Keep all loader side effects excluded from primary pure parser tests.

## 09. Scripts and commands: safe templates, NOT claims of execution

The verified OD-04R work used isolated runners and per-OS overlays. Inspect/reuse those mechanisms after ensuring that they work on the current exact HEAD; **never reuse existing exclusive-create labels or old output folders**, and never invoke unguarded tests against real configured data. Commands below are samples only; agent must record the actual interpreter, cwd, argv, UTC time, exit and log in fresh files.

```powershell
# READ-ONLY preflight from the existing repo
 git rev-parse --show-toplevel
 git branch --show-current
 git rev-parse HEAD
 git status --short
 git diff --name-status
 git diff --check

# In a NEW disposable test copy with RAW_ROOT / DB / PARQUET / RELEASE roots
# redirected into a test sandbox AND DNS/socket/subprocess/protected writes denied:
 & '<isolated-python>' -B -m pytest -q tests/unit/test_od05_era_parsing.py
 & '<isolated-python>' -B -m pytest -q tests/unit/test_od02_acquisition.py tests/unit/test_od04_raw_archive.py tests/unit/test_od04r_adversarial.py tests/unit/test_od05_era_parsing.py
 & '<isolated-python>' -B -m pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
 & '<isolated-python>' -B -m ruff check --no-cache src/omegadata tests scripts
 & '<isolated-python>' -B -m mypy src/omegadata
 & '<isolated-python>' -B -m pip check
```

```bash
# Linux: same commands through a newly reviewed isolated runner on a NATIVE
# filesystem (not an inherited /mnt/<drive> temp root).
python -B -m pytest -q tests/unit/test_od05_era_parsing.py
python -B -m pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
python -B -m ruff check --no-cache src/omegadata tests scripts
python -B -m mypy src/omegadata
python -B -m pip check
```

**These bare command templates are unsafe against the ordinary configured project roots. They must be invoked only after the harness confirms disposable DB/raw/archive/parquet/release/GPG/report roots, blocks market-provider/network/process egress during tests, proves protected writes refused, captures fixtures without personal/secret files, and records OS-specific skips with passing counterparts.** If an environment is unavailable, report BLOCKED rather than claiming it passed.

## 10. Required deliverables and evidence directory

`docs/omegadata_v2/implementation/od05/<UTC-run-id>/`

- `00_preflight_and_owner_gate.md`: actual HEAD/branch/dirty files/owner decision status, exact approved scope, rights/policy status; if missing, end here with read-only artifacts.
- `01_reference_and_era_matrix.md`: source, periods, filename, columns, official citation/version/rights, disputed periods, status; highlight NSE 2020-versus-2024 mismatch.
- `02_contracts_and_adr.md`: typed input/output/error/dispatch and backwards-compatible integration.
- `03_repo_selection.md`: existing vs Pandera vs optional Arrow with pinned upstream identities/licenses and fair measurements or explicit unmeasured.
- `04_negative_first_matrix.md`: all T01–T32 red-before-code with truthful failure classifications, blocked unknowns and hashes/timestamps.
- `05_implementation_diff.md`: exact changed files, permitted scope, no accidental regeneration.
- `06_independent_reference_oracle.md`: separately authored and pinned reference check; source docs do not count as numerical row oracle.
- `07_security_rights_pit_review.md`: rights/default denial, known time vs trade time, historical source reference and secrets.
- `08_runtime_quality_matrix.md`: per-OS full/targeted/collection, type/lint/dependency, warnings/skip nodes, coverage, exact test source identity.
- `09_remaining_defects_and_rollback.md`: no automatic migrations/deletions; fix/unknown/blocked all listed.
- `10_gatekeeper_verdict.md`: `OD05_OFFLINE_TECHNICAL_PASS`, `OD05_PARTIAL_REFERENCE_BLOCKED`, or `OD05_BLOCKED`, with actual evidence; no invented official certification.
- `11_next_phase_request.md`: exactly ONE scoped next action; no automatic OD06/07 authorization.
- `reference_registry.json`, immutable SHA/operation evidence and `logs/` with each actual command, UTC, stdout/stderr and exit; no keys, auth tokens or payload secrets.

All reports must use `RUN`, `TEST/SYN`, `ARCH`, `CLAIM`, `UNK` evidence classes. `ARCH` historical results cannot substitute for fresh execution on current code. A model self-review must not be described as independent human/legal/financial review. Do not modify old audit, Gatekeeper or original raw-object/observation records to make metrics look green. Record skipped/deselected cases and expected adversarial failures separately from tests passing.

## 11. Hard stop and approval criteria

**STOP with `OD05_GATE_BLOCKED_OWNER_DECISION`** if the accountable human did not accept the OD-04 historical process deviation. **STOP with `OD05_GATE_BLOCKED_AUTHORIZATION`** if no separate explicit OD-05 implementation authorization is present. **STOP with `OD05_PARTIAL_REFERENCE_BLOCKED`** if official/lawful historical file specifications and representative authoritative bytes are insufficient for the claimed formats. It is acceptable to finish generic pure parser infrastructure against synthetic fixtures and record format certification as blocked only when both other gates are met and the approved scope explicitly permits that partial deliverable.

**STOP immediately** on unexpected dirty overlap, source policy change, live provider request, authorization failure, protected write, actual signing material access, data/release mutation, unapproved package or Git lifecycle operation, unbounded time/resource behavior, changed inherited assertions, missing negative-first chronology or unreported skip.

Financial-data correctness is the priority. Passing a parser unit test does not authenticate an exchange, verify the publication timeline, confer licensing rights, establish PIT availability or justify a profitable trading strategy. Source-rights owner and independent finance/security reviewer decisions remain separate.

## 12. Required final Codex response

Produce a concise but complete, evidence-linked report:

1. Actual HEAD/branch and precise files changed.
2. OD-04 owner-exception decision: verified explicit approval, rejected or pending (never assumed).
3. Whether OD-05 implementation was expressly authorized and executed, or audit/plan-only.
4. Actual NSE/BSE format era matrix, particularly the 2020–2024 issue, with official versus unverified source citation.
5. Full test matrix per OS, exact skips/exits/coverage and independent oracle outcome.
6. Repository reuse decision with actual proof rather than reputation.
7. P0/P1 issues still open, security/provenance limitations, signed decision evidence identity and next one requested step.
8. Explicit final Gatekeeper code and STOP statement. No next-phase auto-execution.

**END OF OD-05 MASTER EXECUTION CONTRACT.**
