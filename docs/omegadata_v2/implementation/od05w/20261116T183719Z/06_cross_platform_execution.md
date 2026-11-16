# Fresh final runtime execution

All exact argv/cwd/interpreter/UTC/exit/stdout/stderr: [command index](command-index.json), [final matrix](runtime-matrix.json), [source identities](runtime-source-identity.json), [coverage](coverage-summary.json). Final runner/code hashes match across all three runtime matrices. Installed package inventories are in the environment logs.

| Runtime | Focused | A | Unchanged full diagnostic | Ruff / mypy / pip / compile |
|---|---|---|---|---|
| win314 | {'passed': 39} | {'passed': 753, 'skipped': 14} | exit 1: {'passed': 753, 'failed': 4, 'skipped': 14}; C 4 deselected | all exit 0 |
| win311 | {'passed': 39} | {'passed': 753, 'skipped': 14} | exit 1: {'passed': 753, 'failed': 4, 'skipped': 14}; C 4 deselected | all exit 0 |
| linux312 | {'passed': 39} | {'passed': 762, 'skipped': 5} | exit 1: {'passed': 762, 'failed': 4, 'skipped': 5}; C 4 deselected | all exit 0 |

Every OS/privilege skip has an actually passing exact-node counterpart, recorded separately; no skip becomes a pass. WSL PATH translation and SQLite cleanup warnings are retained. Linux is native filesystem code/canary storage on the same WSL host. Pip check verifies installed dependency consistency; it is not a fresh CVE/license audit. Security/source-rights regressions are part of A. The original-mount performance failure and missing OS-isolation backend remain explicit limitations.
