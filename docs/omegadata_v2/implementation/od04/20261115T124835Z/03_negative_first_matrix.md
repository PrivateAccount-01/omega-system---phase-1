# OD04 A01–A28 acceptance and negative-first ledger

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

**Process conformance BLOCKED.** Four real baseline assertion failures ran before
production edits. Many new unit contracts were authored before the core module,
but the complete A01–A28 tranche (notably separate process experiments and later
adversarial cases) was not authored/executed before implementation as Gate 2
required. That chronology cannot be retroactively called compliant. Missing API /
import errors are NOT used as old-code defect proof. Every final row below has
executed green evidence, but technical green does not waive that process gate.

Pre-change [red-old-storage](logs/red-old-storage.json)/[raw](logs/red-old-storage.txt):
exit 1, four assertion failures. Later new-implementation red cases:
[mode relabel](logs/red-mode-relabel.txt), [policy identity](logs/red-policy-identity.txt),
[false structural state](logs/red-structural-state.txt): each exit 1 before its
correction; each final assertion passes. First core green 40 pass/4 genuine Windows
symlink skips; new directory-link tests then use actual Windows junctions paired
with actual Linux symlinks, not a skipped test labeled pass. No inherited test edited.

| Acceptance | Executed node / experiment | Final technical outcome |
|---|---|---|
| A01: exact full digest and original bytes | `test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay`; `test_a01_a02_a06_a12_negative_first_old_storage[existing_corruption]`; `test_a01_a02_a06_a12_negative_first_old_storage[full_hash]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A02: dedup bytes, retain distinct observations | `test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay`; `test_a01_a02_a06_a12_negative_first_old_storage[existing_corruption]`; `test_a01_a02_a06_a12_negative_first_old_storage[full_hash]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A03: same-day different versions | `test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A04: idempotence includes payload/request/policy identity | `test_a04_a05_idempotence_conflict_and_frozen_models`; `test_a04_policy_identity_change_is_not_idempotent`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A05: conflicting operation reuse | `test_a04_a05_idempotence_conflict_and_frozen_models`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A06: marker-last visibility | `test_a01_a02_a06_a12_negative_first_old_storage[existing_corruption]`; `test_a01_a02_a06_a12_negative_first_old_storage[full_hash]`; `test_a01_a02_a06_a12_negative_first_old_storage[partial_failure]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A07: five injected and forced-termination boundaries | `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_object]`; `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_observation]`; `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_stage]`; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A08: read-only inventory/retry after interrupted states | `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_object]`; `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_observation]`; `test_a06_a07_a08_fault_boundaries_recover_without_promoting[after_stage]`; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A09: twelve thread writers | `test_a09_a21_thread_writers_and_reader`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A10: independent same-hash processes | separate guarded process experiments; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A11: independent different-hash processes | separate guarded process experiments; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A12: full bytes/length/link checks and deterministic corruption scan | `test_a01_a02_a06_a12_negative_first_old_storage[existing_corruption]`; `test_a01_a02_a06_a12_negative_first_old_storage[full_hash]`; `test_a01_a02_a06_a12_negative_first_old_storage[partial_failure]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A13: traversal/hash/drive/UNC and real directory-link confinement | `test_a13_a15_a24_invalid_identity_before_storage[attempts--1]`; `test_a13_a15_a24_invalid_identity_before_storage[observed_at-2026-01-01T00:00:00]`; `test_a13_a15_a24_invalid_identity_before_storage[operation_id-../escape]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A14: duplicate/invalid JSON and version refusal | `test_a12_a14_corruption_refuses[commit]`; `test_a12_a14_corruption_refuses[duplicate]`; `test_a12_a14_corruption_refuses[length]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A15: mode and synthetic-origin non-escalation | `test_a13_a15_a24_invalid_identity_before_storage[attempts--1]`; `test_a13_a15_a24_invalid_identity_before_storage[observed_at-2026-01-01T00:00:00]`; `test_a13_a15_a24_invalid_identity_before_storage[operation_id-../escape]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A16: pending/missing/revoked/scope and commit-time policy refresh | `test_a16_explicit_revoked_or_missing_before_io[MISSING]`; `test_a16_explicit_revoked_or_missing_before_io[REVOKED]`; `test_a16_pending_before_write_or_read`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A17: cache-only no fetch / legacy read-only | `test_a17_a18_optin_cache_miss_no_effect`; `test_a17_legacy_facade_is_read_only`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A18: legacy dry-run and all-original preservation | `test_a17_a18_optin_cache_miss_no_effect`; `test_a18_dry_run_migration_and_cli_verifier`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A19: empty/oversize/metadata/entry/total budgets | `test_a19_metadata_and_entry_budget`; `test_a19_payload_and_total_budget[0]`; `test_a19_payload_and_total_budget[17]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A20: typed fsync/link ENOSPC/EACCES/EIO injection | `test_a20_storage_faults_typed_no_success[13-fsync]`; `test_a20_storage_faults_typed_no_success[13-link]`; `test_a20_storage_faults_typed_no_success[28-fsync]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A21: readers during paused publication and independent processes | `test_a09_a21_thread_writers_and_reader`; `test_a21_reader_during_publication`; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A22: URL redaction in observation/structured refusal | `test_a22_url_confidentiality_and_a24_policy`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A23: pinned replay and sorted read-only scan | `test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay`; `test_a12_a23_scan_is_read_only_deterministic_and_refuses_corruption`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A24: actual parser validation, exact era/date/schema/rights references, null published_at | `test_a13_a15_a24_invalid_identity_before_storage[attempts--1]`; `test_a13_a15_a24_invalid_identity_before_storage[observed_at-2026-01-01T00:00:00]`; `test_a13_a15_a24_invalid_identity_before_storage[operation_id-../escape]`; [commands](logs/win314-accepted-targeted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A25: Windows and native Linux filesystem execution | `test_a13_strict_object_contract[sha256-aaaaaaaaaaaa]`; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |
| A26: unchanged inherited/full offline suites | runtime matrix / preservation; [commands](logs/win314-accepted-full.json) | PASS technical; Gate 2 chronology BLOCKED |
| A27: imports/collection, Ruff, strict mypy49 and pip consistency | runtime matrix / preservation; [commands](logs/win314-accepted-collection.json) | PASS technical; Gate 2 chronology BLOCKED |
| A28: measured 4KiB/64KiB/1MiB costs, disk and recovery | separate guarded process experiments; [commands](logs/win-process-accepted.json) | PASS technical; Gate 2 chronology BLOCKED |

[Complete machine matrix](logs/acceptance-matrix.json) includes full nodes, exact argv/cwd/OS/interpreter/UTC/actual exits and tested source hashes, plus raw output references. No claim that all A01–A28 failed on unchanged code. Actual step order is retained.
