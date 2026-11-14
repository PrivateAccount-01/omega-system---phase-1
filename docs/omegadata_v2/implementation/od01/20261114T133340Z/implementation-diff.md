# OD-01 implementation change ledger

Repository: PrivateAccount-01/omega-system---phase-1. Phase: OD-01 IMPLEMENT_OD01_ONLY.
Branch: feature/od01-source-rights. HEAD before/after: d4b5a58f0c50dc348e0d4e1150a725cc6fab5674 (no commit).
Evidence collected 2026-11-14 UTC; exact command times/exit codes in [logs](logs/). Run directory name was allocated at 13:33:40Z; approval/environment delays mean later commands ran through 15:09Z and document checks later. Owner: same-model procedural engineering reviewer, not a human rights approver.

## Authorized files and purpose

| File | Why changed |
|---|---|
| [source_rights.py](../../../../../src/omegadata/track_a/source_rights.py) (new) | Frozen v1 policy/request/decision models, strict register loader, linked revisions/hash, UTC validation, deterministic evaluator, typed refusal |
| [source_rights_policy.v1.json](../../../../../config/source_rights_policy.v1.json) (new) | Exhaustive 13-source pending register; no fabricated approvals/permissions |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | Guard cache, seed, download, probes, discovery, bootstrap and low-level transports; defer mkdir until allowed write; explicit provider/clock injection, terminal policy errors, decision provenance |
| [sequential_pipeline.py](../../../../../src/omegadata/pipelines/sequential_pipeline.py) | Three-line import/rethrow addition: optional feed failure handler must not swallow rights refusal and continue |
| [generate_source_probe_report.py](../../../../../scripts/generate_source_probe_report.py) | Independent curl path bypasses DownloadManager; check source/host/transport before temporary files/subprocess and record policy identity |
| [test_od01_source_rights.py](../../../../../tests/unit/test_od01_source_rights.py) (new) | Negative-first and 100 executed deterministic cases; T01–T18 plus boundary/malformed/fallback/concurrency coverage |
| [conftest.py](../../../../../tests/conftest.py) | Explicit SYNTHETIC_TEST_ONLY immutable provider fixture for mocked legacy tests; no automatic/global approval |
| [test_pipeline_and_api.py](../../../../../tests/unit/test_pipeline_and_api.py) | Five existing downloader tests explicitly inject fake policy; two private fallback tests set source scope. Fake transport label uses its simulated httpx identity; assertions preserved |
| [test_operations_layer.py](../../../../../tests/unit/test_operations_layer.py) | Candidate-selection test explicitly injects fake policy because discovery can perform network calls |
| [reuse decision](../../../decisions/od01-source-policy-reuse.md) (new) | EXTEND_EXISTING comparison, observed versions, limitations |
| This run's evidence directory | Design, schema/admin guide, matrix, rollback, verdict, next request, scripts, examples, raw logs and preservation checks |

The two caller additions were listed in the pre-code [design](design.md). SourceRegistry's technical metadata and Settings are unchanged. No model/DB migration, dependency, CI, price/calendar/math, warehouse or release-manager edit. None of the four realdata tests changed.

[implementation.patch](logs/implementation.patch) captures the tracked-file patch. New files are reviewable at their actual paths; [definition index](logs/definition-index.json) maps functions to line numbers. Existing mixed LF/CRLF was preserved on unchanged lines to avoid unrelated diff expansion. Early local edits briefly normalized line endings; that noise was removed without reverting any functional edits or user work.

## Preservation

[Before snapshot](logs/preservation-before.json) captured tracked files plus data/artifact files/root databases; signing paths were checked only by size/mtime metadata, never content. [After snapshot](logs/preservation-after.json) found changes only in the six authorized pre-existing files above. New files are scoped to the policy register, model, tests and docs. No old verification proof, release manifest, payload, DB, signing file or OD-00 report was regenerated or changed. Subsequent final checks must still pass before the final verdict.

Pre-existing untracked Linux environment, revocation/private-key paths and the supplied OD-01 prompt remain preserved. Only a local feature branch was created, as requested; HEAD is unchanged. No stage/commit/push/PR/deploy/release. The preflight branch was main; the branch operation did not change file bytes.

## Review and limitations

Same-model code review inspected every changed entry point; no independent human/agent signoff claimed. Targeted and complete offline tests execute in a guarded disposable profile. Historical signing and publication P0s remain unresolved. This patch is a rights precondition, not data-source availability or release certification.

