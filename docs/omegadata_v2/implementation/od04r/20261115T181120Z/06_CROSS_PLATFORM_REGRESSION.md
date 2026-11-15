# Complete offline runtime matrix

OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.


All required commands actually executed. [Machine matrix](logs/reviewed-current-runtime-matrix.json) retains exact absolute executable/argv/cwd/OS/UTC/duration/actual exits/raw references and skips; per-node raw JSON remains authoritative. [All146 tested source/config/test identities](logs/reviewed-final-tested-identities.json) match. Second reviewed matrix includes27new tests; earlier final matrix includes20 and is retained, not overwritten. No application code changed between these matrices.

Full selected denominator488, total492 including4realdata deselected. Windows478pass+10skip=488; Linux486+2=488. Targeted denominator377. Collection covers all offline unit/integration tests, not only archive files.

| Runtime | Python | Targeted pass/skip | Full pass/skip/deselected | Collection,targeted,full,ruff,mypy,pip exits | Whole combined line/branch | Archive combined | SQLite warning lines |
|---|---|---|---|---|---|---|---|---|
| win314-reviewed | 3.14.3 | 367/10 | 478/10/4 | all0 | 81.5624% | 88.7550% | 13 |
| win311-reviewed | 3.11.15 | 367/10 | 478/10/4 | all0 | 81.5493% | 88.7550% | 0 |
| linux312-reviewed | 3.12.3 | 375/2 | 486/2/4 | all0 | 81.5493% | 89.5582% | 0 |

Ruff checks --no-cache src/omegadata tests scripts; mypy strict49source files; pip check no broken requirements. Existing exact installed distributions recorded, no installs/locks/CI modifications. No online advisory/CVE clearance claimed. Editor Problems checked; git diff --check0. Initial lint preview1 found new helper dict style and was corrected. Display-only PowerShell ConvertFrom-Json failed on coverage property names; actual coverage JSON was successfully read using Python. First reconciliation helper failed on Windows3.11 backslash coverage paths; fixed only helper normalization and successful exclusive reconciliation recorded. An oversized report-authoring shell command was rejected before execution; switched to direct patches. All are harness/report issues, not application reds.

Ten Windows file-symlink privilege skips are matched by exact passing Linux nodes. Two Linux Windows-junction skips pass on Windows. [Dedicated actual-symlink run](logs/linux312-symlink-proof.json) passes9selected cases; all3original file-link cases actually execute, observed links true and outside reads0. No skip counted as pass. Four realdata deselections preserved. Existing SQLite warnings are retained P2, no suppression. WSL stale D/G PATH warnings retained.

Whole and archive coverage are compared with prior accepted measured coverage; newly critical scan/root/count/walk-error lines execute. Old rare IO/model/lock branches remain partial, not100% coverage. Guard negatives execute for DNS/TCP/UDP/subprocess/protected-write, including Linux dir_fd paths. Tests do not authenticate official source/financial truth.

[CI observation](logs/ci-observed.json): reviewed-SHA statuses[] and first-page PR-workflow_runs[]; no successful feature-SHA CI observed. Query limitation prevents universal all-events absence claim. No CI validates local uncommitted corrections. WSL is the same physical host.

RUN filesystem probes: Windows C: and E: report NTFS through GetVolumeInformationW, success=true, error0 ([exact output](logs/windows-filesystem.txt)). Linux native/home stat reports ext2/ext3 family ([exact output](logs/linux-filesystem.txt)); this does not assert remote/NFS or power-loss durability. Package and runtime profiles are reused, not newly installed.

Current whole combined coverage81.5624%/81.5493%/81.5493% exceeds prior81.3568%/81.3437%/81.3437%. Archive coverage88.7550%/88.7550%/89.5582%; new critical lines covered. [Exact CI tool arguments/results and UTC](logs/ci-query-exact.json) also retained.

Mechanical-check chronology: [first final check](logs/final-acceptance-command.txt) exited1 because the Gatekeeper report linked the acceptance file the checker was about to create. No application/test failure. Corrected the helper to permit only that exact future self-reference, create it exclusively after all other gates, then assert its existence. No general broken-link bypass. The fresh reviewed final command is authoritative; failed proof retained.
