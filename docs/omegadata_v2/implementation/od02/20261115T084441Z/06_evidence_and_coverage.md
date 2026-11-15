# OD-02 execution evidence and coverage

Branch `feature/od01-source-rights`; unchanged HEAD `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.


Requested command equivalents ran through [the isolated runner](verification_runner.py), rather than unguarded pytest. Invocation shape:

```powershell
& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od02/20261115T084441Z/verification_runner.py' <unique-label> <module> <arguments>
```

Each JSON below contains the exact absolute executable, argv, cwd, UTC start/end, duration, exit and output filename. Effective pytest adds `-p pytest_asyncio.plugin -p no:cacheprovider --log-file <disposable> --basetemp <disposable>`; coverage additionally loads pytest_cov explicitly, puts its DB in disposable temp and retains JSON here. Network/DNS/subprocess and original-path writes are forbidden during tests, including collection. Tests that mock signing run only mocks against disposable directories; no historical signing or warehouse script was run.

| Label / effective command | Actual result and exit | Raw evidence |
|---|---|---|
| baseline: `pytest -q -m not realdata` | 286 passed, 3 skipped, 4 deselected; exit **0**, 20.58s | [command](logs/baseline.json), [output](logs/baseline.txt) |
| negative-first: `pytest -q tests/unit/test_od02_acquisition.py` | 16 failed, 2 passed (expected red); exit **1**, 1.45s | [command](logs/negative-first.json), [output](logs/negative-first.txt) |
| targeted-v1: `pytest -q tests/unit/test_od02_acquisition.py tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py` | 192 passed, 3 skipped, 1 failed (old invalid probe fixture); exit **1**, 3.31s | [command](logs/targeted-v1.json), [output](logs/targeted-v1.txt) |
| targeted-v2: `pytest tests/unit/test_od02_acquisition.py tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py -q -m not realdata` | 193 passed, 3 skipped; exit **0**, 3.55s | [command](logs/targeted-v2.json), [output](logs/targeted-v2.txt) |
| adversarial-v1: `pytest tests/unit/test_od02_acquisition.py -q -m not realdata` | 89 passed, 1 failed (missing error context); exit **1**, 1.86s | [command](logs/adversarial-v1.json), [output](logs/adversarial-v1.txt) |
| adversarial-v2: `pytest tests/unit/test_od02_acquisition.py -q -m not realdata` | 90 passed; exit **0**, 1.65s | [command](logs/adversarial-v2.json), [output](logs/adversarial-v2.txt) |
| overrides-negative: `pytest tests/unit/test_od02_acquisition.py -q -k invalid_overrides` | 4 failed, 2 passed, 91 deselected (expected red); exit **1**, 1.36s | [command](logs/overrides-negative.json), [output](logs/overrides-negative.txt) |
| targeted-final: `pytest tests/unit/test_od02_acquisition.py tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py -q -m not realdata` | 272 passed, 3 skipped; final fixture refinements then covered by final-reviewed; exit **0**, 3.74s | [command](logs/targeted-final.json), [output](logs/targeted-final.txt) |
| regression-v1: `pytest -q -m not realdata` | 376 passed, 3 skipped, 4 deselected; exit **0**, 22.64s | [command](logs/regression-v1.json), [output](logs/regression-v1.txt) |
| full-final: `pytest -q -m not realdata --cov=omegadata --cov-branch --cov-report=term-missing` | 383 passed, 3 skipped, 4 deselected; branch coverage; exit **0**, 29.44s | [command](logs/full-final.json), [output](logs/full-final.txt) |
| final-reviewed: `pytest -q -m not realdata --cov=omegadata --cov-branch --cov-report=term-missing` | 383 passed, 3 skipped, 4 deselected; final fixed-metadata/concurrent fixtures, branch coverage; exit **0**, 38.24s | [command](logs/final-reviewed.json), [output](logs/final-reviewed.txt) |
| collection-final: `pytest --collect-only -q -m not realdata` | 386/390 collected, 4 deselected; exit **0**, 2.92s | [command](logs/collection-final.json), [output](logs/collection-final.txt) |
| lint-v1: `ruff check --no-cache src/omegadata tests scripts` | 4 import-order errors; exit **1**, 0.27s | [command](logs/lint-v1.json), [output](logs/lint-v1.txt) |
| lint-v2: `ruff check --no-cache src/omegadata tests scripts` | All checks passed; exit **0**, 0.34s | [command](logs/lint-v2.json), [output](logs/lint-v2.txt) |
| lint-final: `ruff check --no-cache src/omegadata tests scripts` | All checks passed; exit **0**, 5.28s | [command](logs/lint-final.json), [output](logs/lint-final.txt) |
| lint-reviewed: `ruff check --no-cache src/omegadata tests scripts` | All checks passed; exit **0**, 0.26s | [command](logs/lint-reviewed.json), [output](logs/lint-reviewed.txt) |
| type-v1: `mypy src/omegadata` | 3 tuple-inference errors in new validator; exit **1**, 10.63s | [command](logs/type-v1.json), [output](logs/type-v1.txt) |
| type-v2: `mypy src/omegadata` | 48 source files clean; exit **0**, 14.02s | [command](logs/type-v2.json), [output](logs/type-v2.txt) |
| type-final: `mypy src/omegadata` | 48 source files clean; exit **0**, 14.07s | [command](logs/type-final.json), [output](logs/type-final.txt) |
| pip-final: `pip check` | No broken requirements found; exit **0**, 1.26s | [command](logs/pip-final.json), [output](logs/pip-final.txt) |
| py311-targeted: `pytest tests/unit/test_od02_acquisition.py -q -m not realdata` | BLOCKED: missing pytest (no test executed); exit **1**, 0.11s | [command](logs/py311-targeted.json), [output](logs/py311-targeted.txt) |
| linux-targeted: `pytest tests/unit/test_od02_acquisition.py -q -m not realdata` | BLOCKED: missing pytest (no test executed); exit **1**, 0.05s | [command](logs/linux-targeted.json), [output](logs/linux-targeted.txt) |

## Coverage and warnings

Final [coverage JSON](logs/final-reviewed-coverage.json): **4,690 / 5,526 statements (84.87%)**, **1,052 / 1,582 branches (66.50%)**, combined statement/branch coverage **80.78%**. Acquisition module: **247/264 statements (93.56%)**, **97/108 branches (89.81%)**, combined **92.47%**. Downloader: 571/749 statements, 142/250 branches, combined 71.37%. Rights: 269/270 statements, 71/72 branches, combined 99.42%. Coverage is measured, not complete proof; uncovered paths are retained in raw report/JSON, not suppressed. Scripts are outside the `--cov=omegadata` coverage target although their targeted assertions execute.

Final covered run prints **one ResourceWarning for an unclosed temporary SQLite connection during pytest GC** after its summary; earlier OD-01R logs also reported cleanup warnings. It is retained, not suppressed or claimed fixed. Three Windows file-symlink skips are WinError 1314; no case is relabeled PASS. Four realdata tests were deliberately deselected. WSL printed missing drive/PATH translation warnings; both alternate-runtime attempts fail import because pytest/dependencies are absent, not because of a proven application incompatibility.

No installs/pins changes occurred. [Current environment](logs/preflight.json), [Python 3.11 metadata](logs/py311-environment.json), [Linux metadata](logs/linux-environment.json), [113-file Python 3.11 grammar parse](logs/parse-and-component-inventory-v2.json) are separate evidence: syntax parsing is not runtime success. Public upstream lookup supplied dependency/license context only; no dlt/Scrapy benchmark/CVE/official exchange-reference validation occurred.

Read-only inventory command: `& '.venv/Scripts/python.exe' -B 'docs/omegadata_v2/implementation/od02/20261115T084441Z/review_checks.py' inventory`, final exit 0, 113 parsed files and 84 inventoried network/mock boundary calls. Its first attempt saved the valid inventory then failed an assertion in reconstructing the original test fixture; the reconstruction used the actual original `elif revoke_after_bootstrap:` and then verified its original preflight hash. No source or test result was changed by that reporting helper. Original inventory log retained alongside v2.

Final preservation/report check: [review helper](review_checks.py), [QA JSON](logs/final-qa.json). This verifies original path hashes/metadata, exact source policy default, branch/main/index identity, current artifact existence and local links. It does **not** convert blocked runtime dimensions into a passing Gatekeeper.
