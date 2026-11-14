# OD-01 risks, boundaries and rollback

Repository: PrivateAccount-01/omega-system---phase-1. Phase: OD-01 IMPLEMENT_OD01_ONLY.
Branch: feature/od01-source-rights. HEAD before/after: d4b5a58f0c50dc348e0d4e1150a725cc6fab5674 (no commit).
Evidence collected 2026-11-14 UTC; exact command times/exit codes in [logs](logs/). Run directory name was allocated at 13:33:40Z; approval/environment delays mean later commands ran through 15:09Z and document checks later. Owner: same-model procedural engineering reviewer, not a human rights approver.

## Current engineering boundary

Source-rights technical enforcement (D-07's missing precondition) is addressed for DownloadManager-managed APIs, the pipeline caller's terminal policy handling and the canonical standalone source-probe curl path. Default sources are all pending, so real acquisition/cache use is blocked. This is not permission to execute live probes or obtain market data. Existing manual standalone developer probes outside those paths were neither executed nor given publication authority; a universal repository egress sandbox is not implemented.

## Carry-forward findings

| Finding | Still unresolved / required authority |
|---|---|
| D-01 P0 signing custody | Tracked private-key path exposure/trust remains unresolved. No contents read, copied, exported, rotated or removed; only filename/size/mtime checks. Human security remediation separately authorized |
| D-04 P0 release promotion/export | No release-manager, publication or signing change. No new release built/published or old ready:true treated as current certification |
| D-05 P1 payload correctness | NSE HTML/ZIP/date/schema acceptance unchanged. No claim financial payload validation is fixed |
| D-12 P1 provider denial | Policy refusal is terminal now, but actual HTTP 403/429 nested retry/fallback semantics are unchanged for OD-02 |
| D-02/D-08 P1 temporal history | Universe availability/current rows/adjustment revisions unchanged |
| D-03 P1 Parquet/archive | No atomic storage, immutable canonical snapshot or concurrency crash fix |
| D-06 P1 adjustment math | Calendar-day rights gap and price-return/total-return conventions unchanged |
| D-09 P1 official fixtures | No source authenticity or fixture relabeling; no official documents fetched |
| D-10/D-11 P2 stale proof / supply chain | Old reports unchanged; no dependency/CI/current advisory work |
| Existing warehouse/CLI | d4b5a58 SQL insert idempotency and --clickhouse-password process-listing exposure remain separate risks; files unchanged |

## New contract limitations and mitigations

- Human permission evidence is an administrative trust boundary. Required fields and canonical hashes detect malformed/inconsistent records, not forged authority or an administrator rolling the whole register back. No active source is approved. Appoint an independent source-rights steward and retain trusted policy revision history externally before real use.
- Requested/discovered/bootstrap/fallback hosts are checked, but automatic redirect-chain and DNS/SSRF enforcement is deferred by the OD-01 contract to OD-02. No provider network is authorized in this run. Do not interpret the evaluator as a complete transport security sandbox.
- READ_CACHED local transport has no remote requested_host; it authorizes cached source use only. It does not authenticate original cache provenance or allow a new fetch. Existing checksum validation remains.
- DERIVE/RESEARCH/TRADE_DECISION_USE/REDISTRIBUTE/COMMERCIAL_PRODUCT are independent evaluator scopes. Complete downstream API/release usage integration is future OD-11/12; current consumers are not newly certified by this feature.
- Rate/retention/attribution/geography/credentials/cost are explicitly unknown in pending records; lifecycle/cost/geographic engines are deferred. Human reviewers must resolve relevant limits rather than silently treat null as unlimited legal permission.
- Direct Python monkeypatch/model construction by trusted application code is not a sandbox adversary. Production has no dev/test bypass; synthetic providers are explicit test injection. Models/registers are frozen validated snapshots; operation boundaries refresh the provider, not mid-syscall transactional policy snapshots.
- StockReachGraph lacks a dedicated registry source and now refuses UNKNOWN_SOURCE; intentional conservative compatibility break. It must not inherit unrelated BSE rights.
- Source-policy file access and repeated model/hash validation cost are unbenchmarked. No latency/performance claim. Tests run on Windows/Python 3.14.3 only; 3.11/Linux runtime validation remains unexecuted.
- Coverage-enabled full suite emitted disposable SQLite ResourceWarnings in existing tests; logs retain them. No actual service health or financial reference proof inferred.

## Preservation and rollback procedure (not executed)

[Preservation comparison](logs/preservation-after.json) checks 11,411 original file records including source payloads, artifacts/root DBs and metadata-only GnuPG records. Only six authorized original files differ. Final QA must reject any artifact/data/signing/OD-00-file difference. No package, CI, release, warehouse, math or calendar changes are authorized.

If this uncommitted local patch is rejected: first save/review the scoped [change ledger](implementation-diff.md) and current status. Reverse only the six identified existing-file hunks and remove only newly created policy/module/test files after owner review, preserving all new evidence and the user's OD-01 prompt. Do not reset/clean/stash, overwrite user work, delete existing raw data, touch signing state, restore old artifacts or rewrite old manifests. No rollback command or DB migration is part of this run. Reverting a fail-closed precondition must not silently authorize acquisition or certification.

For a deployed future policy change, append a new restrictive revision rather than mutating or deleting old approval/decision records. For the current phase, **overall release certification remains BLOCKED** irrespective of technical test success. Security remediation and source-specific human rights approval require separate authorization.

