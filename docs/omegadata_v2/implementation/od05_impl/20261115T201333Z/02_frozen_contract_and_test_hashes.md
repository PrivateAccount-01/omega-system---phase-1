OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY; run 20261115T201333Z. Evaluated 2026-11-16T08:23:11.592393+00:00. Branch feature/od01-source-rights; unchanged local HEAD bf6f4894c9e5237e8c1a44b625c66b8a420b4aad. RUN=new executed checks; TEST/SYN=synthetic fixtures; ARCH=prior evidence; UNK=unverified official semantics. Same-model procedural review, not independent human/financial/legal certification.

# Frozen tests and honest chronology

All T01–T32 function groups existed before parser package creation. [Initial freeze](logs/preimplementation-freeze-initial.json), [complete pre-code freeze](logs/preimplementation-freeze.json). First baseline: 75 setup errors (API absent). Before application creation, corrected anticipated harness exception types and added revoked/purpose/pinned archive cases: 78 setup errors, API absent, exit1. Neither result proves an old financial defect; no old implementation file was changed. First implementation then passed all78.

Post-initial review added14 cases:89pass/3fail. Reproduced new-code issues: in-memory forged archive pin accepted; archive facade missing consumer purpose; decoded-size cap omitted for plain CSV. Minimal new-module corrections gave92pass. Later two cases: volume lexeme absent (one failure) and explicit synthetic2020 legacy selection (one pass); corrected only ParsedBar/new decoder to preserve volume_lexeme. Final94cases pass each runtime. These later cases are explicitly not pre-initial-implementation tests. Ruff-only import/literal/format changes also changed test bytes after the initial freeze; assertions were not weakened. Initial/final hashes and all failed logs retained.

T32 includes the replay vector plus external three-runtime collection/full/lint/type/package/coverage evidence; a passing unit function alone never proves T32 complete. REF-dependent subcases remain BLOCKED_REFERENCE; synthetic analogues are not official substitute successes. Independent expected-row/hash algorithm was authored and hashed before application code; serialized vector outputs were recorded later, not backdated.

Public contracts: frozen ParseRequest with source/date/full SHA/mode/format/parser/reference/optional observation/count; frozen exact Decimal/int ParsedBar with source/identity/row ordinal/trade/business dates, original price and volume lexemes, inert unknown fields and null publication; frozen ParseResult with refusal codes, raw/semantic hashes, columns and parser/reference identity. Only SYNTHETIC_TEST_ONLY input and syn-v1/synthetic-v1 contracts accepted. Protected pinned reads are separate from in-memory parsing.

Testing strategy: pure Python library, no UI/service/containers needed. Journeys: exact decode/replay; hostile refusal/file-wide quarantine; rights-aware pinned archive read; origin non-escalation; legacy regression. Existing guarded pytest runners use only disposable SQLite/raw/parquet/release roots; no service startup/browser tier applies to this additive library. All existing tests retained, not migrated/rewritten. DNS/TCP/UDP/subprocess and protected writes denied during collection/execution. Windows file-link privileges and Linux junction skips require actual opposite-platform counterparts. [Exact group/test/result mapping](logs/32-group-results.json), [final freeze](logs/final-source-freeze.json).
- T01: test_t01_identity, test_t01_later_expected_count
- T02: test_t02_determinism
- T03: test_t03_revisions
- T04: test_t04_legacy
- T05: test_t05_disputed_dates_explicit_only, test_t05_later_explicit_synthetic_2020_profile
- T06: test_t06_ambiguity
- T07: test_t07_modern_zip
- T08: test_t08_dispatch
- T09: test_t09_bse
- T10: test_t10_official_flag
- T11: test_t11_headers
- T12: test_t12_csv
- T13: test_t13_zip, test_t13_later_zip_variants
- T14: test_t14_denial_empty
- T15: test_t15_dates
- T16: test_t16_volume, test_t16_later_volume_lexeme
- T17: test_t17_exact_decimal_context
- T18: test_t18_prices
- T19: test_t19_identity
- T20: test_t20_text
- T21: test_t21_optional_identity
- T22: test_t22_temporal
- T23: test_t23_raw_and_observation, test_t23_verified_synthetic_archive, test_t23_later_in_memory_cannot_claim_archive_pin
- T24: test_t24_origin
- T25: test_t25_rights, test_t25_revocation_scope, test_t25_later_archive_purpose_is_mandatory
- T26: test_t26_no_io
- T27: test_t27_oracle_digest
- T28: test_t28_no_production_adapter
- T29: test_t29_newline_metadata
- T30: test_t30_limits, test_t30_later_plain_csv_expansion_budget
- T31: test_t31_independent_oracle_and_tamper, test_t31_later_all_fields_modern_and_date
- T32: test_t32_replay_vector
