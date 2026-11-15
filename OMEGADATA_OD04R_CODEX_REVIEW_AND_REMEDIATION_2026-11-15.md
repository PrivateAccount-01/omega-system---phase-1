# OMEGADATA: OD-04R INDEPENDENT VERIFICATION & TARGETED REMEDIATION

**Execution mode:** `OD04R_REVERIFY_AND_REMEDIATE_ONLY`  
**Repository:** `https://github.com/PrivateAccount-01/omega-system---phase-1`  
**Expected working branch:** `feature/od01-source-rights`  
**Reviewed initial HEAD:** `44090a42958869faaab57a42b65f7ad8571d924d`  
**Previous OD-04 baseline:** `d24e9cfd29c8a59e590aaee85983babe9e8bf182`  
**Reference OD-04 evidence:** `docs/omegadata_v2/implementation/od04/20261115T124835Z/`  
**Date authored:** 2026-11-15  
**Scope:** verification, adversarial reproduction, narrowly justified correction, evidence and Gatekeeper only. **Do not start OD-05.**

> **Central decision:** The prior OD-04 implementation reports 58 new tests, passed Windows/Linux offline regressions and cross-process crash experiments, but the Gatekeeper verdict is `OD04_BLOCKED` because the full A01–A28 negative-first tranche was not executed before the core implementation. The historical chronology cannot be fixed after the fact. This phase can independently reverify technical correctness, correct newly reproduced defects and prepare an explicit owner decision, but it must not falsely claim retroactive Gate 2 compliance or grant its own process exception.

## 0. Instructions hierarchy and execution behavior

Read completely, in order:

1. `AGENTS.md`, then `OMEGADATA_AGENTS.md` and the OmegaData master prompt under `docs/verification/` (discover its exact current name; do not invent missing paths).
2. OD-00 audit and phase plan: `docs/omegadata_v2/audit/08_prioritized_defects.md`, `docs/omegadata_v2/plan/09_implementation_phase_plan.md`, `docs/omegadata_v2/plan/10_architecture_and_contract_proposal.md`, `docs/omegadata_v2/plan/11_open_decisions_and_approval_requests.md`.
3. OD-01 / OD-01R / OD-02 / OD-02V Gatekeeper reports and source-rights contracts, especially the unchanged `PENDING_REVIEW` defaults.
4. Every OD-04 document numbered `00` to `10`, and the relevant exact command/exit files under `docs/omegadata_v2/implementation/od04/20261115T124835Z/logs/`; read the accepted rather than the superseded failed proof, while retaining the failed proof in history.
5. Source files, scripts and tests listed in section 2 of this prompt.

Use a **Maker → Design Reviewer → Implementer → Code Reviewer → Gatekeeper → Historian** procedure. If all roles are executed by one model, explicitly label that *same-model procedural review*. Never claim a separate human/security auditor or a second model reviewed anything unless that review actually occurred. Reject inaccurate PASS labels, fabricated command exits, placeholder proof, source-origin upgrades and unsafe shortcuts.

Before editing, report in the new evidence directory: actual branch, HEAD, diff to `main`, dirty files, source/test hash manifest, Python and platform versions, previous Gatekeeper status, outstanding user-owned changes, and exact modifications authorized here. If HEAD differs, **inspect and reconcile**; if differences overlap this task or cannot be reconciled, **stop edits** and report. Do not reset, stash, clean, force checkout, delete branches, rewrite history or overwrite historical evidence. Keep user work and all existing source/fixture bytes.

## 1. Desired outcome and hard boundaries

**Desired outcome:** an independently reproducible OD-04 **technical** verification dossier: exact code identities, meaningful failure-first adversarial tests against the reviewed implementation, valid cross-platform green reruns, independently calculated byte/hash/link invariants and a clear owner exception decision request for the prior Gate 2 chronology violation. Correct application code only when a newly executable test proves an actual error.

**Never** contact market-data providers, exchange endpoints, paid APIs, brokers or live source URLs. Default external egress is `BLOCKED_EXTERNAL_EGRESS`; all 13 actual source policies remain `PENDING_REVIEW`, zero approved. Use synthetic fixtures and the permitted, already-existing isolated test corpus only. Do not enable source approvals, perform actual releases, inspect/copy private signing material, change GPG state, touch historical databases, alter canonical Parquet, publish to the warehouse or turn on browser scraping. Do not start OD-05/OD-10/OD-11/OD-14 or modify unrelated modules.

Do not approve or waive the historical negative-first deviation. Even if all technical checks pass, the reported **process exception stays pending until a human project owner explicitly chooses to accept it**. A user's request to run a new review does not, by itself, constitute approval of that exception.

Security boundary: trusted private local archives only. Never claim protection against hostile concurrent filesystem owners, all filesystem power-loss scenarios, remote/NFS semantics, arbitrary malicious Python or real exchange-data correctness. Unit/WSL tests do not establish independent physical-host/CI success.

## 2. Exact code and evidence inventory

Core files to read and map call-by-call:

- `src/omegadata/track_a/raw_archive.py` (`ObservationRequest`, `RawObject`, `RawObservation`, `RawCommit`, `RawArchive.put`, `_publish`, `_verified`, `read_verified`, `recover_staging`, `scan_verified`).
- `src/omegadata/track_a/download_manager.py` (opt-in `raw_archive` injection, operation IDs, cache-only, rights rechecks, legacy pointer and new manifest paths).
- `src/omegadata/track_a/acquisition.py` (validated structural state, source eras, resource budgets, URL redaction).
- `src/omegadata/track_a/source_rights.py` and `config/source_rights_policy.v1.json` (policy scopes, strict deny, revision consistency).
- `src/omegadata/track_a/storage.py` (read-only inspection only: separate known OD-10 Parquet overwrite defect).
- `scripts/verify_raw_archive.py` and `scripts/plan_legacy_raw_import.py` (rights-aware read-only behavior and dry-run only).
- `tests/unit/test_od04_raw_archive.py`, `tests/unit/test_od02v_portability.py`, `tests/unit/test_od02_acquisition.py`, `tests/unit/test_od01r_rights_hardening.py`, `tests/unit/test_od01_source_rights.py`, and all prior offline regressions.
- OD-04 existing independent process tools: `process_experiments.py`, `process_worker.py`, `process_guard.py`, `measure_corpus.py`, and prior `verification_runner.py` in `docs/omegadata_v2/implementation/od04/20261115T124835Z/`.

The prior report says OD-04 created an **opt-in** raw archive and left the legacy default behavior untouched. Preserve that boundary. Do not confuse raw archive OD-04 with the independent versioned analytical Parquet work reserved for OD-10.

## 3. First gate: audit the prior evidence, do not recycle it as current proof

Create an append-only new run directory, e.g. `docs/omegadata_v2/implementation/od04r/<fresh-UTC-run-id>/`, containing raw logs under `logs/`. **Never reuse OD-04 evidence file paths or overwrite old accepted/failed checks.**

Reconcile:

- What each A01–A28 test actually asserted, its test function/worker, source identity, platform, exit, skip/deselection and test-order chronology.
- Prior Windows 3.14/3.11 reported 451 passed, 10 skipped, 4 realdata deselected; Linux 3.12 reported 459 passed, 2 skipped, 4 deselected. Treat these as **ARCH** historical counts until independently rerun.
- Prior Linux transient `/tmp` corpus disappeared and caused a vacuous 0/0 reference scan. The reported fix reran 18 observations / 13 object files under a persistent native Linux directory. Re-run a fresh nonvacuous verifier; never use a 0/0 result as proof of an expected 18/13 corpus.
- The original A01–A28 complete negative-first chronology was not met. Document exact evidence and retain `OD04_BLOCKED` as the historical verdict.
- Check actual code/tests SHA against the reviewed commit and final-preservation report, not only filename or timestamps.
- Confirm no GitHub Actions result validates this latest feature SHA; only report true observed CI evidence.

Deliver `01_PRIOR_EVIDENCE_INDEPENDENT_RECONCILIATION.md` with **supported**, **unverified** and **contradicted** columns. Missing logs or ambiguous identities are BLOCKED, never assumed green.

## 4. New adversarial design gate, before any new application changes

Create a **fresh OD04R-specific specification and threat model**, independent of the prior implementation's test code. Use one or more independently coded test oracles based on Python stdlib and raw filesystem inspection; do not call `RawArchive._verified()` to compute the expected reference hash for tests of `_verified()`.

The previous gate's past ordering cannot be repaired, but **every new defect/fix in OD04R must be genuinely negative-first**: write the new test first; run it against the current, unchanged OD-04 implementation; capture the asserted failure (not an import/environment error); only then modify the smallest production code region. If a suspected defect does not reproduce, preserve the passing counterexample and do not make speculative code changes.

### Priority R01: missing or empty archive must not masquerade as verified completeness

**Specific code-review suspicion:** `RawArchive._inventory()` returns `(0, 0)` if `root` is missing; `recover_staging()` can then report an empty inventory; `scan_verified(source_key, business_date)` may return a successful `raw-verification/v1` result containing zero observations for a nonexistent archive. This mirrors the earlier independent-verifier vacuous-success failure, but has not yet been reproduced as an actual failing application test.

1. Define explicit semantics for **missing root**, **initialized empty root**, **nonempty archive with zero commits**, **expected empty snapshot**, **expected nonempty snapshot**, **corrupted or missing committed object**, and **uncommitted staging**. Do not silently equate these.
2. Add exact synthetic negative tests for nonexistent root with permitted fake rights, and for an archive that disappears between inventory and verified scan. Capture the pre-fix outcome.
3. Keep read-only inspection possible where appropriate, but ensure a user asking for *verification of expected committed evidence* cannot obtain a misleading empty success. Proposed narrow choices: an explicit `NOT_FOUND/EMPTY_ARCHIVE` reason; or a `complete=false/expected_count` contract where strict verification refuses absent evidence. Choose after tests and document API compatibility.
4. Do not infer completeness merely from a count stored in the same untrusted archive. The independent verifier must obtain an expected count/digest from separately pinned test configuration.
5. Add a nonvacuous external verifier negative test that fails when the expected corpus directory has been removed or moved, **before** the success assertion.

### Priority R02–R18: independent threat checklist

Build a table with one negative or controlled-positive test per category, reusing proven test cases when sufficient and adding new tests only where needed:

| ID | Scenario | Required invariant |
|---|---|---|
| R02 | Same bytes, separate observed events | One SHA object, both immutable event IDs retained |
| R03 | Different bytes for same source/date | Both distinct versions remain pinned and replayable |
| R04 | Idempotent operation retry | Same frozen request+rights+bytes returns same marker; any semantic change conflicts |
| R05 | Policy revision/revocation between steps | No new visible commit; historical stored policy cannot override current refusal |
| R06 | Crash at each of five boundaries | No visible partial marker; safe reattempt; no preexisting bytes modified |
| R07 | Two independent OS processes, same/different content | No inconsistent object/observation/commit links; correct conflict outcome |
| R08 | Concurrent readers during writer publication | Either NOT_COMMITTED or full verified bytes, never partial trusted data |
| R09 | Full hash collision-path adversary / wrong-size prior object | Existing mismatched object never treated as valid |
| R10 | Malformed/truncated/duplicate JSON, unknown versions | Reason-coded integrity refusal; no arbitrary object-path expansion |
| R11 | Symlink, junction, traversal and invalid identifiers | Cannot read or write outside private sandbox; record OS-specific gaps honestly |
| R12 | Filesystem errors at stage, link, fsync and marker | Fail closed with no committed false success; existing immutable objects remain |
| R13 | Resource ceiling, retained stage accumulation | Bounded, deterministic refusal; no automatic garbage collection |
| R14 | Synthetic, cache, seed and provider classifications | No provenance escalation; all synthetic fixtures explicitly synthetic |
| R15 | Invalid parser state or source-era/date mismatch | `PAYLOAD_STRUCTURALLY_VALID` backed by actual OD-02 validation, not a declarative string |
| R16 | URL/token confidentiality and public exception text | No secret/query/token in new logs, canonical records or error context |
| R17 | Legacy cache and dry-run migration | Read-only, no overwrite, no silent origin relabel; missing rights refuse |
| R18 | Recovery/verified scan independent oracle | Expected corpus count and all object SHA/length/link checks verified; missing corpus refuses |

Also exercise `read_verified()` source/date and consumer-purpose mismatches, nested source-policy statuses, unknown source, archive namespace mixing, an initialized but empty archive, an orphan observation, duplicate commit ID, and negative retries. Do not weaken old assertions, add blanket skips, or fake permission approval in runtime configuration.

## 5. Controlled architecture/reuse decision

Re-open the exact prior OD-04 repository-first decision. Candidates include **existing Python stdlib + hardlink/fcntl/msvcrt** (current implementation), `DVC` (`https://github.com/iterative/dvc`), `delta-rs` (`https://github.com/delta-io/delta-rs`), `lakeFS` (`https://github.com/treeverse/lakeFS`), and `PyArrow` (`https://github.com/apache/arrow`).

Compare only relevant scope: append-only byte objects, immutable fetch observations, cross-platform exclusive commit, source-rights intercept, crash recovery, existing-download integration, package/license implications and operational burden. Explicitly distinguish storage of **raw payload** from a mutable lakehouse table. A stable, tested stdlib implementation is a perfectly acceptable decision; adding a large third-party engine without a demonstrated missing capability is not.

Record actual repository links, pin/version (if evaluated), licensing evidence or unresolved licensing issues, benchmark methodology, and a clear **KEEP / WRAP / ADOPT / DEFER / REJECT**. Do not install any new dependency or clone source repositories merely for the report.

## 6. Implementation rule if a defect reproduces

Only these code paths may be changed if independently demonstrated necessary:

- `src/omegadata/track_a/raw_archive.py`
- `src/omegadata/track_a/download_manager.py` (only if the caller or propagation is the cause)
- `scripts/verify_raw_archive.py` (only its read-only verification semantics)
- A new OD04R-specific unit test module, plus narrowly scoped helper/verification code under the new OD04R evidence directory.

**Not permitted:** editing prior OD04 assertions to hide failures; changes to source-rights approvals, acquisition network enablement, exchange era registry, `ParquetStorage`, ORM, releases, signing, warehouse, dependencies, GitHub Actions or previous evidence. The only acceptable failure of the existing compatibility surface is a documented safety-oriented change with a versioned contract, backward-compatible migration strategy and explicit reasoned Gatekeeper decision. Do not auto-migrate any existing archives.

Perform changes as small reviewable diffs. After each fix: targeted test first; related regressions second; full cross-platform suite after code freezes. If a new discovery requires other files, stop and report the required scope expansion instead of silently editing them.

## 7. Reproducible execution, exact commands and runners

Use a **new** evidence directory with **exclusive-create** output. Build sanitized disposable worktrees from the current commit; pin each source/config/test file with hashes and include only previously approved fixture paths. Never copy `.env`, signing material, production DBs, release bundles or complete unknown raw directories into disposable runners. Keep existing source/policy register bytes unchanged. Reuse the already-reviewed offline runner/worker architecture, after auditing it against its own earlier failures; do not trust it as an independent oracle.

Run under at least:

- Windows Python 3.14.3 (if still available).
- Windows Python 3.11.15.
- WSL native Linux Python 3.12.3 (or another explicitly compatible Linux Python >=3.11, with deviation recorded).

**Representative command forms (substitute recorded absolute python/runner/copy paths):**

```text
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest --collect-only -q -m "not realdata"
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q tests/unit/test_od04_raw_archive.py tests/unit/test_od04r_adversarial.py -m "not realdata"
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q -m "not realdata" --cov=omegadata --cov-branch --cov-report=term-missing
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> ruff check --no-cache src/omegadata tests scripts
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> mypy src/omegadata
<python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pip check
<python> -B <new-run>/process_experiments.py <sanitized-copy> <unique-label>
```

Use exact absolute executable, version, argv, cwd, UTC timestamps, duration, OS/FS, exit, raw stdout/stderr, test node IDs, skip and deselection reasons, coverage and source hashes in machine-readable JSON. Do not present these commands as already executed. Adapt existing helper flags only after inspecting the actual script's accepted arguments. **Do not run raw unguarded tests against original data roots.** The pytest sandbox must deny external network/DNS/process and protected-path writes during collection and execution. Dedicated process-crash tests may spawn only approved disposable child workers, under independently enforced no-egress/no-production-write constraints.

Create fresh process tests with a persistent native filesystem path on Linux, not WSL ephemeral `/tmp` for evidence that must survive launcher restarts. Test forced child termination and independent parent verifier with an explicit expected `N=18` observations and `M=13` object files (or separately frozen new corpus manifest with explicit values). Verify each object's **full** SHA-256 and size, observation/commit canonical linkage, plus that missing root fails. Do not let expected values come solely from the service's own inventory method.

Preserve expected Windows privilege skips where actual symlinks cannot be created; require Linux execution of those same actual file-link tests and Windows execution of the corresponding junction tests. Four pre-existing `realdata` tests remain deselected and must never count as passed. Preserve SQLite `ResourceWarning` lines and track them as a separate existing P2 issue. No fabricated 100% coverage requirement; require unchanged-or-better relevant coverage and no uncovered newly critical paths without explicit rationale.

## 8. Evidence and report deliverables

Under the new directory, create:

```text
00_PREFLIGHT_AND_IDENTITY.md
01_PRIOR_EVIDENCE_INDEPENDENT_RECONCILIATION.md
02_THREAT_MODEL_AND_CONTRACT.md
03_NEW_RED_GREEN_TEST_MATRIX.md
04_CODE_REVIEW_AND_MINIMAL_DIFF.md
05_PROCESS_CRASH_AND_INDEPENDENT_ORACLE.md
06_CROSS_PLATFORM_REGRESSION.md
07_RIGHTS_SECURITY_AND_REUSE_DECISION.md
08_REMAINING_DEFECTS_AND_ROLLBACK.md
09_GATEKEEPER_VERDICT.md
10_OWNER_EXCEPTION_DECISION_REQUEST.md
logs/ (exact commands, raw outputs, JSON metadata, independent oracle output, immutable previous-evidence citations)
```

Each report must label evidence `RUN` (current execution), `ARCH` (old committed logs), `TEST/SYN` (synthetic fixtures), `CLAIM` (unreproduced external assertions), `UNK` (unknown). A prior file's claims must not become new `RUN` evidence through paraphrase.

Required output matrix columns: requirement, defect suspicion, original test identity, fresh independent oracle, new red status, minimal change, Windows 3.14, Windows 3.11, Linux, process proof, unresolved uncertainty, Gatekeeper. Include an explicit before/after file hash ledger, exact clean-room fixture list, forbidden path preservation verification, and status of all 13 production policy records.

Create a deterministic rollback plan for any newly changed code; do not actually roll it back or delete orphan staging, prior objects, historic evidence or source data. For new archive storage, no GC/migration/cleanup action is in scope.

## 9. Gatekeeper logic: distinguish technical acceptance from process approval

There are **three possible final outcomes**, not just a green checkmark:

1. `OD04R_BLOCKED`: any uncorrected high-severity defect, missed mandatory current test, unresolved or mismatched source identity, new code not red-first, unauthorized side effect, incomplete independent corpus, or other current technical gate failure.
2. `OD04R_TECHNICALLY_REVERIFIED_PROCESS_EXCEPTION_PENDING`: the newly executed technical evidence and all applicable tests pass, but the historical A01–A28 ordering deviation remains a formally open owner decision. **Do not advance to OD-05** under this status.
3. `OD04R_ACCEPTED_WITH_EXPLICIT_OWNER_EXCEPTION`: technically verified **and** a named accountable human owner separately documents an explicit acceptance of the *past process deviation*, including rationale, residual risks and exact commit / run identities. Record the actual approval reference; never invent it or construe this Codex prompt as the exception. Even then: live acquisition, official source truth, signing, release and production access remain blocked.

A separate independent human/security reviewer is advisable before owner acceptance. Same-model Maker/Reviewer roles, GitHub stars, green tests or 'working locally' are not substitutes for that review.

**Stop after OD04R.** No autonomous progression to OD-05 under any verdict. OD-05 implementation requires a separate user instruction even if the process exception is accepted.

## 10. Next feature after OD04R (plan only, do not implement)

The prospective next development phase is **OD-05: historical source-era specifications, deterministic parsing and independent reference-data provenance**. OD-05 should first compare the exact NSE/BSE historical schema eras with independently authorized reference documents/corpora, model unknown availability correctly and distinguish `PAYLOAD_STRUCTURALLY_VALID` from source-authenticated and financially reconciled information. It should keep all real-source policies pending until a named human rights owner approves the specific use; no browser scraping unless a justified, separately authorized OD-03 pilot is requested.

The source registry's NSE equity transition around January 2020 and BSE variant formats are inherited hypotheses, **not independent official proof**. Do not encode synthetic fixtures as official truth. Require point-in-time decision constraints later in OD-06 through OD-10.

## 11. Exact Codex end-of-session response format

Produce the following sections, with factual results only:

1. Actual branch + HEAD before and after; explicit Git status and source diff.
2. Scope-preservation result: data, DBs, signing material, old proofs and 13 pending real-source policies.
3. OD04 historical process violation, exact impact and whether a human owner has approved an exception (default NO).
4. Prior archive implementation: pass/defect/unverified per component.
5. Fresh negative-first tests: observed reds and corrected greens; absent reds labeled not reproduced.
6. Exact per-environment test counts, skips, deselections, exits, independent process/corpus results and CI status.
7. Minimal changed files and why; concise risk/rollback.
8. **One** Gatekeeper code from section 9, with explicit reasons.
9. Single proposed next action, either owner/process exception review or separately requested OD-05 preparation, without executing it.

**Final prohibition:** Never transform historical `OD04_BLOCKED` into a prior PASS, never create an official source approval, and never treat a valid raw hash as proof of exchange provenance or trading suitability.
