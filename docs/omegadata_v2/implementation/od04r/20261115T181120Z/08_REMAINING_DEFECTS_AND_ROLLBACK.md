# Remaining limitations and rollback

OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.


| Severity | Remaining status |
|---|---|
| P1 process acceptance | Full historical A01â€“A28 negative-first ordering not met; human exception NO, never repaired retroactively |
| Current scoped archive | Reproduced R01/traversal suppression fixed; no uncorrected high-severity defect observed within executed trusted-local boundary |
| P2 compatibility | Scan v2 changes empty/missing success into refusal; existing consumers must handle v2 and explicit independently pinned expected_count; on-disk formats unchanged |
| P2 operation bounds | Retained staging consumes bounded quota; no GC approved. Count-match does not authenticate provenance or ensure external historical completeness |
| P2 warnings | Existing disposable SQLite cleanup ResourceWarnings retained; no production DB touched |
| UNK | Hostile concurrent owner swap, hardware power-loss,NFS,Windows directory fsync, independent physical host/CI, official source truth, comprehensive advisory clearance |
| Inherited P0/P1 | Signing/release-export blockers, fixed analytical Parquet overwrite/current-state knowledge and financial-reference gaps remain outside scope |

Rollback plan only, not executed: freeze/review [patch](logs/application.patch) and [hash ledger](logs/reviewed-before-after-file-ledger.json); pause strict-scan consumers. After explicit owner approval, restore only two application files from reviewed44090a... with current-hash checks and no overwrite of intervening user edits. Keep all new tests/evidence as audit history. Reverting reintroduces vacuous verification, so empty/missing scans must remain administratively blocked if rollback is chosen. No reset/clean, history rewrite, data deletion, stage promotion, GC, migration or policy rollback. Disable optional archive injection for approved legacy facade if needed; retain every raw object/observation/marker and historical release. No rollback performed.

[Preservation](logs/reviewed-preservation-comparison.json) compares12,137 originals; only authorized two application paths differ. Old tests/evidence/data/DBs/releases/config unchanged, signing metadata only unchanged. Local changes remain unstaged/uncommitted; commit/push requires a separate instruction. No source enablement, signing, publication, merge or later phase.
