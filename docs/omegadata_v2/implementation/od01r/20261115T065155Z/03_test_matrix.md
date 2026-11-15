# OD-01R executed verification matrix

All actual commands used the existing configured interpreter, from the repository root. Each successful/expected-red command has a new label, UTC interval, exact argv, stdout/stderr filename and underlying exit in logs. No original OD-01 file was used as an output target. Tests are synthetic/mock/local only. Raw logs are exclusive-create run evidence, not cryptographically immutable records.

## Reproduction recipe

Use a NEW evidence directory or new labels; existing outputs must not be overwritten. The runner's effective module is recorded as argv, not shell-reconstructed text. Current run command prefix:

```powershell
$py = '.venv/Scripts/python.exe'
$runner = 'docs/omegadata_v2/implementation/od01r/20261115T065155Z/verification_runner.py'
& $py -B $runner collection-reviewed pytest --collect-only -q -m 'not realdata'
& $py -B $runner targeted-reviewed pytest -q tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py
& $py -B $runner full-reviewed pytest -q -m 'not realdata' --cov=omegadata.track_a.source_rights --cov=omegadata.track_a.download_manager --cov-branch --cov-report=term-missing
& $py -B $runner ruff-reviewed ruff check --no-cache src/omegadata tests scripts
& $py -B $runner mypy-reviewed mypy src/omegadata
& $py -B $runner pip-reviewed pip check
```

Runner appends explicit asyncio plugin, no cache provider, temporary log file and newly allocated basetemp. Full coverage adds pytest-cov explicitly; its database/JSON are temporary, and JSON is copied after the tests to the run log. The test harness blocks real sockets/DNS/subprocesses and writes/SQLite outside the disposable root; monkeypatched fake clients/curl do not create actual child processes. Tests may read required historical fixture/reference files; those reads do not constitute source-rights approval or official authenticity verification.

| Run / effective command | Exit | Actual result / evidence |
|---|---:|---|
| preflight | 0 | Identity, packages and original-file snapshot saved; [preflight](logs/preflight.json) |
| Initial guarded baseline | 1 wrapper | Before collection: new write guard blocked pytest default logging target; then also blocked result JSON because guard teardown was incomplete. [Original trace](logs/baseline-offline.txt); not an application failure or passing run |
| baseline-offline-v2: pytest -q -m 'not realdata' | 0 | **211 passed, 4 deselected**, 29.61s; [command](logs/baseline-offline-v2.json), [raw](logs/baseline-offline-v2.txt) |
| negative-first: new hardening module | 1 expected | **38 failed, 26 passed, 3 skipped**, unchanged production. Failed URL/cache/manual/F&O/refusal cases; [command](logs/negative-first.json), [raw](logs/negative-first.txt) |
| targeted-v1 | 0 | 166 passed, 3 file-symlink skips; [raw](logs/targeted-v1.txt) |
| full-v1 | 0 | 277 passed, 3 skipped, 4 deselected; interim review, not final scope; [raw](logs/full-v1.txt) |
| refresh-negative-first: -k bootstrap_scoped | 1 expected | 1 failed (revocation after bootstrap), 1 passed; [raw](logs/refresh-negative-first.txt) |
| discovery-negative-first: -k bse_discovery_refreshes | 1 expected | 1 failed; client construction changed provider before unguarded GET; [raw](logs/discovery-negative-first.txt) |
| orchestrator-negative-first: -k production_entry_pending | 1 expected | 3 failed on eager mkdir before policy refusal; [raw](logs/orchestrator-negative-first.txt) |
| targeted-v2 | 1 | 1 failed, 173 passed, 3 skipped. New scheduled-CA test used 08:00 IST outside an actual window; corrected setup to 07:00 IST (01:30 UTC). Same refusal and zero-side-effect assertions retained; no schedule code/expectation weakened. [Raw](logs/targeted-v2.txt) |
| fo-refresh-negative-first: -k fo_loader_rechecks | 1 expected | 1 failed: revoked policy still reached fake HTTP after DB setup; [raw](logs/fo-refresh-negative-first.txt) |
| targeted-reviewed | 0 | **175 passed, 3 skipped**, 2.59s, includes all original 100 unchanged tests; [command](logs/targeted-reviewed.json), [raw](logs/targeted-reviewed.txt) |
| full-reviewed + branch coverage | 0 | **286 passed, 3 skipped, 4 deselected**, 25.07s; [command](logs/full-reviewed.json), [raw](logs/full-reviewed.txt), [coverage](logs/full-reviewed-coverage.json) |
| collection-reviewed | 0 | **289/293 selected**, four realdata excluded; [command](logs/collection-reviewed.json), [raw](logs/collection-reviewed.txt) |
| Ruff reviewed | 0 | All checks passed; [command](logs/ruff-reviewed.json), [raw](logs/ruff-reviewed.txt) |
| mypy reviewed | 0 | No issues, 47 source files; [command](logs/mypy-reviewed.json), [raw](logs/mypy-reviewed.txt) |
| pip reviewed | 0 | No broken requirements; [command](logs/pip-reviewed.json), [raw](logs/pip-reviewed.txt) |
| git diff --check, CR-aware | 0 | No whitespace defects in tracked patch; benign line-ending/global-ignore warnings preserved in tool observations |
| Editor Problems | No errors | Source rights/downloader/orchestration/new tests checked |

Initial Ruff/mypy runs also exited 0; raw v1/v2 files retained. No failed application check remains in final Windows verification. Six unclosed SQLite-connection ResourceWarnings appear during final pytest cleanup after the summary, preserved at the end of full-reviewed.txt. They are not suppressed, do not change exit 0, and do not certify connection hygiene. Historical OD-01's eight warnings were ARCH; this fresh run has its own result.

## Required R01–R16 mapping

All new functions are in [test_od01r_rights_hardening.py](../../../../../tests/unit/test_od01r_rights_hardening.py). Original functions are in [test_od01_source_rights.py](../../../../../tests/unit/test_od01_source_rights.py).

| Ref | Actual test(s) / disposition | Before / after evidence |
|---|---|---|
| R01 | test_r01_r03_url_denied_before_client, three unapproved ports | FAILED initial negative-first; PASS targeted-reviewed/full-reviewed before client |
| R02 | same function HTTP/userinfo/malformed port/netloc/control cases | Multiple FAILED initial; PASS after; unsupported schemes/foreign userinfo already refused, retained |
| R03 | same function IPv4/private/loopback/IPv6/local/malformed DNS cases | Unlisted target cases already PASS; malformed authority had untyped failure, now typed refusal. DNS/address-resolution behavior remains UNVERIFIED/OD-02 |
| R04 | test_r04_https_allowed_mock_transport (three forms) | PASS before and after, HTTPX MockTransport only; default/canonical :443 and normalized trailing-dot/query behavior |
| R05 | test_r05_cache_escape_never_opens_external_sentinel (raw and seed) | Absolute/traversal/manifest escape FAILED before; PASS after, sentinel open spy stays empty. Two pointer file-symlinks skipped on Windows |
| R06 | test_r06_real_symlink_payload_escape; test_r06_windows_junction_escape[partition/payload_directory] | File symlink BLOCKED WinError 1314, not PASS; both real junction variants PASS. Linux file-symlink dimension BLOCKED missing pytest |
| R07 | test_r07_inconsistent_cache_is_miss; test_r07_malformed_manifest_is_miss; test_r07_safe_legacy_cache_compatible | Source/date/size/shape/empty and bare legacy compatibility failures reproduced; checksum mismatch already rejected. Final safe old absolute/repo-relative/bare paths PASS |
| R08 | test_r08_fo_loader_pending_before_db_or_http; test_r08_production_entry_pending_no_output; test_r08_pending_probe_bootstrap_no_temp_or_subprocess; original test_t01_t11_download_refusals_have_zero_side_effects and revoked cache tests | F&O/constructor failures reproduced; final typed missing/denied/pending/revoked refusal has zero relevant effects |
| R09 | test_r09_backfill_policy_refusal_terminal; original test_t17_optional_pipeline_refusal_does_not_try_later_source | Backfill FAILED before, PASS after; optional-source pipeline already PASS, preserved |
| R10 | test_r10_probe_authority_before_curl; test_r10_probe_bootstrap_scoped_mock_and_refresh | Bad port/HTTP and stale bootstrap permission FAILED before; pending zero temp/children and scoped synthetic two-curl success PASS; revocation permits bootstrap only, no target curl |
| R11 | original test_t15_every_registered_default_is_pending and test_default_pending_blocks_every_source_before_cache | PASS unchanged: 13 pending, 0 approved, no permissions; strict register validation exercised |
| R12 | test_r12_forged_strings_are_only_technical_consistency + original missing-evidence tests | PASS limitation proof: forged administrative strings with valid hashes can satisfy structural checks. Never asserted legal authority; operational administrative gate required |
| R13 | test_r13_simultaneous_source_scopes_and_refresh; test_r13_bse_discovery_refreshes_before_get; test_r13_fo_loader_rechecks_after_db_setup; original T18 concurrency | Source scopes overlap with barrier and stay distinct; subsequent revoked request has no extra client call. BSE/F&O stale-request red logs then final PASS |
| R14 | Original full 100-test OD-01 module, T01–T18 | Unmodified and included in targeted-reviewed/full-reviewed, all 100 PASS |
| R15 | test_r15_manual_diagnostics_disabled_before_side_effects (five callable entries) and [inventory](logs/source-entry-inventory.json) | Initial five FAILED, final PASS; static classifications in findings, no real diagnostics executed |
| R16 | test_r16_harness_blocks_real_side_effects; complete commands above | PASS Windows authorized offline suite/lint/type/pip. Linux/Python 3.11 testing BLOCKED dependencies; no fabricated CI/live result |

## Coverage and environmental limits

Actual branch coverage displays source_rights 99% (269/270 statements; 72 branches, one partial), downloader 62% (478/719 statements). Exact branch counts/percentages in saved JSON. Original policy tests are unchanged and still pass; prior OD-01 coverage is historical only. No fresh baseline coverage delta or whole-application no-regression percentage is claimed.

Linux dependency check passes only because its installed metadata has no broken declared requirements; it does not mean pytest or the editable application's full dependencies exist. Actual targeted attempt failed before collection with ModuleNotFoundError: pytest. Python 3.11.15 base has only pip/setuptools/project metadata and lacks pytest and application packages. No packages installed/upgraded, no extra runtime environment created, no paid service or credential used. Four live tests intentionally remain excluded. Windows symlink privileges were not elevated, no developer-mode/security setting changed. Current CI, Airflow and external services remain unexecuted.
