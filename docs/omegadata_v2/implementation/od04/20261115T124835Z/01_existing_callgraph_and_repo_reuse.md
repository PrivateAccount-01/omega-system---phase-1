# Existing call graph and reuse

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

DownloadManager.download validates request options -> per-job bounded budget ->
_download_in_job -> READ_CACHED with consumer purpose -> raw/seed confined legacy
manifest parser, identity/length/checksum/structural checks. Cache-only miss raises
CACHE_MISS before candidates or storage. Uncached paths authorize FETCH/STORE_RAW,
render era and candidates -> per-profile _fetch_candidate -> bounded transport
and existing _validate_payload -> typed terminal denial escapes all fallbacks ->
fresh FETCH/STORE_RAW authorization -> old per-manager RLock -> storage boundary.

Legacy boundary uses date+12 hash prefix, conditional raw/manifest writes and
direct latest write. Four pre-change executable failures establish truncated
identity, collapsed events, existing corruption reuse and partial payload after
manifest failure. Existing default legacy path is retained, not certified immutable.

New constructor raw_archive opts into service put only AFTER valid candidate and
fresh rights checks; early return prevents legacy directory/pointer writes. Artifact
adds optional observation_id/commit_id/archive_state; prior fields retained. Explicit
operation_id/observed_at support retries; ordinary new acquisition gets new ID/time.
Archive fresh observations are SYNTHETIC_TEST_ONLY because actual egress is disabled.
Current cache return is unchanged except LEGACY_UNVERIFIED flag in opt-in mode;
cache/seed source_mode stays distinguishable. No implicit import/latest inference.

IngestionOrchestrator.ingest_raw_source -> its manager.download -> artifact.path;
public default remains compatible, orchestrator unchanged. ParquetStorage.store_daily
still writes fixed part-00000.parquet: D03 canonical analytical storage remains OD10.
No financial computation, ORM or release service changes.

[Repository selection](../../../decisions/od04-raw-archive-reuse.md): EXTEND_EXISTING,
stdlib filesystem/hash/JSON and existing Pydantic/OD02 validator/OD01 policy APIs.
DVC/lakeFS/delta-rs/DuckDB compared for fit/footprint/rollback; exact primary-source
tag licenses checked, runtime/advisory details unknown, external benchmarks
UNMEASURED and external tests NOT_RUN. No fetched library/code or new dependency.
Two local publish protocols exercised; selected exclusive hardlink with kernel
writer lock and final marker. No claim that rename alone is a transaction.
