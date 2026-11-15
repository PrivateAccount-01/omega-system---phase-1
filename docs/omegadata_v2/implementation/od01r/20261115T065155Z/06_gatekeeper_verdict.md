# Gatekeeper: OD-01R

**OD01R_TECHNICAL_PASS — executed Windows/Python 3.14.3 scope only. NOT PRODUCTION_READY. Overall release certification BLOCKED.**

Actual branch **feature/od01-source-rights**; HEAD **3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc**, one commit ahead of main d4b5a58f0c50dc348e0d4e1150a725cc6fab5674. Upstream feature matched HEAD in a read-only query; no update/merge performed. Changes remain local, unstaged and uncommitted. Final mechanical scope/preservation/document/exit check is recorded in [final-qa.json](logs/final-qa-reviewed.json); this verdict is valid only with that check passing.

## Executable acceptance

| Gate | Actual result |
|---|---|
| Fresh feature baseline | 211 passed, four realdata excluded; actual exit 0 |
| Negative-first reproduction | Initial 38 failures plus separate bootstrap-refresh, BSE-refresh, eager-output and F&O-refresh failures, all captured before their corrections |
| Exact authority contract | Approved synthetic HTTPS/443 works via mock; bad scheme/port/userinfo/authority refuses before client. No DNS/redirect safety claim |
| Cache boundary | Static absolute/traversal/sidecar/identity/digest/shape/size failures closed; harmless sentinel outside raw/seed never opened. Two real Windows junction attacks pass |
| File symlink / other runtimes | Three Windows file-symlink cases BLOCKED by privilege, not PASS. Linux pytest and Python 3.11 matrix BLOCKED missing dependencies; no install. This remains an explicit unverified dimension |
| Entry paths | Orchestrator/pipeline pending source has zero output/client effects; original optional refusal terminal; independent F&O and canonical probe guarded; five manual diagnostic entries hard-disabled; backfill refusal terminal |
| Policy refresh/thread scope | Concurrent request scopes remain separate; revoked request stops before next GET/curl; per-request provider checks, not atomic mid-syscall revocation |
| Retained policy/attestation contract | Original frozen v1/history/hash/scope cases unchanged; actual 13 pending, zero approved. Forged-string limitation explicitly tested/documented; trusted human process external |
| Final targeted | **175 passed, 3 skipped**, exit 0; all original 100 included unchanged |
| Final complete offline / collection | **286 passed, 3 skipped, 4 deselected**, exit 0; collection **289/293 selected**, exit 0 |
| Quality | Ruff exit 0, mypy exit 0 (47 source files), pip check exit 0; editor Problems clear; CR-aware whitespace check exit 0 |
| Coverage / warnings | Source rights 99%, downloader 62% displayed branch coverage; actual JSON retained. Six temporary SQLite cleanup ResourceWarnings retained. No whole-app coverage delta claimed |
| Scope preservation | Final mechanical check must show zero unexpected original-byte/metadata deltas, unchanged branch/HEAD/index, complete documents/links. GnuPG metadata only, never content |
| Forbidden actions | No provider HTTP, live test, service startup, dependency install, workflow edit, signing action, release, git mutation or OD-02 implementation |

Exact commands, UTC intervals and underlying exits: [test matrix](03_test_matrix.md). Baseline and negative traces are evidence of this checkout; historical OD-01 reports are ARCH context only. The two harness failures and invalid new scheduled-test setup are retained and explained; no existing assertion was weakened or skipped to obtain green results.

## Same-model AEF review record

Maker: [pre-code design and essential-scope addendum](02_contract_and_design.md); reused existing Pydantic and stdlib. Reviewer/design: reproduced hostname-port and manifest-boundary leads, separated already-denied IP/local cases and challenged administrative strings. Implementer: minimal boundary changes after red tests. Reviewer/code: inspected the complete tracked diff, call inventory, helper refusals, cache roots/legacy fallback and no-network/disposable harness. Gatekeeper: checked current command exits, counts, skip reasons, evidence and preservation; no independent reviewer or human signoff implied. Historian: [ledger](04_implementation_diff.md), [risk/rollback](05_risks_rollback.md), [ADR](../../../decisions/od01r-policy-boundary.md), [single next-phase proposal](07_next_phase_request.md).

No P0/P1 failure in this executed OD-01R technical boundary remains. Same-model technical pass is not human source authorization, independent financial/security audit, full OS/Python portability, data truth or release certification. D-01 and D-04 P0 remain unresolved; D-02/03/05/06/08/09/12 etc. remain assigned to later phases. Live collection stays prohibited, every production policy remains pending and publication stays blocked. No automatic phase advancement.
