# OD-02 preflight

Branch `feature/od01-source-rights`; unchanged HEAD `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.


## Approval and preservation

Read the supplied OD-02 execution contract, automatic instruction facade, repository operating instructions, master and OD-01 instructions, OD-00 audit/plans, OD-01 evidence and complete OD-01R reports/code contract. Runtime registry, policy, downloader, orchestration, sequential pipeline, canonical probe and affected tests/transport helpers were inspected. No nested agent instruction files were discovered under source/tests/scripts/config. No sub-agent or independent human approval is claimed.

The prerequisite is [OD-01R Gatekeeper](../../od01r/20261115T065155Z/06_gatekeeper_verdict.md), `OD01R_TECHNICAL_PASS` for its executed Windows scope. Its [final reviewed QA](../../od01r/20261115T065155Z/logs/final-qa-reviewed.json) passed. The existing ten-file uncommitted patch matched its [reviewed patch](../../od01r/20261115T065155Z/logs/implementation.patch) byte for byte before OD-02: [fresh patch comparison](logs/od01r-patch-match.json). These were known prior work from this conversation, preserved by layering explicit OD-02 changes. Previous environment limitations do not become new approvals.

Repository root/remote/branch/HEAD/main merge-base, status, main...HEAD diff, Python/packages and tracked signing paths were freshly recorded in [preflight JSON](logs/preflight.json). Main remains `d4b5a58f0c50dc348e0d4e1150a725cc6fab5674`. No index/branch/commit/push mutation occurred. Worktree was already dirty: prior OD-01R production changes, automatic instruction file, supplied prompts, OD-01R tests/ADR/evidence, existing Linux environment and signing/revocation paths. No cleanup/stash/reset or source approval was performed.

[Before snapshot](logs/preservation-before.json) covers original tracked files, data/artifacts/root databases, source/tests/config, old OD-01R evidence/decisions and supplied prompts. Signing paths use length/mtime metadata only; key bytes were never opened or hashed. Final scope and preservation are checked in [final QA](logs/final-qa.json); exactly six prior files receive authorized OD-02 changes, plus three new implementation/config/test files. No historical report/data/release/signing changes are allowed.

## Execution environment and baseline

Windows 11 build 26300, PowerShell 5.1, repository `.venv/Scripts/python.exe` Python 3.14.3. Observed pytest 9.0.2, HTTPX 0.28.1, Pydantic 2.12.5, Ruff 0.15.9, mypy 1.20.0, coverage 7.13.5. Fresh baseline: **286 passed, 3 skipped, 4 realdata deselected**, exit 0; [command](logs/baseline.json), [output](logs/baseline.txt). The three file-symlink skips require unavailable Windows privileges; real junction cases execute.

The new [runner](verification_runner.py) derives from the audited OD-01R isolation harness: fresh temporary DB/raw/seed/reprocess/Parquet/release/report/GPG roots; blocked DNS/socket/subprocess; write audit outside disposable root refuses; explicit asyncio plugin only, cache/bytecode disabled. Windows internal socketpair is narrowly permitted for asyncio, not arbitrary connections. The harness self-test actually exercises prohibited DNS, subprocess, file and SQLite writes. Collection excludes the four realdata cases; no market/provider call, real signing or release-generation script is authorized. Package metadata and public upstream code lookup are read-only; no installs occurred.

Windows Python 3.11.15 and WSL Linux Python 3.12.3 were freshly inspected and targeted attempts made. Both lack pytest and necessary dependencies: actual **exit 1, ModuleNotFoundError**, not test failures or passes. See [Windows environment](logs/py311-environment.json), [attempt](logs/py311-targeted.txt), [Linux environment](logs/linux-environment.json), [attempt](logs/linux-targeted.txt). They remain BLOCKED. WSL also printed inherited missing drive/PATH translation warnings; no environment was repaired or installed.
