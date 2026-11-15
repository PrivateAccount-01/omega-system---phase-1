# Cross-process crash/recovery evidence

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

## win

[controller command](logs/win-process-accepted.json), [all worker commands/exits/output](logs/win-process-accepted.txt). Overall exit 0, passed=True. Five actual disposable workers killed, not exception mocks; Windows exit 1 and Linux -9 expected. Before-stage/after-stage/after-object/after-observation/before-marker have zero visible commit, then fresh worker retries same identity successfully. Kernel locks released on death.

Three writers plus independent reader (maximum four simultaneous workers) tested same and different bytes; every reference object/observation link verified. One conflicting operation produces one success and one expected exit 2 refusal, never two conflicting successes. Independent stdlib scan: **18 observations / 13 object files**, all full SHA/length/observation links valid; [scan](logs/win-corpus-reference.txt).

## linux

[controller command](logs/linux-process-persistent.json), [all worker commands/exits/output](logs/linux-process-persistent.txt). Overall exit 0, passed=True. Five actual disposable workers killed, not exception mocks; Windows exit 1 and Linux -9 expected. Before-stage/after-stage/after-object/after-observation/before-marker have zero visible commit, then fresh worker retries same identity successfully. Kernel locks released on death.

Three writers plus independent reader (maximum four simultaneous workers) tested same and different bytes; every reference object/observation link verified. One conflicting operation produces one success and one expected exit 2 refusal, never two conflicting successes. Independent stdlib scan: **18 observations / 13 object files**, all full SHA/length/observation links valid; [scan](logs/linux-corpus-persistent.txt).

Both exclusive hardlink and kernel-lock+absent-destination rename prototypes
execute on both OSes. The second prototype establishes basic local feasibility,
not a full production alternative implementation/concurrency certification.
Selected hardlink writer has actual concurrent process/crash evidence. Publication
never overwrites existing final files; existing destinations are read/compared.

The earlier process-v1 attempt exited 1: Windows audits Popen argv as a string,
the strict list allowlist refused it before any worker. Exact-issued-command
comparison corrected without widening executable/script authority. process-v2
then exercised workers but prototype fsync on read-only Windows fd failed EBADF;
changed prototype to writable fd. These are harness errors, not application red
proofs. v3/reviewed/accepted logs retained; accepted source hashes are authoritative.

Trusted fixed child executable/script (worker hash recorded), isolated root and
fixed argument variants only. Four child negative probes refuse DNS, TCP,
subprocess and protected copy writes. Each child blocks egress/process creation;
parent allows only exact issued commands. This separate harness does not weaken
the unchanged pytest audit guard. It is trusted Python, not an arbitrary ctypes
or kernel security sandbox. No user process targeted.

Recovery inventories retain staging, orphan observations and immutable objects;
no automatic reprocessing/promotion/deletion/GC. Counts explicitly UNVERIFIED;
scan_verified is separate full integrity verification. Idempotent supplied-request
retry safely reuses only matching records. No operational cleanup is authorized.
OS process death is tested; sudden power-loss, remote filesystem semantics and
hostile concurrent directory-owner races are NOT certified. Windows directory
fsync unsupported; POSIX created-child directories and final links fsynced, root
parent durability remains caller responsibility. Private trusted local root only.


## Corpus verifier correction and authoritative evidence

The first post-process Linux independent scan returned 0 observations/0 objects
after WSL removed the fresh /tmp corpus on session shutdown. This was a harness
verification defect: a missing root could pass vacuously. The retained
[old scan](logs/linux-corpus-reference.txt) and first final-preservation.json do
not prove persistent corpus completeness. The strengthened scanner requires an
existing root and exactly 18 commits/13 object files. Its
[missing-evidence negative](logs/linux-missing-corpus-negative.json) exits nonzero.
Linux process experiments were rerun in a fresh private native /home directory;
[new process commands](logs/linux-process-persistent.json) exit 0 and the
[independent persistent scan](logs/linux-corpus-persistent.txt) verifies all 18/13.
No old experiment or original data was deleted by this task. Both earlier logs
remain intact; this correction does not waive the separate Gate 2 chronology
block. Application/test source did not change for this harness correction.
