# OD-02V runtime verification matrix

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


Final authoritative command set below uses explicit per-runtime Python and sanitized copy. Pytest is guarded against DNS, TCP/UDP, subprocess and protected-path writes during import/collection and execution, with fresh DB/raw/seed/release/report/GPG paths, explicit asyncio/cov plugins, disabled bytecode/cache and redirected coverage/mypy caches. Full exact command arguments, cwd, baseline, UTC intervals, duration and actual process exit are in every command JSON. No original data/release pointer is a write target.

| Runtime | Collection | Targeted rights/hardening/acquisition/OD02V | Complete offline regression | Exit |
|---|---|---|---|---|
| Windows 3.14.3 | 403/407 selected, 4 realdata deselected; [log](logs/win314-reviewed-collection.txt) | **282 passed, 0 failed, 10 skipped**; [log](logs/win314-reviewed-targeted.txt) | **393 passed, 0 failed, 10 skipped, 4 deselected**; [log](logs/win314-reviewed-full.txt) | all three **0** |
| Windows 3.11.15 | 403/407 selected, 4 realdata deselected; [log](logs/win311-reviewed-collection.txt) | **282 passed, 0 failed, 10 skipped**; [log](logs/win311-reviewed-targeted.txt) | **393 passed, 0 failed, 10 skipped, 4 deselected**; [log](logs/win311-reviewed-full.txt) | all three **0** |
| WSL Linux 3.12.3 | 403/407 selected, 4 realdata deselected; [log](logs/linux312-reviewed-collection.txt) | **290 passed, 0 failed, 2 skipped**; [log](logs/linux312-reviewed-targeted.txt) | **401 passed, 0 failed, 2 skipped, 4 deselected**; [log](logs/linux312-reviewed-full.txt) | all three **0** |

| Runtime | Ruff | mypy | pip check | Combined statement/branch coverage |
|---|---|---|---|---|
| Windows 3.14.3 | [exit 0](logs/win314-ruff.txt) | [exit 0](logs/win314-mypy.txt), 48 files | [exit 0](logs/win314-pip-check.txt) | **81.0265%**, [exact JSON](logs/win314-reviewed-full-coverage.json) |
| Windows 3.11.15 | [exit 0](logs/win311-ruff.txt) | [exit 0](logs/win311-mypy.txt), 48 files | [exit 0](logs/win311-pip-check.txt) | **81.0125%**, [exact JSON](logs/win311-reviewed-full-coverage.json) |
| WSL Linux 3.12.3 | [exit 0](logs/linux312-ruff.txt) | [exit 0](logs/linux312-mypy.txt), 48 files | [exit 0](logs/linux312-pip-check.txt) | **80.9564%**, [exact JSON](logs/linux312-reviewed-full-coverage.json) |

Acquisition module measured combined coverage **93.6709%** on each runtime: 264/279 statements, 106/116 branches. Different whole-project line/branch attribution across interpreters is retained rather than forced to match. Historical OD-02 coverage 80.78% is a separate ARCH number. Source-rights/acquisition and all inherited regression modules execute; the dedicated symlink proof is 4 passed/zero skipped. 17 new cases are present in the canonical `pytest` collection; no side test framework was introduced.

Windows 3.14 final full log contains **13 ResourceWarning lines for unclosed disposable SQLite connections** (plus their tracemalloc hints). They are not filtered or hidden. No such warning is emitted by the final 3.11/3.12 logs; those runtimes' warning behavior differs, which is not proof that connection hygiene is fixed. No unrelated connection-management refactor occurred. WSL also emits inherited missing drive/PATH translation warnings, retained in launch/setup logs. All final process exits are 0 despite these documented warnings/skips.

## Exact effective command forms

```text
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest --collect-only -q -m 'not realdata'
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py tests/unit/test_od02_acquisition.py tests/unit/test_od02v_portability.py -m 'not realdata'
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> ruff check --no-cache src/omegadata tests scripts
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> mypy src/omegadata
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pip check
```

The stored JSONs expand all placeholders to actual absolute paths/argv. Windows command logs use the Windows interpreter paths; Linux uses native /home venv/copy and /tmp tests, reached through WSL. Mypy caches are fresh temp; no old proof is regenerated. Pytest coverage DB/JSON is inside the disposable root and copied to fresh logs after guards are disabled. Per-test outcomes and deselected node IDs are retained in JSON, not inferred from summary text alone.

## Retained failures and no pass fabrication

| Attempt | Actual process result | Cause/disposition |
|---|---|---|
| `win314-baseline-targeted`, `win311-baseline-targeted` | exit 0; 272 pass / 3 skip | Unmodified reviewed baseline |
| `win314-baseline-full` | exit 1; 4 failed / 379 pass / 3 skip / 4 deselected | Sanitized copy omitted required local corpus archives; fixed only by exact fixture allowlist |
| `linux312-baseline-targeted` | exit 1; 8 failed / 265 pass / 2 skip | Runner misinterpreted descriptor-relative cleanup paths; app assertions otherwise successful; corrected guard pathname resolution |
| `confidentiality-negative` | exit 1; 7 failed / 9 deselected | Real synthetic confidentiality reproductions before application edits |
| `confidentiality-green` | exit 0; 7 passed / 9 deselected | Same tests after narrow evidence redaction fix |
| Initial `win311-*`, `linux312-*` pytest launcher commands | exit 1 after pytest summaries, missing result JSON | Runner post-test platform metadata queried while its os.open wrapper still enforced writes; raw launcher trace retained. Not counted as successful commands; reviewed reruns above exit 0 |
| Cache-only package resolution | exit 1, before tests | Existing local wheels insufficient; allowed official-index setup succeeded |

All named attempts have raw `.txt` logs under logs; launcher failures have `*-launcher.txt` and aggregate `*-matrix.json` actual exits. Setup controller observations are documented separately; no assertion was weakened and no failing requirement is silently removed. The two platform-specific skip sets are covered by actual corresponding filesystem execution on the other required platform; no physical-host independence or CI success is claimed.


## Final evidence-check correction

The retained [first mechanical check](logs/final-check.json) exited 1. It
identified a patch link checked before the patch had been created, and two
Windows 3.14 overlay hashes equal to the empty-file hash. Those hashes were
captured during a concurrent copy operation; the original Windows 3.14 matrix
therefore does not establish exact tested-source identity. No empty-file test
result is accepted as an identity proof. The sequential `win314-reviewed`
collection, targeted and complete regression commands replace that matrix as
authoritative evidence and record fresh source hashes. The first check and
all earlier command logs remain unchanged. The already-created patch is now
byte-compared with the current source diff, and the [reviewed final check](logs/final-check-accepted.json)
must pass before the Gatekeeper verdict is valid. No application or test
changes were made for this evidence correction.
