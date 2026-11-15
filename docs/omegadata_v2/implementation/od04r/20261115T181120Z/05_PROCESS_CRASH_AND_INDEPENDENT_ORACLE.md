# Crash, concurrency and independent byte oracle

OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.


Reused audited worker/guard architecture with fresh disposable roots and exact launcher logs. Parent allows only issued exact worker argv; children deny DNS/TCP/UDP/process and protected writes. Four guard-negative probes per OS succeed. This protects against accidental side effects, not arbitrary malicious Python. [Windows result](logs/win-process-result.json), [Linux result](logs/linux-process-result.json) retain executable/platform/UTC/duration/PID/exits/raw output, worker hashes and both application source hashes. Source code did not change after these experiments; subsequent changes added tests only.

| Process proof | Windows3.14.3 | Linux3.12.3 |
|---|---|---|
| Same bytes | 3writers,3events/1object, concurrent reader | Same |
| Different bytes | 3writers,3events/3objects, concurrent reader | Same |
| Conflicting ID | Two workers, exactly one0 and one2 | Same |
| Forced crash boundaries | All5, killed exit1, no marker, fresh-process retry succeeds | All5, killed exit-9, no marker, retry succeeds |
| Independent corpus | 18observations/13objects | 18observations/13objects |
| Oracle order | Missing1 then positive0; moved-old-root1 then moved-positive0 | Same |

Readers verify three committed payloads each; paused-publication unit tests also prove NOT_COMMITTED until complete. Five crash points: before_stage,after_stage,after_object,after_observation,before_commit. Existing bytes remain; retained staging is not promoted/deleted. Recovery inventory for same namespace reports3markers explicitly UNVERIFIED; independent byte oracle supplies trust. Killed/losing/negative exits are expected experiments, never pytest successes.

[Independent oracle](independent_oracle.py) uses stdlib and imports no archive code. Counts and payloads are separately pinned, never read from service inventory: same3/1,different3/3,conflict1/1,five crashes each1/1,benchmark6/3. Every full SHA/size, canonical marker/observation bytes, duplicate-key refusal, operation/file/observation identity, raw observation SHA/commit link, content-derived object path and source/date checked. All modes SYNTHETIC_TEST_ONLY; published_at null and SOURCE_REFERENCE_PENDING. Conflict winner may be either of two known frozen candidates; no fabricated deterministic winner.

First missing-root negative runs before positive assertions. Then only each run's exact recorded disposable corpus is moved after absolute parent/prefix/destination checks; old path must fail and new path independently verify18/13. [Windows moved positive](logs/win-oracle-moved-positive.txt), [Linux moved positive](logs/linux-oracle-moved-positive.txt), corresponding negative and relocation argv/UTC/exits retained. No old/source-data root moved. Native Linux /home corpus survives separate WSL launches; no vacuous transient/tmp result accepted.

Local measurements include4KiB/64KiB/1MiB put/read/recovery time, tracemalloc, logical retained bytes and hardlink-aware inode bytes in process JSON. Single synthetic local samples, no p95/third-party speedup claim. Hardlink versus kernel-lock/rename pilots are feasibility controls; rename pilot is not adopted as an alternate transaction engine. No physical-host, hardware power-loss, Windows directory-fsync, NFS or hostile-owner guarantee.
