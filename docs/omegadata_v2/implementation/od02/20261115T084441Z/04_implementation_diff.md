# OD-02 implementation ledger

Branch `feature/od01-source-rights`; unchanged HEAD `3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc`. OD-02 only, run `20261115T084441Z`. Synthetic/mock evidence, never official financial certification.


The [OD-02-only normalized text diff](logs/od02-only.patch) reconstructs the reviewed OD-01R patch in memory on HEAD, then compares to this implementation. It includes new files. No checkout/index/worktree manipulation is used. The three edited prior production files retain rights enforcement and existing calling contracts. Other original OD-01R production changes, all old evidence, user prompts, data and keys are preservation-checked separately in [final QA](logs/final-qa.json).

| File | Bounded OD-02 change |
|---|---|
| [acquisition.py](../../../../../src/omegadata/track_a/acquisition.py) (new) | Backward-compatible typed DownloadError, immutable explicit limits, one budget/deadline, status/body rules, URL redaction, strict source-era ZIP/CSV and conservative JSON validation |
| [acquisition_limits.v1.json](../../../../../config/acquisition_limits.v1.json) (new) | Explicit fail-closed engineering ceilings, not source permission |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | Shared ContextVar budget; terminal denial through nested call graph; reject all redirects; stream bound; actual egress disabled; explicit mock callbacks; validation before public success/store; SHA and acquisition evidence; cache-only; cache/seed identity; per-manager candidate-write lock; sanitized URLs/body previews |
| [generate_source_probe_report.py](../../../../../scripts/generate_source_probe_report.py) | No real curl invocation; only explicit offline runner. Bootstrap and actual request share policy/budget; terminal status; no retry/location/insecure flags; bounded test files; common validator. Generic non-equity shape never claims date/financial verification |
| [load_nse_fo_into_pipeline_db.py](../../../../../scripts/load_nse_fo_into_pipeline_db.py) | Keep existing policy checks (including refresh after DB setup); unconditionally stop BLOCKED_EXTERNAL_EGRESS before legacy direct GET. Legacy unreachable redirect flag set false. FO-specific acquisition remains unverified/deferred, not silently approved |
| [test_od02_acquisition.py](../../../../../tests/unit/test_od02_acquisition.py) (new) | 97 actual cases, all synthetic, fixed ZIP timestamps, clocks/callbacks, negative and positive assertions |
| [conftest.py](../../../../../tests/conftest.py) | Synthetic valid NSE archive fixture for policy-attribution test |
| [test_od01_source_rights.py](../../../../../tests/unit/test_od01_source_rights.py) | One allowed probe fixture changes arbitrary MOSPI text to valid NSE ZIP; original policy attribution assertions retained |
| [test_od01r_rights_hardening.py](../../../../../tests/unit/test_od01r_rights_hardening.py) | Existing fake probe explicitly injects offline_runner; revocation callback independently runs when bootstrap now also has bounded -o output. Two-call success/one-call revocation assertions retained. Reconstructed original test bytes match preflight SHA |

No dependency pins, registry era ranges, real source policy, warehouse, business math, public endpoints, universe or release/signing implementation is edited. OD-02 documentation consists of this fresh ten-report run, design, replay/review helpers, raw logs and [ADR](../../../decisions/od02-direct-acquisition-reuse.md). Helpers are not production entry points.

Compatibility: DownloadError remains importable from download_manager with existing message/status/stage arguments; new attributes add reason/terminal/retry-after/context. Dataclass new fields have defaults. Existing public positional source/date arguments remain. `cache_only` is additive. A private fetched candidate means HTTP_RECEIVED, not validated. Old manifests/cache remain conservatively HTTP_RECEIVED, not retroactively certified. Strict NSE/BSE structures can now refuse previously tolerated malformed data by design. Explicit private fake clients/callbacks are trusted test code, never a general Python sandbox.

Storage remains the existing legacy versioned raw/manifest/latest contract; the new lock serializes one manager's candidate writes, not processes or crash recovery. Tests never target original dataset paths. Existing manifest `storage_mode=immutable_versioned` is historical terminology, **not an OD-02 proof of atomic immutable publication**. OD-04 owns that architecture and migration. The standalone FO guard occurs after authorized legacy DB initialization; no production invocation is performed, and source policy pending still stops before DB. Re-enabling its actual fetch requires separately reviewed migration.
