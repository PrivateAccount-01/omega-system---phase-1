# Existing code audit

[Exact paths, hashes, functions](support/legacy-source-audit-final.json) were read as code only. No operational validator, calibration, raw backfill or alert was invoked.

| Component | Decision | Limitation and opt-in treatment |
|---|---|---|
| CrossSourceValidator | OPT_IN_REPLACEMENT | ISIN/date matching, dictionary overwrite and missing skips lack exact venue/field identity; bounded candidate groups expose duplicates/missing rows. |
| Confidence | WRAP | Legacy numerical score retained; strict eligibility preserves independent hard blocks. |
| Tolerance loader | REUSE / LEGACY_RISK_RETAINED | Mutable/hardcoded thresholds are not authentic calibration; immutable policy pins scope and knowledge. |
| ManualReviewService / review policy | OPT_IN_REPLACEMENT | Legacy mutable queue/alerts retained for callers; new append-only ledger performs no dispatch. |
| CorporateActionMatcher / discontinuity | WRAP | Similarity/price jumps do not establish economic event truth; strict explanation replays exact OD07 proof. |
| Domain/ORM | REUSE | Original tables/rows unchanged; disposable additive SQLAlchemy schema uses upstream transaction/codec conventions. |
| Source calibration scripts | BLOCKED_EXTERNAL | Code inspected, actual data/calibration not executed. |

All original APIs, test identities and financial expectations retained. Full A includes existing cross-source, confidence, manual-review, tolerance, corporate-action, identity/calendar, parser and universe regressions.
