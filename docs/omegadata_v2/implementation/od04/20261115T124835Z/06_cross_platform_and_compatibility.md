# Cross-platform and compatibility verification

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

| Runtime | Targeted pass / skip | Full pass / skip / deselected | Combined coverage | Static/package exits |
|---|---:|---:|---:|---|
| win314-accepted | 340 / 10 | 451 / 10 / 4 | 81.3568% | Ruff 0; mypy 0; pip 0 |
| win311-accepted | 340 / 10 | 451 / 10 / 4 | 81.3437% | Ruff 0; mypy 0; pip 0 |
| linux312-accepted | 348 / 2 | 459 / 2 / 4 | 81.3437% | Ruff 0; mypy 0; pip 0 |

All final collection/targeted/full commands exit 0; mypy checks 49 files. Exact
command/exit/time/per-node metadata and complete raw output are paired under logs
using each runtime prefix above. 58 new OD04 cases execute on all three runtimes.
Windows retains 10 inherited real file-link privilege skips; Linux retains only
two Windows-junction skips. Linux actually executes the original three file-link
security cases; Windows actually executes junction cases. New archive directory
escape tests use real junctions on Windows and real symlinks on Linux, zero new
skips. Existing tests were not changed, xfailed or suppressed.

Default APIs, exact corpus identities, synthetic parser schemas, SQL/Parquet clients,
orchestration and rights/transport/resource denials all regress unchanged. Opt-in
cache miss produces no legacy/archive directories or request. Read-only legacy
facade has LEGACY_UNVERIFIED, absent commit ID; dry-run mapping hashes exact local
bytes and never updates latest. No in-place data migration or official relabeling.
Byte identity and ISO UTC times are stable; cached/seed transport distinction
preserved. No locales/case/path semantics beyond actual runtime tests certified.

Windows 3.14 SQLite ResourceWarnings remain unsuppressed; exact counts in metrics.
No warning filters added. WSL inherited missing-drive PATH warnings retained,
not interpreted as failed tests or silently removed. WSL shares physical host;
this is OS filesystem/runtime evidence, not an independent physical-host/CI run.
