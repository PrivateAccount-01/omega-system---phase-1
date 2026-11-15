# OD-01R risks, controls and rollback

Branch feature/od01-source-rights; baseline/retained HEAD 3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc. Same-model engineering assessment. Overall research release certification remains BLOCKED even when this bounded technical patch passes.

## Residual findings and enforceable stop conditions

| Risk / ownership | Disposition and stop condition |
|---|---|
| D-01 P0 signing custody / security owner | UNRESOLVED, OD-11/14. Tracked private-key/revocation paths and repository-local trust remain. No key bytes inspected, key usability tested, GPG command run, custody change or history rewrite. No release authenticity certification until separately approved security-owner review and trusted external custody/public verification root |
| D-04 P0 publication / release owner | UNRESOLVED, OD-11. Existing unfiltered export/promotion/overwrite path unchanged. No bundle publication, distribution, signing or readiness claim. A rights-policy unit suite cannot waive this gate |
| D-05/D-12 P1 acquisition / OD-02 owner | HTML/era/date/payload validation and real HTTP 403/429 terminality still unresolved. Redirects, DNS/address egress/SSRF, finite shared budgets and multi-transport consistency require next-phase mocked negatives. No actual HTTP denial or live availability is certified |
| D-03 P1 storage / OD-04/10 owner | Fixed daily overwrite, content-addressed archive, atomic writes/correction versions/concurrency/disk faults unresolved. Path.resolve prevents tested static escapes but is not a descriptor-based race-free filesystem sandbox. No concurrent hostile filesystem certification |
| D-02/D-08 P1 knowledge history / OD-06/07/08/10 owner | Historical identity, membership publication time, mutable price/action revisions and as-known consumers unchanged; no lookahead/PIT guarantee |
| D-06/D-09 P1 math/provenance / OD-06/07/14 owner | Prior-session rights adjustment and original official fixture authenticity unresolved; no financial truth inferred from checksum/schema or old corpus labels |
| D-10/D-11 P2 / OD-11/14 owner | Historical green readiness stale; dependencies unlocked/advisories/license/CI/supply-chain not certified. Existing workflow unchanged; no network package setup or CI run requested |
| Warehouse/CLI risks | Existing SQL idempotency and CLI password exposure risks unchanged, outside phase; no live warehouse/service validation |
| Local environment coverage | Windows file-symlink privilege unavailable; real junctions pass. Linux 3.12 and Windows 3.11 tests BLOCKED missing packages. No new package/environment installation. Later independent matrix reproduction remains needed |
| SQLite cleanup warnings | Six unclosed temporary connection warnings in final covered suite; not suppressed or claimed resolved. All DB writes are disposable |

No P0/P1 failure in the implemented OD-01R acceptance boundary remains in executed Windows cases. Unverified dimensions are explicitly not counted as successful runs. Broader P0/P1 findings above continue to block production/release certification. OD-03 browser integration remains deferred: only a separately rights-approved need and benchmark may justify Obscura/Playwright later; none added here.

## Administrative approval control (mandatory, not performed)

The policy loader verifies structure/hash/history, not a legal principal. The forged-string test deliberately shows a newly hashed forged record can pass structural checks. No signature verifier or independent authority store is implemented. Full-register rewrites/rollback cannot be authenticated by the register alone.

All 13 actual records remain PENDING_REVIEW, with no scopes/hosts/transports, so real acquisition and cache use refuse by default. Source jobs must remain disabled and operators must not deploy an APPROVED revision solely on a JSON/hash/string change. Before any source enablement, a named human rights owner must independently access the original terms/permission record, check source, operation, transport, exact DNS authority/HTTPS:443, purpose, retention/rate/geography/cost and finite validity; validate terms digest and retrieval/approval timestamps; retain signoff and trusted revision checkpoints in an access-controlled administrative record outside this repository. A separate authorized operator verifies that external signoff before deploying/enabling a job. Revocation appends a restrictive revision and disables the job. These are operational controls; this run neither supplies legal permission nor proves an external approval system exists.

Legacy endpoint/BSE/matrix diagnostics are unconditionally disabled in code. Re-enabling requires a separately reviewed migration to a guarded approved source path and explicit owner authorization; no dev flag or standing fake approval exists. Direct source APIs and standalone F&O/probe paths enforce default pending refusal. No general claim is made that arbitrary historical parser/report reads already enforce downstream usage rights; that integration belongs OD-11/12.

## Cost and reuse

No dependency, paid service, package install, model, browser, new service or DB migration. Stdlib URL/path checks and existing Pydantic used. No throughput/latency/cost-saving benchmark claimed; extra validation and repeated file/provider checks may add unmeasured overhead. Canonical JSON hashes indicate byte/record consistency, never financial truth. No terms documents or external advisory database were fetched.

## Rollback procedure (not executed)

Review [exact ledger](04_implementation_diff.md), [patch](logs/implementation.patch), [final scope](logs/final-qa-reviewed.json) and current user work first. Reverse only the ten tracked-file hunks plus the new automatic-instruction facade/test/ADR after separate owner review, retaining all new evidence and supplied prompt. Do not use reset/clean/stash, revert unrelated work, rewrite old reports, delete caches/data/keys or regenerate manifests. There is no schema/DB migration to undo. Reversal would restore known permissive boundary defects, so it must leave real source jobs and publication disabled. No rollback action is authorized or performed in this run.
