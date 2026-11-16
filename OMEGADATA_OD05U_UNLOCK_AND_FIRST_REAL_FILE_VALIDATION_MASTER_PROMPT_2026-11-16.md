# OmegaData OD-05U2: Break the reference-input deadlock and run the first genuinely permitted real-file comparison

**Status:** Proposed execution contract. It is **not** publisher permission, an authenticated source receipt, an owner signature, a command to download market data, or a production release authorization.

**Date:** 2026-11-16. **Repository:** `PrivateAccount-01/omega-system---phase-1`.
**Branch:** `feature/od01-source-rights`. **Verified GitHub HEAD at preparation:** `0d43a43a7df2a997b394269d6a9ebf1e64a00de1`. Recheck before execution; preserve newer code if HEAD moves.
**Phase:** `OD05U2_BOUNDED_REAL_REFERENCE_REVIEW_AND_OFFLINE_COMPARISON_ONLY`.
**Prior status:** OD05T metadata engineering technical pass; OD05U real acceptance blocked. The earlier OD04 process exception was separately decided; do **not** start that loop again.

## 0. Objectives and non-negotiable truth conditions

The task is to move from **3,626 verified local NSE-CM metadata manifests / 0 independently verified market rows** to an actual measurable, legally permissible real-file validation result. Do **not** manufacture prices, symbols, dividends, volumes, historical sessions, expected rows, publisher receipts, reviewer approvals, or usage rights. No generated synthetic financial data may contribute to any real-financial score. Existing synthetic regression suites may still run separately as engineering checks.

The previous instructions inadvertently created a circular dependency: they demanded a frozen human-reviewed expected-row corpus **before even permitting an authorized person to inspect the real source ZIP**. Separate the stages. A reviewer can transcribe and independently verify rows directly from a permitted original source **after rights clearance and before seeing or running the Omega production parser**. This is independent *of the parser*, but not independent *of the publisher source*, and does not itself establish publisher authenticity or exchange rights.

**Do not repeat the OD05U metadata-only note.** Deliver concrete evidence and executable results for all stages that actual inputs allow. If rights cannot be established, complete permitted official-document reconciliation and a minimal source-rights/receipt request, then stop with only the irreducible missing permission; no fresh enormous pseudo-implementation dossier.

## 1. Grounded facts, sources and limits

Read `AGENTS.md`, `OMEGADATA_AGENTS.md`, `docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md`, OD05/OD05R/OD05S/OD05T reports, `docs/omegadata_v2/implementation/od05u/20261116T123744Z/evidence-resolution-gate.md` if present, and any newer owner instructions. Verify branch/HEAD, clean tracked files, candidate metadata and source-rights status. Never open private keys or ignore untracked owner data.

**Candidate only:** `data/raw/nse_equity_bhavcopy/year=2024/month=07/20240723__6e7b99b88b17.zip`. Prior IDE `Get-Item` reported 165,041 bytes and an adjacent manifest. The archive itself was **not** opened or hashed; neither its content nor issuer is yet authenticated. Treat that byte length as an IDE observation to confirm, not a built-in trusted constant.

**Prior documentation:** The IDE obtained official-hosted `https://nsearchives.nseindia.com/web/sites/default/files/inline-files/MSD62142.zip`, circular **NSE/MSD/62142 (22 May 2024)**, containing `Annexure C_UDiFF trade and Bhavcopy file formats.xlsx` and `Annexure B_UDiFF Catalogue_Ver2.0.xlsx`. This is an official-URL **document-origin lead**, not automatic proof it is the final specification applicable to 23 July. The IDE noted a potential `.csv.gz` internal naming versus `.zip` report product difference; resolve by original amended documentation and real ZIP structure, not guesses. The newest currently linked forms page is updated later and must not be retro-applied to 2024.

**Official public links** (documentation only; they do not grant market-data rights):
- NSE forms and historical UDiFF circular index: https://www.nseindia.com/static/resources/forms-formats-members
- NSE reports and discontinuation notice: https://www.nseindia.com/all-reports/
- NSE 2024 documentation archive: https://nsearchives.nseindia.com/web/sites/default/files/inline-files/MSD62142.zip
- NSE market-data usage policy: https://betanseapi.nseindia.com/static/market-data/nse-data-policy
- NSE noncommercial research route: https://betanseapi.nseindia.com/static/research/initiatives-data-for-research
- NSE market-data subscription/contact: https://betanseapi.nseindia.com/static/market-data/eod-historical-data-subscription
- Official NSE MCP, if researched as an alternative, says informational/noncommercial only: https://www.nseindia.com/nse-mcp . Do not infer permission to train AI or operate a commercial/trading system.

NSE official reports state old CM Bhavcopy and Common Bhavcopy CSV reports were discontinued effective **8 July 2024**, directing users to **CM-UDiFF Common Bhavcopy Final (ZIP)**, referring to 12 June 2024 circular `NSE/MSD/62424`. That does not prove that the candidate byte contents match this product, exact format version, member name or trading session. Resolve `62142`, `62424`, and any intermediate effective amendments by authentic bytes when legally accessible; log contradictory or unknown claims.

Current repository has **13 pending source policies, 0 approved** per prior evidence. Do not modify those policies or treat the owner's project role as exchange permission.

## 2. Owner input contract (single private manifest, no made-up answers)

Accept a **separate private** `od05u_owner_pack.json` based on `OMEGADATA_OD05U_PRIVATE_OWNER_PACK_TEMPLATE_2026-11-16.json`, located outside Git and outside publisher payload directories. This file is a *request/attestation record*, not a self-executing trust root or an NSE licence.

It specifies:

- `candidate_local_path`, `nomination_confirmed_by_owner`, owner identity and actual date; no fabricated backdate.
- Actual `local_operations_approved_by_owner`: metadata check; SHA-256/hash; ZIP member inventory; privately bounded original row review; private temporary copy; local parser comparison; private retention. Each must be separately selected. Absent means not authorized by owner.
- `publisher_rights_evidence_path` plus an actually reviewed legal/contract/terms applicability record. If absent, record `RIGHTS_UNRESOLVED` and **do not** read market payload bytes. Owner authorization alone is insufficient.
- `original_receipt_path` and pre-existing independent provenance pins **if genuinely available**. If no download receipt exists, record `NOT_AVAILABLE`, never create a fictional earlier receipt. A newly computed SHA is `CURRENT_SHA256_ONLY`.
- `format_document_local_path`, official publisher URL, document version and effective-date evidence; applicable 2024 amendments.
- `independent_expected_rows_path`, reviewer name/role/date/method, specifically separate from the Omega parser. Rows are allowed to be created in an initial **authorized independent review stage**; they need not exist before permission-cleared inspection.
- Allowed purpose: `PRIVATE_NONCOMMERCIAL_RESEARCH` only when genuine rights evidence covers that purpose; `COMMERCIAL_QUANT_RESEARCH`, `TRADING`, `AI_TRAINING`, `REDISTRIBUTION` each separately restricted until explicit rights evidence covers it. Do not broaden an academic grant into Omega's commercial future.

If owner has not supplied permission evidence, emit one concise `RIGHTS_PENDING` checkpoint and a ready-to-send enquiry to `marketdata@nse.co.in`. Do not assume a fee-free outcome. For a genuine academic-only request, `nseri@nse.co.in` and NSE's research route may be appropriate, but such permission must **not** be used as trading/commercial authorization.

## 3. Phase A: permissions and source-document reconciliation (no market payload read)

A1. Confirm repository/branch/current HEAD and the exact candidate filename/size/manifest metadata without opening the candidate ZIP. Inspect named private permission paths **only if owner permits** and keep sensitive terms out of public logs. Do not open or hash secret/signing paths.

A2. Verify rights evidence per operation: local hash, read, parse, temporary copy, retention, derivative research, trading use, redistribution and publication. Unknown = not allowed for this run; no self-approval through a claimed `APPROVED` string.

A3. Obtain/read only lawfully accessible **public documentation** from first-party issuer links with bounded redirects, bytes and timeouts. Record actual final URL, retrieval UTC, byte length, SHA-256, format, version, issuer and the documentation scope. No restricted market-data API requests or anti-bot workarounds. If a document cannot be retrieved, record `UNAVAILABLE`; a search index excerpt is not full document authentication.

A4. Build minimal chronological spec lineage: `59875` Dec 2023, `62142` May 22 2024, `62424` Jun 12 2024, July 8 discontinued reports and any relevant exact annexure revisions. Track which documents govern report generation vs exchange-member interfaces vs packaging/availability. Preserve unknowns. Do **not** globally change the production 2020 routing.

**A-stage outputs:** compact `documentation-reference-ledger.json`, `rights-and-operations-matrix.json` and exactly one next-action line when blocked. Do not claim rows processed.

## 4. Phase B: authorized identity checks, no interpretation yet

Only after actual owner nomination AND applicable local-payload permission are supplied:

B1. Verify candidate is a regular file within the approved existing data root; refuse symlinks/reparse points/escaping, hard links if dangerous, filesystem ownership surprises, protected paths and concurrent untrusted writer. Do not alter original data. Use a readonly file descriptor and measure current bytes and SHA-256. Compare manifest's recorded checksum *as an untrusted claim*; separately preserve observed SHA. Disagreement is a real anomaly; do not rewrite manifest.

B2. If private disposable copying is separately permitted, make one byte-exact copy inside approved private output root, and rehash it. If not, run permitted hash/read-only operations without copying.

B3. Inventory ZIP central directory **read-only** under small fixed decompression/entry-count/size/ratio budget, reject unsafe names, duplicate members, nested archives, zip bombs, encryption, odd codecs, CRC failure, incompatible member count. **No extract-to-arbitrary-folder**. Preserve internal member names as confidential if needed.

B4. Record `CURRENT_FILE_INTEGRITY_VERIFIED` only if actually verified. Record `PUBLISHER_ORIGIN_VERIFIED` only if independent issuer/acquisition evidence ties this exact file to NSE, not because the URL looks familiar or its SHA matches its local manifest. If original receipt missing: `PUBLISHER_ORIGIN_UNVERIFIED` even if later schema matches.

B5. No public release, machine source-rights promotion or ingestion job. Keep every result in private reports with no row payload leakage.

## 5. Phase C: create a *genuinely independent* expected-row reference after authorized read

This resolves the deadlock. It is legal/operationally conditional; **not** a bypass of rights.

C1. Authorized reviewer opens the permitted original read-only in a separate tool (spreadsheet/text/standard ZIP viewer), **not** the new or existing Omega parser, and records exact source field names, member names, record ordinals, quoted CSV behavior, original lexemes and explicit NULL/absent values. Never infer ISINs, scrip-code leading zeros or special session status.

C2. Select a predeclared deterministic stratified sample of e.g. up to 20 legitimate real rows if the file contains enough: first nonheader data record, last valid record, high- and zero-volume if they exist, distinct series if any, identifiers with leading zeros if any, extreme OHLC if any; document selections that do not exist. Use the exact file, not fabricated test rows. Optionally count all real records independently if feasible under bounds. Preserve order and proper handling of quoted newlines.

C3. Reviewer signs off **actual** name, date/time, review method, source hash, format document and specific fields. Freeze a separate `expected_rows.json` before running Omega's real parser. If reviewer unavailable, non-Omega inspection may still yield provisional parsed rows, but cannot be scored as independently verified. Do not assign that reviewer identity to the agent or invent it.

C4. Separate *two kinds of independence*: (1) row expectations are independent of Omega's parser (even if transcribed from same original permitted file), versus (2) separate publisher/source origin corroboration. Claim only the first when that's all that exists. For stronger numerical validation, independently confirm selected records against a separate lawfully accessible issuer source or another authorized source with explicit comparison semantics.

C5. Expected-row file may remain private and contain actual source values, never in Git. A sealed digest of private expectations may appear in public audit, but only when privacy/data terms allow.

## 6. Phase D: exact bounded real-format parser and measured comparison

Only after B and a verified applicable 2024 schema C reference are present, and after expected rows are independently frozen for any numerical PASS claim:

D1. Freeze negative-first tests specific to **genuine permitted** original file. Map semantic columns using the applicable 2024 version; reject ambiguous ZIP/CSV/GZ packaging rather than silently treating a `.zip` wrapper as the 2024 `.csv.gz` schema. No hardcoded 2026 header. Preserve original raw SHA, actual filename/member format, row ordinals, `Decimal` OHLC and exact unsigned integer volume and original lexemes. Ignore only documented permissible optional columns; keep unexpected columns inert.

D2. Reuse OD05 parser contracts/OD05R reference verifier only where semantics are demonstrably compatible. Implement an additive, opt-in **2024-07-23 only** adapter if necessary. Do not touch current production `source_registry.py`, acquisition, warehouse, signals, Parquet, raw archive or policy files without separately authorized exact scope. No fabricated sample rows or default production route.

D3. Execute failure tests: wrong raw hash, invalid ZIP, wrong member, unsupported compression, duplicate columns, incorrect date, nonfinite/rounding/negative prices, overflow/negative volume, series collision, missing source permission, reference version mismatch, archive/payload alteration, mismatched expected row, unsafe source path, no writes. For tests needing corruption, mutate byte arrays **only in disposable test copies**. Label these as adversarial engineering inputs, not synthetic market performance observations.

D4. Run independent expectations against actual parsed rows; record every matched/mismatched field, original literal and parsed precision only in private logs. Field mismatch denominator = number of source fields actually independently verified, not all unexamined rows. Count source real rows, sampled rows, unreviewed rows, duplicate instruments, rejected rows, source schema mismatches, missing independently known sessions, and unknown PIT. Do not claim 100% data completeness because 20/20 sampled rows match.

D5. Three-runtime guarded regression (Windows 3.14, Windows 3.11, Linux 3.12) only on permitted temporary private copies; record absolute Python executable, exact command, exit, test node counts, skip pairs, Ruff, mypy, pip, compilation and SHA of each input. If native Linux copy is disallowed by rights, mark that part `BLOCKED_RIGHTS`; do not invent green results.

## 7. Precise acceptance states (NEVER collapse)

Use separate status axes:

- `SOFTWARE_ENGINEERING`: PASS / FAIL / NOT_RUN.
- `MARKET_PAYLOAD_ACCESS`: NOT_AUTHORIZED / HASH_ONLY_AUTHORIZED / ROW_INSPECTION_AUTHORIZED.
- `LOCAL_BYTE_INTEGRITY`: VERIFIED_CURRENT_SHA / MISMATCH / NOT_RUN.
- `PUBLISHER_PROVENANCE`: NSE_AUTHENTICATED_INDEPENDENTLY / UNVERIFIED / CONFLICT.
- `FORMAT_APPLICABILITY_2024`: AUTHENTIC_DOCUMENT_AND_SCOPE_VERIFIED / PENDING / CONFLICT.
- `EXPECTED_ROW_REVIEW`: HUMAN_REVIEWED_FROZEN / PROVISIONAL_PARSER_INDEPENDENT / NOT_SUPPLIED.
- `REAL_PARSER_COMPARISON`: REAL_ROWS_MATCHED(n) / MISMATCHES(n) / BLOCKED.
- `RIGHTS`: PERMITTED_FOR_SPECIFIED_OPERATION / UNRESOLVED / DENIED.
- `PIT`: VERIFIED / UNKNOWN.
- `PRODUCTION_RELEASE`: NOT_AUTHORIZED (always this phase).

`PUBLISHER_PROVENANCE` and `RIGHTS` must both be verified before anyone calls a result **official, lawful, production-grade real NSE market data**. A successful comparison of privately held unproven files is useful but must be labeled `REAL_LOCAL_INPUT_COMPARISON_ONLY`, *not* `AUTHENTIC_NSE_CORRECTNESS_PASS`.

## 8. Specific test categories and stop rules

**R01–R05 Source and rights:** authentic local file nomination, documented local operation rights, original receipt/provenance, independent current bytes vs pin comparison, guarded private copying where permitted.

**R06–R09 Historical specification:** old/current versions separated, `62142` and `62424` scope checked, exact 2024 schema and ZIP member/payload encoding matched, unsupported 2020 claims refused.

**R10–R14 Independent row reference:** reviewer/row-oracle separation, literal Decimal and volume, date semantics, identity and distinct series/ISIN, expected rows frozen before parser run.

**R15–R18 Security and regression:** path/ZIP/CSV hostile cases, no side effects, cross-platform unchanged old tests, reference/permission revocation response.

**R19–R20 Scorecard and Gatekeeper:** non-vacuous denominator/mismatch counts; no positive labels on missing real data, source rights or provenance.

If rights **absent**, run R01/R02 as meta-checks only, stop; do not execute R03–R20 or record them PASS. If rights exist but provenance absent, authorized inspection may proceed with origin `UNVERIFIED`; official source certification remains BLOCKED. If expected rows cannot be independently reviewed, present only raw-file structural parsing and mark financial comparison blocked, not full project success.

## 9. Deliverables and preservation

Only create new phase-owned source/test files if justified by actual authorized access; no repo churn for a blocked gate. Place private inputs/outputs **outside Git**. Reports may include:

1. `00_actual_owner_rights_decision.md` with verified rights scope and missing bits (redacted).
2. `01_document_version_and_issuer_ledger.md` for May/June/July 2024, original source hashes (when obtained).
3. `02_real_file_integrity_and_structure.json` with actual SHA, current length, member count, format and independent receipt status.
4. `03_independent_review_procedure.md` and a separate private immutable expected-row digest.
5. `04_real_parser_comparison.json` with real denominators and honest missing fields.
6. `05_cross_platform_regression.md` with exact logs only when executed.
7. `06_gatekeeper.json` with all axes in §7; one concrete next input/action.

Every prior OD04/OD05/OD05R/OD05S/OD05T report, signing item, rights policy, archive, database and release path remains unchanged. No network acquisition of restricted market data, no paid subscriptions, no data migration, no auto-trading, no CI/push/merge/OD06 without separate user approval.

## 10. Mandatory reply shape and no-loop instruction

At completion report:

```
Reviewed HEAD: <actual>
Candidate: <actual or absent>
Owner nomination: YES / NOT_SUPPLIED
Exchange/local rights: PERMITTED_BY_EVIDENCE(path,scope) / UNRESOLVED / DENIED
Publisher 2024 documents: <exact original docs/versions, or indexed-only>
Market ZIP opened: YES / NO
Market ZIP hashed: <actual SHA or NOT_RUN>
Market rows inspected: <number actually inspected>
Independently reviewed real rows: <number, reviewer evidence or ZERO>
Real field comparisons: <actual numerator>/<actual denominator or NOT_RUN>
Source provenance: independently authenticated / unverified
Technical verdict: <actual>
Real financial verdict: <actual>
Single next owner action: <only the irreducible item>
```

Do not ask the owner to provide row expectations **before** allowing a separately authorized reviewer to construct them from the original file, and do not allow agents to certify their own outputs. Do not repeatedly ask for a receipt the owner reports does not exist; report source origin unverified and present options for genuine corroboration or a different authorized source. Stop after OD05U2; no automatic OD06.
