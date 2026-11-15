# Proposed versioned parser contract and implementation plan

Run20261115T190654Z; audit/plan only @bbc38716d902fe27192f80affaca29c6f51e9890. RUN static findings; ARCH inherited code/tests; TEST/SYN future fixtures; UNK official semantics. Same-model design review. ADR-OD05-001 status **PROPOSED**, not accepted.

## Smallest prospective architecture

New pure modules only after owner exception, separate implementation authorization and approved reference/synthetic scope: proposed parsers/contracts.py, dispatch.py, nse_cm.py and references.py; BSE parser deferred unless its separate proof gate closes. Reuse stdlib csv/zipfile/hashlib/Decimal/date and existing frozen Pydantic conventions. No DB, filesystem writer, network client or wall-clock dependency in the pure parser. No new package required by this plan.

ParseRequest freezes source key, business date, exact raw SHA, raw observation ID if pinned, explicit format ID, requested parser version and reference ID/version. Do not select by guessed year, suffix or header alone. Dispatch requires source+format+reference coverage; unknown/overlapping/unsupported versions return ERA_UNKNOWN/REFERENCE_PENDING/VERSION_UNSUPPORTED. Immutable original archive capture-era labels remain historical metadata; new interpretation has separate version/reference lineage. Never rewrite old observations to repair an old label.

ParsedBar retains source/exchange/date, exact text symbol/series/ISIN/scrip identity, source row index, Decimal OHLC and bounded integer volume, plus inert raw optional/unknown fields or manifest. Do not infer missing identity, adjusted prices, units or publication time. ParseResult has immutable row/quarantine tuples, raw hash, parser/schema/reference identities, original field manifest and canonical semantic hash. Operational timestamps excluded. Distinguish PARSED_UNVERIFIED from SCHEMA_REFERENCE_VERIFIED and financial reconciliation; strings alone cannot grant an official state.

Validate exact input digest before parse, reject duplicate/colliding headers and malformed quoting/field counts; preserve benign unknown columns without treating them as trading features. Exact finite numeric lexemes, no float conversion/locale/comma guessing/empty-to-zero; freeze digit/exponent/volume ceilings with the supported specification. OHLC and legitimate zero-volume rules per evidenced format. Keep trade/business/publication/observation time meanings distinct. File-level failure must not present partial trusted success. Strict bounded ZIP membership/path/symlink/expansion/candidate/row/byte budgets reused where correct, not blindly duplicated.

Protected archive bytes are obtained through existing rights-aware pinned read_verified(source,date,purpose) before the pure call; synthetic in-memory bytes remain explicitly SYNTHETIC_TEST_ONLY. No implicit latest or cached policy override. Parser acceptance cannot establish PIT eligibility; unknown published_at remains unknown.

Proposed public errors: ERA_UNKNOWN,REFERENCE_PENDING,SCHEMA_UNKNOWN,HEADER_DUPLICATE,DATE_MISMATCH,CSV_INVALID,ZIP_INVALID,ROW_INVALID,PRICE_INVALID,VOLUME_INVALID,IDENTITY_AMBIGUOUS,RAW_HASH_MISMATCH,SOURCE_SCOPE_DENIED,VERSION_UNSUPPORTED,INTERNAL_PARSER_ERROR. Include bounded row/field location, never raw confidential values or payload excerpts.

## Ordered execution plan after gates, NOT executed

1. Obtain actual named-owner disposition, separately authorize OD05_IMPLEMENT_ONLY on verified SHA and freeze lawful specs/corpus or explicitly permitted partial synthetic scope. Reconcile any subsequent HEAD/user edits.
2. Freeze source/format/reference table, field/date/identity rules, parser contract, exact fixture bytes/hashes and supported versions. No unsupported2020/2024 date substitution.
3. Author **all32 groups** in the proposed new test module plus independent oracle before any application edit; freeze test SHA and run unchanged baseline under protected disposable runners. Classify assertion defects, new APIs, missing references and harness errors separately. No implementation if original gate is incomplete.
4. Implement smallest pure NSE CM parser. Preserve raw bytes and old on-disk v1 formats; no production writer. Unknown/reference-pending formats remain quarantined or explicitly unverified under approved partial scope.
5. Narrow registry/acquisition integration only where red-proven and backed by exact verified reference. Existing raw_archive/downloader edits require reproduced integration defect and documented scope amendment. Legacy loaders unchanged unless explicit default-OFF adapter meets old regression contract; PriceRecord writes excluded from primary output.
6. Independent stdlib oracle consumes separate frozen expected rows/identities/numeric strings, never parser-produced expected values. Compare every field/source-row index and canonical digest.
7. Fresh targeted/full offline collection/regression/Ruff/mypy/pip on Windows3.14.3,Windows3.11.15,native Linux3.12.3; rights/archive/crash regressions and skip pairing. Exact command/time/exits/source hashes, no warning suppression.
8. Same-model adversarial review, preservation, Gatekeeper and STOP. Human legal/financial/security review remains external; no OD06 inferred.

Risk/reversibility: new parser version and default-OFF adapter preserve old consumers and pinned history. No migration/cleanup/GC/re-ingestion. If reference or semantic invariants cannot be proved, quarantine and stop; do not alter old tests or lower validation requirements.
