# OmegaData OD-05U: Resolve Authentic NSE Reference Evidence and Execute First Real-Data Verification

**Document status:** Proposed Codex handoff, not permission to inspect restricted data, waive usage terms, alter source-rights policies, or advance to OD-06.  
**Date prepared:** 2026-11-16  
**Repository:** `PrivateAccount-01/omega-system---phase-1`  
**Branch:** `feature/od01-source-rights`  
**IDE-reviewed starting commit:** `0d43a43a7df2a997b394269d6a9ebf1e64a00de1` (verify live HEAD before acting).  
**Execution:** `OD05U_OWNER_EVIDENCE_RESOLUTION_THEN_SINGLE_AUTHORIZED_REAL_FILE_VERIFICATION_ONLY`.  
**Candidate for owner nomination:** `data/raw/nse_equity_bhavcopy/year=2024/month=07/20240723__6e7b99b88b17.zip` (165,041 bytes according to the IDE's directory metadata). **Candidate identification is not owner nomination or authorization.**

## 1. Hard objective

Conclude OD-05U with either (A) a genuinely authorized and authenticated historical NSE CM file validated against human-reviewed independent row expectations, or (B) a precise `BLOCKED_REAL_DATA` result with the smallest missing owner inputs. Do not mistake a code test, a source URL, a file name, a publisher webpage, or a file hash for financial authenticity or licensing.

Previous IDE output established a candidate 2024-07-23 ZIP by *directory metadata and its manifest only*: its bytes were not opened; no row was verified. OD-05T already delivered a successful read-only metadata CLI and a separate metadata test gate. Do not rerun another general metadata phase. Do not regenerate any synthetic prices, securities, volumes, returns, corporate actions, or purportedly official sample records. Existing software regression fixtures may remain for engineering safety and are counted separately.

## 2. Read controlling instructions and establish ground truth

Read `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, and the prior OD-05S, OD-05T and OD-05U Gatekeeper reports and owner pack requirements. Verify branch, current HEAD, index/worktree, original archive file identity at the OS **metadata-only** level, the exact manifest and source policy applicable to NSE equity bhavcopy. Discrepancies from the recorded commit trigger re-review, not blind use of historic hashes. Preserve all existing data, signatures, secrets, tests, policies, releases, prior evidence, and commit history.

Identify the candidate and verify that the *path* and filename are not merely an invented location. Record whether the owner's explicit nomination and permission to use that file exist. **No payload reads, hashes, ZIP listing, decompression or extraction before the required permission gate**. Even SHA-256 calculation reads the bytes and is therefore prohibited until permission for the proposed inspection has been established. Never read signing keys or private/revocation files.

## 3. Non-payload work allowed immediately

Do the following without touching historical market-data payloads:

- Examine the existing manifest's recorded source identity, time, acquisition mode and source-rights status as **claims**. Keep fields tagged `UNVERIFIED` until corroborated. Do not display private URLs, query tokens or absolute local paths in public logs.
- Read and catalog **lawfully accessible** public NSE technical documentation pages and circular metadata, without evading access restrictions or automatically acquiring restricted market data. Distinguish documentation consultation from market-data access.
- Open the official NSE Forms & Formats web page and identify the Capital Market (CM) UDiFF Bhavcopy **format document**, **test-file links**, catalog versions and relevant circulars; identify 2024 historical revisions applicable to the 2024-07-23 market business date. The currently linked format spreadsheet was updated in June 2026; do **not** silently assign 2026 schema rules to the 2024 file.
- Independently establish whether the 2024-07-23 file is intended to be legacy CM CSV, common bhavcopy, UDiFF ZIP, or still unknown. An NSE all-reports discontinuation notice says older CSV CM bhavcopy variants were discontinued effective 2024-07-08, but that notice alone does not establish the complete field schema, every availability overlap, timestamp semantics or actual file authenticity.
- Search **authorized existing local reference folders only**, using filename and file metadata first, for matching original specifications, publisher provenance, use-rights records, independent pin manifests and reviewed expected values. Do not silently infer permission from a present file, a seeded cache or a prior agent log.
- Identify exact missing artifacts in a compact owner handoff. Do not create another massive evidence dump that obscures the single blocker.

Authoritative public starting points (these URLs are documentation leads, not rights or row validation):

- NSE CM UDiFF Forms & Formats: https://www.nseindia.com/static/resources/forms-formats-members
- NSE historical reports/discontinuation notes: https://www.nseindia.com/all-reports/
- NSE data sharing and usage policy: https://betanseapi.nseindia.com/static/market-data/nse-data-policy
- NSE approved non-commercial academic research access: https://betanseapi.nseindia.com/static/research/initiatives-data-for-research
- NSE paid/historical market-data information: https://www.nseindia.com/static/market-data/eod-historical-data-subscription

These sites have different scopes. An academic/non-commercial research access route is **not** permission for Omega's future trading/profit-generating use. Contact `marketdata@nse.co.in` for the applicable licensed commercial or systematic research use if existing permissions do not cover it; academic requests may use `nseri@nse.co.in` **only** if the stated project use genuinely qualifies. No purchases, subscriptions or contact messages without explicit owner instruction. No use of third-party mirrors to fabricate issuer authenticity.

## 4. Exact owner-supplied evidence pack (private, outside Git)

Record the following four components as independent fields, with actual paths and actual evidence. Unknown fields remain `null` or `NOT_SUPPLIED`, never silently populated.

**A. Actual market file and provenance:** Explicit owner nomination of the 2024-07-23 ZIP (or another real file), exact local file path, issuer/source name, original publisher URL if known, acquisition/receipt/channel/date, original file name and byte length, independently recorded historical checksum if it exists, and what independent publisher receipt or original reference establishes origin. An SHA computed for the first time now is a **new current integrity observation**, not an invented historical independent pin. If no independent origin receipt exists, record `PUBLISHER_ORIGIN_UNVERIFIED`.

**B. Scoped market-data permission:** Evidence of authorization for **local inspection, parsing, retained copies and research usage** for this specific file and purpose. Explicit project-owner authorization to work on the private file does not create third-party publisher rights. Preserve restrictions for derivative use, publication, redistribution and future trading, each separately. The 13 existing source policies must not be flipped from `PENDING_REVIEW` through self-authored metadata. No broad assertions of fair use or open access.

**C. Matching publisher specification:** Original lawfully held NSE CM technical specification/circular/annexure applicable to the file's 2024 date with version, publisher URL/receipt, document bytes SHA/length observed lawfully, effective-scope evidence, and precise column/units/ZIP member/date/identity definitions. Do not substitute a later 2026 version without separately proving applicability to the earlier observation.

**D. Independent expected rows:** A separately authored, human-reviewed and dated expectation table produced from *lawfully available genuine source records and publisher specifications*, not from Omega's parser output. Use exact literal identifiers (symbol, series, ISIN where present), actual trade/business dates, original price lexemes, volume lexeme, interpreted units, ZIP member, original data-record ordinal, expected row count where independent, and documented reviewer identity and method. If legal restrictions prevent raw-value reproduction in logs, keep expectations private and emit only comparisons and limited non-sensitive mismatch codes. A reviewer copying values directly from an authentic source file independently of Omega's parser can provide an independent **parser check**, but does not by itself authenticate publisher origin or provide independent cross-source corroboration.

**Optional PIT evidence:** Actual publication timestamp/timezone, document version availability time, first observed timestamp and any exchange corrections. Missing PIT evidence means `PIT_UNVERIFIED`, even if rows match.

## 5. Strict gate and honest execution states

The states are distinct:

1. `CANDIDATE_METADATA_IDENTIFIED`: filename and size only; payload not opened.
2. `PAYLOAD_INSPECTION_AUTHORIZED`: precise rights and project-owner read-only authority confirmed for the intended operation; no authenticity implied.
3. `CURRENT_FILE_INTEGRITY_VERIFIED`: authorized file bytes hashed and independently rehashed in guarded private read-only environment. A matching manifest hash proves integrity relative to that manifest, not publisher provenance.
4. `PUBLISHER_ORIGIN_VERIFIED`: independent publisher receipt/source evidence sufficient to link this exact original file to NSE (not a local self-declaration).
5. `FORMAT_REFERENCE_VERIFIED`: applicable original document/version/format semantics independently checked, with permissions.
6. `REAL_ROWS_PARSER_VERIFIED`: an actual human-reviewed comparator finds the specified genuine row values, identity and units match; count real checked rows and mismatches.
7. `RESEARCH_USE_AUTHORIZED`: precise use rights documented. This is **separate** from format correctness and from future production, trading and redistribution rights.
8. `PIT_VERIFIED` and `RELEASE_ELIGIBLE`: separate later gates, never granted by this task.

If A, B, C or D is absent, report exact missing fields, keep `BLOCKED_REFERENCE` / `BLOCKED_REAL_DATA`, and stop before opening market payloads. If permission to hash exists but authenticity/reference/expectations are missing, perform only the explicitly authorized integrity operation, then stop without financial-accuracy claims. In no case grant approvals from self-authored machine JSON, public listing alone, cached URLs or LLM assertions.

## 6. Conditional *minimal* real-file verification (only after valid A+B+C+D)

- Freeze exact real corpus/document/expected-value identities before implementation or execution. Store sensitive payloads off Git, in an owner-approved private directory. Code may be committed only separately with explicit permission and no restricted payloads.
- Use existing OD-05/05R/05T rights-aware archive and parser APIs where their assumptions are actually verified. Make the smallest additive, opt-in real-format adapter needed for the confirmed specific version. No changes to production source registry or acquisition routing.
- Use single-file, read-only, bounded streaming in a disposable sandbox. Reject ZIP member traversal, duplicate names, symlinks, over-expansion, malicious compression ratios, unsafe codecs, huge rows, Unicode/CSV ambiguity and source-version mismatch. Do not extract raw data to uncontrolled paths.
- Derive canonical values using exact Decimal/integer handling without float coercion. Distinguish market-trade date, business date, report publication date and ingestion time. Preserve original lexemes, full raw SHA and parser/reference versions.
- Compare each reviewed row to an *independent* frozen expectation source; record mismatches by field and original data-record ordinal. Any unverified fields or row values remain UNKNOWN. A parser successfully reading a file does not imply financial accuracy.
- Execute the applicable OD-05U R01-R20 acceptance checks, plus an independent comparator, tampering and missing-reference refusals, source-rights checks and cross-platform regression on authorized private disposable copies only. Report actual commands/exits/skip counts, not planned green claims.
- No live NSE requests, bypasses, production data rewrites, price adjustments, release/signing actions, new paid tools or OD-06 implementation.

## 7. Evidence and numerical scorecard

Produce exactly one bounded OD-05U review directory (unless gate-blocked, where one compact blocker note suffices), containing:

- `00_owner_authority_and_rights.md`: actual authenticated evidence, scope, remaining restrictions; never invent signatures or legal determinations.
- `01_source_and_schema_evidence.md`: 2024 publisher specification and circular lineage, raw vs reference hashes, any version/era ambiguity.
- `02_real_file_and_row_oracle.md`: original file count, independently reviewed expected row count, actual parsed row count, correct/incorrect comparisons, exact precision; private raw values not committed.
- `03_adversarial_tests_and_runtime.md`: exact negative-first chronology and three-runtime results only if tests actually ran.
- `04_real_data_scorecard.json`: `authentic_market_files_independently_verified`, `market_records_inspected`, `market_records_independently_verified`, `field_mismatches`, `rows_with_any_mismatch`, `rejected_records`, `completeness_denominator`, `completeness_coverage`, `PIT_status`, `legal_rights_status`, `synthetic_acceptance_contribution=0`. Unknown values remain `null`.
- `05_gatekeeper_verdict.md`: separate `ENGINEERING` and `REAL_FINANCIAL` statuses. Do not call a blocked result PASS.
- `06_single_next_action.md`: one actionable owner next step, not another automatic later phase.

Never overwrite the existing OD-05T and earlier reports. No commit/push/PR/deploy without explicit owner approval. No private data, restricted documents, confidential receipt records or personal signatures in public GitHub evidence.

## 8. Expected final answer from Codex

Report: current branch/HEAD, whether the owner has *actually* nominated the local file, whether existing scoped permissions apply, public original documentation references discovered and verified (by original issuer source), exact local missing paths/values (redacted where appropriate), whether the payload was accessed, whether any real financial row was independently verified, what commands actually ran and the sole next owner action. Do not ask to bypass rights. Do not create synthetic market values. Stop at OD-05U.

**Critical instruction:** A lack of historical independent publisher receipt cannot be repaired by hashing the same local ZIP today. If no such evidence exists, record `PUBLISHER_ORIGIN_UNVERIFIED` and request an authentic replacement/reference or independently corroborating source; do not manufacture proof of source authenticity.
