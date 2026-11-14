# 04 — Source rights and acquisition unknowns

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Source policy owner / Reviewer; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure and registry evidence

Inspected [DataSource fields](../../../src/omegadata/track_a/source_registry.py#L21), [download entry](../../../src/omegadata/track_a/download_manager.py#L863), transport/error handling and existing probe artifacts. No source was contacted. The registry defines URL/era/format/rate/retry/checksum/partition fields, but no approved/pending_review/denied permission state or mandatory rights-policy version. Download checks registry membership and cache, not human authorization.

| Registry key | Stated source / route | Rights status in this audit | Required owner experiment |
|---|---|---|---|
| NSE_EQUITY_BHAVCOPY | NSE archives, legacy/revised CSV ZIP | pending_review / UNK | Data-rights owner verifies automated commercial research, retention and derived/export rights by era |
| BSE_EQUITY_BHAVCOPY | BSE CSV and ZIP fallbacks | pending_review / UNK | Same; assess each supported fallback |
| NSE_CORPORATE_ACTIONS | NSE API/announcements | pending_review / UNK | Preserve announcement/circular source and publication evidence |
| BSE_CORPORATE_ACTIONS | BSE API | pending_review / UNK | Check payload semantics and use permissions |
| NSE_FO_BHAVCOPY | NSE legacy/UDiFF archives | pending_review / UNK; OD-16 expansion deferred | Separate derivatives contract and license |
| NSE_FII_DII | NSE activity API | pending_review / UNK | Separate feed register |
| INDIA_VIX | NSE allIndices | pending_review / UNK | Snapshot versus historical-date semantics |
| GDELT | HTTP lastupdate pointer | pending_review / UNK | Original publishers' article/text rights and pointer integrity |
| RBI_DBIE | RBI listings/download route | pending_review / UNK | Dataset-specific permission and revision semantics |
| MOSPI | Ministry dataset listing | pending_review / UNK | Dataset-specific terms |
| AMFI_MONTHLY_PORTFOLIOS | AMFI portfolio disclosure listing | pending_review / UNK | Underlying fund documents and permitted downstream use |
| NSE_BULK_BLOCK_DEALS | NSE disclosure API | pending_review / UNK | Separate delayed-publication evidence |
| INSIDER_TRADES | NSE/BSE disclosure APIs | pending_review / UNK | Separate legal entities/endpoints and timestamp policy |

These statuses are audit classifications, not changes to the runtime registry. No human approval evidence was established for any row. Public reachability and successful old probes do not settle commercial/redistribution rights.

## Required OD-01 register

For each source: legal entity; exact source/terms URL and retrieved-at/hash; approved use case; raw/derived permissions; rate/access/authentication/robots rules; cost; retention/geography/attribution; redistribution and downstream consumers; approval owner/date/evidence; revocation procedure; policy version; approved/pending_review/denied. Unknown fields stay unknown and block automated acquisition.

## Acquisition findings

1. Cache hash revalidation already exists at [cache loader](../../../src/omegadata/track_a/download_manager.py#L93). Keep it.
2. NSE equity payload validation accepts a nonempty HTML denial page: [experiment](logs/disposable-integrity-experiments.txt). Empty checks and specialized BSE/FO checks do not cover the NSE equity ZIP/date/schema contract.
3. Inner request handling raises on 403/429, and NSE transport workaround refuses those statuses. However, the outer download loop catches all exceptions and continues through candidate/header profiles ([loop](../../../src/omegadata/track_a/download_manager.py#L883)). Source-wide denial stop requires an explicit terminal category. No bypass was attempted.
4. Raw file/manifest/latest writes are direct, not atomic; existing names use a truncated checksum. Concurrency/collision/disk failure are unverified.
5. Redirected/discovered URLs and ZIP expansion need a bounded host/resource policy; no live SSRF or archive stress test ran.

## Limitations / next action

Owner: user-appointed source-rights steward, with legal/compliance review outside agent authority. Experiment: collect approved policy documents, freeze a narrowly authorized cash-equity source corpus, test denied/pending/revoked states with mocked HTTP. Blocking condition: no automated external source access or redistribution until that source is approved. OD-01 may implement offline policy enforcement only after explicit phase approval; no credentials or paid subscription is requested here.

