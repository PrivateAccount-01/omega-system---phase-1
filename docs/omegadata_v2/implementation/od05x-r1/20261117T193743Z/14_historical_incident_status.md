# Historical and current incident dispositions

Historical OD05V39files/6,135,515recorded bytes remain PENDING_HUMAN_OWNER_REVIEW, never self-approved. Existing ledger/evidence was preserved. No deliberate incident-copy read/hash/copy/delete occurred.

**New R1 incident:** reporting finalizer invoked `git diff --name-only` across the original working tree under WSL. Tracked market files exist; cross-platform stat differences can cause Git to read/hash payloads. Git PID503 was paused with SIGSTOP and then killed with SIGKILL; finalizer exited1. Native counters/maps/FD metadata were captured while paused. Counters are not a complete lifetime syscall trace and cannot prove zero payload access. No payload content was returned to the tools, but actual payload read/hash extent is UNKNOWN. Do not infer no access from missing output or current mappings. [Incident record](logs/finalization-git-safety-incident.json), [termination](18_final_quality_and_command_reconciliation.json).

All further tests/source verification stopped. Only existing-log reporting and evidence sealing followed. No original/retained data was deleted, rehashed or copied for investigation. Both incident dispositions require human review; no retrospective approval was generated.
