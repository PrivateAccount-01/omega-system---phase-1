# OmegaData 2.0 — OD-05R Authenticated Source-Era Reference & Parser Verification

**Execution contract:** `OD05R_REFERENCE_AND_PARSER_VERIFICATION_ONLY`  
**Prepared:** 2026-11-16  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Branch:** `feature/od01-source-rights`  
**Reviewed GitHub HEAD:** `2326936860f64cadf4f4c24a968c073114598b26`  
**Previous baseline:** `bf6f4894c9e5237e8c1a44b625c66b8a420b4aad`  
**OD-05 synthetic Gatekeeper:** `OD05_SYNTHETIC_TECHNICAL_PASS`, with official reference gate `BLOCKED_REFERENCE`  
**Scope:** Complete the **next bounded, offline-oriented source-reference milestone**; do not begin OD-06, enable source feeds, modify a release, or rewrite any historical observation.

> **Nonnegotiable entry distinction:** G0 and G1 were addressed in the completed OD-05 synthetic implementation and are recorded in `docs/omegadata_v2/implementation/od05_impl/20261115T201333Z/00_authorization_and_branch_identity.md`. Do not reopen the same historical exception merely because this is a new run; verify the record has not been invalidated or superseded. **This prompt is the user's scope selection for OD-05R when they actually issue it to Codex**, but it does not authorize external market-data collection, legal source approval, signing, release promotion or changes to production source routing.

## 00 — Operating hierarchy and current state

1. Read repository-root `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, and the phase plan `docs/omegadata_v2/plan/09_implementation_phase_plan.md`. Obey higher-priority system and user instructions and repository instruction hierarchy.
2. Review the exact current source: `src/omegadata/parsers/{contracts.py,dispatch.py,nse_cm.py,reference_registry.py}`, `tests/unit/{test_od05_era_parsing.py,od05_oracle.py}`, source registry, `track_a/acquisition.py`, downloader, `track_a/raw_archive.py`, `pipelines/sequential_pipeline.py`, existing backfill/probe scripts. Inspect relevant config and tests for duplicate era assumptions.
3. Read and reconcile all numbered OD-05 implementation reports `docs/omegadata_v2/implementation/od05_impl/20261115T201333Z/00_...10_...`, especially Gatekeeper, test chronology, independent oracle, source hash ledger, coverage, and residual defects; read original OD-05 audit and OD-04/OD-04R gate history. Never equate archived logs with newly rerun commands.
4. Run **read-only** `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff --name-status`, `git diff --cached --name-status`, merge-base, and compare the actual feature branch HEAD to this reviewed SHA. If HEAD advanced, inspect changed files and reconcile scope before edits. Preserve all pre-existing tracked/untracked state.
5. Safeguard existing data (`data/raw`, `data/seed`, archive, Parquet, SQLite/ClickHouse, `.venv*`), release manifests, source-policy files and historical evidence. **Do not open, hash, copy, move, print, rotate or delete any private GPG key/revocation contents under `artifacts/gnupg`**. Signing exposure P0 and release-promotion P0 remain open and out of scope. No `git reset --hard`, `clean`, stash, force-push, history rewrite, wholesale formatting, old test edits, package upgrade, or surprise commits/PRs/merges.
6. Source rights: 13 registered real sources `PENDING_REVIEW`, zero approved in last verified run; recheck mechanically, never change approvals. All provider transport remains `BLOCKED_EXTERNAL_EGRESS`. No NSE/BSE API/feed/scrape request, browser automation, bypass, cookies, proxy tricks, market-source download or paid vendor. Public document discovery is not blanket permission to fetch market records. No deployment, trading, finance performance claims, or OD-06 implementation.

### Verified start snapshot from commit, to be rechecked

- Five additive production-independent parser files under `src/omegadata/parsers/`, plus two test/helper files.
- `OD05_SYNTHETIC_TECHNICAL_PASS` recorded: Windows Python 3.14 and 3.11 each `572 passed, 10 skipped, 4 realdata deselected`; WSL Linux Python 3.12 `580 passed, 2 skipped, 4 realdata deselected`; 94 synthetic OD-05 cases passed on each; parser combined line/branch coverage ~94.37%. Ruff/mypy/pip/compile all recorded exit zero. These are **stored local logs, not CI or independently rerun now**.
- Synthetic selectors `legacy-illustrative`, `udiff-illustrative`, `syn-v1`, `synthetic-v1`; strict test member `synthetic.csv`. This is intentionally NOT real NSE compatibility.
- Current production registry's newer NSE cash-era start is 2020-01-01, and acquisition validator uses a year-2020 split; source date semantics unverified. Existing business-date/TradeDt/BizDt and series/identity assumptions require official-spec evidence.
- Official reference corpus still has zero independently verified cases. Human G0 exception for historical OD-04 ordering was documented; do not rewrite old Gatekeeper.
- No new branch GitHub Actions result was identified at the snapshot. Verify current state without inventing CI success.

## 01 — Primary mission and deliverable

Build an **auditable reference-evidence pipeline and versioned format specification**, then extend parser coverage **only when exact, lawful, independently verified reference material supports it**. Separate these concepts:

- Publisher announcement that a format was introduced/discontinued.
- Proof that a specific format was publicly available on a particular date.
- Original versioned schema/guidance document authenticity.
- Original representative raw file identity and human reference-use rights.
- Exact field-level semantic interpretation and source-row correctness.
- Point-in-time availability, which is NOT established by a parse, an official filename, or a publication-date guess.

The phase's **minimum useful executable outcome** even if official rows cannot be obtained is a small, tested, locally ingestible **reference-evidence validator** and a generated **uncertainty/cutover matrix**, with precise refusal cases for forged, incomplete, self-labeled or ambiguous references. Do not make another documentation-only gate report if bounded reference-verifier code can be implemented safely without enabling real-source access. No official-format parser is required to be implemented if its prerequisites remain missing. Never mislabel a partial reference result as OD-05 complete.

## 02 — Research targets and proof sources

Start with these publicly indexed starting points (verify status and terms before opening, do not treat a link as permission to download restricted samples):

1. Official NSE All Reports — `https://www.nseindia.com/all-reports/`. Reports page identifies `CM - Bhavcopy(csv)` and `CM - Common Bhavcopy(csv)` as discontinued **effective 2024-07-08**, referring to NSE Circular **62424** of **2024-06-12**, and directs readers to `CM-UDiFF Common Bhavcopy Final(zip)`.
2. Official NSE Forms & Formats — `https://www.nseindia.com/static/resources/forms-formats-members`. Lists UDiFF guidance, catalogue versions **1.0 through 4.0**, Bhavcopy format specification and sample test files. Version pinning and effective scopes require separate verification; the page's existence alone does not establish numeric semantics.
3. NSE circular identifier **`NSE/MSD/62424`**, dated 2024-06-12. A separately hosted public copy (NOT an authenticated NSE-hosted original) describes release rescheduled to **2024-06-24** and parallel old/new dissemination through **2024-07-05**; treat that copy only as a lead until independently reconciled with NSE-hosted original, circular metadata and annexures. In case of circular/public-page mismatch, explicitly preserve both claims and cite the mismatch.
4. Official capital-market calendar circular `NSE/CMTR/59722`, 2023-12-12, for **2024** holiday context; it is not independently sufficient to prove actual sessions, later amendments or any 2020 trading calendar. Do not infer a trading session merely because the date was a weekday or absent from a holiday list.
5. Existing local `docs/omegadata_v2/implementation/od05/20261115T190654Z/reference_registry.json`: retain unchanged. Existing `tests/fixtures/official_source` are `ARCHIVED_UNVERIFIED` unless authentic original publisher bytes and human review substantiate them.
6. BSE's official historical cash-equity schema/dated formats must have their own proof; **no NSE document certifies BSE**. F&O UDiFF evidence may corroborate rollout dates but not cash-equity schema semantics.

**Allowed safe research procedure:** Search public index or read publicly accessible explanatory documentation if site terms permit, record access method and real UTC retrieval timestamp, canonical URL, document issuer, original bytes' SHA256 **only if those bytes were actually acquired lawfully**, version, the relevant paragraph/table/page, license/use constraint, and a human verification state. Do not automatically request market-data endpoints or stock bhavcopy samples from unapproved providers. Prefer owner-supplied, locally mounted, lawfully acquired reference documents and approved representative samples. If not supplied, mark original-document hash and sample proof `MISSING`, rather than fabricating them. A third-party mirrored circular can never silently substitute for its claimed authoritative source.

The exact **format-by-date matrix** must distinguish separate cash-equity formats and allowed overlap, at minimum check: 2019-12-31 / 2020-01-01, 2024-06-21 / 24 / 25, 2024-07-04 / 05 / 08 / 09, and a later control date. For each distinguish **calendar/session evidence**, publisher announcement date, dissemination start/end dates, actual sample date, schema version, format/member naming, column list, semantic date/units/identity fields, permissions and confidence. Denote `UNKNOWN`, `PENDING_REFERENCE`, `OVERLAP`, and `SUPPORTED_BY_AUTHENTICATED_EVIDENCE` separately. Do not apply a blind global `2020 -> 2024` constant replacement.

## 03 — Evidence capability and trusted status model

Implement an **additive, offline-first reference verifier** under `src/omegadata/parsers/` (suggest `reference_evidence.py`, `era_matrix.py`) with no side effects at import. Accept separately supplied local documents/bytes and metadata; no built-in exchange downloader. An agent may propose an exact alternate design using existing Pydantic/dataclass conventions, but must justify it and retain unit test isolation.

A candidate reference must include:
- `reference_id`, issuer, document/circular ID, document version and applicable source+segment+format scope;
- canonical document URL and real acquisition method/time (or `null`/`UNKNOWN`);
- SHA256 and length of original bytes **if present**, never a hash of a paraphrase masquerading as original;
- original file's MIME/extension, a separately declared legitimate source of the bytes, applicable legal usage permission and approval owner if actually provided;
- reviewed field/date/series/identifier/unit semantics tied to exact document and page/section/column;
- optional approved representative raw file: independently pinned SHA and field-level expected values, with rights scope and sample provenance;
- independent approval/reviewer identity when real, plus actual review time; do not allow a boolean/string supplied by the parser caller to manufacture approval;
- parser and schema version identity independent of the original announcement's publication date.

Minimal state set: `DOCUMENT_DISCOVERED`, `DOCUMENT_BYTES_UNVERIFIED`, `DOCUMENT_HASH_VERIFIED`, `SCHEMA_REFERENCE_PENDING`, `SCHEMA_EVIDENCE_VERIFIED`, `ROW_REFERENCE_PENDING`, `ROW_REFERENCE_VERIFIED`, `BLOCKED_RIGHTS`, `CONFLICT`, and `UNKNOWN`. If too many states complicate the design, map them to a smaller typed state machine while preserving their safety distinctions. **Only a human-reviewed, authorized, attributable reference** may ever be eligible for any `OFFICIAL_REFERENCE_VERIFIED` claim. A passing hash alone proves byte identity, not officialness. Tests must prove call-site flags, filenames, a website title, an LLM-created citation, and a synthetic `official=True` metadata key never elevate status. Evidence files alone may be valid while their historical financial interpretation remains pending.

The validator must be deterministic and read-only: strict canonical JSON field policy, duplicate-key detection, path traversal/UNC/drive/link refusal, bounded input size and number of records, UTC validation, correct URL scheme/no secrets in errors, no symlink escape, no auto-download, no external HTTP/DNS and no database/old-fixture mutations. Do **not** store credentials or copy copyrighted source bundles into public Git history. Prefer store hashes and permitted non-copyrighted metadata, not whole copyrighted circulars or market samples. If raw reference bytes are included in local tests, only synthetic/disposable bytes, never restricted real data.

## 04 — Explicit parser-extension gate

Separate **reference verifier completion** from **an official-data parser extension**:

**Gate A — document validity:** authentic publisher document, exact version/effective applicability, original bytes/hash and actually permitted use. If A missing, only reference-verifier code plus synthetic negative tests are allowed.

**Gate B — representative row truth:** lawfully supplied original format sample covering the intended era, exact file/ZIP member/name/columns and row semantics; human-reviewed independently frozen expected values; source legal/retention scope. If B missing, do not implement or claim an official parser profile. Synthetic new test vectors may be added but must remain `SYNTHETIC_TEST_ONLY`.

**Gate C — production-route change authority:** a separately approved **exact-file scope amendment** naming `source_registry.py`, `acquisition.py`, downloader and/or `sequential_pipeline.py` with cutover semantics validated. Gate C is NOT granted by this prompt. Even if A/B pass, new parsers must stay opt-in/offline, no legacy migration or production routing updates.

With A+B evidenced and scope approved for **new parser files only**, Codex may add a narrow versioned format profile in `src/omegadata/parsers/`, verified against the permitted local sample; preserve original illustrative profiles and deterministic old results. Keep raw bytes immutable, original archived observations' legacy era labels untouched, `published_at` unknown unless supported, and preserve identity/series/zero-volume/Decimal semantics exactly. If A/B fail, do not pretend unsupported spec changes are implementation progress; emit `BLOCKED_REFERENCE`, but the reference-verifier component may still achieve its limited independent technical PASS.

## 05 — Mandatory defect and compatibility audit

Before changes, map these specific hazards to executable negative cases:

- **2020 split:** `source_registry.py` modern cash-era `2019_present` starting 2020-01-01; `acquisition.py` uses `requested.year < 2020`. Why that date? Search authentic historical references; unknown remains unknown. Freeze the distinction between *filename pattern availability* and *official validity*.
- **2024 cutover:** distinct June 24 rollout, July 5 overlap end and July 8 discontinuation leads; actual sessions and any CM exceptions require source proof. No import of F&O-derived assumptions into NSE CM.
- **Real ZIP incompatibility:** current `nse_cm.unpack()` accepts only one member literally called `synthetic.csv` and simplistic final end-of-central-directory shape, by design. Actual NSE ZIP validation must be source-versioned and corpus-backed; do not “fix” synthetic parser by accepting any ZIP/member. Include ZIP64/extra/comment/CRC/safe-member-path tests grounded in the selected format only.
- **Trade vs business dates:** `nse_cm.decode()` currently requires both `TradDt` and `BizDt` to equal requested synthetic date. Real contract may differ; preserve separate fields, reject ambiguous semantics until authenticated.
- **Identity:** current synthetic identity is `(symbol, series, ISIN, trade_date)`; real source may have other series, identifiers or missing fields. Do not collapse distinct securities or assume ISIN always exists.
- **Downstream mutation risk:** old sequential pipeline changes `PriceRecord` current rows, may skip invalid records, uses lossy decoding and first ZIP member. OD-05R must not directly invoke the existing writer or silently switch it to the new parser.
- **Version/provenance:** semantic hash excludes operational timestamps, but must bind exact parser/ref/schema/source scope and immutable row identities. Prevent synthetic cached/seed/in-memory data from being transformed into official labels via a forged reference ID.
- **Resource limits:** current illustrative `Limits` cap body 2MB, decoded 8MB, 10,000 rows, ZIP ratio 100; these are synthetic budgets, not certified production limits. Reproduce resource exhaustion against bounded synthetic fixtures before recommending new official limits.
- **Unverified statuses:** a reference index link, MIME extension, document heading, or hash copied from an agent-written JSON must never suffice for `OFFICIAL_REFERENCE_VERIFIED`.
- **No vacuous pass:** missing, empty, truncated or moved reference directory or expected samples must refuse. Independently pinned expected document and sample counts must be compared with observed, not computed from the service's own inventory.

## 06 — Negative-first executable verification groups

Before adding or editing application code, freeze ALL planned tests and fixture hashes, run against HEAD and classify results: **genuine old-behavior failing assertion**, **new API absent**, **missing reference/rights** or **test/harness error**. Do not credit import errors as legacy defects. No later-added test may be backdated. Recommended `tests/unit/test_od05r_reference_evidence.py` and separate `tests/unit/od05r_reference_oracle.py`.

At minimum **R01–R24**, with original/test IDs, purpose, oracle, expected, executed outcome, timestamp and file SHA:

R01 — no-source/missing directory refuses non-vacuously, no successful zero reference count; R02 — malformed/duplicate JSON keys; R03 — raw original byte SHA and wrong length; R04 — paraphrase hash never used as original document hash; R05 — false issuer/official/approved flag cannot authorize; R06 — pending legal rights refuse status promotion; R07 — paper document-only evidence cannot certify a CSV row; R08 — sample-only evidence cannot certify a schema; R09 — divergent authentic claims create conflict; R10 — explicit dates and overlapping intervals retain ambiguity; R11 — multiple spec versions and superseded documents remain separate; R12 — wrong segment (FO vs CM), exchange or source refuses; R13 — BSE records never inherit NSE authority; R14 — synthetic and cached/seed origin non-escalation; R15 — secrets in URL/path/report redacted; R16 — Unicode/canonical/malformed date and version bounds; R17 — traversal/symlink/junction/UNC/relative escapes; R18 — bounded document/sample bytes and case/entry budgets; R19 — corrupt/missing/moved pinned expected corpus refuses; R20 — deterministic versioned reference digest across OS, with timestamps non-semantic; R21 — no HTTP/DNS/process/protected writes under guarded collection and execution; R22 — existing `parse`, `parse_archive`, OD-01/OD-02/OD-04/OD-05 synthetic behavior unchanged; R23 — independent stdlib reference-envelope oracle and intentional tamper negatives; R24 — full runtime/quality/security regression and evidence/preservation gate.

For a format-specific parser extension, define **F01–F12** before production-code edits: actual permitted raw bytes and full SHA, actual ZIP member/CSV schema, source era/cutover checks, trade/business dates, Decimal prices, volume units, source row index, ISIN/series/scrip identity, unknown/optional columns, original sample expected rows, invalid format negatives, replay/rights/lineage. If authentic corpus missing, F-cases are `BLOCKED_REFERENCE` and do not count toward official acceptance.

The independent comparator must be stdlib-only and must not import the verifier or parser-under-test to calculate expected hashes/fields. Use pinned literal inputs and independently authored canonical reference layouts. Deliberately mutate issuer, timestamp, original-byte hash, reference version, file length, numeric row and expected-count separately; all must fail as designed. Preserve all actual red results and classify correctly.

## 07 — Approved implementation files and no-surprise scope

After negative-first freeze, OD-05R may **add**:
- `src/omegadata/parsers/reference_evidence.py` and `era_matrix.py` (or minimal equivalent names); no network/IO on import;
- `tests/unit/test_od05r_reference_evidence.py` and `tests/unit/od05r_reference_oracle.py` and controlled synthetic fixture helpers;
- `docs/omegadata_v2/implementation/od05r/<UTC-run-id>/` reports, design, reference metadata, raw command logs; optionally `docs/omegadata_v2/decisions/od05r_reference_contract.md` as additive ADR;
- narrowly scoped additions to `src/omegadata/parsers/reference_registry.py`, `contracts.py` or `dispatch.py` ONLY if a real negative test demonstrates an issue and existing synthetic APIs/semantics remain unchanged. Prefer a separate service to avoid unnecessary changes.

**Do NOT modify by default:** `source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `sequential_pipeline.py`, `storage.py`, `db/models.py`, old tests/oracles, config/source rights, CI, dependencies, release/signing/warehouse, production dataset or history. Reference authenticity is not authorization to modify production routing. No real source web requests, provider access, market CSV/ZIP acquisition or automated historical backfill.

Source file and test authorship must stay reversible: compare exact current blob/SHA before each changed path; no broad formatting. A parser extension under new filenames is allowed only when A+B evidence and lawful scope are demonstrable. If any potentially important new defect is found in an excluded original file, log an exact test/reproducer and a **separate narrowly scoped amendment request**, rather than silently editing it.

## 08 — Cross-platform, security, and reproducibility

Run fresh **offline**, **disposable**, guarded test sessions (no source/dataset original writes) with the exact suitable interpreters available:

1. Windows Python 3.14; Windows Python 3.11; native-filesystem WSL Linux Python 3.12. Use existing verified environments where appropriate, without installing or upgrading dependencies into originals.
2. `python -B -m pytest -q tests/unit/test_od05r_reference_evidence.py -m 'not realdata'` in an isolated guard; then full targeted OD-01/OD-01R/OD-02/OD-02V/OD-04/OD-04R/OD-05 suites and `python -B -m pytest -q -m 'not realdata' --cov=omegadata --cov-branch` under the guard. If the existing runner requires explicit label/cwd parameters, use it as audited, never invoke a normal unmanaged run against production paths.
3. `python -B -m ruff check --no-cache src/omegadata tests scripts`; `python -B -m mypy src/omegadata`; `python -B -m pip check`; source compilation; `git diff --check`. Record exact executable, argv, cwd, UTC start/end, real process exit and stdout/stderr per command.
4. Guard network operations: DNS/TCP/UDP, HTTPX/urllib/curl adapters, proxies, browser commands, subprocesses and writes to original/secret/dataset roots. Test the guard itself with safe synthetic-denial probes. The test guard is trusted Python, not an arbitrary-code kernel sandbox.
5. Compare precise skip node IDs across Windows and Linux, verify each privilege-specific skip genuinely runs on another supported platform. Four `realdata` deselections do not become passes. Do not suppress SQLite warnings or lie about incomplete coverage.
6. Verify tested-source and fixture hashes, exact old-source preservation, archive rights and full byte identity. Output deterministic machine-readable evidence and independently pinned expected counts. Re-run failed tests after corrections, retain old failures and timestamps. If a required platform is unavailable, verdict `BLOCKED_PLATFORM`, not fabricated PASS.
7. Performance: bounded synthetic reference bundles, measure actual time/RSS or tracemalloc (label what it measures), bytes and file count. Do not claim official capacity, third-party speedup or performance budgets without a baseline.

## 09 — Required evidence documents (fresh directory, never overwrite old)

Produce these twelve numbered Markdown reports plus raw JSON command logs, source/fixture hash ledgers and independent verifier output:

- `00_preflight_and_permissions.md`: branch/HEAD/commit, actual user authority limited to OD-05R, current rights and protected paths; existing G0/G1 recognized, not regenerated.
- `01_publisher_reference_inventory.md`: real page/circular/catalogue version/source evidence, exact original bytes if acquired, lawful use, issuer/URLs, UTC retrieval metadata; distinguish original vs mirror.
- `02_era_transition_evidence_matrix.md`: 2019/2020 and June/July 2024 boundary/overlap/session/format/date semantics with explicit unknowns.
- `03_reference_contract_and_repo_selection.md`: frozen schema/state/ADR and stdlib-vs-existing-dependency choice; no new vendor without evidence.
- `04_precode_R01_R24_and_F01_F12.md`: complete pre-code test/fixture freeze, exact classification, missing refs and process chronology.
- `05_code_delta_and_compatibility.md`: exact new/changed code SHA, default-off behavior, backwards API tests, no prohibited mutations.
- `06_independent_reference_oracle.md`: separate expected values/hash/counts, missing/corrupt/forged negative and actual output comparison.
- `07_source_rights_PIT_security.md`: current pending/revoked decisions, no egress, no false official/PIT promotion, confidentiality and residual risks.
- `08_runtime_coverage_evidence.md`: fresh Windows/Linux matrix/coverage/skip/commands/actual exits, not historical counts.
- `09_remaining_defects_and_rollback.md`: P0 signing custody, P0 publication bypass, P1 2020 cash routing/official schema/identity/calendar/PIT/Parquet overwrite and new defects; no silent waiver.
- `10_gatekeeper_verdict.md`: distinguish `OD05R_REFERENCE_VERIFIER_TECHNICAL_PASS_REFERENCE_PENDING`, `OD05R_OFFICIAL_REFERENCE_SUBGATE_PASS`, `BLOCKED_REFERENCE`, `BLOCKED_PLATFORM`, `BLOCKED_SECURITY`, or `BLOCKED_REGRESSION` according to actual evidence; no false official certification.
- `11_single_next_request.md`: exactly ONE next user/owner authorization request based on what is outstanding: supply permitted authentic docs+samples / approve exact-file routing change / after OD-05 official acceptance consider OD-06. Do not start later phases.

Machine-readable `reference_registry.od05r.json`: include status, issuer, source/segment, exact version, proof URLs/doc IDs, retrieval mode and real UTC, original-file size+SHA only when actual bytes were lawfully obtained, rights decision, sample proof and blocker codes; never invent missing provenance.

## 10 — Stop/go matrix

| Case | Required disposition |
|---|---|
| New reference verifier tests pass; official docs/samples missing | `OD05R_REFERENCE_VERIFIER_TECHNICAL_PASS_REFERENCE_PENDING`; no official parser or production route changes. |
| Authentic document A verified, representative row B missing | Document/reference-contract success only; `ROW_REFERENCE_PENDING`; no official parser claim. |
| A+B independently supported in explicitly permitted local corpus | Versioned **opt-in** official-format parser extension may be tested; still NO production route change. Exact limits and independent review remain required. |
| Reference conflicts, uncertain dates/schema/permissions | `BLOCKED_REFERENCE` for affected era; retain historical unknowns and preserve existing data. |
| Any security, source-rights, preservation, lint/type/required-platform failures | Gatekeeper blocked with actual exit codes and minimal scoped correction plan; do not continue to OD-06. |
| All eligible parser/reference technical checks pass but P0 signing/release issues remain | Clearly limit verdict to parser/reference technical scope. No release, main merge, live access or trading certification. |

## 11 — Engineering discipline and final return format

Run AEF Maker → Reviewer → Implementer → Gatekeeper → Historian as **procedural roles**, never pretend multiple independent human approvals. Every major code step starts with a falsifiable test/oracle; no silent skip, no claim that missing import is an old defect; retain initial failures and corrections. Reuse existing components rather than broad rewrite. Support the existing namespace and Python 3.11 minimum. No extra paid services or dependency adoption by wishful thinking.

Return to the user: actual reviewed branch+SHA; exact human-approved OD05R scope; which documents were authenticated vs indexed only vs missing; tested example raw SHA/format/version/rights; exact changed paths; R01–R24 (and F01–F12 if applicable) per-node outcomes; all platform execution counts/skip/deselections and quality exits; independent oracle results; any unresolved code or rights issues; honest Gatekeeper verdict; exactly one next decision request. **STOP** after OD-05R. No commit/push/PR/merge or unapproved phase work.
