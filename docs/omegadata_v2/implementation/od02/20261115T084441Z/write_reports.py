"""Create the OD-02 report set from actual retained evidence; exclusive writes."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
ROOT = Path.cwd()
SHA = "3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc"
BRANCH = "feature/od01-source-rights"
banner = f"Branch `{BRANCH}`; unchanged HEAD `{SHA}`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.\n\n"


def write(name, body):
    with (HERE / name).open("x", encoding="utf-8", newline="\n") as file:
        file.write(body)


write("00_preflight.md", "# OD-02 preflight\n\n" + banner + """
## Approval and preservation

Read the supplied OD-02 execution contract, automatic instruction facade, repository operating instructions, master and OD-01 instructions, OD-00 audit/plans, OD-01 evidence and complete OD-01R reports/code contract. Runtime registry, policy, downloader, orchestration, sequential pipeline, canonical probe and affected tests/transport helpers were inspected. No nested agent instruction files were discovered under source/tests/scripts/config. No sub-agent or independent human approval is claimed.

The prerequisite is [OD-01R Gatekeeper](../../od01r/20261115T065155Z/06_gatekeeper_verdict.md), `OD01R_TECHNICAL_PASS` for its executed Windows scope. Its [final reviewed QA](../../od01r/20261115T065155Z/logs/final-qa-reviewed.json) passed. The existing ten-file uncommitted patch matched its [reviewed patch](../../od01r/20261115T065155Z/logs/implementation.patch) byte for byte before OD-02: [fresh patch comparison](logs/od01r-patch-match.json). These were known prior work from this conversation, preserved by layering explicit OD-02 changes. Previous environment limitations do not become new approvals.

Repository root/remote/branch/HEAD/main merge-base, status, main...HEAD diff, Python/packages and tracked signing paths were freshly recorded in [preflight JSON](logs/preflight.json). Main remains `d4b5a58f0c50dc348e0d4e1150a725cc6fab5674`. No index/branch/commit/push mutation occurred. Worktree was already dirty: prior OD-01R production changes, automatic instruction file, supplied prompts, OD-01R tests/ADR/evidence, existing Linux environment and signing/revocation paths. No cleanup/stash/reset or source approval was performed.

[Before snapshot](logs/preservation-before.json) covers original tracked files, data/artifacts/root databases, source/tests/config, old OD-01R evidence/decisions and supplied prompts. Signing paths use length/mtime metadata only; key bytes were never opened or hashed. Final scope and preservation are checked in [final QA](logs/final-qa.json); exactly six prior files receive authorized OD-02 changes, plus three new implementation/config/test files. No historical report/data/release/signing changes are allowed.

## Execution environment and baseline

Windows 11 build 26300, PowerShell 5.1, repository `.venv/Scripts/python.exe` Python 3.14.3. Observed pytest 9.0.2, HTTPX 0.28.1, Pydantic 2.12.5, Ruff 0.15.9, mypy 1.20.0, coverage 7.13.5. Fresh baseline: **286 passed, 3 skipped, 4 realdata deselected**, exit 0; [command](logs/baseline.json), [output](logs/baseline.txt). The three file-symlink skips require unavailable Windows privileges; real junction cases execute.

The new [runner](verification_runner.py) derives from the audited OD-01R isolation harness: fresh temporary DB/raw/seed/reprocess/Parquet/release/report/GPG roots; blocked DNS/socket/subprocess; write audit outside disposable root refuses; explicit asyncio plugin only, cache/bytecode disabled. Windows internal socketpair is narrowly permitted for asyncio, not arbitrary connections. The harness self-test actually exercises prohibited DNS, subprocess, file and SQLite writes. Collection excludes the four realdata cases; no market/provider call, real signing or release-generation script is authorized. Package metadata and public upstream code lookup are read-only; no installs occurred.

Windows Python 3.11.15 and WSL Linux Python 3.12.3 were freshly inspected and targeted attempts made. Both lack pytest and necessary dependencies: actual **exit 1, ModuleNotFoundError**, not test failures or passes. See [Windows environment](logs/py311-environment.json), [attempt](logs/py311-targeted.txt), [Linux environment](logs/linux-environment.json), [attempt](logs/linux-targeted.txt). They remain BLOCKED. WSL also printed inherited missing drive/PATH translation warnings; no environment was repaired or installed.
""")

write("01_repo_selection.md", "# OD-02 repository-first component decision\n\n" + banner + """
Decision: **EXTEND_EXISTING**. No added dependency, downloaded executable, package install, browser integration or performance superiority claim. Actual current local behavior was measured by synthetic tests, not a throughput benchmark. Upstream lookups used only public GitHub/PyPI/documentation, never exchange/market endpoints.

| Candidate | Observed identity/license and API | Fit, cost, compatibility and decision |
|---|---|---|
| Existing OmegaData | Local 0.1.0 at the recorded HEAD plus reviewed OD-01R patch; project license metadata absent, not license-cleared. Downloader `download`, `probe_source_candidates`, existing policy/registry/raw/cache contracts | Existing integration and column mappings; add one small acquisition contract module, explicit resource config and guarded adapters. Synthetic regression measured here. Windows 3.14 runs; 3.11/Linux runtime verification BLOCKED. **EXTEND_EXISTING** |
| HTTPX and stdlib | Installed HTTPX **0.28.1**, BSD-3-Clause; `Client.stream`, explicit `MockTransport`, `follow_redirects=False`, `trust_env=False`; stdlib CSV/JSON/ZIP/hashlib | HTTPX direct dependencies include httpcore/anyio/certifi/idna. Observed httpcore 1.0.9 BSD-3-Clause, anyio 4.13.0 MIT, h11 0.16.0 MIT, idna 3.11 BSD-3-Clause, certifi 2026.2.25 MPL-2.0. Full installed dependency metadata retained below. No new setup. **EXTEND_EXISTING**; no advisory/security certification |
| dlt | Inspected [version-tagged pyproject 1.32.0](https://github.com/dlt-hub/dlt/blob/1.32.0/pyproject.toml): Apache-2.0, Python >=3.10,<3.15, Windows classifier. Typical API resource/source/pipeline loading; no built-in OmegaData rights/era certification | Requests, pendulum, tenacity, orjson, GitPython, sqlglot and Windows-specific pywin32 expand integration. Indirect closure and advisories were not resolved; no install or local benchmark. Estimated medium/high integration effort for policy-aware adapter plus loading semantics. No pagination/loading bottleneck demonstrated. **DEFER**, no adoption justified |
| Scrapy | Inspected [tagged pyproject 2.20.0](https://github.com/scrapy/scrapy/blob/2.20.0/pyproject.toml) and [license](https://github.com/scrapy/scrapy/blob/2.20.0/LICENSE): BSD-3-Clause, Python >=3.11, OS-independent metadata; Spider/Request/Response crawling interfaces | Twisted, cryptography/pyOpenSSL, lxml, parsel and other crawling dependencies; indirect closure/advisories unmeasured. Estimated high integration surface: scheduling, retries, redirects, middleware and policy budgets. No crawler requirement in fixed direct acquisition. Windows install not executed. **DEFER** |
| Obscura / Playwright | OD-03 only; no code/install/version/security review attempted | Browser acquisition not authorized or required. **DEFER** |

Version tags are inspected identifiers, not newly installed pins or independently verified commit hashes. Local metadata is exact to this environment; repository dependencies remain lower bounds. Upstream release metadata shows published support, not proof of this repository's runtime compatibility. No CVE scan or source-specific financial benchmark was performed. A dlt `LICENSE` URL returned 404; license classification comes from its tagged package metadata, not a claimed license-file review.

Evidence: [local license/dependency and syntax inventory](logs/parse-and-component-inventory-v2.json), [installed versions/preflight](logs/preflight.json), [full measured regression](logs/final-reviewed.txt), [targeted results](logs/targeted-final.txt). The separate [decision record](../../../decisions/od02-direct-acquisition-reuse.md) records the same bounded choice.
""")

rows = [
("T01", "test_t01_t04_t07_invalid_nse_never_validated", "HTML denial rejects; no structural acceptance"),
("T02", "test_t01_t04_t07_invalid_nse_never_validated", "Corrupt/truncated ZIP central directory rejects ARCHIVE_INVALID"),
("T03", "test_t01_t04_t07_invalid_nse_never_validated; test_t07_numeric_date_row_and_header_corruption", "Wrong member or row market date rejects"),
("T04", "test_t04_t19_expansion_encoding_and_declared_caps; test_t04_archive_unsafe_members; test_t01_t04_t07_invalid_nse_never_validated", "Bomb/expanded cap/member count/traversal/nested archive refusal"),
("T05", "test_t05_t06_valid_synthetic_era[True-day0]", "2019 legacy repository mapping structurally accepted; SOURCE_REFERENCE_PENDING"),
("T06", "test_t05_t06_valid_synthetic_era[False-day1]", "2026 UDiFF mapping structurally accepted; SOURCE_REFERENCE_PENDING"),
("T07", "test_t07_numeric_date_row_and_header_corruption; test_t07_content_type_mismatch; test_t04_t19_expansion_encoding_and_declared_caps", "Duplicate/missing headers, row widths/duplicates, NaN/negative/inverted prices, fractional volume and bad encoding refuse; zero volume accepted"),
("T08", "test_t08_bse_synthetic_modern_and_wrong_date", "BSE modern CSV/ZIP accept exact date, reject wrong date; existing BSE pipeline tests also green"),
("T09", "test_t09_json_denial_not_success; test_t09_json_strict_errors; test_t09_json_not_financially_verified", "HTML/error/missing-index/malformed/duplicate JSON reject; generic structure remains HTTP_RECEIVED"),
("T10", "test_t10_t13_terminal_status_no_later_candidate; test_t10_terminal_denial_entire_call_graph", "403 stops download/probe/bootstrap/discovery after one request"),
("T11", "test_t10_t13_terminal_status_no_later_candidate; test_t11_retry_after_and_typed_public_context", "429 terminal, Retry-After retained, attempts=1, source/date/transport context retained"),
("T12", "test_t10_t13_terminal_status_no_later_candidate", "401/451 terminal, no next candidate/profile/transport"),
("T13", "test_t13_transient_retries_bounded_and_recovers; test_t13_attempt_cap_stops_candidates_and_profiles; test_t10_t13_terminal_status_no_later_candidate", "404 terminal absent; selected 503 recovers in three calls or stops at global cap"),
("T14", "test_t14_t15_redirect_never_contacts_second_host; test_t14_t15_all_redirect_destinations_refused", "No redirected host contact"),
("T15", "test_t14_t15_all_redirect_destinations_refused", "Allowed-to-allowed redirects also refused; no hop following supported"),
("T16", "test_t16_t17_unsafe_destination_before_transport; test_t16_tls_invalid_is_terminal_no_fallback", "Bad scheme/port/userinfo/URL refuse before transport; TLS-invalid terminal"),
("T17", "test_t17_default_external_egress_disabled; test_t17_rebinding_and_env_proxy_never_resolved; test_t16_t17_unsafe_destination_before_transport", "Private/metadata/loopback denied; rebind resolver never called because actual egress disabled; not a DNS-pinning proof"),
("T18", "test_t18_cross_transport_budget_no_cookie_leak; test_t18_default_alternate_transports_disabled", "Three explicit fake HTTPX->urllib->curl attempts share budget; no Cookie/Authorization reaches adapter; default real alternatives disabled"),
("T19", "test_t19_deadline_includes_backoff; test_t19_transport_limits_before_write; test_t19_stream_growth_bounded; test_t19_configuration_fails_closed; test_t19_missing_and_malformed_configuration; test_t19_public_invalid_overrides_refuse_before_transport", "Deadline/stream/length/expansion/config/override bounds; no trusted partial output"),
("T20", "test_t20_revoked_after_mock_fetch_no_storage; inherited test_policy_change_is_rechecked_before_operation; test_r10_probe_bootstrap_scoped_mock_and_refresh", "Removed/revoked authority after fetch or bootstrap refuses before store/next request; inherited pending tests execute"),
("T21", "test_t21_cache_only_never_fetches", "Miss never escalates to network"),
("T22", "test_t22_valid_fetch_cache_hash_and_secret_free_evidence; test_t22_urls_sanitized_and_seed_mode_distinct", "Exact original bytes/SHA, cache vs seed vs mock-unverified identity, token-free evidence, no extra request"),
("T23", "test_t23_concurrent_dates_repeated_candidate_staging", "Four threads/eight jobs/three dates, repeated same candidates, exact separate bytes/manifests in disposable root"),
("T24", "test_t24_probe_bootstrap_terminal_and_redirect_budget; test_t24_probe_strict_validation_and_shared_budget", "Offline curl/bootstrap denials, redirect refusal, strict validator and shared cap; no real subprocess"),
]
matrix = "# OD-02 red/green acceptance matrix\n\n" + banner + """
The initial [negative-first log](logs/negative-first.txt) reproduced **16 failed, 2 passed**, exit 1, against unchanged production. The two valid archive positive controls passed. Failures included HTML/corrupt/wrong-date/schema/unsafe archive, JSON denial, terminal status, redirect and external-transport blocking. No failure involved actual provider contact. New complementary cases were added during bounded review; they are not falsely represented as pre-patch failures.

[Adversarial v1](logs/adversarial-v1.txt): 1 failed, 89 passed, exit 1; missing public typed error context was then implemented. [Override negatives](logs/overrides-negative.txt): 4 failed, 2 passed, 91 deselected, exit 1; zero/negative/NaN timeout and zero-attempt defaults were corrected. These are real defect reproductions, not missing-import failures. [Targeted v1](logs/targeted-v1.txt) additionally showed one old probe test expected arbitrary text to count as validated: the fixture became a genuine synthetic ZIP, with original policy assertions preserved.

Final [Windows full run](logs/final-reviewed.txt), [command/exit](logs/final-reviewed.json): **383 passed, 3 skipped, 4 deselected**, exit **0**. All **97 new OD-02 parameterized cases** ran and passed, none skipped. The OD-01/OD-01R targeted run has **272 passed, 3 skipped**, exit 0; its final fixture refinements (fixed ZIP metadata and three-date concurrency) also executed in the final full run. Full collection: **386 selected / 390 total**, four live-data deselected. Original baseline was 286 pass + 3 skips; the increment is exactly 97.

Test functions below are in [the new test module](../../../../../tests/unit/test_od02_acquisition.py), except explicitly inherited tests. Collection contains actual parameterized node IDs in [collection log](logs/collection-final.txt). For T01–T24, GREEN means executed offline assertions, not live/source financial certification. All reference fixtures are SYNTHETIC_TEST_ONLY and SOURCE_REFERENCE_PENDING.

| ID | Actual test function/node family | Observed final assertion | Result/log/exit |
|---|---|---|---|
"""
for case, names, outcome in rows:
    matrix += f"| {case} | `{names}` | {outcome} | GREEN, [full](logs/final-reviewed.txt), exit 0 |\n"
matrix += """| T25 | Entire OD-01 and OD-01R modules, including `test_r05_cache_escape_never_opens_external_sentinel` and `test_r06_real_symlink_payload_escape` | 175 prior cases pass, three inherited file-symlink cases skip WinError 1314; two real Windows junction cases pass | **BLOCKED for 3 cases**, [targeted](logs/targeted-final.txt), command exit 0 does not convert skips to pass |
| T26 | Complete offline suite, collection, Ruff, mypy, pip; Python 3.11 and Linux attempts | Windows commands pass; one temporary SQLite ResourceWarning after collection cleanup; other interpreters lack pytest/dependencies | Windows GREEN exits 0; **platform verification BLOCKED**, [3.11](logs/py311-targeted.txt) and [Linux](logs/linux-targeted.txt) exit 1 |

There are **24 green scenario groups, 2 groups with blocked dimensions**, not 26 unqualified passes. No live case or skipped case is counted as successful. Accordingly overall Gatekeeper is BLOCKED, despite successful bounded Windows implementation checks. Unsupported financial/era interpretations remain visibly pending independent review.
"""
write("03_red_green_test_matrix.md", matrix)

write("04_implementation_diff.md", "# OD-02 implementation ledger\n\n" + banner + """
The [OD-02-only normalized text diff](logs/od02-only.patch) reconstructs the reviewed OD-01R patch in memory on HEAD, then compares to this implementation. It includes new files. No checkout/index/worktree manipulation is used. The three edited prior production files retain rights enforcement and existing calling contracts. Other original OD-01R production changes, all old evidence, user prompts, data and keys are preservation-checked separately in [final QA](logs/final-qa.json).

| File | Bounded OD-02 change |
|---|---|
| [acquisition.py](../../../../../src/omegadata/track_a/acquisition.py) (new) | Backward-compatible typed DownloadError, immutable explicit limits, one budget/deadline, status/body rules, URL redaction, strict source-era ZIP/CSV and conservative JSON validation |
| [acquisition_limits.v1.json](../../../../../config/acquisition_limits.v1.json) (new) | Explicit fail-closed engineering ceilings, not source permission |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | Shared ContextVar budget; terminal denial through nested call graph; reject all redirects; stream bound; actual egress disabled; explicit mock callbacks; validation before public success/store; SHA and acquisition evidence; cache-only; cache/seed identity; per-manager candidate-write lock; sanitized URLs/body previews |
| [generate_source_probe_report.py](../../../../../scripts/generate_source_probe_report.py) | No real curl invocation; only explicit offline runner. Bootstrap and actual request share policy/budget; terminal status; no retry/location/insecure flags; bounded test files; common validator. Generic non-equity shape never claims date/financial verification |
| [load_nse_fo_into_pipeline_db.py](../../../../../scripts/load_nse_fo_into_pipeline_db.py) | Keep existing policy checks (including refresh after DB setup); unconditionally stop BLOCKED_EXTERNAL_EGRESS before legacy direct GET. Legacy unreachable redirect flag set false. FO-specific acquisition remains unverified/deferred, not silently approved |
| [test_od02_acquisition.py](../../../../../tests/unit/test_od02_acquisition.py) (new) | 97 actual cases, all synthetic, fixed ZIP timestamps, clocks/callbacks, negative and positive assertions |
| [conftest.py](../../../../../tests/conftest.py) | Synthetic valid NSE archive fixture for policy-attribution test |
| [test_od01_source_rights.py](../../../../../tests/unit/test_od01_source_rights.py) | One allowed probe fixture changes arbitrary MOSPI text to valid NSE ZIP; original policy attribution assertions retained |
| [test_od01r_rights_hardening.py](../../../../../tests/unit/test_od01r_rights_hardening.py) | Existing fake probe explicitly injects offline_runner; revocation callback independently runs when bootstrap now also has bounded -o output. Two-call success/one-call revocation assertions retained. Reconstructed original test bytes match preflight SHA |

No dependency pins, registry era ranges, real source policy, warehouse, business math, public endpoints, universe or release/signing implementation is edited. OD-02 documentation consists of this fresh ten-report run, design, replay/review helpers, raw logs and [ADR](../../../decisions/od02-direct-acquisition-reuse.md). Helpers are not production entry points.

Compatibility: DownloadError remains importable from download_manager with existing message/status/stage arguments; new attributes add reason/terminal/retry-after/context. Dataclass new fields have defaults. Existing public positional source/date arguments remain. `cache_only` is additive. A private fetched candidate means HTTP_RECEIVED, not validated. Old manifests/cache remain conservatively HTTP_RECEIVED, not retroactively certified. Strict NSE/BSE structures can now refuse previously tolerated malformed data by design. Explicit private fake clients/callbacks are trusted test code, never a general Python sandbox.

Storage remains the existing legacy versioned raw/manifest/latest contract; the new lock serializes one manager's candidate writes, not processes or crash recovery. Tests never target original dataset paths. Existing manifest `storage_mode=immutable_versioned` is historical terminology, **not an OD-02 proof of atomic immutable publication**. OD-04 owns that architecture and migration. The standalone FO guard occurs after authorized legacy DB initialization; no production invocation is performed, and source policy pending still stops before DB. Re-enabling its actual fetch requires separately reviewed migration.
""")

write("05_security_failure_analysis.md", "# OD-02 security and failure review\n\n" + banner + """
Same-model Maker/Reviewer/Gatekeeper engineering procedure, not independent security/legal/financial signoff. [AST/network-boundary and dependency inventory](logs/parse-and-component-inventory-v2.json) parsed 113 source/script/test/Airflow files using Python 3.11 grammar. Calls are inventoried, not all claimed executed or sandboxed in arbitrary application code. [OD-02 diff](logs/od02-only.patch) and negative/green logs substantiate the following bounded controls.

| Boundary | Enforced behavior and evidence | Precise limit |
|---|---|---|
| Source rights | Existing source/operation/transport/host/consumer rules precede fetch/cache; refresh before request/store. Pending/revoked and mid-bootstrap changes propagate. All 13 actual sources remain pending, zero approved | JSON canonical hash/string is consistency, not authenticated legal authority; external administrative signoff/checkpoints still required |
| Provider denial | 401/403/451/429/404 terminal across request, bootstrap, discovery, probe, profile and candidate loops; valid Retry-After recorded, never immediately retried. HTML/login/error/structural validation terminal | Not a real provider-status/availability claim; approved availability fallback only for typed selected transient failures |
| Redirects | All 3xx rejected before another request, HTTPX follow_redirects=False, no auto urllib, no curl location/retry/insecure. Original/final URL sanitized; response-URL mismatch rejects | No redirect-support/hop-history claim, since no hops followed |
| DNS/SSRF/proxy/TLS | Existing HTTPS:443/no-userinfo authority checks. Actual HTTPX HTTPTransport refuses before DNS/connect even on fake approved policy; proxy mounts cannot bypass mock boundary. Actual urllib/curl disabled. No verify=False; TLS error terminal | **BLOCKED_EXTERNAL_EGRESS** is intentional. DNS pinning/rebinding/connect-time address enforcement not implemented/certified; no one-lookup sham control. Future actual egress requires separate constrained transport review |
| Credential boundary | Alternate offline adapters strip Cookie/Authorization/Proxy-Authorization; query/fragment/userinfo removed from evidence. Body previews blank. No credentials, .env contents or key bytes inspected | Trusted arbitrary Python test callback can itself execute code; runtime API is not a hostile-Python sandbox. Test runner independently blocks socket/subprocess and external writes |
| Resource budget | Explicit five requests total, 30s operation, <=8s request, deterministic injected backoff. One context survives discovery/bootstrap/profile/fallback; invalid overrides/config refuse before request. Stream size checked before extension, Content-Length strict | Cooperative callback cannot be forcibly killed mid-execution; post-return monotonic deadline and real egress block apply. Not a hard preemptive OS quota against malicious Python. Caps are conservative engineering limits, not rights/rate permissions |
| Archive safety | Response <=8 MiB, expansion <=32 MiB, <=8 entries, ratio<=100, <=20,000 rows. Metadata checked before extraction; bounded selected-member read; encrypted, nested archive, symlink/path traversal/duplicate names reject; no extraction to filesystem | Synthetic bounded malicious examples, not exhaustive ZIP fuzzing. Memory/time/payload envelope deliberately conservative; unknown archives quarantine |
| Payload safety | Strict UTF-8/BOM; unique required era columns; exact dates; deterministic expected member; finite nonnegative OHLC/integer volume; duplicate row/width reject; zero volume valid. Content-type HTML/mismatch denies; malformed/error JSON refuses | Registry's NSE 2020 cutover is inherited, not independently authenticated. Unknown or unsupported schemas cannot be financially verified. JSON/sidefeeds/FO remain HTTP_RECEIVED; structural hash success never independent financial truth |
| Provenance/storage | SHA-256 of exact original bytes, requested era/date, status/type/transport/policy, actual attempts and sanitized original/final URLs; synthetic/unverified vs cache vs seed distinct. Per-manager write lock, disposable concurrent test | No atomic multi-process/crash-safe publishing, descriptor-race filesystem sandbox, canonical dataset migration or immutable latest solved. OD-04/10 handoff |

Existing disabled manual diagnostics remain disabled. StockReachGraph remains unregistered/refused; it cannot borrow a registered feed's policy. Canonical source-probe default invocation refuses before subprocess/temp artifacts once policy allows; default policy refuses even earlier. Standalone F&O is blocked before its direct GET; legacy DB setup is not rearchitected here. Other repository downstream services are not claimed to have universal rights/egress guarantees beyond OD-01R scope. No unauthorized network attempt or credential-exfiltration observation occurred.

Unverified dimensions: Python 3.11/Linux dependencies, three privileged file symlink paths, official source-era authenticity/terms, OS egress controls, resource fuzzing, crash/process concurrency, financial reconciliation, package advisory closure. These are recorded as BLOCKED/pending, never counted as successful tests. No production release, signing, brokerage, payment, external provider smoke or browser scraping occurred.
""")

commands = "# OD-02 execution evidence and coverage\n\n" + banner + """
Requested command equivalents ran through [the isolated runner](verification_runner.py), rather than unguarded pytest. Invocation shape:

```powershell
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od02/20261115T084441Z/verification_runner.py' <unique-label> <module> <arguments>
```

Each JSON below contains the exact absolute executable, argv, cwd, UTC start/end, duration, exit and output filename. Effective pytest adds `-p pytest_asyncio.plugin -p no:cacheprovider --log-file <disposable> --basetemp <disposable>`; coverage additionally loads pytest_cov explicitly, puts its DB in disposable temp and retains JSON here. Network/DNS/subprocess and original-path writes are forbidden during tests, including collection. Tests that mock signing run only mocks against disposable directories; no historical signing or warehouse script was run.

| Label / effective command | Actual result and exit | Raw evidence |
|---|---|---|
"""
labels = ["baseline", "negative-first", "targeted-v1", "targeted-v2", "adversarial-v1", "adversarial-v2", "overrides-negative", "targeted-final", "regression-v1", "full-final", "final-reviewed", "collection-final", "lint-v1", "lint-v2", "lint-final", "lint-reviewed", "type-v1", "type-v2", "type-final", "pip-final", "py311-targeted", "linux-targeted"]
summaries = {
"baseline":"286 passed, 3 skipped, 4 deselected",
"negative-first":"16 failed, 2 passed (expected red)",
"targeted-v1":"192 passed, 3 skipped, 1 failed (old invalid probe fixture)",
"targeted-v2":"193 passed, 3 skipped",
"adversarial-v1":"89 passed, 1 failed (missing error context)",
"adversarial-v2":"90 passed",
"overrides-negative":"4 failed, 2 passed, 91 deselected (expected red)",
"targeted-final":"272 passed, 3 skipped; final fixture refinements then covered by final-reviewed",
"regression-v1":"376 passed, 3 skipped, 4 deselected",
"full-final":"383 passed, 3 skipped, 4 deselected; branch coverage",
"final-reviewed":"383 passed, 3 skipped, 4 deselected; final fixed-metadata/concurrent fixtures, branch coverage",
"collection-final":"386/390 collected, 4 deselected",
"lint-v1":"4 import-order errors", "lint-v2":"All checks passed", "lint-final":"All checks passed", "lint-reviewed":"All checks passed",
"type-v1":"3 tuple-inference errors in new validator", "type-v2":"48 source files clean", "type-final":"48 source files clean",
"pip-final":"No broken requirements found", "py311-targeted":"BLOCKED: missing pytest (no test executed)", "linux-targeted":"BLOCKED: missing pytest (no test executed)",
}
for label in labels:
    item = json.loads((LOGS/(label+".json")).read_text())
    commands += f"| {label}: `{' '.join(item['effective_module'])}` | {summaries[label]}; exit **{item['exit_code']}**, {item['elapsed_seconds']:.2f}s | [command](logs/{label}.json), [output](logs/{label}.txt) |\n"
commands += """
## Coverage and warnings

Final [coverage JSON](logs/final-reviewed-coverage.json): **4,690 / 5,526 statements (84.87%)**, **1,052 / 1,582 branches (66.50%)**, combined statement/branch coverage **80.78%**. Acquisition module: **247/264 statements (93.56%)**, **97/108 branches (89.81%)**, combined **92.47%**. Downloader: 571/749 statements, 142/250 branches, combined 71.37%. Rights: 269/270 statements, 71/72 branches, combined 99.42%. Coverage is measured, not complete proof; uncovered paths are retained in raw report/JSON, not suppressed. Scripts are outside the `--cov=omegadata` coverage target although their targeted assertions execute.

Final covered run prints **one ResourceWarning for an unclosed temporary SQLite connection during pytest GC** after its summary; earlier OD-01R logs also reported cleanup warnings. It is retained, not suppressed or claimed fixed. Three Windows file-symlink skips are WinError 1314; no case is relabeled PASS. Four realdata tests were deliberately deselected. WSL printed missing drive/PATH translation warnings; both alternate-runtime attempts fail import because pytest/dependencies are absent, not because of a proven application incompatibility.

No installs/pins changes occurred. [Current environment](logs/preflight.json), [Python 3.11 metadata](logs/py311-environment.json), [Linux metadata](logs/linux-environment.json), [113-file Python 3.11 grammar parse](logs/parse-and-component-inventory-v2.json) are separate evidence: syntax parsing is not runtime success. Public upstream lookup supplied dependency/license context only; no dlt/Scrapy benchmark/CVE/official exchange-reference validation occurred.

Read-only inventory command: `& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od02/20261115T084441Z/review_checks.py' inventory`, final exit 0, 113 parsed files and 84 inventoried network/mock boundary calls. Its first attempt saved the valid inventory then failed an assertion in reconstructing the original test fixture; the reconstruction used the actual original `elif revoke_after_bootstrap:` and then verified its original preflight hash. No source or test result was changed by that reporting helper. Original inventory log retained alongside v2.

Final preservation/report check: [review helper](review_checks.py), [QA JSON](logs/final-qa.json). This verifies original path hashes/metadata, exact source policy default, branch/main/index identity, current artifact existence and local links. It does **not** convert blocked runtime dimensions into a passing Gatekeeper.
"""
write("06_evidence_and_coverage.md",commands)

write("07_remaining_defects.md", "# OD-02 remaining defects and ownership\n\n" + banner + """
No known uncorrected P0/P1 was observed in the **executed bounded Windows OD-02 transport/structural acceptance**. That statement is not closure of blocked verification or inherited financial/release findings. Overall verdict remains BLOCKED. Original [OD-00 defect register](../../../audit/08_prioritized_defects.md) and [OD-01R risk register](../../od01r/20261115T065155Z/05_risks_rollback.md) remain unchanged.

| Finding | Current disposition / owner / acceptance handoff |
|---|---|
| D-01 **P0**, signing custody | **OPEN**, security owner, OD-11/14. No key contents/history/use reviewed or changed. Owner must establish trusted custody/public verification root under separate authorization |
| D-04 **P0**, release export/eligibility/promotion bypass | **OPEN**, release owner, OD-11. No new release/readiness/distribution claim; immutable staged verification and fail-closed promotion still required |
| D-03 **P1**, canonical overwrite/raw atomicity | **OPEN**, storage owner, OD-04/10. One manager's thread lock and retained raw hashes do not solve process/crash-safe immutable archives, canonical Parquet or release pointers |
| D-02 **P1**, universe knowledge-time | **OPEN**, OD-08 (with OD-06/10 identity/version contract). Historical decision/as-known availability not fixed |
| D-08 **P1**, mutable price/action history | **OPEN**, OD-06/07/10. Observation revisions, point-in-time corrections and reproducible adjustment versions deferred |
| D-06 **P1**, rights prior calendar day | **OPEN**, OD-07. Prior exchange-session/staleness policy and independent factors unresolved |
| D-09 **P1**, official fixture provenance | **OPEN**, OD-05/07/09/14 and independent financial/source reviewer. New synthetic fixtures explicitly SOURCE_REFERENCE_PENDING, do not count as official truth |
| D-05 **P1**, HTML payload acceptance | **CORRECTED in tested offline OD-02 scope**: strict equity ZIP/CSV/date/content checks and terminal failure. Source-era official interpretation/actual 2020 cutover remains unverified; unknown formats quarantine, no live certification |
| D-12 **P1**, provider denial retry | **CORRECTED in tested offline call graph**: terminal 401/403/451/429/404 and body denials across request/bootstrap/discovery/profile/candidate/probe; no live-source availability claim |
| D-07 **P1**, rights enforcement | OD-01/01R implemented technical default denial; administrative authority/terms/revision trust remains mandatory human ownership. All 13 actual sources pending, zero approved |
| D-10 **P2**, stale readiness | **OPEN**, OD-11/14. Historical reports not regenerated; green archived booleans are not current certification |
| D-11 **P2**, supply chain/CI/compatibility | **OPEN**, OD-14. No lock/advisory/license clearance or CI runtime matrix claimed. 3.11/Linux missing dependencies; three privileged symlink scenarios blocked |
| OD02-V01 verification blocker | Python 3.11/Linux targeted runs exit 1 before tests (missing pytest/dependency set); Windows file symlinks lack privilege. Completion needs authorized disposable dependency setup and capable runner; no installation authorized here |
| OD02-R01 source-reference/live blocker | Independent source-era/schema/date/financial interpretation pending. Real HTTPX/urllib/curl remains BLOCKED_EXTERNAL_EGRESS until separately authorized constrained address-level transport and rights review |
| OD02-R02 storage/callback limits | Cooperative trusted offline callbacks cannot be preemptively timed out in-process; no hostile-Python sandbox, cross-process atomic publication or descriptor-level symlink-race protection certified. Keep actual egress disabled and candidate/test scope disposable |
| Other inherited operational risks | Warehouse idempotency/CLI credentials and downstream use-scope integration deferred; no actual service/warehouse test, broker, signing or production artifact modification |

No P0/P1 financial/release gate is waived by these tests. OD-03 browsers, OD-04 storage implementation and OD-05+ work were not begun. Future phases need separate scoped authorization; no rollback or cleanup action is implied. Review the OD-02-only patch before any selective rollback; reversing this phase would restore known acquisition defects, so jobs must stay disabled. Never reset/clean/stash or remove historical evidence/data/keys.
""")

write("08_gatekeeper_verdict.md", "# OD-02 Gatekeeper verdict: BLOCKED\n\n" + banner + """
**Verdict: BLOCKED.** The bounded Windows offline implementation checks pass; the execution contract's complete verification gate cannot honestly be marked OD02_OFFLINE_TECHNICAL_PASS while T25/T26 have blocked dimensions. No known remaining P0/P1 failure was observed within executed OD-02 controls, but unexecuted cases are not removed from the denominator.

| Criterion | Evidence / outcome |
|---|---|
| Prerequisite OD-01R approved technical evidence | Prior OD01R_TECHNICAL_PASS and final QA verified; reviewed code patch matched byte-for-byte before changes |
| T01–T24 offline assertions | All 97 new parameterized cases executed GREEN, final full suite exit 0; synthetic/source-reference limits explicit |
| T25 inherited coverage | 175 prior rights/hardening cases pass; **three file-symlink cases blocked by privilege**, not PASS; real junctions pass |
| T26 regression/static/dependency checks | Windows **383 passed / 3 skipped / 4 deselected**, Ruff/mypy/pip/collection exit 0; **Python 3.11 and Linux attempts exit 1 missing pytest/dependencies** |
| Provider denial / redirects / source authority | Mock negatives show terminal status/body/policy refusal; all redirects rejected; denied source cannot select later candidate/profile/transport |
| Per-hop/address security | Actual provider egress remains **BLOCKED_EXTERNAL_EGRESS**; no connect-time DNS/private-address security certification or sham lookup control |
| Payload correctness | Strict bounded equity era/archive/header/date/numeric validation. No HTML/wrong date/corrupt archive can become structurally validated in tested paths. Generic JSON/sidefeeds remain HTTP_RECEIVED |
| Provenance | Exact raw bytes/SHA, sanitized URL/status/type/transport/policy/attempt/schema/era and offline source mode; cache and seed distinct |
| Preservation / phase safety | [Final QA](logs/final-qa.json) verifies exact scope, original hashes/metadata, default pending policy and branch/main/index identity. No actual source request, payment, publication, release/signing change, warehouse/broker operation or later phase |
| Independent verifier | **SOURCE_REFERENCE_PENDING**, same-model review only. Fixture interpretation is not official authenticity; live/financial certification blocked |

Baseline **286 passed, 3 skipped, 4 deselected**; final **383 passed, 3 skipped, 4 deselected**, delta **97**. Combined statement/branch coverage **80.78%**, acquisition module **92.47%**. One unclosed disposable SQLite ResourceWarning retained. Detailed exact commands/exits, environment, failed red runs, test fixture migration and coverage limits are in [execution evidence](06_evidence_and_coverage.md) and [T01–T26 matrix](03_red_green_test_matrix.md).

All **13 real policies PENDING_REVIEW, 0 APPROVED**. D-01/D-04 P0 and inherited D-02/03/06/08/09 P1 remain open; D-05/D-12 corrected only in the documented tested offline boundary. No production/live/release certification. See [remaining risks](07_remaining_defects.md).

**STOP: OD-02 only.** No commit/push/PR or OD-03/OD-04 work is implied. The one proposed approval is the bounded verification completion in [next request](09_next_phase_request.md); no source enablement or provider smoke is included.
""")

write("09_next_phase_request.md", "# Single next approval request\n\n" + banner + """
**Proposed action only:** authorize an **OD-02 verification-only follow-up** to prepare disposable Python 3.11 and Linux test environments with the existing approved repository dependency requirements, and run the unchanged offline suite on a runner capable of the three file-symlink cases. Capture exact installed versions, preserve this evidence, keep network/provider/subprocess restrictions during tests and original data/signing/release locations protected. No dependency pin upgrade, production setup, provider access, source approval or signing/release action is included. Environment/package installation needs separate approval under section 7 of the OD-02 execution contract; none was performed here.

Once that verification blocker is resolved and independently reviewed, the architecture handoff favors a separately scoped **OD-04 immutable raw archive** proposal: append-only content-addressed candidates, crash/process-safe atomic writes, immutable manifests, reproducible replay and explicit legacy-pointer migration. This is context, not a second approval request or permission to implement OD-04 now. OD-03 browser comparison remains optional and deferred; no demonstrated crawling need or authorized rights scope justifies adding Obscura/Playwright.

Human source-rights/terms authority, independent official era/reference/financial reconciliation, address-level egress security and inherited release/signing P0 gates remain prerequisites before any separately specified live or publication action. Completing offline tests cannot approve data rights, financial correctness or production releases.
""")

adr = ROOT/"docs/omegadata_v2/decisions/od02-direct-acquisition-reuse.md"
with adr.open("x",encoding="utf-8",newline="\n") as file:
    file.write("""# OD-02 direct acquisition reuse decision

Status: **EXTEND_EXISTING** implemented offline; verification Gatekeeper **BLOCKED**. Branch feature/od01-source-rights, HEAD 3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc, run 20261115T084441Z.

Use current OmegaData rights/registry/DownloadManager, HTTPX 0.28.1 and stdlib bounded ZIP/CSV/JSON/hash parsing. Add explicit validated engineering resource limits and one context-local budget across discovery/bootstrap/profiles/transports, typed terminal denial, reject-all redirects, strict era/date/row validation and source-candidate evidence. Real HTTPX/urllib/curl stays BLOCKED_EXTERNAL_EGRESS because connection-time address isolation is not demonstrated. MockTransport and explicitly injected trusted callbacks are synthetic only. Do not mistake conservative HTTP_RECEIVED or cache provenance for official/financial reconciliation. Preserve legacy storage and leave atomic multi-process/crash-safe publication to OD-04.

Alternatives: **DEFER dlt 1.32.0** (Apache-2.0 tagged metadata), **DEFER Scrapy 2.20.0** (BSD-3-Clause), **DEFER OD-03 browsers**. No install, local alternative performance benchmark or advisory closure supports adoption. Published compatibility metadata is not a tested local runtime guarantee. See [candidate evidence](../implementation/od02/20261115T084441Z/01_repo_selection.md).

Measured result: 97 new offline assertions pass; complete Windows regression 383 passed, 3 inherited symlink skips, 4 realdata deselected. Lint/mypy/pip/collection pass. Missing pytest/dependencies block Python 3.11/Linux; three symlink paths require privileges. Overall **BLOCKED**, no denominator exclusion. Same-model design/security review; independent official source interpretation SOURCE_REFERENCE_PENDING. All 13 policies pending, no provider/release/signing action. D-01/D-04 P0 and other financial/storage P1 remain open.

Design was written before implementation; review recorded actual red failures then corrections. [Design and review](../implementation/od02/20261115T084441Z/02_design_and_adrs.md), [test matrix](../implementation/od02/20261115T084441Z/03_red_green_test_matrix.md), [diff](../implementation/od02/20261115T084441Z/04_implementation_diff.md), [Gatekeeper](../implementation/od02/20261115T084441Z/08_gatekeeper_verdict.md), [next verification request](../implementation/od02/20261115T084441Z/09_next_phase_request.md).
""")
print("Created nine new reports plus ADR; pre-existing design report retained.")
