# OD-01R reproduced review findings

Review/implementation on feature/od01-source-rights at 3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc. Same-model review; no independent consensus. Suspicions were tested locally; none required provider traffic. Baseline: 211 offline pass, four live exclusions. Test functions below are in [hardening tests](../../../../../tests/unit/test_od01r_rights_hardening.py); exact results are in [matrix](03_test_matrix.md).

| Finding | Local evidence and severity | Disposition / owner |
|---|---|---|
| OD1-R01 scheme/port dropped | DownloadManager._authorize_url used hostname only. Approved-domain :4443/:80/:8080 and HTTP cases failed expected refusal in negative-first | P1 FIXED: shared HTTPS/443 DNS preflight; OD-01R engineer |
| OD1-R02 malformed/userinfo authority | Empty userinfo, malformed port and parse-error cases were accepted or raised untyped errors. Control/whitespace stripping also broadened input | P1 FIXED: reject ambiguity before client; valid HTTPS/443 mock paths preserved |
| OD1-R03 IP/local authority | Unlisted IP/local names already refused in negative run: false positive as an existing bypass for the supplied fake policy. Direct evaluator DNS syntax alone is not SSRF enforcement | v1 URL preflight now rejects IP literals; unlisted local names remain denied by exact host policy. DNS rebinding/addresses OD-02, no claim of resolution safety |
| OD1-R04 manifest escape | _path_from_manifest accepted absolute/traversal references. Harmless external sentinel open was trapped; raw and seed tests failed before fix | P1 FIXED: canonical root/partition confinement before any referenced open |
| OD1-R05 manifest identity/shape | Wrong source/date/length, empty paths, duplicate fields and list/null JSON returned bytes or raised untyped errors | P1 FIXED: strict object parsing, identity/size/digest checks, invalid cache miss. Checksum mismatch already rejected: retained valid behavior |
| OD1-R06 symlink/junction | Original code lacked containment; Windows file-symlink attempts skip with WinError 1314 | P1 static boundary FIXED; two real directory junction attacks PASS with zero external opens. File-symlink execution BLOCKED by host privileges; no unsupported file-symlink PASS claim |
| OD1-R07 independent F&O loader | main called init_db and httpx.get without policy. Negative test trapped HTTP after DB call | P1 FIXED: FETCH/STORE_RAW before DB, refreshed before GET/storage, decision provenance in new manifests |
| OD1-R08 legacy diagnostic bypass | Endpoint/BSE probes construct independent clients, matrix starts child and rewrites canonical evidence | P1 FIXED operational gate: unconditional refusal at all five callable entries; no permissive option/flag. Separately approved migration needed to re-enable |
| OD1-R09 swallowed refusal | Historical backfill live helper caught SourcePolicyError as generic failure and could continue later dates | P1 FIXED: typed refusal rethrows. Pipeline optional handler already terminal: legacy test verifies no next source |
| OD1-R10 stale boundary decisions | Separate negative-first tests failed for probe bootstrap→target curl, BSE constructor→GET, F&O DB setup→GET policy changes | P1 FIXED: refresh immediately before each explicit request; source-scope thread isolation retained. Mid-syscall atomic revocation is not claimed |
| OD1-R11 eager output | IngestionOrchestrator constructed ParquetStorage before policy checks, creating output even for pending source. Three negative tests trapped mkdir | P2 FIXED: lazy cached storage property; raw-source refusal creates no output. Explicit tabular storage functionality retained |
| OD1-R12 trust/discovery | Hash plus forged principal string passes technical evaluator; original docs already disclosed this. Root instruction discovery and master pointer were defective | No claim of cryptographic authority. Human trust operational gate specified in design/risks. P2 documentation correction applied; no schema or policy approval changed |

## Exhaustive inspected source entry inventory

[AST call inventory](logs/source-entry-inventory.json) enumerates direct HTTP/urllib/subprocess and download/ingest calls under src, scripts and airflow; workflow file identity recorded. Broad rg search additionally inspected URL references, curl/wget and broad exception handlers. Static inventory is runtime-accompanied for guarded entry points; it is not proof of arbitrary dynamic code execution or universal egress control.

| Route / file | Classification | Enforced status and runtime accompaniment |
|---|---|---|
| DownloadManager.download, cache helpers | Production path | READ_CACHED/CACHE/SEED_CACHE before inspection; FETCH/STORE_RAW before discovery/writes. Original T01–T18 plus R05–R08 |
| probe_source_candidates / _candidate_urls / _fetch_candidate | Production path | Shared source/transport/URL guard before client; typed terminal refusal; original entry-point tests and R01–R04 |
| _request_once/_request/_request_with_workarounds | Production path | HTTPX policy at each operation/request, ContextVar identity; terminal policy refusal before fallback; R13 thread test and original fallback tests |
| _request_via_urllib/_request_via_curl | Production path | Guard before SSL/request object or temp/subprocess; original private-entry tests. Redirect behavior unchanged for OD-02 |
| _bootstrap_nse_session/_discover_nse_fo_urls | Production path | Source-scoped bootstrap and direct URLs checked; original unknown/pending tests; no provider call |
| _discover_bse_equity_urls | Production path | Check before client, refresh before direct GET; R13 constructor-change negative/green |
| fetch_bse_stockreach_graph | Production path, blocked | UNKNOWN_SOURCE before client: dedicated identity still absent; never borrows BSE CA rights |
| IngestionOrchestrator / sequential Track A / scheduled CA / run_full_day | Production path | Guarded downloader; deferred storage; R08 no-output refusal and original optional-source propagation tests |
| Track B / scheduled confirmation | Production computation | No direct source acquisition; operates on existing DB state. Full offline regressions retained; downstream rights/PIT/release integration is later work |
| airflow omegadata_pipeline | Production scheduler | Three callbacks call guarded orchestrator. Static chain inspected; actual Airflow service not started or certified |
| airflow omegadata_verification | Production scheduler | Source-probe child invokes guarded canonical report; failure is check=True and aborts task. Scheduler bootstrap child itself may run before policy, but no provider/cache/output access in child before guard. Release tasks out of scope and remain blocked by D-01/D-04; no scheduler executed |
| generate_source_probe_report._probe_entry/_curl_probe/main | Production/scheduled verification | HTTPS/443 and policy before temp/bootstrap; refresh each curl. Pending bootstrap zero calls and synthetic two-curl success/revocation tested. No live report generated |
| load_nse_fo_into_pipeline_db.main | Production acquisition/import | Newly guarded before DB/HTTP/raw writes; R08 pending and R13 refresh tests. Parsing/persistence semantics otherwise retained |
| probe_endpoints / probe_bse_urls / generate_source_probe_matrix | Manual developer diagnostics | Hard-disabled; five callable entries tested before clients/children/cache/output. No live-without-approval gate can be bypassed by changing config flags |
| backfill_nse_equity_history._attempt_live_download | Manual backfill acquisition | Guarded downloader, typed refusal terminal. Cached archive enumeration/validation is offline historical verification, not newly certified downstream usage permission; no real archive was read by this script in this run |
| import_seed_raw_cache and proof/report generators | Offline verification / historical reprocessing | Local reads/writes, not provider transports; not executed against canonical data. Existing report/raw/DB effects require separately bounded corpus/output authorization. References to source URLs alone are not request calls |
| alerting.route / warehouse / DB / Kafka/Redis helpers | Out of source-rights scope | Operational egress, not market-source acquisition. Webhook empty and sockets denied in tests. No live service health claim |
| release_manager GPG subprocesses / run_db_migrations | Out of scope | No key/migration command executed; mocked release test stays disposable; no signer inspection |
| .github trading-calendar-guard | Offline CI check with dependency setup | Existing workflow unchanged; package setup uses network, unlike offline test execution. No new CI or current CI success claimed |

Inventory does not authorize manual execution of historical generators, service startup, source access or releases. Cache confinement does not authenticate financial payload truth. Source policy operation scopes remain granular and every actual production policy remains pending.
