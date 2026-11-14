# 08 — Prioritized defects and reproduction register

- Repository: PrivateAccount-01/omega-system---phase-1; branch main.
- HEAD: `09631ae5cdca7d35172724a68d70847183b914df`; inspected working tree includes pre-existing changes.
- Evaluated: 2026-11-14 UTC; run ID `OD-00-20261114-1107Z`.
- Owner: Reviewer / Gatekeeper; evidence classes: RUN / SYN / CMP / ARCH / UNK.
- Mode: OD-00 AUDIT_AND_PLAN_ONLY. No implementation approval or production certification.

## Procedure, scope and severity

Verified findings combine static source inspection, preserved entry state, historical evidence and disposable diagnostic experiments. Severity describes a plausible impact path, not a claim that every old release is wrong. No defect was fixed in OD-00. Counts: **2 P0, 8 P1, 2 P2, 0 P3**, derived from the twelve records below. P0/P1 block publication certification; all remain unresolved. Related mitigations are procedural only. Source line references can move after later changes; this report is pinned to the recorded working-tree baseline.

## D-01 — P0: Signing private-key material tracked

- Evidence / location: [src/omegadata/track_b/release_manager.py:142](../../../src/omegadata/track_b/release_manager.py#L142); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Authenticity of releases signed with repository-accessible material.
- Reproduction: Run git ls-files artifacts/gnupg; inspect only path names in logs/tracked-gnupg-paths.txt and signing key-selection logic.
- Expected: Private signing material stays outside source control; trusted public verification identity is separately governed.
- Observed: Two private-key-directory files and a revocation certificate are tracked; key generation can use an empty passphrase. Key usability/public exposure was not tested.
- Impacted tests: Release build unit test mocks signing; does not prove key custody.
- Root cause / uncertainty: Verified repository layout and repository-local signing-home default; actual compromise remains unknown.
- Compensating control: No certification or new signatures; preserve key files and restrict sharing.
- Minimal recommended fix: Security-owner-approved classification, external key custody and public trust root; separately approve rotation/history remediation if needed.
- Acceptance: Secret-history/path scanner rejects private material; isolated public-only signature verification and forged-signature refusal tests.
- User action / approval: YES: security owner and remediation scope; no rotation/deletion authorized.

## D-02 — P1: Universe query lacks knowledge-time filter

- Evidence / location: [src/omegadata/track_b/universe_manager.py:74](../../../src/omegadata/track_b/universe_manager.py#L74); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Historical research universes and survivorship/lookahead claims.
- Reproduction: Use disposable-integrity-experiments recipe: added_date=2026, effective=2019, query=2020.
- Expected: Strict decision-time query excludes unavailable membership or explicitly refuses unknown availability.
- Observed: One membership returned; strict expected zero.
- Impacted tests: Existing universe tests pass business-date expectations; no strict late-knowledge negative test.
- Root cause / uncertainty: Verified query only effective/removal dates; ORM lacks knowledge intervals.
- Compensating control: Do not label existing universes lookahead-safe.
- Minimal recommended fix: Append observation revisions, source availability policy and decision_at predicate; unknown availability rejects.
- Acceptance: Delayed observation/correction, missing master, actual identifier transitions and delisted-history tests.
- User action / approval: YES: availability/unknown-time policy and OD-08 implementation.

## D-03 — P1: Daily canonical Parquet overwrite

- Evidence / location: [src/omegadata/track_a/storage.py:28](../../../src/omegadata/track_a/storage.py#L28); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Daily canonical datasets and replay reproducibility.
- Reproduction: Store close=100 then close=101 for the same dataset/day in fresh temporary storage.
- Expected: Both revisions remain addressable; immutable prior bytes unchanged.
- Observed: Same path returned, prior hash changed; original bytes lost at that path.
- Impacted tests: No current concurrency/version-preservation assertion exposed this.
- Root cause / uncertainty: Verified fixed part-00000.parquet with direct to_parquet.
- Compensating control: No audit calls against existing data paths.
- Minimal recommended fix: Versioned paths, staging/atomic commit and immutable manifests.
- Acceptance: Two versions coexist, duplicate idempotence, concurrent collision, crash and rollback byte tests.
- User action / approval: YES: OD-10 and storage contract/migration approval.

## D-04 — P0: Release export/promotion can bypass publication eligibility

- Evidence / location: [src/omegadata/track_b/release_manager.py:242](../../../src/omegadata/track_b/release_manager.py#L242); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Any generated bundle consumed through latest/profile or direct dataset files.
- Reproduction: Inspect unfiltered equity export, build_release lines 494–575, and fixed release ID at line 92; do not execute on existing releases.
- Expected: Build into a new immutable ID; filter/quarantine blocked rows; promote latest only after all critical gates pass.
- Observed: Export selects all prices through as_of without PublicationService filtering; date/profile ID reused; writes overwrite paths; quality evaluated after writes; latest updated unconditionally. Static path verified; no destructive rerun performed.
- Impacted tests: Signed release unit test mocks signing/warehouse and does not prove blocked-row omission or failed-gate promotion refusal.
- Root cause / uncertainty: Verified generation and promotion conflated; per-row API controls are separate.
- Compensating control: Do not certify, distribute or rebuild existing bundles; current checksum success is insufficient.
- Minimal recommended fix: Separate staged generation/verification/atomic promotion; enforce row/series/instrument/release blocks and immutable revision IDs.
- Acceptance: Injected blocking review, synthetic row, stale proof, bad hash/signature and warehouse failure prevent promotion; old release bytes remain unchanged.
- User action / approval: YES: OD-11 contract approval and explicit migration scope; no existing bundle changes in OD-00.

## D-05 — P1: NSE equity payload validator accepts HTML denial

- Evidence / location: [src/omegadata/track_a/download_manager.py:693](../../../src/omegadata/track_a/download_manager.py#L693); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: NSE raw success classification; downstream parse may later fail.
- Reproduction: Call _validate_payload for NSE_EQUITY_BHAVCOPY with nonempty HTML Access denied body in memory.
- Expected: Reject content/ZIP/schema/date mismatch before reporting acquisition success.
- Observed: No exception; diagnostic records ACCEPTED. This does not prove HTML became published prices.
- Impacted tests: Existing immutable-download test mocks validator; no general NSE equity HTML-negative expectation.
- Root cause / uncertainty: Verified specialized BSE/FO branches and generic nonempty/JSON checks leave NSE equity validation incomplete.
- Compensating control: No external fetch; treat acquisition success separately from parsed_validated.
- Minimal recommended fix: Explicit era-aware bounded ZIP/header/market-date validation; classify denial as terminal failure.
- Acceptance: HTML, login body, truncated ZIP, wrong date, partial rows and schema-era negative fixtures.
- User action / approval: YES: OD-02/05; rights before live smoke.

## D-06 — P1: Rights factor uses prior calendar day

- Evidence / location: [src/omegadata/track_b/adjustment_engine.py:218](../../../src/omegadata/track_b/adjustment_engine.py#L218); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Rights events following nontrading/missing preceding calendar dates.
- Reproduction: Supply Monday ex_date, only a Friday previous bar, P=100 N=4 R=1 S=50.
- Expected: Use validated prior exchange session with bounded gap policy; factor 0.9 for supplied math.
- Observed: None returned because Sunday row absent. This is synthetic diagnostic data, not a real action.
- Impacted tests: Rights tests do not establish holiday/weekend session selection.
- Root cause / uncertainty: Verified ex_date - timedelta(days=1) lookup.
- Compensating control: Flag missing factors; do not declare adjustment completeness from nonnull fields.
- Minimal recommended fix: Prior valid session lookup with missing/stale rejection; no arbitrary stale price fallback.
- Acceptance: Independent 0.9 vector; Monday/holiday, suspension, missing prior bar and staleness tests.
- User action / approval: YES: OD-07 and prior-session/staleness policy.

## D-07 — P1: Source registry has no enforceable rights state

- Evidence / location: [src/omegadata/track_a/source_registry.py:21](../../../src/omegadata/track_a/source_registry.py#L21); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: All registered automated collection and downstream licensed use.
- Reproduction: Inspect DataSource fields and DownloadManager.download preconditions.
- Expected: Only versioned human-approved access scope may fetch; denied/pending/revoked states fail closed.
- Observed: No rights state/policy reference fields or corresponding downloader gate. Actual legal permissions unknown, not proven denied.
- Impacted tests: No rights-state negative test in current suite.
- Root cause / uncertainty: Verified technical endpoint registry predates rights contract.
- Compensating control: No acquisition or redistribution in OD-00.
- Minimal recommended fix: Add minimal rights policy schema and shared pre-fetch enforcement with actionable reason codes.
- Acceptance: Mock pending/denied/revoked source: zero HTTP calls, explicit policy-block error; approved source proceeds within limits.
- User action / approval: YES: OD-01 scope plus human rights owner; live access remains separately approved.

## D-08 — P1: Current-state prices/actions cannot reproduce knowledge revisions

- Evidence / location: [src/omegadata/db/models.py:189](../../../src/omegadata/db/models.py#L189); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: As-of adjusted prices, future corrections and reproducibility.
- Reproduction: Inspect PriceRecord uniqueness, loader existing-row assignments, adjustment current-action selection and correction supersedes flag.
- Expected: New observations/corrections retain prior versions and availability; pinned research replay is unchanged.
- Observed: One current price row per ISIN/exchange/day; mutable adjusted fields; latest non-superseded action selection; no known intervals/raw hash/parser/release version per equity row.
- Impacted tests: Correction/math tests pass latest-state semantics; no full historic-decision replay proof.
- Root cause / uncertainty: Verified schema/current-state design; extent of historical overwritten data unknown.
- Compensating control: Do not assert bitemporal/total-return/as-known correctness.
- Minimal recommended fix: Append-only observations, adjustment chain revisions and immutable snapshot references; retain raw fields and legacy read facade.
- Acceptance: Late correction plus later demerger value creates a new version; old decision result/hash unchanged.
- User action / approval: YES: temporal contract and disposable migration/restore plan.

## D-09 — P1: Official fixture labels lack independent provenance

- Evidence / location: [tests/fixtures/official_source/circular_extracts/20microns_reverse_split_2025-06-24.json:1](../../../tests/fixtures/official_source/circular_extracts/20microns_reverse_split_2025-06-24.json#L1); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Official-corpus readiness counts and confidence in transformational events.
- Reproduction: Read cited extract and 21stcenmgm demerger extract; inspect reference test path-existence assertions.
- Expected: Official claims link exact original circular/payload, retrieval evidence, rights and checksum; event parameters independently checked.
- Observed: Inspected extracts self-label official but lack official URL/circular ID/retrieval/hash. Event truth unverified, not declared fabricated.
- Impacted tests: Existing official reference test uses stored values/path existence and mathematical assertions.
- Root cause / uncertainty: Provenance assertions can be counted without authenticating original documents.
- Compensating control: Classify these claims UNK; do not use case count as independent official certification.
- Minimal recommended fix: Attach verified raw source references or conservatively relabel/quarantine under approved fixture scope.
- Acceptance: Missing/tampered provenance cannot count toward official gate; independent event and math comparison.
- User action / approval: YES: official reference access/rights and OD-07/14 fixture review scope.

## D-10 — P2: Stored green readiness and README are stale/mismatched

- Evidence / location: [README.md:460](../../../README.md#L460); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Operational interpretation of April/May releases in November.
- Reproduction: Read generated_at and recompute age against current UTC policy; compare corpus count fields.
- Expected: Current readiness derived from current evidence; historical status labeled accurately.
- Observed: Stored ready=true from May 2; probe/pipeline about 4727.53h old against 24h limits; README 14/5 versus corpus 23/11.
- Impacted tests: No time-travel documentation freshness assertion required; existing gate freshness tests pass.
- Root cause / uncertainty: Verified archived reports and prose are snapshots.
- Compensating control: Audit marks all historical booleans ARCH; no proof regeneration.
- Minimal recommended fix: Later update documentation and consumer freshness enforcement without rewriting historic evidence.
- Acceptance: Time-frozen stale-report refusal test; report separates generated-at age, source mode and evaluated-at.
- User action / approval: YES for code/docs outside OD-00; no need to overwrite existing proofs.

## D-11 — P2: Supply-chain and CI coverage incomplete

- Evidence / location: [pyproject.toml:14](../../../pyproject.toml#L14); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Reproducible dependency/runtime baseline and automated guard coverage.
- Reproduction: Inspect lower-bound dependencies and sole workflow; repository filename search for locks/license.
- Expected: Approved pins/hashes/SBOM/license/advisory evidence and full offline checks across supported runtimes.
- Observed: No inspected lockfile or project LICENSE; one calendar workflow; advisory status UNK. Current 3.14 environment passes checks.
- Impacted tests: 111 offline tests and lint/type pass locally; Python 3.11 run not executed.
- Root cause / uncertainty: Minimal packaging/CI scope, not evidence of an actual CVE.
- Compensating control: Record exact installed versions; no dependency changes.
- Minimal recommended fix: Scoped reproducibility/CI/license plan under OD-14, preserve full integration profile.
- Acceptance: Clean pinned install, license/advisory/secret gates, offline tests/lint/type on supported Python/OS matrix.
- User action / approval: YES: OD-14 and approved dependency/advisory access.

## D-12 — P1: Outer acquisition loop continues after access denial

- Evidence / location: [src/omegadata/track_a/download_manager.py:883](../../../src/omegadata/track_a/download_manager.py#L883); [diagnostic output](logs/disposable-integrity-experiments.txt) where applicable; [security path inventory](logs/tracked-gnupg-paths.txt) for D-01.
- Affected data/release: Source access-policy compliance and retry volume.
- Reproduction: Inspect inner 403/429 classification versus outer catch-and-continue across candidates/header profiles.
- Expected: A denied source job stops terminally with denial evidence, without further source requests.
- Observed: Inner workaround avoids denied NSE fallback, but outer download catches Exception and continues. Static evidence; no denied site contacted.
- Impacted tests: Existing transport fallback tests target generic errors; no source-wide terminal-denial assertion.
- Root cause / uncertainty: Verified error taxonomy lost in outer loop.
- Compensating control: No live probes/acquisition; do not interpret transport alternatives as access authorization.
- Minimal recommended fix: Typed terminal source-policy denial propagated through candidate/profile loops; retain approved transient retry paths.
- Acceptance: Mock 403/429/robots denial: one policy-terminal outcome, no later candidate/profile/transport calls.
- User action / approval: YES: OD-02 and rights policy.

## Limitations and next action

This register is not exhaustive CVE, exchange-truth or concurrency certification. P0 release-export findings are statically established; a full new bundle reproduction was intentionally not run because signing, warehouse and canonical side effects exceed OD-00. P0 signing exposure is based on tracked private-key paths and signing policy; actual key compromise is unknown. Same-model review is not independent signoff. Assign named human owners to the role-owned experiments in [open decisions](../plan/11_open_decisions_and_approval_requests.md), review OD-01, and authorize only that phase if desired.

