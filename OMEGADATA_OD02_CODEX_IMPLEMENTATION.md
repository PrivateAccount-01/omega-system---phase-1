# CODEX EXECUTION CONTRACT: OmegaData OD-02

## 0. Invocation and authorization boundary

**Phase:** `OD-02: IMPLEMENT_DETERMINISTIC_DIRECT_ACQUISITION_ONLY`  
**Repo:** `https://github.com/PrivateAccount-01/omega-system---phase-1`  
**Starting branch:** `feature/od01-source-rights` unless an approved successor branch has been explicitly selected.  
**Historical baseline commit (recheck current HEAD):** `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`.  
**Prerequisite:** OD-01R latest Gatekeeper result must be `OD01R_TECHNICAL_PASS` and its code contract reviewed. **If OD-01R has not passed, do not implement OD-02.**  
**Operating posture:** **offline synthetic/mocked acquisition only**; no NSE/BSE/GDELT or other provider requests; no paid tools, broker use, derivatives-trading actions, publication, source-rights approvals, secret handling, or production service access.  
**Phase end:** after offline implementation, full authorized verification, and report. Never silently begin OD-03 or OD-04.

### Required reading

Inspect real current paths, not historical guessed paths:

- Root `AGENTS.md` (if OD-01R added it) and `OMEGADATA_AGENTS.md`, resolving any conflicts.
- `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md` and `docs/verification/OMEGADATA_OD01_CODEX_NEXT_PROMPT.md`.
- OD-00 audit and plans at `docs/omegadata_v2/audit/` and `docs/omegadata_v2/plan/`.
- OD-01 evidence and new OD-01R evidence, especially tests, source-policy schema, Gatekeeper verdict, code diffs, and deferrals.
- Runtime files: `src/omegadata/track_a/{source_registry,download_manager,source_rights,orchestration}.py`, `src/omegadata/pipelines/sequential_pipeline.py`, `scripts/generate_source_probe_report.py`, related test modules/fixtures, and all transport/redirect/parse utilities these call.
- Any current `config/source_rights_policy.v1.json` and relevant source-era registry entries.

Read complete files needed for your patch, not merely the README. Check current Git branch, SHA, status and `main...HEAD` diff. Do not overwrite pre-existing modified files. Avoid `git clean`, `git reset --hard`, stash, force update, database reset and editing historical proof artifacts. Use a new run ID and entirely new evidence directory. No commits/pushes/PRs unless separately authorized.

## 1. Product requirement and non-goals

**Objective:** build a deterministic, source-rights-aware, safe direct-acquisition component whose success means *the requested bytes passed bounded transport and source-era validation*, not merely that an HTTP request returned status 200. Preserve the existing OmegaData architecture and correct D-05 (HTML denial can pass NSE equity raw validator) and D-12 (provider 403/429 can retry across candidates/profiles). Bring direct and fallback transports under one coherent source-policy, attempt-budget, redirect, content and provenance contract. Do not replace ingestion with dlt unless a measurable, scoped pilot justifies it.

**DO NOT:**
- Activate any `PENDING_REVIEW` source, manufacture a legal/terms approval, or silently invent a source/use authorization.
- Perform live market requests. Any live smoke must be an independently authorized future action specifying exact source, URL/host, transport, time window, usage rights, request budget and storage boundary; this phase grants none.
- Add Obscura, Playwright, browser stealth, CAPTCHA workarounds, IP rotations, alternate domains used to evade rate/access limits, or third-party paid data tools. Optional browser comparison is OD-03.
- Rewrite adjusted OHLCV, universe, corporate actions, point-in-time data, Parquet releases or signing/warehouse code. Their P0/P1 defects remain assigned to later stages.
- Assert profitable results, alpha, better strategy quality, legal suitability of a data source, or production release readiness.

## 2. Starting audit and exact suspected implementation gaps

Prior inspected feature source contained:

1. `_request_once`: raises `DownloadError` for 403/429; `_request` retries `(httpx.HTTPError, DownloadError)` before checking terminal status. The outer `download()` exception loop continues through header profiles/candidate URLs. `_bootstrap_nse_session` may continue after 403. `probe_source_candidates()` can continue profiles after request denial. Discovery helpers may suppress provider denial. **Fix the entire call graph, not a single exception handler.**
2. `curl --location --retry 2 --retry-all-errors` and standalone probe `curl -L`: uncontrolled redirect/retry behavior incompatible with allowlisted source rights. `urllib` automatically follows redirects unless explicitly controlled. HTTPX clients use `follow_redirects=True`. **Do not assume initial hostname preflight also validates every network hop.**
3. `NSE_EQUITY_BHAVCOPY` falls through generic nonempty-text validation in `_validate_payload`. Nonempty HTML access-denied response is not a genuine bhavcopy. Other source handlers may accept partial CSV/JSON and unbounded ZIP inputs. **Implement correct structural validation per format/era.**
4. `_request_via_urllib` reads response bytes without an explicit size bound; curl writes to temporary files with no consolidated payload cap. ZIP member extraction requires decompression limits. **Add bounded resource controls.**
5. Multiple nested retry loops have separate budgets; an apparent 5-attempt inner limit can become far more than 5 actual HTTP calls. **Count real attempts across bootstrap, discovery, fallbacks and profiles; distinguish successful data retrieval, validation failures, and denied requests.**
6. Existing source policy is a precondition but does not yet enforce complete DNS/private-network, redirect, final response URL, or post-fetch use rights. OD-01R should already reject bad URL ports/schemes. **Build on its result rather than bypassing it.**
7. Existing `DownloadManager` raw writes are not atomic and canonical Parquet writes can overwrite. **Do not claim immutable storage is solved in OD-02; record handoff to OD-04.**

These are actual source-inspection leads requiring fresh failing tests. If current code differs, document accurate line numbers and revise the test hypothesis.

## 3. Architecture: interface boundaries

Implement a simple, stable, internal design. Favor existing `httpx`, stdlib `zipfile/csv/json/hashlib`, and current source registry/Pydantic policy. Introduce a new module only where it reduces complexity and has a minimal public API. Proposed logical stages:

`Authorized SourceRequest` → `Policy Decision / Bounded Budget` → `Endpoint / Transport Adapter` → `Per-Hop Guard` → `Transport Result` → `Payload Validation` → `Provenance Candidate` → `existing raw archival contract (OD-04 later)`.

### 3.1 Source request contract

At minimum: registered `source_key`, requested market date, business purpose, requested transport, source-era identity, candidate URL, source-policy revision, global attempt budget, operation deadline, response byte limit, archive-expansion limit, and allowed content types. All budget numbers must be **explicit configuration values**, justified by current source policies and bounded; do not invent permissions from defaults. If configuration is absent or invalid in an external-acquisition path, fail closed.

### 3.2 Typed outcomes

Use structured failure classes/reason codes suitable for upstream no-retry decisions, for example:

- `POLICY_DENIED`, `POLICY_PENDING`, `POLICY_REVOKED`, `SOURCE_UNREGISTERED`.
- `HTTP_ACCESS_DENIED` for 401/403/451 or other explicit access-control responses.
- `HTTP_RATE_LIMITED` for 429: terminate the **current job**, record permitted cooldown if policy allows future scheduling, do not immediately evade via a different host, profile or transport.
- `HTTP_NOT_FOUND` for valid absent date/artifact: non-retryable absent-source classification, not synthetic zero-price data.
- `HTTP_TRANSIENT` for allowed finite retry of selected 5xx/network timeouts.
- `REDIRECT_NOT_ALLOWED`, `DESTINATION_NOT_ALLOWED`, `PRIVATE_NETWORK_BLOCKED`, `TLS_INVALID`, `UNSAFE_URL`.
- `PAYLOAD_EMPTY`, `PAYLOAD_HTML_DENIAL`, `ARCHIVE_INVALID`, `ARCHIVE_TOO_LARGE`, `ZIP_ENTRY_UNSAFE`, `SCHEMA_UNKNOWN`, `TRADE_DATE_MISMATCH`, `PARTIAL_PAYLOAD`, `ENCODING_UNSUPPORTED`, `HASH_MISMATCH`.
- `ATTEMPT_BUDGET_EXCEEDED`, `TOTAL_DEADLINE_EXCEEDED`, `BODY_LIMIT_EXCEEDED`, `INTERNAL_ERROR`.

Typed public errors should preserve source/date/transport/candidate/policy/attempt counts (not credentials or body secrets). Preserve backwards-compatible `DownloadError` surfaces where needed; make terminality explicit rather than matching fragile error-string substrings.

### 3.3 Authorization per hop

Do **not** use `follow_redirects=True`, stdlib auto redirect, or curl `--location` with no interception/authorization. Every planned redirect destination must be checked before any connection; disallowed redirects stop immediately, with zero contact to the new host. Choose one of: (i) no redirects by default (preferred initially), or (ii) explicit bounded redirect handler with separate authorization for each hop. Treat HTTPS downgrade, new host, nonstandard port and userinfo as denied unless source-specific human approval explicitly allows them. No credential/cookie forwarding to a new host by default. Record actual original and final URLs without leaking secret tokens.

Guard against private/loopback/link-local/metadata/reserved destinations and DNS rebinding. **A one-time hostname lookup is not a sufficient security proof**, because resolution at connect time may differ. Prefer constrained transport/egress settings and isolated execution; document and test the precise boundary. If address-level control cannot be demonstrated, keep the provider network path disabled and mark `BLOCKED_EXTERNAL_EGRESS` rather than implement a sham control.

### 3.4 One bounded retry budget

Create one coherent request budget across `download -> candidate discovery -> bootstrap -> profile -> HTTPX / urllib / curl`.
- Count **actual network attempts**, not merely outer-loop counters.
- Enforce `max_attempts` and an absolute deadline at the whole-job level; nested components cannot reset it.
- Backoff only for approved transient cases. Never retry forbidden access, source-rights refusal, login/HTML denial, unsupported format, bad business date, revoked rights or 429 within the current job.
- For 429, record `Retry-After` if present and valid without using it to retry immediately, switch domains or bypass source limits.
- Candidate fallback must be a documented legitimate availability fallback, not an access-denial circumvention.
- Avoid sleeping in unit tests; inject fake clock/backoff and deterministic schedules.

### 3.5 Payload validation before success

A response is `ACQUIRED_VALIDATED` only when all relevant checks succeed. Keep distinct stages `HTTP_RECEIVED` / `RAW_BYTES_CAPTURED` / `PAYLOAD_STRUCTURALLY_VALID` / `FINANCIAL_CONTENT_RECONCILED`; OD-02 certifies structural validity and market-date identity, not independent financial truth (later OD-05/09).

Build **source-era-specific parsers/validators** for at least NSE equity legacy and newer Bhavcopy format. Inspect `SOURCE_REGISTRY` era ranges, current fixtures, actual historic CSV column mappings, and reference archives **only if allowed locally**; do not assume a single modern header applies to 2010 data. Validate:
- expected ZIP magic and complete central directory; no silent acceptance of HTML/text in place of ZIP;
- reasonable bounded compressed/uncompressed sizes, entry counts, nesting, duplicates and zip-slip names; reject encrypted/path traversal member names;
- one or clearly identified expected CSV member; deterministic selection with explicit reason; no silently choosing arbitrary member;
- allowed encoding(s) with explicit failure policy; no `errors='ignore'` for fields where corrupted bytes affect content;
- required columns by source era, correct date formats and exact requested trade date;
- at least one valid trading row where expected; row structure, numeric prices/volume semantics, duplicate keys and field count; distinguish legitimate market zero-volume rows from errors;
- no negative numeric values where disallowed, no price inversion (high lower than low, etc.) and no silently coerced NaNs;
- content-type mismatches and HTTP 200 login/error pages fail, even if the body is nonempty;
- source provenance and fetch vs cache/seed identity remain unchanged; synthetic fixture results never counted as live official data.

Where an older legitimate format is not provable from current material, record `SCHEMA_UNKNOWN` and quarantine. Do not invent headers. Source-specific semantics for options/futures/sidefeeds may remain explicitly deferred if not part of approved OD-02 target but generic validators must never label invalid content a successful verified source.

### 3.6 Storage handoff

Preserve exact source bytes and SHA-256. Append (do not falsify) policy decision, URL, effective transport, HTTP status, content type, byte count, source requested date, payload parser/schema identifier, and acquisition state. Keep `source_seed_imported`, `source_cached_raw`, `source_acquired_live` distinct. No production cache/data rewrite; create a source candidate in a disposable namespace, and leave full content-addressed atomic publishing to OD-04. Do not overwrite `latest` pointers in existing data or release locations during test runs.

## 4. Repository-first candidate evaluation

Candidate A: **existing OmegaData DownloadManager + httpx + stdlib parsers (default)**.  
Candidate B: **dlt** (`https://github.com/dlt-hub/dlt`) as optional wrapper for source-independent API pagination/loading, not automatic source-rights enforcement.  
Candidate C: **Scrapy** (`https://github.com/scrapy/scrapy`) only if source workload genuinely requires crawling; otherwise defer.  
Optional browser: **Obscura** (`https://github.com/h4ckf0r0day/obscura`) vs Playwright, **OD-03 only**, no code here.

For each candidate, record actual version/commit/license, known direct/indirect dependencies, Windows/Python 3.11 compatibility, public API behavior, source-specific fit, security/maintenance status, estimated setup cost and integration surface. Public source-code/docs lookup may occur only when approved by the environment; no external exchange/provider requests. **Do not install anything just to fill the matrix.** Prefer `EXTEND_EXISTING` unless an independently executed local mock benchmark demonstrates a material benefit from adoption. No invented upstream performance or maintenance claims.

## 5. Negative-first test suite (mandatory minimum)

Implement `tests/unit/test_od02_acquisition.py` with real assertions and fake HTTPX/urllib/curl transport or subprocess boundary. Every case needs a traceable red/green result where existing behavior is wrong. Tests must be deterministic and network-denied even if an earlier fixture sets synthetic `APPROVED`.

| ID | Case | Expected outcome |
|---|---|---|
| T01 | NSE equity HTTP 200 with HTML Access Denied | REJECT with `PAYLOAD_HTML_DENIAL`, no accepted data/write |
| T02 | NSE ZIP truncated or corrupt central directory | REJECT; deterministic stage/reason |
| T03 | NSE ZIP with CSV wrong trade date | REJECT `TRADE_DATE_MISMATCH` |
| T04 | ZIP bomb/member count/excess size | REJECT before excessive extraction or memory allocation |
| T05 | Correct legacy NSE ZIP with verified-era fixture | ACCEPT structurally, record schema/era, preserve raw bytes |
| T06 | Correct newer NSE ZIP with verified-era fixture | ACCEPT structurally, correct date/columns |
| T07 | Missing/duplicate/garbled CSV columns and rows | REJECT or quarantine with exact reason |
| T08 | BSE CSV/ZIP representative authorized synthetic fixtures | Correct schema/date decisions, no regression |
| T09 | JSON endpoint returns HTML/login/"missing index" | REJECT, no false success |
| T10 | Fake HTTPX 403 | One current-job terminal deny, zero later candidates/profiles/transports |
| T11 | Fake HTTPX 429 with Retry-After | One current-job terminal throttle; no immediate alternate host/transport |
| T12 | 401/451 and known forbidden responses | Terminal deny, no network follow-up |
| T13 | 404 date absent vs 503 transient | Typed absent versus bounded approved transient retry |
| T14 | Mock redirect from allowed host to disallowed host | Zero requests to redirected host |
| T15 | Allowed-to-allowed redirect under explicitly approved synthetic policy | Enforce cap/authorization and preserve hop record if redirects supported; otherwise refuse all redirects by design |
| T16 | HTTPS downgrade, nondefault port, malformed URL | Reject before any request |
| T17 | Local/private/metadata endpoint / DNS rebind simulation | No connection; if runtime cannot guarantee, mark external egress blocked |
| T18 | Cross-transport fallback HTTPX → urllib → curl | Transport-specific authorization, one global attempt budget, no cookie leak |
| T19 | Strict total timeout, response body bound, zip bound | Stop with reason; no orphaned file/partial trusted artifact |
| T20 | Source rights PENDING/REVOKED mid-workflow | Deny at relevant operation boundary; never store/publish payload under invalid policy |
| T21 | Cache-only path with no valid artifact | Must not escalate to network fetch |
| T22 | Valid mocked fetch + cache | Exact bytes/hashes, distinct source mode, reproducible evidence, no extra request |
| T23 | Concurrency, repeated request, idempotent candidate staging | No mixed outputs; no read/write to original dataset paths |
| T24 | Source-probe script curl and NSE bootstrap | Identical refusal and redirect/attempt limits to manager, no hidden bypass |
| T25 | Old OD-01/OD-01R tests | All still passing |
| T26 | Full offline suite, lint, type, pip | Real outputs and accurate exits |

All fixtures must be marked `SYNTHETIC_TEST_ONLY` unless already independently authenticated. Never invent official-source circulars, access rights or provider availability. For cases requiring actual source validation, record `SOURCE_REFERENCE_PENDING` and do not claim financial-data certification.

## 6. Implementation sequence and stopping checkpoints

**Stage 0: Preflight**: inspect git HEAD, dirty worktree, Python interpreter, files and upstream docs. Reconcile OD-01R Gatekeeper. If not PASS, STOP.  
**Stage 1: Design**: write concise ADR for existing versus dlt, source-budget model, transport redirect policy, era validator contract, error taxonomy; run adversarial design review.  
**Stage 2: Red tests**: implement T01–T26 negative fixtures; run expected failures; store exact logs and assert they reflect missing behavior, not a broken test harness.  
**Stage 3: Bounded code**: make minimum production edits in DownloadManager and closely related parser/transport helpers and the canonical probe; no warehouse/universe/signing/release edit.  
**Stage 4: Green targeted tests**: get exact targeted acceptance with isolated no-network harness and reproducible logs; no skipped tests hidden as pass.  
**Stage 5: Regression and security review**: run full offline suite with permissions, static lint/type, parse integrity, cross-platform smoke if available, safety review of all HTTP/curl/urllib, reviewer independent wherever available.  
**Stage 6: Gatekeeper and stop**: never advance to OD-03/04, never enable live source policies, never publish releases.

When tests identify an unrelated P0/P1 issue in signing, release promotion, PIT or corporate-action calculation, log it as inherited blocker with minimal safe containment; do not expand OD-02 into a blanket rewrite.

## 7. Practical execution commands

Run commands **only after verifying their side effects and using an isolated test harness**. Example PowerShell commands, replacing paths if the runtime differs:

```powershell
$py = '.venv/Scripts/python.exe'
& $py --version
& $py -m pytest --collect-only -q -m 'not realdata' -p no:cacheprovider
& $py -m pytest -q tests/unit/test_od02_acquisition.py tests/unit/test_od01_source_rights.py -p no:cacheprovider
& $py -m pytest -q -m 'not realdata' -p no:cacheprovider
& $py -m ruff check --no-cache src/omegadata tests scripts
& $py -m mypy src/omegadata
& $py -m pip check
```

The above pytest command lines **do not alone prohibit network calls**. Use a reproducible, isolated no-egress runner derived from audited OD-01/OD-01R verification harness with new log path and test output directories, blocked socket/subprocess calls, mock transports, disposable SQLite/raw/seed/release/parquet paths, disabled pytest cache and bytecode or redirected caches. Never execute market-data integration tests merely because the marker is missing. Inspect imports/test fixtures that may attempt network at startup. Do not run historical release or signing scripts to produce fresh-looking green JSON.

If in Linux, use the actual venv interpreter; where Python 3.11 cannot be installed or the dependency set is not resolved, accurately mark platform verification BLOCKED. Do not change existing dependency pins or install new packages without approval.

## 8. Mandatory preservation and security rules

- No source policy approval modification; the 13 real sources stay pending.
- No modification to historical `data/`, `artifacts/`, signing GnuPG or old verification logs, main branch, latest release pointers or user uncommitted files.
- No exchange requests, no retry/transport evasion, no stealth/captcha, no synthetic mock mistaken for live truth.
- No raw credentials in command line or test logs; no reading secrets, key files or production `.env` beyond permitted config keys.
- No arbitrary executable download, dependency upgrade, container start or live service access.
- If a negative test reveals credential exfiltration or external network access, stop immediately, report sanitized details, and seek security-owner review.
- Hash-valid data can still be financially wrong. OD-02 proof is transport/structural correctness, not official authenticity or profitable strategies.

## 9. Required output artifacts

Use new run directory `docs/omegadata_v2/implementation/od02/<run-id>/` with:

1. `00_preflight.md`: git/OS/environment/preservation; exact previous approval gate evidence.
2. `01_repo_selection.md`: URLs, pins/licenses, measured alternatives or DEFER, reasons and dependency risks.
3. `02_design_and_adrs.md`: data contract, error taxonomy, redirect/SSRF, retry budget, legacy compatibility.
4. `03_red_green_test_matrix.md`: every T01–T26 actual test name, result, logs and exit code; no placeholder PASS.
5. `04_implementation_diff.md`: actual changed file list and backward compatibility.
6. `05_security_failure_analysis.md`: source rights, 403/429 behavior, source redirects, DNS/private IP, budgets, TLS, body/zip safety; exact unverified risks.
7. `06_evidence_and_coverage.md`: exact requested vs executed commands, counts, deviations, pytest warnings/coverage, SHA and environment.
8. `07_remaining_defects.md`: open P0/P1, OD-04/05/06/07/08/09/10/11/14 ownership, independently verifiable source rights unknowns.
9. `08_gatekeeper_verdict.md`: `OD02_OFFLINE_TECHNICAL_PASS | BLOCKED | REJECT` with criteria; NEVER label live source ready.
10. `09_next_phase_request.md`: OD-04 immutable archive versus optional OD-03 browser and financial/approval gates, exact next proposed action only.
11. `logs/` unique timestamps, raw command outputs and structured machine-readable result evidence. No overwriting previous logs.
12. An updated targeted repo-decision file (e.g. `docs/omegadata_v2/decisions/od02-direct-acquisition-reuse.md`) with `EXTEND_EXISTING / ADOPT / WRAP / DEFER / REJECT` grounded in evidence.

## 10. Gatekeeper criteria

`OD02_OFFLINE_TECHNICAL_PASS` is permissible **only** when:
- OD-01R passed beforehand and no contradictory authority exists;
- all applicable T01–T26 assertions actually executed and pass; any blocked scenario is reflected as BLOCKED rather than excluded from denominator;
- provider 403/429 and source-policy refusal cannot route around denials;
- each source/network hop is authorized or external egress remains disabled;
- validated payload cannot be HTML error, wrong date, corrupt archive, invalid schema or unbounded decompression;
- no unauthorized network request, payment, release, broker operation, secret mutation or historical dataset overwrite occurred;
- full relevant regression, static checks and explicit warnings reported;
- no new P0/P1 in OD-02's own scope remains unaddressed;
- an independent verifier has reviewed the financial/source-specific interpretation or that review remains visibly pending and live certification blocked.

**Always report:** branch+HEAD, files changed, baseline vs final counts, exact commands and exits, execution environment, coverage and unverified dimensions, source policy state (13 pending, 0 approved unless human performed separate authorized action), status of D-01/D-04 and every new/remaining P1, and the single next approval request.

**STOP after OD-02.** Do not integrate Obscura, Qlib, RD-Agent, strategy models, broker APIs or trading code in this phase. OmegaData must be correct and auditable before downstream intelligence uses it.
