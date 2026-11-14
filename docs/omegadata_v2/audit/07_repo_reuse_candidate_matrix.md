# 07 — Repository-first reuse candidate register

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Maker / product-cost reviewer; evidence classes: RUN / ARCH / CLAIM / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure and decision boundary

Compared candidate roles with the inspected modules and installed metadata. No candidate was installed, fetched, benchmarked or approved. Upstream versions/commits, code licenses, commercial compatibility, advisories and maintenance are **UNVERIFIED** unless a local installed version is explicitly stated below. Metadata is not license clearance. No model weights are needed by core OmegaData.

The master suggests per-candidate decision files outside audit/plan, while OD-00 permits writes only inside audit/plan. This consolidated register preserves those decision fields here; separate decision files require later phase scope. All dispositions are DEFER; no ADR is ACCEPTED.

| Candidate / exact repository | Current baseline / comparator | Current version evidence | Proposed pilot and disposition |
|---|---|---|---|
| [dlt](https://github.com/dlt-hub/dlt) | DownloadManager / httpx | dlt pin UNK; httpx 0.28.1 installed | Does wrapper reduce code while preserving original bytes, terminal denial and retry budgets? DEFER OD-02 |
| [Obscura](https://github.com/h4ckf0r0day/obscura) | Direct HTTP / [Playwright](https://github.com/microsoft/playwright) | Both pins/licenses/advisories UNK | Only rights-approved JS-only corpus, OS isolation, no stealth/circumvention; DEFER optional OD-03 |
| [Scrapy](https://github.com/scrapy/scrapy) | Source-specific HTTP / [trafilatura](https://github.com/adbar/trafilatura) | Pins UNK | Fidelity, original document retention and article rights; DEFER OD-16 |
| [Pandera](https://github.com/unionai-oss/pandera) | Typed checks / Pydantic | Pandera UNK; Pydantic 2.12.5 installed | Per-era drift/negative rows without silent coercion; DEFER OD-05 |
| [DuckDB](https://github.com/duckdb/duckdb) | SQLite/Postgres + current Parquet | DuckDB pin UNK; SQLAlchemy 2.0.49 installed | Reproducible pinned-snapshot read and cost versus simple Arrow; DEFER OD-10 |
| [Arrow](https://github.com/apache/arrow) | Existing PyArrow Parquet | PyArrow 23.0.1 installed | Keep format initially; test atomic/versioned wrapper versus adoption; DEFER OD-10 |
| [DVC](https://github.com/iterative/dvc) | Content-addressed raw + manifests | Pin UNK | Is added service/tool state justified by reproducibility? DEFER OD-04/10 |
| [exchange_calendars](https://github.com/gerrymanoim/exchange_calendars) | Existing calendar / official session documents | Pin UNK | Verify actual NSE/BSE special sessions, coverage and update cadence; DEFER OD-06 |
| [Qlib](https://github.com/microsoft/qlib) | Minimal read-only pinned Parquet client | Pin UNK | Preserve basis, decision time and refusal semantics; DEFER until OD-11/12 |
| [Lean](https://github.com/QuantConnect/Lean) / [Nautilus](https://github.com/nautechsystems/nautilus_trader) | Downstream portfolio comparator | Pins UNK | Outside current repository implementation; DEFER |
| [RD-Agent](https://github.com/microsoft/RD-Agent) / [AEF](https://github.com/paril-01/agents) | Same-model procedural review / human verifier | Pins UNK; not verified locally | No external model APIs or generated gatekeeper as authorization; DEFER |

## Mandatory fields for every deferred pilot

Owner: respective OD phase owner. Mission fit and API surface: narrowly bounded row above; exact upstream public API compatibility remains UNK. Integration preference: reuse current code or small adapter before fork. Code/model license: code UNK pending official license at pinned tag/commit; model weights N/A for core, separately review any optional model. Security/maintenance/dependency graph/Python+OS: UNK pending pinned inspection. Operating costs and hidden network: UNMEASURED; no paid service assumed. Evaluation corpus: source-rights approved normal/adverse raw bytes with hashes; synthetic rows separately labeled. Baseline: existing offline suite and four diagnostic gaps, no performance benchmark. Metrics: correctness, completeness, lineage fidelity, bounded failure, then wall time/p50/p95/RSS/CPU/disk, integration effort and recurring costs. Independent comparator: listed baseline plus official source or hand calculation as appropriate. Risk: source normalization, noncommercial licensing, unbounded egress and needless complexity. ADR: PROPOSED after evidence, conclusion currently DEFER.

## Limitations / next action

No performance numbers, legal compatibility or upstream quality claims are asserted. No candidate rejection is invented. Earliest action is review of OD-01 registry requirements; candidate fetching/pinning/benchmarks need phase and network authorization. Founder guidance is NOT_AVAILABLE in the configured skill inventory for this task; no invented guidance applied. Same-model role checklists do not establish independent consensus.

