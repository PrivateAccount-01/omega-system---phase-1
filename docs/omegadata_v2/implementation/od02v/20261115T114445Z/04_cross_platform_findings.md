# OD-02V findings and review

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


| Finding | Executed evidence | Narrow action / final state |
|---|---|---|
| V-01 runtime dependency absence | Prior attempts failed before collection; new pre-install inventories confirm missing pytest/app dependencies | Authorized fresh Windows 3.11 and native Linux 3.12 venvs, existing declared requirements, official PyPI and working-version constraints; full matrix now executes with exit 0 |
| V-02 skipped symlink assertions | Original three real-file symlink cases now execute and pass on Linux, real links true/outside reads 0 | No inherited test edit. Windows WinError 1314 remains an explicit OS privilege limit; Windows junction analogues pass |
| V-03 confidential URL evidence **P1, corrected** | Seven executable negative-first failures: recognized path credential values, legacy cached URL query/path, typed public error context expose only synthetic sentinel | Evidence-only safe_url redacts known credential field/value path segments and malformed URL fallback; legacy cached URL uses same helper. Seven green plus full regression on all three runtimes |
| H-01 sanitized fixture omissions | First Windows full run has four failures due missing existing archive references/seed identity map | 47 exact fixture dependency files (6,138,891 bytes) copied/hashed to isolated trees only. No data fixture mutation, generated fake prices, assertions change or source approval |
| H-02 POSIX dir_fd cleanup | Linux targeted run has eight TemporaryDirectory cleanup failures under write guard | Resolve actual /proc/self/fd anchor for relative unlink/rmdir/mkdir/link/rename and wrapped os.open. Added negative tests deny descriptor-relative protected writes. No blanket allow of relative paths or sockets |
| H-03 controller metadata and WSL lifetime | First Linux install exited 0, controller failed generated egg-info checksum assertion; retry of finalizer after WSL restart found /tmp copy gone | Record build-generated egg-info separately from source equality; new disposable /home native location persists. Old /tmp paths were not manually removed. No historical data involved |
| H-04 postlude runner exit | First 3.11/Linux matrix commands reached successful pytest summaries but launcher exited 1 on protected devnull open during platform metadata | Warm complete OS metadata before guards; restore wrapped os.open only after guarded tests finish. Preserve initial traces and rerun collection/targeted/full to real exit 0 |
| Portability evidence | English_India/1252/IST on Windows; C.UTF-8/UTC on Linux. Case-insensitive CRLF vs case-sensitive LF measured; 320/304 character paths succeed | Exact HEAD code/tests copied using Git blobs; inherited drive/port/path/ISO/date/ZIP checks execute. ZIP legacy/current expected mixed-case member names and raw hashes pass all runtimes. Not an exhaustive locale/filesystem/ZIP fuzzing certificate |
| SQLite cleanup **P2, open** | Thirteen unclosed disposable-connection ResourceWarnings in Windows 3.14 full log | Kept visible. No unrelated DB cleanup refactor; no original DB touched. Lower Python versions' absence of warning is not closure |
| Hostile concurrent filesystem ownership, open limitation | Static path confinement and pre-call retarget scenarios verified; no descriptor-based atomic file-open boundary in existing manager | Do not claim TOCTOU/symlink-race sandbox. Cache directories require trusted ownership. Actual provider egress remains blocked; larger archive/storage redesign not authorized |

The first setup-controller checksum assertion and later FileNotFoundError were observed in tool output (not a fresh raw controller transcript), while each underlying venv/cache/install command has exclusive logs/metadata. They are reporting/setup mistakes, not application negative tests. Corrected setup did not install into or alter the original repository.

Maker: required runtime/security matrix and fixture provenance; Reviewer: fresh failures separated from missing setup/guard limitations; Implementer: only two red-proven application changes; Reviewer: unchanged inherited assertions, exact tested hashes, 17 additional cases and all platforms; Gatekeeper: command exits/denominator/preservation; Historian: this report set plus patch/logs. This is same-model procedure, not invented independent human consensus. Independent human/security review remains recommended before new production capabilities. No sub-agents, paid service or external market requests.


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

The [second mechanical check](logs/final-check-reviewed.json) also exited 1 solely because its own not-yet-written JSON link was treated as missing. All source identity, test, policy and preservation checks were true. The checker now exempts only its exact forthcoming result path; all other links must exist. The [accepted check](logs/final-check-accepted.json) is the final authoritative result. Both earlier failed checks are retained.
