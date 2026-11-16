# OmegaData 2.0 — OD-05S: Authenticated Source-Reference Intake and Historical CM Schema Pilot

**Document ID:** OD2-OD05S-20261116  
**For:** Codex engineering agent working on the EXISTING OmegaData repository  
**Prepared:** 2026-11-16  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Working branch:** `feature/od01-source-rights`  
**Last independently inspected GitHub HEAD:** `25fb5aa4a2f4312e7bfafb9084c29aa95ee2bd48`  
**Predecessor:** OD-05R, `OD05R_REFERENCE_VERIFIER_TECHNICAL_PASS_REFERENCE_PENDING`  
**Execution mode:** `OD05S_OFFLINE_REFERENCE_INTAKE_AND_EVIDENCE_BOUND_PARSER_PILOT_ONLY`  
**Not authorized:** OD-06, production source-route changes, live market collection, signing, releases, merging, or broad migration.

## 0. Mission and essential distinction

The OD-05 synthetic parser and OD-05R offline evidence verifier are implemented and have recorded technical pass results. They do **not** have verified actual NSE/BSE schema-by-era truth. The existing code contains `source_registry.py` modern NSE CM routing starting in 2020, while NSE public documentation reports discontinuation of older CM bhavcopy products from July 8, 2024. Neither the 2020 assumption nor a global 2024 replacement is proven for every file and overlap. OD-05S must create a usable, **read-only intake/review bridge** from lawfully supplied original publisher reference documents and representative data rows to independent tests of the existing parser architecture. Do NOT create a fake official-approval pipeline.

**Crucial separation:** SHA-256 establishes byte identity only. A claimed NSE URL, `issuer='NSE'`, PDF magic bytes, `reviewer_ref`, or a user-written JSON field does NOT establish publisher authenticity, legal permission, review authority, an actual exchange session, row accuracy, point-in-time availability, or release eligibility. The existing `ReferenceResult.official_eligible: Literal[False]` is an intentional safety design. Do not flip it to True, remove its blockers, or create another status that secretly grants identical powers.

**Mandatory real-world input:** A human source-rights/reference owner must supply (or explicitly authorize obtaining) genuine date/version-specific NSE CM documentation, exact original byte files with independently recorded hashes and provenance, permitted representative sample rows, and human-reviewed expected field/date/unit identities. No such authenticated pack was recorded by OD-05R. If absent, implement only the useful offline intake/read-only comparison tooling with self-generated SYNTHETIC_TEST_ONLY fixtures and clearly leave official/reference-sensitive cases BLOCKED_REFERENCE. Do not produce a third generic audit-only commit or claim completion of official format work.

## 1. Required reading and unalterable history

Read completely before touching code:

1. `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`.
2. `docs/omegadata_v2/plan/09_implementation_phase_plan.md` OD-05/OD-06; `docs/omegadata_v2/audit/08_prioritized_defects.md`; source rights, repository reuse, current audit, approved architecture contracts.
3. OD-05 synthetic Gatekeeper: `docs/omegadata_v2/implementation/od05_impl/20261115T201333Z/09_gatekeeper_verdict.md`; OD-05R Gatekeeper and reports under `docs/omegadata_v2/implementation/od05r/20261116T084526Z/`.
4. Current `src/omegadata/parsers/{contracts,dispatch,nse_cm,reference_registry,reference_evidence,era_matrix}.py`, their tests, independent oracles and final acceptance/input identity logs.
5. Existing `source_registry.py`, `acquisition.py`, `download_manager.py`, `raw_archive.py`, `sequential_pipeline.py`, read-only inspection of historical backfill/probe scripts. Inspect exact paths before expanding scope.
6. Inspect `git status --porcelain=v1`, `git branch --show-current`, `git rev-parse HEAD`, main merge-base and user-modified/untracked paths. If HEAD differs from stated SHA, **reconcile the commit diff and current evidence before application edits**. Never reset/stash/clean/force-push to force a match.

Preserve original OD-04's historical chronology failure and OD-04R's recorded human exception decision. No repeated G0/G1 approval loop: the owner-approved synthetic OD-05 work already occurred. **This new phase itself must be explicitly requested**, as the Codex invocation below does, but it does not authorize later phases.

No signing-key contents may be read, hashed, scanned, copied, or logged. Handle only approved metadata. No existing data, raw/seed archives, application DB, fixed Parquet partitions, release/latest pointers, old proof logs, old tests, existing environments, or historical user files may be overwritten or deleted.

## 2. Verified starting snapshot and non-negotiable gates

Prior OD-05R commit: `25fb5aa4a2f4312e7bfafb9084c29aa95ee2bd48`; previous OD-05 commit `2326936860f64cadf4f4c24a968c073114598b26`.

Previously recorded OD-05R cross-platform full offline tests:

| Runtime | Passed | Skipped | Real-data deselected | New OD-05R cases | Quality |
|---|---:|---:|---:|---:|---|
| Windows Python 3.14.3 | 632 | 11 | 4 | 60 pass / 1 platform skip | Ruff/mypy/pip/compile 0 |
| Windows Python 3.11.15 | 632 | 11 | 4 | 60 pass / 1 platform skip | Ruff/mypy/pip/compile 0 |
| WSL Linux Python 3.12.3 | 640 | 3 | 4 | 60 pass / 1 platform skip | Ruff/mypy/pip/compile 0 |

These are ARCHIVED claims backed by committed logs, NOT executions for OD-05S. The new phase must rerun its own suite with actual commands, source hashes and exits. GitHub Actions did not provide a successful current feature-SHA run in the last audit. WSL shares a physical host with Windows.

Three independent reference gates:

- **A, source documents:** Original, immutable, authorized NSE-hosted/canonical publisher document or annexure; exact title, circular/catalogue version, true acquisition method, original bytes/hash/length, claimed publisher and independently inspected origin. Mere web snippet or third-party mirror is a REFERENCE_LEAD only.
- **B, representative rows and semantics:** Separately permitted real sample bytes with exact hash, source date/format/member, approved field interpretation and **human reviewer** evidence; independently calculated expected row fields and dates. Schema claims based only on A, or a copied expected hash from the parser, cannot satisfy B.
- **C, production route changes:** An additional separate owner-approved integration scope plus A/B and current rights for the intended use. C is **out of scope** of OD-05S. No changes to `source_registry.py`, acquisition, `DownloadManager`, legacy pipeline, DB, signing/release manager or historical backfill default paths.

All 13 real source policies remain PENDING_REVIEW; zero approved. Public documentation research is not source data permission. No exchange market-data network requests, scraping, authentication or fallback proxies.

## 3. Official public documentary leads to reconcile, without overclaiming

These are research STARTING POINTS, not a preauthenticated corpus:

- NSE Forms & Formats, UDiFF guidance, versions 1–4, CM bhavcopy file format and sample-test-file links: `https://www.nseindia.com/static/resources/forms-formats-members`.
- NSE All Reports: `https://www.nseindia.com/all-reports/` — reports old CM Bhavcopy(csv) and CM Common Bhavcopy(csv) discontinued effective July 8, 2024, with UDiFF final ZIP successor and reference to NSE circular 62424.
- NSE/MSD/59875 dated Dec 21, 2023: official-hosted indexed circular `https://nsearchives.nseindia.com/web/sites/default/files/inline-files/MSD59875.pdf` — publication of UDiFF documentation and sample file availability, not proof of prior live dissemination or every schema version.
- NSE/MSD/62142 dated May 22, 2024: referenced on NSE Forms & Formats; determine exactly which date applies to which change (tag changes, file splitting, report class, parallel availability).
- NSE/MSD/62424 dated June 12, 2024: NSE reports page cites it; any third-party mirror must remain UNVERIFIED until original publisher evidence and exact wording are authenticated. Separate revised June 24 *large-file-splitting* date from July 8 old-CM-bhavcopy discontinuation; never collapse unrelated change types.
- UDiFF guidance says the broader harmonization **exercise** began in 2020. That does **not** establish January 2020 launch of the relevant NSE CM UDiFF bhavcopy format.

Capture exact document/reference IDs, issuer, publication/announced/effective date, format and segment, version, field/table source with page/section number, local evidence path (if legally held), SHA/length, handling rights, and reviewed semantic scope. Record a lead as a LEAD, independently held original as ORIGINAL_BYTES_IDENTITY_CHECKED, and human-reviewed semantic reference as REVIEWED_REFERENCE_CANDIDATE. The latter does not automatically mean official authenticity or acquisition rights. No synthetic-to-official relabeling.

For 2020-01-01 and 2019-12-31, do not infer sessions from weekdays. For 2024 June 21/24/25, July 4/5/8/9, and other chosen boundary controls, identify calendar/session source authority separately. Handle special sessions/holidays and publication versus trade/business dates as distinct facts.

## 4. Exact authorized implementation work

Implement actual usable code, if current explicit task phase approval is valid. Extend existing OD-05R modules rather than rewriting the validator. Only add files needed to close a demonstrated contract gap:

- **Prefer** a new module `src/omegadata/parsers/reference_intake.py`: offline-only, read-only `intake_report` to combine an externally pinned `ExpectedCorpus` and existing `read_bundle` results with human-review evidence objects; report required missing data and supported/unsupported format claims without granting authority. Use frozen typed contracts and bounded reason codes.
- Optional narrowly scoped `src/omegadata/parsers/review_contracts.py` for immutable review objects: reviewer identity/role supplied by human, exact hashes of reviewed file/expected-row list, source kind, document/circular/version/field table/page, date scope, explicit permission/ref, actual review time. **A free-form reviewer name is self-asserted, not cryptographic identity verification.** Trust anchors remain outside this module. No signing key or signature generation.
- New read-only CLI `scripts/inspect_od05_reference_pack.py`: accepts an absolute, private, local pack root and **separately provided expected pin file**; rejects missing root, empty corpus, recursive/symlink/junction escapes, duplicate files, forged/unknown reference IDs, mismatched hashes/lengths, unreviewed rights and out-of-scope CM/F&O/BSE references. Does not modify pack or original roots, perform network access, create prompts, approve commercial use, publish data or perform raw migration. CLI output should be an explicit JSON decision ledger, with secret-free reason codes and deterministic counts.
- Optional `src/omegadata/parsers/nse_cm_verified_profiles.py` ONLY AFTER A+B exist and human approved the exact reference's permitted test scope: explicit immutable format/version/field/date/identity contract, quarantining unknown/overlap. This is NOT a production dispatcher. If A/B absent, do not create a fake `official-2024` profile. Existing synthetic `legacy-illustrative`, `udiff-illustrative`, `syn-v1` must stay unchanged.
- Add `tests/unit/test_od05s_reference_intake.py`, `tests/unit/od05s_expected_oracle.py`, and explicitly synthetic test fixtures. No reference documents or real rows committed without a legal/privacy/copyright-aware approval for the precise permitted subset.
- New evidence ONLY under `docs/omegadata_v2/implementation/od05s/<UTC_RUN_ID>/`. No edits to previous dossiers or Gatekeeper verdicts.

If an existing implementation already meets the acceptance contract, reuse it, document the exact test proving sufficiency and skip redundant code. Each changed application file must be justified by a failing executable test and current owner-authorized scope. Do not add Pandera, another lake engine, transport clients, new browser automation, API credentials, paid vendors, or new package dependencies.

## 5. Source pack intake and independent pinning: concrete contract

The **intake root** is a disposable/private local directory, outside production/archive/signing paths. Its content may be owner-supplied offline or wholly synthetic for initial engineering. It must not be implicitly read from a previous test/log's output. Pin every allowed file using a separately supplied manifest from an accountable owner/reviewer; do not let attacker-controlled `index.json` authorize its own hash. Reuse `ExpectedCorpus` and fail-closed `read_bundle`; do not copy/paste the validation logic into another weaker path.

Suggested conceptual contract:

```text
ReferencePackInput:
  root: path (local absolute private directory, no links)
  externally_pinned_bundle_sha256: 64-hex
  externally_pinned_files: [(relative_name, full_sha256, length)]
  expected_reference_count: positive int
  expected_scope: NSE / CM / source_key / permitted format IDs / dates
  rights_evidence_ref: human supplied, scoped, not self-authorizing
  reviewer_evidence_ref: human supplied, scoped, not self-authorizing

IntakeDecision:
  state: CORPUS_IDENTITY_PASS | NEEDS_HUMAN_REVIEW | BLOCKED_REFERENCE
  document_hashes: exact bytes independently verified
  row_semantic_status: pending | independently reviewed
  declared/verified format+version and effective window
  exclusions and typed refusal codes
  public_official_certification: false
  production_eligibility: false
```

`CORPUS_IDENTITY_PASS` must NOT be presented as `APPROVED_NSE` or source permission. A fake `reviewer_ref` or `OWNER_SUPPLIED_REFERENCE_USE` string must not change authority without an external trusted process. No automatic elevation in `ReferenceResult.official_eligible`.

For supported **human-reviewed** row examples, a separate expected-value oracle (not generated from parsing results) must compare exact symbolic identities, row ordinal, series/ISIN, Decimal OHLC, volume and units, source-vs-business date, original lexemes and header/schema version. Check every reviewed field, not just a row count, SHA or success status. Reference documents and raw data may have different use/redistribution permissions.

If the original publisher files exceed the current 1 MiB per-file or 16-reference caps, record `BUDGET_REVIEW_REQUIRED`. Do not silently relax limits, truncate PDFs or split originals and pretend they are unchanged. Any cap/contract change requires an explicit, bounded, test-first scope amendment.

## 6. Mandatory negative-first test matrix, S01–S24

Before any application edits, freeze all 24 groups (including tests for unavailable official inputs as explicit blocked subcases), fixtures and independent expected hashes. Capture actual SHA/time/argv/exits and old-code behavior. Missing new module is `NEW_API_ABSENT`, never a proven old bug. Write exact negative assertions before corrections; keep later tests honestly later.

| Group | Mandatory assertion (synthetic unless separately reviewed authentic pack exists) |
|---|---|
| S01 | Missing root/index, empty corpus, absent expected pin FAIL, never vacuous success. |
| S02 | Expected count and file/hash pins supplied independently; self-pinned index cannot grant eligibility. |
| S03 | Length, SHA, duplicate-key, truncated or modified document/sample fails. |
| S04 | No source pack read before approved local scope; no secret/signing/environment path reads. |
| S05 | Forged `issuer=NSE`, URL, reviewer_ref or permission string never grants official status. |
| S06 | Web-index excerpt, third-party mirror, paraphrase or simulated PDF remain leads only. |
| S07 | Exact versioned document identity and sample identity remain distinct and linked. |
| S08 | Fake HTTPS domain, URL credential, path traversal, UNC, symlink, junction and hardlink refuse. |
| S09 | Original document SHA plus canonical published path still require origin verification. |
| S10 | Human semantic review without externally pinned expected rows cannot certify rows. |
| S11 | Correct hash but incompatible field/date/units/series semantics refuses. |
| S12 | Legacy NSE 2019 format remains pending without proper dated reference. |
| S13 | NSE 2020 assumptions cannot be inferred from UDiFF guidance project start. |
| S14 | June 2024 tag-format, large-file splitting, availability and overlap are separate change kinds. |
| S15 | July 5, July 8 and July 9 controls preserve discontinuation vs first availability uncertainty. |
| S16 | Trading session/date evidence must be explicit; weekdays do not prove sessions. |
| S17 | Same symbol different series/ISIN not collapsed; preserve leading zeros. |
| S18 | TradDt, BizDt, announced, effective, published and observed times not conflated. |
| S19 | Independently calculated exact Decimal OHLC comparisons and nonfinite refusals. |
| S20 | Integer volume and quantity-unit handling, valid zero, range overflow refusal. |
| S21 | Unknown header/extra field, ambiguous version, empty/missing sample and invalid critical row fail closed. |
| S22 | No modifications or regressions to all OD-01, OD-02, OD-04, OD-04R, OD-05 and OD-05R behavior. |
| S23 | Windows Python 3.14, Windows 3.11, WSL native Linux 3.12: full matrix, paired link skips, Ruff, mypy, pip check, exact source hashes. |
| S24 | No provider network, repo signing/release/DB/data mutations, source-rights changes, Git lifecycle changes or OD-06. |

Do not count official subcases whose human-reviewed original bytes and rights are absent as passed. An actual synthetic test might pass an invariant while the related real source case is `BLOCKED_REFERENCE`. Publish both, never combine them into one green statistic.

## 7. Execution sequence for Codex

**Stage 0 — freeze.** Verify exact HEAD/diff/owner scope; read master instruction chain; inspect current reference verifier/era matrix and tests. Record original file hash manifest excluding protected secret contents. Verify prior OD-05R Gatekeeper truth: full recorded Windows 632/632, Linux 640, three platforms' exact skips, 60 new per runtime plus 1 platform skip; all tests archival to this phase.

**Stage 1 — capture available reference intake inputs.** If an actual lawful owner-supplied NSE pack exists and owner granted its use for this phase, verify and use it in an isolated local read-only workspace. If absent, report `REFERENCE_PACK_ABSENT`, create only synthetic test pack for intake functionality, and do not invoke exchange market-data endpoints. Public indexed NSE documentation can be consulted for source ID planning; never copy unverified web snippet into official expected rows.

**Stage 2 — test-first.** Define contract and all S01–S24 assertions. Freeze test source and fixture identities before new module code, execute baseline, classify missing API vs actual assertion defects vs fixture/harness errors. Never weaken tests to make an exception look green.

**Stage 3 — minimal implementation.** Extend OD-05R validator using read-only offline wrapper/CLI only. Validate externally supplied pins, known owner-review status and independent field/date/schema claims. Do not duplicate input parsing or mutate the old verifier's conservative `official_eligible` behavior. If actual authorized reference rows exist, build only the required opt-in versioned format profile with independently authored field-accurate tests.

**Stage 4 — two separate oracles.** (a) A stdlib independent byte/hash/pin comparator that does not import production reference-verifier methods for expected results; (b) an independent exact integer/Decimal/field comparison with pinned source sample and independently reviewed expected outputs. Test wrong expected corpus counts and missing/moved roots first to prevent 0/0 success.

**Stage 5 — security.** Deny DNS/TCP/UDP, subprocess, protected original-path writes and signing-key reads under the established disposable test guard. Run malicious ZIP/path/reference metadata and rights-negative tests, including actual Linux symlink and Windows junction cases. Never claim Windows no-symlink privileges are a passing test; pair cross-OS.

**Stage 6 — complete regression.** Use existing declared Python environments and isolated cleanroom copies only; no new packages unless separately authorized. Record exact commands and exits:

```text
<python> -B -m pytest --collect-only -q -m 'not realdata'
<python> -B -m pytest -q tests/unit/test_od05s_reference_intake.py -m 'not realdata'
<python> -B -m pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
<python> -B -m ruff check --no-cache src/omegadata tests scripts
<python> -B -m mypy src/omegadata
<python> -B -m pip check
<python> -B -m compileall -q src/omegadata/parsers
```

Where an existing protected runner mandates a different exact invocation, use it and record the full argv. Tests must not install new packages, contact providers, or write protected paths. Include focused OD-05R and OD-05 synthetic tests as part of targeted regressions. Do not report compiler, lint or other gates as successful until actually executed.

**Stage 7 — preservation and Gatekeeper.** Record exact new source hashes, old protected file identities (metadata-only for signing paths), failed and successful commands, independent oracle output, missing evidence, and rollback. Stop after OD-05S.

## 8. Required evidence package and truthful verdict

Create a NEW unique directory `docs/omegadata_v2/implementation/od05s/<UTC_RUN_ID>/` with:

1. `00_scope_and_repo_identity.md` — branch/HEAD/owners/inputs and original protections.
2. `01_reference_pack_inventory.md` — actual doc IDs, date/version, original byte status, rights, reviewer, SHA/length and blockers; no copied full copyrighted publisher content.
3. `02_historical_cutover_matrix.md` — 2019/2020/2024 cases, format change kinds, overlap and verified/unknown session state.
4. `03_contract_and_reuse_decision.md` — extend OD-05R, explicit trust boundary, new/old source diffs and external review contract.
5. `04_S01_S24_negative_first.md` — frozen pre-code test IDs/hash, chronology, classifications and final results.
6. `05_code_changes_and_compatibility.md` — precise source diff and why, default-off and rollback.
7. `06_independent_byte_and_row_oracles.md` — exact independent pinned bytes and reviewed/synthetic expectations, no vacuous corpus.
8. `07_rights_source_authenticity_security.md` — separate doc rights/sample rights, source policy counts, no network and hostile input results.
9. `08_cross_platform_runtime_matrix.md` — full/targeted/per-group results, Ruff/mypy/pip, skip counterpart, coverage and warnings; every exit/time/source identity.
10. `09_remaining_defects_and_rollback.md` — P0 signing custody, P0 release promotion, P1 2020 route/PIT/Parquet/unknown actual reference, P2 SQLite, other gaps.
11. `10_gatekeeper_verdict.md` — one precise technical result without promoting official claims.
12. `11_single_next_request.md` — single actionable next step, no default next phase.
13. `reference_review_inventory.json`, frozen external expected-corpus pin metadata and hashes, tests/logs with raw failures and command evidence.

Choose exactly one relevant verdict:

- `OD05S_INTAKE_TECHNICAL_PASS_REFERENCE_PENDING`: all offline intake/security/regression tests pass, but original publisher docs or reviewed sample semantics/permission are absent. **This is an acceptable useful software result**, not an official-reference PASS.
- `OD05S_REVIEWED_REFERENCE_CANDIDATE_READY`: actual lawful original reference pack and reviewer expectations provided and verified for documented scope; separate human source/financial owner has not yet formally approved use or production. No automated official certification.
- `OD05S_BLOCKED`: missing implementation authorization, actual failing technical gate, protected-path effect, noncomparable cross-OS results or other serious failure. Explain exact blocker, do not hide it.

Do NOT issue production/trading readiness, OD-05 full official certification, source rights approval or automatic OD-06 start. OD-05S is a reference-input pathway, not release governance.

## 9. Explicit carry-forward risks

- D-01 P0: tracked private/revocation signing material custody; human security owner required. Never read/hash/copy secrets in this phase.
- D-04 P0: release export/promotion eligibility bypass; untouched and blocks publication.
- D-03 P1: fixed analytical daily Parquet overwrite; OD-10, NOT OD-05S.
- D-02/D-08 P1: PIT historical knowledge-time and corporate-action/event revisions; later dedicated phases.
- NSE CM historical 2020 source era remains UNVERIFIED, without authentic format/version and row-by-row reference.
- Calendar/session verification and BSE historical schema remain separate; don't borrow F&O or index evidence.
- Full-scope rights and independent human legal/financial review absent; no real provider access.
- Current cross-platform checks from Windows/WSL on same physical host, no hosted CI pass.

## 10. Command invocation and mandatory stopping point

Once the prompt file is in the repository root, invoke Codex with:

```text
Execution mode: OD05S_OFFLINE_REFERENCE_INTAKE_AND_EVIDENCE_BOUND_PARSER_PILOT_ONLY.
Read AGENTS.md, OMEGADATA_AGENTS.md, docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md,
and OMEGADATA_OD05S_AUTHENTIC_REFERENCE_INTAKE_CODEX_PROMPT_2026-11-16.md fully.
Verify current branch and HEAD, starting from inspected 25fb5aa4a2f4312e7bfafb9084c29aa95ee2bd48.
This invocation authorizes the bounded OD-05S offline implementation and guarded disposable tests,
not live acquisition or Git lifecycle changes.
Build usable read-only pinned reference-pack intake and owner-review gap reporting even if
no authenticated original documents were supplied. Run S01–S24 negative-first tests and
all three protected runtime regressions. Add evidence-backed optional real-format parser
profiles ONLY if separately lawful original bytes, human-reviewed field expectations,
and permitted reference-use evidence are available. Never invent them.
Preserve every original code/data/proof/signing artifact. Keep source rights pending,
production routing unchanged and old synthetic and verifier tests intact.
Produce fresh exact test evidence and truthful Gatekeeper. STOP after OD-05S.
```

**Do not automatically commit, push, open PR, merge or deploy.** The current user must explicitly authorize any such operation separately. The repo owner must separately decide how to supply the reference pack, permitted content and human field expectations. Keep all original source bytes outside Git unless expressly approved.
