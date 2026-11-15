# OD04 repository-first raw archive selection

2026-11-15; baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182.
Decision: EXTEND_EXISTING conditionally on actual process/fault/platform tests.
No new dependencies or fetched production code. Metadata below is conservative;
unverified license/version is not cleared for adoption. Local pilots UNMEASURED
until recorded in OD04 evidence, no advertised throughput adopted as measured.

| Candidate | Verified source / pin/license | Fit and mismatch | Footprint, platforms, rollback/tests |
|---|---|---|---|
| Python stdlib plus existing Arrow | Local Python 3.14.3, existing pyarrow 23.0.1; upstream https://github.com/apache/arrow; exact upstream commit/license for checked source UNVERIFIED | hashlib/os/pathlib/tempfile/json reused; Arrow is columnar not transaction envelope | No additional dependency; Windows/Linux local tests required; disable opt-in rollback; inherited regression suite |
| DVC | https://github.com/iterative/dvc redirects to https://github.com/treeverse/dvc in observed web read; checked exact tag/commit/license UNVERIFIED | Dataset/versioned cache relevant; legal observation/rights semantics still need adapter | Python-oriented tooling, precise current platform/dependency support UNVERIFIED; benchmark UNMEASURED; not installed; upstream tests not executed; remove adapter rollback |
| lakeFS | https://github.com/treeverse/lakeFS; exact pin/license UNVERIFIED | Object-lake version control; separate service/object-store administration disproportionate for local bytes | Exact checked runtime/platform/dependency footprint UNVERIFIED; service overhead inferred from architectural role, not benchmark; UNMEASURED; tests not run; migration rollback burden high |
| delta-rs | https://github.com/delta-io/delta-rs; exact pin/license UNVERIFIED | Rust Delta table library/Python bindings per upstream; raw bytes still need observation wrapper | Additional native/table dependencies; precise platform support UNVERIFIED; no install; UNMEASURED; tests not run; table migration rollback beyond scope |
| DuckDB | https://github.com/duckdb/duckdb; exact pin/license UNVERIFIED | Analytical verification candidate, no stand-alone cross-file raw envelope | Extra database runtime and duplicate metadata system; exact platform/runtime/license UNVERIFIED; UNMEASURED; tests not run; unnecessary rollback surface |

Official upstream pages read with web tool; no code/license pinned-source retrieval
or installation. Names/language above come only from visible upstream descriptions;
not a supply-chain/license approval. Live candidate pilot would need separate
installation and license review. The archive has a capability gap, not a need for
a new engine. Existing source_rights, acquisition.safe_url, validation and downloader
contracts are the reuse baseline. Hardlink vs kernel-lock/rename prototypes and
reference hashlib reader provide local comparators, not third-party product speed
claims. Acceptance: exact bytes, separate events, immutable replay, no overwrites,
rights, bounded storage, crash/process evidence and full regressions both OSes.

## Pinned license follow-up (official primary-source read)

After the initial conservative inventory, the following tag-specific license
files were successfully opened with the web tool. This supersedes ONLY the
unverified pin/license cells above, not runtime/advisory or benchmark clearance.
No commit SHA was verified; tags are references, not an assertion of immutable
third-party checkout identity. No third-party code was installed or adopted.

| Candidate checked tag | License from that version | Primary source |
|---|---|---|
| Arrow apache-arrow-23.0.1 | Apache-2.0 plus bundled third-party notices | [checked license](https://raw.githubusercontent.com/apache/arrow/apache-arrow-23.0.1/LICENSE.txt) |
| DVC 3.59.2 | Apache-2.0 | [checked license](https://raw.githubusercontent.com/iterative/dvc/3.59.2/LICENSE) |
| lakeFS v1.48.0 | Apache-2.0 | [checked license](https://raw.githubusercontent.com/treeverse/lakeFS/v1.48.0/LICENSE) |
| delta-rs python-v0.25.0 | Apache-2.0 | [checked license](https://raw.githubusercontent.com/delta-io/delta-rs/python-v0.25.0/LICENSE.txt) |
| DuckDB v1.2.2 | MIT | [checked license](https://raw.githubusercontent.com/duckdb/duckdb/v1.2.2/LICENSE) |

License-family identification is not legal advice or transitive dependency
clearance. stdlib Python already exists locally; no redistributable engine was
added. Actual local publishing/benchmark comparisons are in the new OD04 process
evidence, never measurements of uninstalled external tools.
