# Negative-first chronology and acceptance limits

[Freeze](logs/negative-first-freeze.json): SHA `b5628964d0ff67c54b7ad33c9ca6578b9ca2e740865c40f3f19efcb5896f3d77`, before adapter existed. [Red](logs/r1-d1884b5d2a-command.json):32failed/1passed/7skipped,exit1. Missing API is NEW_FEATURE_ABSENT. No native Windows attack was issued. WIN17 already passed an old contract. [Final](logs/r1-afb1e01c18-command.json):33passed/7blocked-skipped,exit0 in Linux OS boundary. Every command has exact source hashes/runtime/UTC. One equivalent C408 dict-literal style edit changed test SHA after red; [old/new pins](logs/test-source-style-correction.json) preserve that distinction. Assertions and case counts were unchanged.

| Group | Actual initial condition | Final limited result |
|---|---|---|
| WIN01 | NEW_FEATURE_ABSENT | PASS_SAFE_CONTRACT_ONLY |
| WIN02 | NEW_FEATURE_ABSENT | PASS_SAFE_CONTRACT_ONLY |
| WIN03 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN04 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN05 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN06 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN07 | NEW_FEATURE_ABSENT | PASS_SAFE_CONTRACT_ONLY |
| WIN08 | NEW_FEATURE_ABSENT | PASS_SAFE_CONTRACT_ONLY |
| WIN09 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN10 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN11 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN12 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN13 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN14 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN15 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN16 | NEW_FEATURE_ABSENT | PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED |
| WIN17 | PASS_EXISTING_CONTRACT | PASS_SAFE_CONTRACT_ONLY |
| WIN18 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |
| WIN19 | NEW_FEATURE_ABSENT | PASS_SAFE_CONTRACT_ONLY |
| WIN20 | OS_CAPABILITY_BLOCKED | BLOCKED_NATIVE_NOT_RUN |

WIN09/10/12/13 compare provided identity values, not actual native Windows handles/races. WIN11 tests lexical rules on Linux. WIN16 has actual Linux collection only. Windows native/provenance acceptance is blocked. The40test cases do not mean20completed Windows groups. Ruff C408, wrapper I001 and strict adapter type error were recorded before correction; final quality checks pass. [Quality lineage](18_final_quality_and_command_reconciliation.json). A later Git-audit incident blocks global engineering regardless of these test results.
