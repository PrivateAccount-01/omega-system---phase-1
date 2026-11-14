# OD-01 executed test matrix

Repository: PrivateAccount-01/omega-system---phase-1. Phase: OD-01 IMPLEMENT_OD01_ONLY.
Branch: feature/od01-source-rights. HEAD before/after: d4b5a58f0c50dc348e0d4e1150a725cc6fab5674 (no commit).
Evidence collected 2026-11-14 UTC; exact command times/exit codes in [logs](logs/). Run directory name was allocated at 13:33:40Z; approval/environment delays mean later commands ran through 15:09Z and document checks later. Owner: same-model procedural engineering reviewer, not a human rights approver.

## Environment and command execution

Existing repo interpreter: `.venv/Scripts/python.exe`, Python 3.14.3 on Windows. [Preflight](logs/preflight.json) records commands, shell, OS, versions, stderr and underlying exits. No packages installed. All pytest commands run through [verification_runner.py](verification_runner.py), with socket connect/connect_ex/create_connection/sendto denied except Windows internal socketpair construction; subprocess audit hook denies child execution during tests. Disposable DB/raw/seed/release/report/reprocess/GPG output paths, disabled bytecode/cacheprovider, empty alert destination and run-local coverage files preserve existing work.

Reproduce from repository root with the configured interpreter:

```powershell
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od01/20261114T133340Z/verification_runner.py' targeted-reviewed pytest -q tests/unit/test_od01_source_rights.py
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od01/20261114T133340Z/verification_runner.py' full-offline-reviewed pytest -q -m 'not realdata' --cov=omegadata.track_a.source_rights --cov=omegadata.track_a.download_manager --cov-branch --cov-report=term-missing --cov-report=json:docs/omegadata_v2/implementation/od01/20261114T133340Z/logs/coverage-reviewed.json
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od01/20261114T133340Z/verification_runner.py' ruff-reviewed ruff check --no-cache src/omegadata tests scripts
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od01/20261114T133340Z/verification_runner.py' mypy-reviewed mypy src/omegadata
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od01/20261114T133340Z/verification_runner.py' pip-final pip check
```

These are actual command recipes already executed, not authority to overwrite their logs. A later reproduction must choose new unique labels/run directory. Exact UTC/start/end/elapsed/module arguments and exits accompany every saved result JSON. No marked realdata test, release/readiness builder, pipeline reset, service profile or provider probe was executed.

| Run | Exit / observed outcome | Evidence |
|---|---|---|
| Fresh collection | 0; 111/115 tests selected, four deselected | [JSON](logs/baseline-collection-v3.json), [output](logs/baseline-collection-v3.txt) |
| Fresh baseline | 0; 111 passed / four deselected, 17.43s | [JSON](logs/baseline-offline-v3.json), [output](logs/baseline-offline-v3.txt) |
| Baseline Ruff / mypy | 0 / 0; clean lint; 46 source files typed | [Ruff](logs/baseline-ruff.txt), [mypy](logs/baseline-mypy.txt) |
| Negative-first, existing production code | 1; one failed: DID NOT RAISE RuntimeError POLICY_PENDING (cache mock returned) | [JSON](logs/negative-first.json), [failure](logs/negative-first.txt) |
| Same crucial test after guard | 0; one passed, same expected refusal/side-effect assertions | [JSON](logs/negative-first-green.json), [output](logs/negative-first-green.txt) |
| Initial comprehensive rights cases | 0; 69 passed | [output](logs/targeted-v1.txt) |
| First full regression after feature | 0; 180 passed / four deselected | [output](logs/full-offline-v1.txt) |
| Final targeted after review | 0; **100 passed**, 1.35s | [JSON](logs/targeted-reviewed.json), [output](logs/targeted-reviewed.txt) |
| Final full offline + branch coverage | 0; **211 passed, 4 deselected, 8 warnings**, 19.35s | [JSON](logs/full-offline-reviewed.json), [output](logs/full-offline-reviewed.txt) |
| Final Ruff / mypy / pip | 0 / 0 / 0; clean lint, 47 source files typed, no broken requirements | [Ruff](logs/ruff-reviewed.json), [mypy](logs/mypy-reviewed.json), [pip](logs/pip-final.json) |

The 8 final warnings are ResourceWarning messages for unclosed disposable SQLite connections in existing API/FO/universe tests under coverage/GC; extra cleanup warnings appear after pytest's summary. They were not suppressed or fixed by widening this phase. Non-coverage baseline and first regression passed without these reported warnings; this run does not prove they are caused by OD-01.

## Mandatory T01–T18 mapping

All functions below live in [test_od01_source_rights.py](../../../../../tests/unit/test_od01_source_rights.py); each was executed in the final targeted run (exit 0) and final full run (exit 0). Parametrized names in brackets refer to the test's actual case labels.

| Case | Actual test(s) | Verified expectation / status |
|---|---|---|
| T01 unknown | test_t01_t11_download_refusals_have_zero_side_effects[unknown-UNKNOWN_SOURCE] | Typed UNKNOWN_SOURCE; zero cache/candidate/client/fetch/payload-read/write/mkdir calls — PASS |
| T02 missing | same function [missing-MISSING_POLICY]; test_missing_policy_file_is_typed_refusal | Known source missing record/file refuses — PASS |
| T03 pending | same [pending-POLICY_PENDING]; test_pending_default_stops_before_cache_disclosure; test_default_pending_blocks_every_source_before_cache (13 keys) | No payload return or raw directory creation — PASS |
| T04 denied | same [denied-POLICY_DENIED] | No fallback selection — PASS |
| T05 revoked | same [revoked-POLICY_REVOKED]; test_t16_revoked_cache_and_seed_do_not_read_payload | Zero cache/seed payload bytes read, writes or HTTP — PASS |
| T06 expiry | same [expired-POLICY_EXPIRED] and [expiry_state-POLICY_EXPIRED] | Half-open valid_until and explicit EXPIRED state refuse — PASS |
| T07 evidence | same [evidence-EVIDENCE_INCOMPLETE]; test_t07_each_missing_approval_evidence_field_is_denied (nine fields) | Missing principal/terms/hash/times/reference/interval refuses — PASS |
| T08 operations | test_t08_fetch_does_not_grant_redistribution | FETCH can allow, REDISTRIBUTE refuses under same fake policy — PASS |
| T09 purpose | test_t09_research_does_not_grant_trade_use | RESEARCH does not grant TRADE_DECISION_USE — PASS |
| T10 host | same [host-HOST_NOT_ALLOWED]; test_t10_evaluator_exact_host_scope; test_foreign_discovered_host_is_denied_before_client | Foreign/scheme/port/wildcard/absent remote host refuses before client — PASS |
| T11 transport | same [transport-TRANSPORT_NOT_ALLOWED]; test_t17_denied_fallback_transport_is_terminal | Unapproved HTTPX/fallback transport refuses, no later fallback — PASS |
| T12 happy fake acquisition | test_t12_fake_http_acquisition_preserves_envelope | Exactly one MockTransport request; raw bytes/SHA-256/envelope preserved; subsequent approved cache hit no second request; new decisions attributable, old manifest unchanged — PASS |
| T13 revisions | test_t13_latest_revocation_keeps_old_decision_attributable | Revision 2 revoked denies, old revision-1 immutable decision/hash retained — PASS |
| T14 strict schema | test_t14_naive_policy_dates_reject; test_t14_request_timestamp_ambiguity_rejects; test_t14_malformed_fields_reject; test_t14_duplicate_entries_and_unlinked_revisions_reject; test_t14_malformed_file_denies_before_transport; test_structural_policy_inconsistencies_are_malformed; test_invalid_register_history_identity_rejects | Unknown fields/status/ops, naive/non-UTC/numeric time, bad digest, duplicate JSON/revisions, unlinked history and invalid encoding reject — PASS |
| T15 exhaustive defaults | test_t15_every_registered_default_is_pending | 13 discovered == 13 policy keys; zero approvals/permissions — PASS |
| T16 cache/seed | test_t16_revoked_cache_and_seed_do_not_read_payload (both roots); test_cache_only_permission_does_not_escalate_on_miss | READ_CACHED explicitly enforced, cache miss cannot gain FETCH — PASS |
| T17 terminal refusal | test_t17_policy_refusal_in_fetch_is_not_swallowed; test_t17_denied_fallback_transport_is_terminal; test_t17_optional_pipeline_refusal_does_not_try_later_source | No candidate/profile/transport/optional-source retry after policy refusal — PASS |
| T18 concurrency | test_t18_concurrent_decisions_are_immutable_and_deterministic; test_t18_transport_source_context_is_thread_local | 32 equal fixed-input decisions, frozen models and per-thread source scope — PASS |

Additional covered boundaries: all manager acquisition entry points fail closed; standalone source-probe script denies before curl; valid mocked probe retains policy revision; policy provider refresh at an operation boundary; malformed source-key container rejects rather than raising an untyped hash lookup error; STORE_RAW precondition; future approvals; normalized DNS/local cache semantics.

## Coverage and limitations

[Actual branch/line coverage JSON](logs/coverage-reviewed.json): new policy module 250/251 statements (99.60%), 65/66 branches (98.48%), combined 99.37%; display 99%. Downloader has 427/678 statements and 88/210 branches, combined 58.00%. Low downloader physical-path coverage is explicit, not a claim of source availability. No baseline coverage delta was measured; the new policy module had no previous baseline counterpart. No coverage-regression claim for the whole application is made.

Source-specific rights, human evidence authenticity, current external advisories, live sources, supported Python 3.11 runtime and Linux/service behavior remain UNVERIFIED/PENDING. Redirect chains, actual HTTP 403/429 terminal propagation and payload financial truth are future-phase acceptance, not tested as newly fixed here.

## Failed attempts retained

Initial extra subprocess guard replaced Popen with a function, breaking Windows asyncio subclass import (exit 1 before collection; empty initial output files, original traceback in tool transcript). Corrected to an audit hook; the next attempt blocked stdlib platform.uname's local OS command (pytest module exit 4; [collection trace](logs/baseline-collection-v2.txt), [baseline trace](logs/baseline-offline-v2.txt)). Warmed only the stdlib OS cache before the guard, then both full baseline commands passed. These are harness failures, not application regressions; no permission was granted for arbitrary test subprocesses.

[Initial Ruff errors](logs/ruff-v1.txt) were import placement and lambda assignment in new tests, corrected without weakening expectations. One added fallback-negative test had Mock.cookies non-iterable ([trace](logs/targeted-v3.txt)); corrected the mock client to supply an empty cookie dictionary, keeping expected terminal refusal/call counts unchanged. Same negative-first function body was preserved; only import positions/line numbers moved during formatting. All earlier output is retained with distinct labels.

