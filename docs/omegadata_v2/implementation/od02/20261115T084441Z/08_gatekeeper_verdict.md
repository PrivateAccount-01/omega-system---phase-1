# OD-02 Gatekeeper verdict: BLOCKED

Branch `feature/od01-source-rights`; unchanged HEAD `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.


**Verdict: BLOCKED.** The bounded Windows offline implementation checks pass; the execution contract's complete verification gate cannot honestly be marked OD02_OFFLINE_TECHNICAL_PASS while T25/T26 have blocked dimensions. No known remaining P0/P1 failure was observed within executed OD-02 controls, but unexecuted cases are not removed from the denominator.

| Criterion | Evidence / outcome |
|---|---|
| Prerequisite OD-01R approved technical evidence | Prior OD01R_TECHNICAL_PASS and final QA verified; reviewed code patch matched byte-for-byte before changes |
| T01–T24 offline assertions | All 97 new parameterized cases executed GREEN, final full suite exit 0; synthetic/source-reference limits explicit |
| T25 inherited coverage | 175 prior rights/hardening cases pass; **three file-symlink cases blocked by privilege**, not PASS; real junctions pass |
| T26 regression/static/dependency checks | Windows **383 passed / 3 skipped / 4 deselected**, Ruff/mypy/pip/collection exit 0; **Python 3.11 and Linux attempts exit 1 missing pytest/dependencies** |
| Provider denial / redirects / source authority | Mock negatives show terminal status/body/policy refusal; all redirects rejected; denied source cannot select later candidate/profile/transport |
| Per-hop/address security | Actual provider egress remains **BLOCKED_EXTERNAL_EGRESS**; no connect-time DNS/private-address security certification or sham lookup control |
| Payload correctness | Strict bounded equity era/archive/header/date/numeric validation. No HTML/wrong date/corrupt archive can become structurally validated in tested paths. Generic JSON/sidefeeds remain HTTP_RECEIVED |
| Provenance | Exact raw bytes/SHA, sanitized URL/status/type/transport/policy/attempt/schema/era and offline source mode; cache and seed distinct |
| Preservation / phase safety | [Final QA](logs/final-qa.json) verifies exact scope, original hashes/metadata, default pending policy and branch/main/index identity. No actual source request, payment, publication, release/signing change, warehouse/broker operation or later phase |
| Independent verifier | **SOURCE_REFERENCE_PENDING**, same-model review only. Fixture interpretation is not official authenticity; live/financial certification blocked |

Baseline **286 passed, 3 skipped, 4 deselected**; final **383 passed, 3 skipped, 4 deselected**, delta **97**. Combined statement/branch coverage **80.78%**, acquisition module **92.47%**. One unclosed disposable SQLite ResourceWarning retained. Detailed exact commands/exits, environment, failed red runs, test fixture migration and coverage limits are in [execution evidence](06_evidence_and_coverage.md) and [T01–T26 matrix](03_red_green_test_matrix.md).

All **13 real policies PENDING_REVIEW, 0 APPROVED**. D-01/D-04 P0 and inherited D-02/03/06/08/09 P1 remain open; D-05/D-12 corrected only in the documented tested offline boundary. No production/live/release certification. See [remaining risks](07_remaining_defects.md).

**STOP: OD-02 only.** No commit/push/PR or OD-03/OD-04 work is implied. The one proposed approval is the bounded verification completion in [next request](09_next_phase_request.md); no source enablement or provider smoke is included.
