# 03 — Historical evidence and release status

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Historian / financial integrity reviewer; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure

Cataloged 41 top-level JSON reports in the verification directory without running generators; recorded hashes, top-level fields and available timestamps in [artifact catalog](logs/artifact-catalog.json). Forty decoded as UTF-8; the API stress report initially raised a decoding error and was then read successfully as UTF-16. Inspected manifests, recomputed all referenced dataset SHA-256 values, calculated evidence ages, and queried two SQLite DBs through read-only URI/query_only. [Results](logs/read-only-evidence-checks.json) are new audit evidence; original files were preserved.

## Verified findings and corrected prior leads

| Lead / claim | Observed current working tree | Classification |
|---|---|---|
| Old unit log says 101 pass | Historical only; current run has 111 pass, 4 deselected | ARCH vs TEST |
| Prompt says readiness false on May 1 | Current file generated 2026-05-02T08:26:58.747543Z says true; file was already modified at entry | Prior snapshot obsolete; ARCH |
| README says fresh replay and ready true | Historical booleans exist, but November evidence is stale | CLAIM unsupported as current readiness |
| Equity historical 'successful_downloads=1724' | cache_only=true, seed=1703, canonical cache=21, network/live=0 | source_seed_imported / source_cached_raw; no source_acquired_live proof |
| Six successful April pipeline dates | Every ingest_paths array empty; source=canonical_verification_db_state; no errors stored | ARCH derived DB/replay evidence, not live fetch |
| Five NIFTY50 validations | Five snapshots, 70 membership rows loaded; report lists counts, not full transition coverage | ARCH bounded membership evidence |
| Official adjustment corpus | Current 23 cases / 11 transformational; README says 14 / 5 | ARCH counts; independent official authenticity UNVERIFIED |
| Synthetic/manual corpus | 14 cases | SYN math coverage only |
| Portable release paths | Current release references resolve and all hashes match | RUN byte identity, not financial truth |

All **19 dataset references across three release profiles matched** their current manifest checksums. This verifies present byte identity only; manifests themselves are already modified user state. No signature was independently verified in this audit. Stored 'signature verified' and warehouse SYNCED remain ARCH assertions.

## Freshness at 2026-11-14T11:11:19Z

| Evidence | Age hours (approximately) | Relevant limit hours | Current assessment |
|---|---:|---:|---|
| Stored readiness report | 4706.74 | 24 used as audit comparison, not a standalone readiness-report policy | stale historical report |
| Canonical source probe | 4727.53 | 24 | exceeds current policy |
| Pipeline state | 4727.53 | 24 | exceeds current policy |
| Tolerance report | 4727.51 | 168 | exceeds current policy |
| Matching benchmark | 4727.53 | 168 | exceeds current policy |

Limits come from [readiness policy](../../../config/release_readiness_policy.json). This is a read-only freshness assessment, **not a full runtime readiness reevaluation**. Current publication must not be approved from stored ready=true.

## Databases and provenance

[Verification DB](../../../artifacts/verification/pipeline_run_work.sqlite) has 44,219 prices: 14,715 labeled nse_bhavcopy and 29,504 bse_bhavcopy; 70 memberships; 1 confirmed action; 2,066 reviews; 3 release records, each GENERATED/SYNCED. Labels do not establish original acquisition, rights or independent verification. No per-price raw hash / observation history exists in the inspected schema, so full live-vs-seed ancestry cannot be reconstructed from those labels alone.

The root development DB has 2 prices, one nse_bhavcopy and one secondary_source, no confirmed actions or universe rows. Treat it as mixed/unverified development content, not certified real data. Other existing DBs were not opened. No DB was reset, migrated, committed or modified.

## Evidence state taxonomy

- source_acquired_live: no new acquisition executed; historical probe success only ARCH.
- source_cached_raw: canonical cache references in backfill report; sampled hash checks below do not prove legal rights.
- source_seed_imported: 1,703 seed hits explicitly recorded in historical backfill.
- source_unverified: development DB secondary rows and unauthenticated fixture claims.
- parsed_validated: existing test assertions / archived parser claims within their limited semantics.
- official_cross_checked: not independently established by this audit.
- published: release files and GENERATED DB states exist; no new publication or certification.

## Encoding exception and missing evidence metadata

[Archived API stress results](../../../artifacts/verification/api_stress_results.json) are valid UTF-16 JSON, not proven malformed. A separate read observed 500 successful requests and zero failures for each of three localhost endpoints, elapsed_ms about 12910.06. No generated_at, run_id or code_commit is present, so this remains ARCH with unverifiable execution identity/freshness, not a benchmark executed by OD-00. The original catalog decoding error is retained for transparency. [Encoding follow-up](logs/encoding-followup.json) records the resolution.

## Limitations / next action

Code-commit/run-id fields are not uniformly present in old reports; the catalog exposes their absence rather than imputing HEAD. Original official retrieval times, rights, complete row lineage, signature trust and live warehouse state remain unknown. Do not regenerate canonical proofs to make them fresh. An approved later phase must produce independently reproducible evidence in isolated locations.

