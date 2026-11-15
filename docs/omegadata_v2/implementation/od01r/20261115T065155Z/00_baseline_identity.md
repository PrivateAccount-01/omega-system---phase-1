# OD-01R baseline identity and preservation

Phase: REVIEW_VERIFY_AND_HARDEN_OD01_ONLY. Evidence classes RUN/TEST/SYN/ARCH/UNK. AEF roles are same-model procedural reviews, not separate humans or independent agents.

## Verified checkout

Repository root E:/omega system - phase 1; origin PrivateAccount-01/omega-system---phase-1 (HTTPS). Branch **feature/od01-source-rights**; HEAD **3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc**. Read-only git ls-remote returned that same upstream feature SHA. Main and merge-base are **d4b5a58f0c50dc348e0d4e1150a725cc6fab5674**: feature is one commit ahead of main. No fetch/rebase/reset/checkout/stash, stage/commit/push/PR or phase advance was performed. [Preflight commands and package versions](logs/preflight.json) preserve stdout/stderr and exits. [Final QA](logs/final-qa-reviewed.json) checks branch/HEAD and the index again.

Entry tracked diff was empty. Pre-existing untracked items: user remediation prompt, Linux environment, and three GnuPG signing/revocation paths. These are disjoint from edits and preserved. Only filenames/size/mtime of GnuPG paths were inspected; no signing contents opened, hashed, copied, tested or transmitted. The new evidence directory was created after initial orientation, so its entry in preflight status belongs to this run.

## Instructions and historical evidence

Read the complete supplied OD-01R contract, root OMEGADATA_AGENTS.md, current master at docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md, OD-01 prompt, all nine OD-00 audit reports, plans 09/10/11, all seven required OD-01 implementation reports, verification runner and affected source/tests. No root or nested AGENTS.md existed initially. The stale master pointer is a documentation defect, not a conflicting phase authorization; latest user authorization selects OD-01R. Root AGENTS.md now loads the retained instruction file, whose pointer alone was corrected. No technical rule was weakened. The optional November branch-audit lead file was absent. AEF/Founder external packages were not fetched or invented.

## Runtime matrix

| Dimension | Observed result |
|---|---|
| Primary | Windows 11 Home Single Language, build 26300; PowerShell 5.1; existing .venv/Scripts/python.exe 3.14.3 |
| CPU/RAM | Intel i7-1360P, 16 logical processors; 16,454,352 KiB visible RAM, 2,180,716 KiB free at query |
| Packages | Pydantic 2.12.5, httpx 0.28.1, pytest 9.0.2, Ruff 0.15.9, mypy 1.20.0, coverage 7.13.5; complete pip list in preflight |
| Python 3.11 | Existing base 3.11.15 found, but only omegadata metadata/pip/setuptools installed; pytest, Pydantic, httpx and application dependencies absent. Execution matrix BLOCKED; no install. [Metadata](logs/py311-environment.json) |
| Linux | Existing Ubuntu/WSL Python 3.12.3; pip check exit 0, but pytest import raises ModuleNotFoundError and Pydantic/httpx/SQLAlchemy are absent from inventory. Matrix BLOCKED; no install. [Inventory](logs/linux-environment.json), [failed run](logs/linux-targeted.txt), [pip](logs/linux-pip.json) |
| CI | Existing calendar-only Python 3.11 workflow inspected and unchanged. No CI run, new workflow or CI success claimed |

Initial CIM and WSL inventory queries were sandbox-denied; approved read-only retries succeeded. WSL emitted inherited PATH translation warnings for unavailable Windows drive paths; no source access resulted. py launcher reported no registered runtimes, but filesystem inventory found uv-managed 3.11; its package inventory was inspected without installation and the original configured 3.14 environment restored. Details: [tool observations](logs/tool-observations.md).

## Test isolation and protection

Audited OD-01 runner before copying it into this new directory. OD-01 logs were never reused as output targets. New runner uses exclusive evidence creation, temporary SQLite/raw/seed/parquet/release/report/reprocess/GPG locations, disabled bytecode/cacheprovider, empty webhook, socket/DNS/subprocess denial, and an audited write/SQLite-path guard. Windows internal socketpair construction alone retains its stdlib connection exception. Only explicitly needed pytest plugins load. The guard self-test verifies forbidden file, DB, DNS and child-process operations raise before effects. Coverage writes to disposable paths, then the runner copies its JSON after tests end. This is an accidental-side-effect guard, not an OS sandbox against malicious Python/native code.

[Original snapshot](logs/preservation-before.json) covers tracked files plus data/artifacts/root DBs and the untracked supplied prompt; GnuPG is metadata-only. Snapshot capture overlapped the fresh read-only/guarded baseline, but completed before production edits. [Final QA](logs/final-qa-reviewed.json) compares every original record, allowing only the ten explicitly scoped tracked edits. No test depends on a production DB. Historical raw data, releases, OD-00/OD-01 reports, signatures and user work remain protected. Ignored environment internals were not exhaustively hashed.
