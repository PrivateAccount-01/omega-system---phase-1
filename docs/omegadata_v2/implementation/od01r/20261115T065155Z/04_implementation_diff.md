# OD-01R bounded implementation ledger

Baseline feature HEAD 3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc, retained throughout. All changes are reversible, unstaged and uncommitted. No PR/push/merge. Exact tracked hunks are captured in [implementation.patch](logs/implementation.patch); new files are directly reviewable. Tests and required documents were authored as new files, without modifying original expectations or evidence.

| Exact file | Change / reason |
|---|---|
| [source_rights.py](../../../../../src/omegadata/track_a/source_rights.py) | Add stdlib policy_url_host preflight: canonical HTTPS/443 DNS authority only, typed downstream refusal on ambiguity. Retain schema, records, hashes, evaluator and default provider |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | Use shared URL preflight; confine pointer/payload/sidecar paths before opens; validate object/identity/length/digest/date; reject malformed cache as miss; refresh BSE policy before GET |
| [orchestration.py](../../../../../src/omegadata/track_a/orchestration.py) | Defer ParquetStorage using cached_property; no unrelated mkdir before pending raw-source refusal |
| [generate_source_probe_report.py](../../../../../scripts/generate_source_probe_report.py) | Shared preflight for _probe_entry and all curl/bootstrap URLs; refresh before each subprocess; keep typed refusal terminal |
| [load_nse_fo_into_pipeline_db.py](../../../../../scripts/load_nse_fo_into_pipeline_db.py) | Initial FETCH/STORE_RAW before DB/network/output, refresh GET and storage boundaries, add exact policy decisions to newly created manifests |
| [backfill_nse_equity_history.py](../../../../../scripts/backfill_nse_equity_history.py) | Import/rethrow SourcePolicyError before generic exception handler so missing rights is terminal |
| [probe_endpoints.py](../../../../../scripts/probe_endpoints.py) | Disable both legacy callable diagnostics before clients/bootstrap; retain old implementation for review |
| [probe_bse_urls.py](../../../../../scripts/probe_bse_urls.py) | Disable legacy main entry before direct client |
| [generate_source_probe_matrix.py](../../../../../scripts/generate_source_probe_matrix.py) | Disable main and _run before canonical evidence reads, children or output; no permissive flag |
| [OMEGADATA_AGENTS.md](../../../../../OMEGADATA_AGENTS.md) | Correct only introductory filename/master pointer; retain all operating rules |
| [AGENTS.md](../../../../../AGENTS.md), new | Canonical automatic-discovery facade pointing to retained instruction source; no contradictory duplicate rules |
| [test_od01r_rights_hardening.py](../../../../../tests/unit/test_od01r_rights_hardening.py), new | 78 new parametrized cases, real junctions/harmless sentinels, mock transports/curl, zero-effect denial, thread refresh and guard self-test |
| [od01r-policy-boundary.md](../../../decisions/od01r-policy-boundary.md), new | Small stdlib/Pydantic extension ADR and administrative trust boundary |
| [This evidence directory](./), new | Eight required reports, guarded runner/read-only checker, original-file snapshots, actual failures and final results |

## Compatibility and preservation

No policy schema or production permission changed: config/source_rights_policy.v1.json remains byte-identical, all 13 sources pending. SourceRegistry technical URLs/eras/checksums/rates unchanged; HTTP GDELT stays blocked pending a separately approved contract. V1 now conservatively supports only HTTPS/443 remote requests. Host matching still normalizes case and one trailing dot without broadening domains. No new dependency, service, browser or environment bypass.

Safe same-source/date cache pointers remain usable with absolute in-root, repository-relative or bare partition paths and valid checksum. Missing optional sidecar retains legacy fallback to the self-contained pointer after validating the reference is confined. Existing safe downloader/seed reuse tests pass unchanged. Ambiguous/malicious manifests now miss, potentially requiring a separately approved refetch; no original cache is edited or repaired. Identity absent from old manifest is tolerated only within dated source namespace and naming convention, not asserted as authenticated provenance. Hostile concurrent filesystem changes are not solved by Path.resolve.

Cached storage property retains ParquetStorage/store_daily semantics on explicit tabular use. No edits to storage.py, sequential_pipeline.py, financial math, warehouses, release/publication code, dependency specifications, workflow, existing tests/fixtures, data, artifacts, keys or previous reports. No historical signed bytes, DB or original user files were regenerated. Final checked scope/preservation result: [final-qa.json](logs/final-qa-reviewed.json).

## Review history

Maker/design preceded production edits. Initial new tests reproduced URL, path, metadata, unguarded loader/manual entry and refusal failures. Later same-model review added red tests for bootstrap/client/DB-to-request refresh and eager orchestrator output, then minimal corrections. A scheduled-CA test timestamp was corrected to an actual existing window; assertions unchanged. New Windows symlink tests report unavailable privilege, real junction tests execute. No rejected test expectation was lowered to obtain green results. All original 100 policy cases remain untouched.
