# Observed lineage and unresolved historical format

The [remote Phase-2 Git tree metadata](logs/phase2-git-lineage.json) was obtained through the GitHub connector; the tree was not truncated. Two original names were compared against Phase-1 `git ls-tree HEAD` metadata, without fetching remote market blobs:

| Date | Phase-2 original name | Matching committed Git blob ID |
|---|---|---|
| 2011-06-22 | cm22JUN2011bhav.csv.zip | ce354dcab7abdacb66210bf854194a2e10916bc7 |
| 2020-01-02 | cm02JAN2020bhav.csv.zip | a06166765f3d6c904a262cc2df655d743cc99f6c |

This establishes matching committed-object metadata across user repositories. It does not authenticate issuer origin, current worktree bytes, publication time or permissions. The current July 23 Phase-1 blob ID was recorded; no nominated Phase-2 July comparison was inferred. The separate initial setup helper did read/hash/copy some market files; that deviation is documented in [the chronology](00_scope_reuse_and_chronology.md), not credited as lawful lineage validation.

[Phase-2 ingestor code review](logs/phase2-ingestor-review.json) confirmed its historical EQUITIES URL constructor and first-member/EQ-only parsing. It was consulted, not run, imported or adopted. Its daily indices fallback is not proof of CM source equivalence. Existing Phase-1 safety primitives are reused instead.

The pinned 2020-01-02 manifest claims legacy-style `cm02JAN2020bhav.csv.zip`. [Source registry](../../../../../src/omegadata/track_a/source_registry.py) selects its modern pattern from January 1, 2020, and [acquisition](../../../../../src/omegadata/track_a/acquisition.py) uses `requested.year < 2020` for legacy validation. The new report marks **ERA_CONFLICT_2020_REFERENCE_PENDING**. A filename claim does not prove its inner schema, so neither a universal 2024 switch nor an automatic route correction was made. Conditional proof remains: permitted original header/member review against an authenticated applicable specification, then an independent row reference before any parser comparison.

The [previous public-document ledger](../../od05u2/20261116T125239Z/documentation-reference-ledger.json) distinguishes December 2023 documentation, May 22, 2024 NSE/MSD/62142 Annexure C, indexed June 12 circular 62424 and the July 8 old-report discontinuation. May/June publication, interface generation and packaging, June 24 amendments, public delivery availability and actual trade dates are separate facts. The original May bundle hash is recorded; the June amendment chain is incomplete. The current 2026 workbook is not retrospectively applied. [NSE reports](https://www.nseindia.in/all-reports/) identify the July 8 public product transition, without authenticating local files. No new exchange market request, schema-era certification or production routing change occurred.
