# OD-01 repo-first policy reuse decision

Date: 2026-11-14 UTC. Repository HEAD: d4b5a58f0c50dc348e0d4e1150a725cc6fab5674; feature/od01-source-rights. Decision: **EXTEND_EXISTING**. Technical choice implemented within explicit OD-01 scope; no human legal/source approval implied. Old ADR-OD-001 remains a proposal requiring human administrative acceptance where applicable.

## Evidence / original modules

[DataSource/SourceEra](../../../src/omegadata/track_a/source_registry.py), [DownloadManager](../../../src/omegadata/track_a/download_manager.py), [Settings](../../../src/omegadata/config.py), [orchestration](../../../src/omegadata/track_a/orchestration.py) are the existing boundaries. The registry has 13 keys and technical metadata; it had no rights precondition. Existing cache checksum validation and transport implementations are retained. [Pre-code design](../implementation/od01/20261114T133340Z/design.md) mapped independent source-probe curl and optional-source exception handling before edits.

## Alternatives

| Alternative | Fit / complexity / failure modes / maintainability | Disposition |
|---|---|---|
| A: typed dataclasses plus handwritten JSON validation | Fits small immutable decisions and current dataclasses, but adds custom enum/date/extra-field/revision validation that can drift. Easy fake providers; more duplicated validation tests | Considered; use existing dataclasses for transport envelopes only |
| B: existing Pydantic frozen models + JSON register + small evaluator | Existing dependency; central strict field/UTC/schema validation, immutable tuples, plain deterministic evaluator. Failure modes include malformed config, time ambiguity and stale permissive providers; covered by explicit refusal and per-boundary reload. No service/DB needed | **EXTEND_EXISTING**, B for policy; current dataclasses for acquisition results |
| dlt comparator (https://github.com/dlt-hub/dlt) | Acquisition platform cannot confer source rights or human evidence. Adds integration/dependency/network surface unrelated to this local policy gate | DEFER OD-02 comparison; not imported, installed or fetched |

## Observed versions, licensing and pins

[Preflight package metadata](../implementation/od01/20261114T133340Z/logs/preflight.json): Python 3.14.3, Pydantic 2.12.5, pydantic-settings 2.13.1, httpx 0.28.1, pytest 9.0.2, Ruff 0.15.9, mypy 1.20.0, coverage 7.13.5. These are observed installed versions, not new dependency pins or declarations of upstream commercial license clearance. Existing pyproject lower bounds and CI remain untouched. No new runtime/dev dependency; no model weights. dlt pin, current advisories, dependency-graph/license compatibility and current upstream maintenance remain UNVERIFIED because network retrieval/install is out of scope. Source-data rights are a separate human review even when code license permits use.

## Chosen boundaries and cost

New pure policy module with frozen records, exact scope enums and revision hash; default register pending; constructor-injected synthetic fixtures only in tests. No generalized authorization service, framework migration, global permissive test flag, cache relabeling or human impersonation. No performance benchmark, cost saving or external reliability claim made. Correctness tests cover blocked state, cache disclosure, transport/host preflight, terminal errors, malformed history and concurrency. Operational cost is local JSON validation/reading at operation boundaries; workload scaling is unmeasured.

## Acceptance / rollback

[Matrix](../implementation/od01/20261114T133340Z/test-matrix.md), [verdict](../implementation/od01/20261114T133340Z/gatekeeper-verdict.md) and [risk/rollback](../implementation/od01/20261114T133340Z/risk-and-rollback.md) hold actual outcomes. No current policy source is APPROVED. Later rollback must isolate this diff and preserve old artifacts; removing a fail-closed gate is not authorization to resume acquisition. Independent review and named human rights owner remain pending.

