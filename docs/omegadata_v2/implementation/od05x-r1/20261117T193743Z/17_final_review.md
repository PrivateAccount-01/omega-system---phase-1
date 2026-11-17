# OD-05X-R1 — BLOCKED, stopped on new audit incident

Branch `feature/od01-source-rights`; reviewed/entry HEAD `e139cd168fb026c77a27bd4b1a87f8a9b180a1ec`. Added [Windows admission/contracts](../../../../../scripts/od05xr1_windows_backend.py), [40 safe/blocked contract cases](../../../../../tests/unit/test_od05xr1_windows_contract.py) and this dossier. Existing Linux/application/test files were not edited. No commit/push/merge/sign/release/OD06.

Windows isolation could not be established: Home edition, Sandbox absent, no approved VM/worker supplied. Only safe validation/refusal code was implemented; a native Windows backend is **not implemented or accepted**. Windows3.14/3.11 CLI refuses with exit2 before input reads/output creation. Static Ruff/mypy/pip/compilation pass; Windows collection/A/diagnostic/native/stress are NOT_RUN. [Final Windows/static lineage](18_final_quality_and_command_reconciliation.json), [capabilities](02_windows_capability_assessment.json).

| Fresh Linux scope | Actual result |
|---|---|
| Collection |848=A840+B4+C4|
| New R1 cases |33passed/7explicit native blocks-skips,exit0|
| Existing X / V / W |33passed /40passed+1skip /39passed,exit0|
| A engineering |828passed/12skipped,exit0|
| Full unchanged non-realdata diagnostic |828passed/4failed/12skipped/C4deselected,**exit1**|
| Ruff/mypy/pip/compilation/new strict adapter type |final exit0|

The12A skips comprise five unchanged Windows-specific nodes and seven new blocked native requirements. No skip is a pass. Full diagnostic fails exactly the four originalB cases; their assertions remain unchanged. C4remain unexecuted. Linux12native denials and positive privateIPC precede canonical stage in each worker; no bootstrap fallback exists. [Exact matrix](11_linux312_regression_execution.json), [inventory](08_exact_regression_inventory.json), [negative-first](06_negative_first_WIN01_WIN20.md), [coverage](12_cross_platform_coverage.json).

**New stop-triggering incident:** final reporting issued an unscoped WSL `git diff --name-only`, which can rehash tracked market files across OS stat differences. It was paused/terminated; finalizer exited1. No payload content appeared in tool output, but available counters are insufficient to exclude original payload reads/hashes. Whole-phase access is **UNKNOWN**, not zero. All further verification stopped. [Incident and containment](14_historical_incident_status.md). This error is not approved or erased by passing tests.

Before that incident, fresh stat observations reconciled3626present/size-matched paths:seed3596/cache30,hardlinks2760/single866; fresh-before/after and historical stat comparisons had no changes. They do not establish raw-byte integrity, permission, authenticity or financial truth. Prior361W/386X dossiers and permitted code identities passed preservation checks before the unsafe Git step. No post-incident original verification ran. Windows INPUT_CHANGED remains UNKNOWN and original WSL performance remains separately blocked.

**G1:** scoped Linux tests pass before incident. **G2:** Windows execution BLOCKED. **G3:** global containment BLOCKED, including new controller incident. **G4:** BLOCKED_REAL_DATA; independently verified financial rows0. Overall safe engineering **BLOCKED**. Historical OD05V and new R1 incidents remain pending human owner review. [Machine Gatekeeper](16_gatekeeper.json).

**One immediate next owner action:** review and disposition the new R1 Git-audit incident before resuming this phase. A separately approved isolated Windows VM/worker remains necessary for eventual engineering closure. No source-permission loop, paid service or later phase is requested.

STOP after OD-05X-R1. No commit or push.
