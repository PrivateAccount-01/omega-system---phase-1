# OD-02 remaining defects and ownership

Branch `feature/od01-source-rights`; unchanged HEAD `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.


No known uncorrected P0/P1 was observed in the **executed bounded Windows OD-02 transport/structural acceptance**. That statement is not closure of blocked verification or inherited financial/release findings. Overall verdict remains BLOCKED. Original [OD-00 defect register](../../../audit/08_prioritized_defects.md) and [OD-01R risk register](../../od01r/20261115T065155Z/05_risks_rollback.md) remain unchanged.

| Finding | Current disposition / owner / acceptance handoff |
|---|---|
| D-01 **P0**, signing custody | **OPEN**, security owner, OD-11/14. No key contents/history/use reviewed or changed. Owner must establish trusted custody/public verification root under separate authorization |
| D-04 **P0**, release export/eligibility/promotion bypass | **OPEN**, release owner, OD-11. No new release/readiness/distribution claim; immutable staged verification and fail-closed promotion still required |
| D-03 **P1**, canonical overwrite/raw atomicity | **OPEN**, storage owner, OD-04/10. One manager's thread lock and retained raw hashes do not solve process/crash-safe immutable archives, canonical Parquet or release pointers |
| D-02 **P1**, universe knowledge-time | **OPEN**, OD-08 (with OD-06/10 identity/version contract). Historical decision/as-known availability not fixed |
| D-08 **P1**, mutable price/action history | **OPEN**, OD-06/07/10. Observation revisions, point-in-time corrections and reproducible adjustment versions deferred |
| D-06 **P1**, rights prior calendar day | **OPEN**, OD-07. Prior exchange-session/staleness policy and independent factors unresolved |
| D-09 **P1**, official fixture provenance | **OPEN**, OD-05/07/09/14 and independent financial/source reviewer. New synthetic fixtures explicitly SOURCE_REFERENCE_PENDING, do not count as official truth |
| D-05 **P1**, HTML payload acceptance | **CORRECTED in tested offline OD-02 scope**: strict equity ZIP/CSV/date/content checks and terminal failure. Source-era official interpretation/actual 2020 cutover remains unverified; unknown formats quarantine, no live certification |
| D-12 **P1**, provider denial retry | **CORRECTED in tested offline call graph**: terminal 401/403/451/429/404 and body denials across request/bootstrap/discovery/profile/candidate/probe; no live-source availability claim |
| D-07 **P1**, rights enforcement | OD-01/01R implemented technical default denial; administrative authority/terms/revision trust remains mandatory human ownership. All 13 actual sources pending, zero approved |
| D-10 **P2**, stale readiness | **OPEN**, OD-11/14. Historical reports not regenerated; green archived booleans are not current certification |
| D-11 **P2**, supply chain/CI/compatibility | **OPEN**, OD-14. No lock/advisory/license clearance or CI runtime matrix claimed. 3.11/Linux missing dependencies; three privileged symlink scenarios blocked |
| OD02-V01 verification blocker | Python 3.11/Linux targeted runs exit 1 before tests (missing pytest/dependency set); Windows file symlinks lack privilege. Completion needs authorized disposable dependency setup and capable runner; no installation authorized here |
| OD02-R01 source-reference/live blocker | Independent source-era/schema/date/financial interpretation pending. Real HTTPX/urllib/curl remains BLOCKED_EXTERNAL_EGRESS until separately authorized constrained address-level transport and rights review |
| OD02-R02 storage/callback limits | Cooperative trusted offline callbacks cannot be preemptively timed out in-process; no hostile-Python sandbox, cross-process atomic publication or descriptor-level symlink-race protection certified. Keep actual egress disabled and candidate/test scope disposable |
| Other inherited operational risks | Warehouse idempotency/CLI credentials and downstream use-scope integration deferred; no actual service/warehouse test, broker, signing or production artifact modification |

No P0/P1 financial/release gate is waived by these tests. OD-03 browsers, OD-04 storage implementation and OD-05+ work were not begun. Future phases need separate scoped authorization; no rollback or cleanup action is implied. Review the OD-02-only patch before any selective rollback; reversing this phase would restore known acquisition defects, so jobs must stay disabled. Never reset/clean/stash or remove historical evidence/data/keys.
