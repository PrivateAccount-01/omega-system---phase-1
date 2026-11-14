# 02 — Executed tests and validation matrix

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Test engineer / Gatekeeper; evidence classes: RUN / TEST / SYN / CMP / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure and actual results

Run cwd: E:/omega system - phase 1. Interpreter for every Python command: existing .venv/Scripts/python.exe. No dependency install. [Exact command recipes](logs/command-ledger.md) include the guard and failed invocation. Logs retain start/end UTC, underlying exit codes and output; PowerShell wrapper success is not the Python result.

| Command / scope | UTC interval | Underlying exit | Result / output |
|---|---|---|---|
| Python --version; pip --version/list/check | 11:07:34–11:07:42 | pip check 0 | [Python/dependencies](logs/environment.txt) |
| pytest --collect-only -q -m 'not realdata' -p no:cacheprovider | 11:08:06–11:08:14 | 0 | 111/115 collected, 4 deselected; [collection](logs/pytest-collection.txt) |
| Initial inline guarded pytest invocation | 11:08:16 | 1 | PowerShell 5.1 native quoting stripped string quotes; SyntaxError before tests; [failed invocation](logs/pytest-offline.txt) |
| Guarded pytest, all connect calls denied | 11:08:39–11:09:09 | 1 | 98 passed, 13 failed, 4 deselected, 2 warnings; Windows asyncio socketpair construction blocked by audit harness; [full output](logs/pytest-offline-retry.txt) |
| Guarded pytest, socketpair construction exception only | 11:10:34–11:10:57 | 0 | **111 passed, 4 deselected, 21.21s**; [final offline baseline](logs/pytest-offline-final.txt) |
| ruff check --no-cache src/omegadata tests scripts | 11:08:51–11:08:54 | 0 | All checks passed; [ruff](logs/ruff.txt) |
| mypy --cache-dir TEMP/od00-mypy-20261114 src/omegadata | 11:08:54–11:09:21 | 0 | No issues in 46 source files; [mypy](logs/mypy.txt) |
| compileall -q src/omegadata scripts, temporary PYTHONPYCACHEPREFIX | 11:10:46–11:10:48 | 0 | No compile errors; [compileall](logs/compileall.txt) |
| Disposable integrity experiments | 11:12:07–11:12:09 | 0 | Four reproducible gaps observed; command exit 0 means experiment completed, not integrity acceptance; [results](logs/disposable-integrity-experiments.txt) |

Final pytest invoked the same complete selected suite after correcting the harness. No repository test, assertion or expectation was changed. Socket connect/connect_ex/create_connection were denied; Windows internal socketpair could call original connect only during thread-local socketpair construction. No live provider test ran. This is an offline baseline, not the entire suite including realdata.

## Execution matrix for future phases

| Layer | Now | Future gate |
|---|---|---|
| Offline unit / local DB / TestClient | Executed, 111 pass | Repeat in pinned supported Python 3.11+ matrix |
| Live integration: NSE equity, BSE equity, NSE CA, GDELT | Excluded, 4 deselected | Human-reviewed rights, explicit source/network scope, timeouts and isolated raw storage |
| Postgres / ClickHouse / Kafka / Redis / Airflow | UNVERIFIED | Disposable service profile explicitly authorized; no production endpoints |
| Signature verification | ARCH report only | Public trust root and isolated verification keyring; avoid mutating operational GnuPG home |
| Vulnerability advisory scan | BLOCKED for current advisories | Approved advisory retrieval; no install/network in OD-00 |
| Concurrency / disk failure / release rollback | Static gaps; daily overwrite reproduced | New tests under approved OD-04/10/11 scopes |
| Independent financial source comparison | UNVERIFIED | Official raw documents with rights and hashes; separate reviewer |

## Investigation coverage

Synthetic command experiments show: late-added membership admitted at an earlier as-of date; same-day Parquet replaced; HTML denial accepted by NSE equity validator; a rights event with no immediately prior calendar-day row returns no factor versus independent Decimal TERP factor 0.9. These are diagnostic RUN/SYN/CMP checks, not new committed tests or official-source claims.

## Limitations / next action

Passing offline tests do not cover the discovered invariants. Two unsuccessful harness attempts remain in evidence. No current application regression failure remains in the final selected baseline; no pristine-HEAD comparison was run. Approve only phase-specific negative tests, then verify failures before fixes. No test was weakened to obtain the passing result.

