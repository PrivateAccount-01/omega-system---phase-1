# OD-01 design gate — bounded implementation
Prepared before production edits, 2026-11-14 UTC. Baseline HEAD d4b5a58f0c50dc348e0d4e1150a725cc6fab5674; local branch feature/od01-source-rights. Explicit user OD-01 authorization supersedes OD-00 default. No source approval is inferred.

## Evidence and instruction reconciliation
The OD-01 prompt was read completely. Root OMEGADATA_AGENTS.md was reread; no actual AGENTS.md found. Master was read completely during OD-00; git diff against f43ecec verifies the current master and instructions are byte-identical to that version. Its actual path is docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md; root instructions' shorter path remains stale. All nine OD-00 audit reports and relevant plans/ADR/open decisions were reviewed. d4b5a58 warehouse/CLI changes are preserved; no new changes overlap authorized files. Preflight logs record actual interpreter, branch, HEAD and disjoint untracked files. No signing contents inspected: preservation uses metadata only for the GnuPG directory.

## Current call graph
Pipeline.run_track_a → IngestionOrchestrator.ingest_raw_source → DownloadManager.download → canonical/seed _load_cached_artifact → return; on miss → _candidate_urls → optional BSE/NSE-FO discovery (network!) → profiles/candidates → _fetch_candidate → NSE session bootstrap → _request_with_workarounds → httpx retry / urllib / curl → validate → raw/manifest/latest writes.
DownloadManager.probe_source_candidates → same discovery/candidate/fetch paths.
DownloadManager.fetch_bse_stockreach_graph → BSE URLs + _request directly; this helper has no dedicated registered source key.
scripts/generate_source_probe_report._probe_entry → _curl_probe → bootstrap and target subprocess, independently of DownloadManager.
Other manual probe scripts are independent developer tools, not DownloadManager-managed acquisition APIs; remain out of scope and must not be executed.

## New call graph / contract
Default local file → immutable Pydantic SourcePolicyRegister → latest recorded revision per known source → deterministic UTC decision → SourcePolicyError on refusal. No dev/test bypass; explicit dependency injection only for synthetic tests. No new libraries, services, DB tables or migrations.

download(use_cache=True) checks READ_CACHED before calling cache helpers; canonical/seed helpers independently check CACHE/SEED_CACHE before filesystem inspection or payload reading. Cache-only permission can serve valid cache; miss requires FETCH plus STORE_RAW before discovery. Explicit use_cache=False permits fetch-only callers without reading cache. A local cache read has no requested remote host; this is explicit local-transport scope, not inferred permission to fetch. Cache bytes/checksum behavior stays unchanged. Returned artifacts carry decision records; old manifest bytes are not rewritten.

Every network boundary checks FETCH/transport/exact normalized host. A per-manager ContextVar source scope supplies source identity to private transports without global mutable flags; direct low-level calls without scope refuse UNKNOWN_SOURCE. Bootstrap/discovery and every selected fallback are checked. SourcePolicyError rethrows before broad catches and suppression; HTTP 403/429 behavior is unchanged for OD-02. Actual automatic redirect-chain enforcement is explicitly deferred to OD-02; only requested/discovered hosts are preflight-checked here. No live access is authorized even if an approved record were later provisioned.

StockReachGraph is blocked as UNKNOWN_SOURCE until it has its own approved registry identity; it must not borrow BSE corporate-action rights. Acquisition decisions are returned/persisted with policy ID, revision and full revision hash. No terms document or credentials appear in records.

## Schema / immutable revisions
source-policy/v1, tuple records, frozen models, extra fields forbidden, strict string/integer/hash/UTC validation. IDs stable per source; revisions strictly increasing, append-linked using previous revision hash; duplicate source+revision or duplicate JSON keys refuse. Full canonical SHA-256 verifies each record. Latest revision wins even for an earlier requested decision timestamp; an administrative revocation must not be bypassed by backdating requests. Old decisions retain their old revision/hash. File/provider refreshed at every operation boundary; no permissive stale cache.

APPROVED missing evidence yields EVIDENCE_INCOMPLETE, not malformed success; pending/denied/revoked/expired have explicit reasons. Intervals use [valid_from, valid_until); approved_at, terms retrieval and creation cannot be future evidence. No indefinite approval in v1 (valid_until mandatory). Optional consumer purpose must itself be permitted; research does not imply trade use. Metadata rate/retention/geography/cost is explicit unknown by default and not an implemented lifecycle engine. Human administrative evidence review remains external; a checksum/string alone cannot prove approval authority.

## Exact edit budget
New source_rights.py + pending JSON register + test_od01_source_rights.py; download_manager.py guard/injection/decision fields only; narrow existing downloader tests receive explicit synthetic provider injection. Technical SOURCE_REGISTRY and Settings stay unchanged if no linkage edit needed.
Two additional essential callers: sequential_pipeline.py adds a typed terminal-refusal rethrow before optional-source catch; scripts/generate_source_probe_report.py checks policy before its independent curl path. No warehouse, release, math, calendar, dependency, CI, signing, artifacts or data edits. New evidence/documents are under this run directory plus decisions/od01-source-policy-reuse.md.
These two caller edits prevent hidden policy refusal and probe bypass; they do not change provider denial/retry/payload logic.

## Design adversarial review (same model)
Check cache/read bypass, cache miss escalation, direct private transport access, bootstrap hosts, changing provider at boundary, revoked revision selection, future/naive dates, duplicate keys/revisions, invalid hashes/unknown fields, source-key attribution, thread isolation, zero side effects on refusal and no broad catch swallowing. Tests use fake endpoints and fake approval clearly labeled SYNTHETIC_TEST_ONLY. No real-data integration test is weakened. Negative-first test must fail before code edits.

## Verification / rollback
Use checked-in run-specific verification_runner.py with explicit repo interpreter, socket/subprocess guards and disposable DB/output settings. Correct initial harness import failures without changing app tests; retain errors. Baseline, targeted T01–T18, full offline pytest, ruff, mypy, pip and coverage (installed) must execute. Compare preservation snapshot, excluding only approved implementation paths. No rollback command executed: later revert only this bounded patch, retaining evidence; do not restore permissive acquisition in a certified release. OD-02 and release certification remain blocked.

