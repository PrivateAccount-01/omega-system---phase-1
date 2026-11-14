# 00 — Baseline identity and preservation

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Historian / Gatekeeper; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure and identity

Read the entire [master contract](../../verification/OMEGADATA_CODEX_MASTER_PROMPT.md) in UTF-8 chunks (lines 1–end) and the entire [supplied agent instructions](../../../OMEGADATA_AGENTS.md). Initial root AGENTS.md read failed: file absent. Searches found no nested AGENTS.md. E:/AGENTS.md was also absent. No PLANS.md, GOALS.md or PROMPTS.md was found by filename search. The supplied instruction file points to a master path that does not exist; this run uses the explicitly supplied verification path. Neither file was renamed.

Executed git identity/status/remote queries. Origin matches the expected HTTPS repository; branch and HEAD match the contract snapshot. The worktree is **not clean**. [Initial status](logs/git-status-before.txt) and [diff statistics](logs/git-diff-before.txt) are the authoritative full path lists.

Pre-existing edits include [warehouse.py](../../../src/omegadata/track_a/warehouse.py), [build_release_bundle.py](../../../scripts/build_release_bundle.py), GnuPG state, three profiles' manifests/signatures/quality/lineage, verification DB, release-build and readiness evidence. Existing untracked items include the Linux environment, supplied instructions/master prompt, and GnuPG files. These edits were not attributed to this audit. The saved status-before file was written after the audit log directory was created, so its untracked audit-directory entry is this run's own addition, not pre-existing user work. The initial tool orientation preceded that creation. Baseline results describe this working tree, not pristine HEAD.

## Environment matrix

| Property | Observed |
|---|---|
| OS / shell | Windows NT 10.0.26300.0 AMD64; Windows PowerShell 5.1.26100.9818 |
| CPU | Intel64 Family 6 Model 186 Stepping 2 |
| Interpreter | Existing .venv/Scripts/python.exe, Python 3.14.3 |
| Project | omegadata 0.1.0, editable at this checkout |
| Declared Python | >=3.11; CI calendar job uses 3.11 |
| Installed core | pandas 3.0.2; numpy 2.4.4; pyarrow 23.0.1; SQLAlchemy 2.0.49; FastAPI 0.135.3; httpx 0.28.1 |
| Installed checks | pytest 9.0.2; ruff 0.15.9; mypy 1.20.0 |
| Dependency health | pip check exit 0; no broken requirements |
| Other runtimes | Linux environment exists; not executed; Python 3.11 portability unverified |

Full versions and timestamps: [environment](logs/environment.txt), [host](logs/host.json), [package metadata](logs/module-and-package-inventory.json). Python tools configured the existing environment; no packages were installed or upgraded. VIRTUAL_ENV was not set in the shell; all Python commands used the explicit executable.

## Preservation

Started SHA-256 capture for 11,357 tracked files before tests; the long capture completed at 11:10:27Z, overlapping the first guarded attempt but preceding the final full offline run. [Read-only comparison](logs/preservation-check.json) found **zero tracked-file byte changes** after that snapshot. The new reports/logs are confined to this audit directory and the sibling plan directory. No commit, reset, push, PR, deployment or external acquisition occurred.

Temporary SQLite, Parquet and caches were created only for isolated checks. Pytest cache provider and bytecode writes were disabled; compileall redirected its bytecode cache to the sandbox temporary directory. No operational DB was initialized by this audit. The read-only SQLite inspections used mode=ro and query_only, without ORM startup.

## Limitations and next action

The hash snapshot is not an atomic pre-test filesystem image: early guarded execution overlapped its capture. The final full offline run and disposable integrity experiments occurred after capture completed. Ignored/untracked environment internals were not exhaustively hashed. Existing user work requires owner review before implementation; no stashing, committing or restoration is authorized. Install the intended AGENTS.md only in a separately approved change. Gate: CONDITIONAL for an audit package; no OD-01 work has begun.

