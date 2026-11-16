OD05R_REFERENCE_AND_PARSER_VERIFICATION_ONLY; run20261116T084526Z; evaluated 2026-11-16T09:18:44.511483+00:00. Branch feature/od01-source-rights; HEAD 2326936860f64cadf4f4c24a968c073114598b26. RUN=fresh commands; TEST/SYN=synthetic; ARCH=prior evidence; REF-DOC=indexed documentary lead only; UNK=unverified. Same-model procedural review, no independent human/legal/financial certification.

# Frozen tests and exact chronology

[Pre-code freeze](logs/preimplementation-freeze.json) at08:52:25UTC binds both new test files before application modules existed; first guarded baseline54API-absence errors, exit1. Missing API is new-feature absence, not a legacy behavioral defect. First implementation53pass/1Windows file-link skip. Later five review tests:55pass/1skip/3fail (root .. traversal, untyped malformed file value, accepted orphan pin). Corrections58pass/1skip. Later two tests reproduced field-semantics conflict misclassified as overlap and mutable expected pins (2fail/59deselected); corrections60pass/1skip. Later tests and scoped Ruff formatting are honestly post-initial-code, never backdated or old-test edits.

Every R01–R24 group existed at freeze, including the external R24 runtime gate represented by a replay vector. [Exact per-node results](logs/R01-R24-results.json) link all current cases and complete runtime metadata. Original frozen SHA and [final freeze](logs/reviewed-source-freeze.json) remain separate. All tests are synthetic; the real OS link/junction cases operate only disposable storage and have passing counterparts.

F01–F12 were declared BLOCKED_REFERENCE in pre-code design: original source SHA, real ZIP/member/schema, era, dates, Decimal, volume units, ordinals, identity, optional columns, reviewed rows, invalid-format negatives, replay/rights/lineage. [F matrix](logs/F01-F12-results.json) counts no official successes. A+B absent; no official-format parser code/fixtures are fabricated. All original OD05 tests/oracle remain byte-identical and pass94cases each runtime.

Initial broad evidence read output was truncated; corrected reads completed remaining numbered reports, and all293prior evidence files were mechanically rehashed. Original inventory was slow but completed read-only; no process was terminated or file overwritten. One new-test patch failed to match formatting and made no edits; corrected patch then executed the negative tests. All executed failing test logs are retained.
- R01: test_r01_absent_empty
- R02: test_r02_json, test_r02_later_unhashable_file
- R03: test_r03_identity
- R04: test_r04_paraphrase
- R05: test_r05_no_caller_authority
- R06: test_r06_rights
- R07: test_r07_document_not_row
- R08: test_r08_sample_not_schema
- R09: test_r09_conflict, test_r09_later_conflicting_field_semantics
- R10: test_r10_dates_overlap
- R11: test_r11_versions
- R12: test_r12_scope
- R13: test_r13_bse_no_inheritance
- R14: test_r14_origin
- R15: test_r15_secret_redaction
- R16: test_r16_bounds
- R17: test_r17_names, test_r17_real_link, test_r17_later_root_traversal, test_r17_later_windows_junction
- R18: test_r18_budgets
- R19: test_r19_pinned_corpus, test_r19_later_orphan_pin, test_r19_later_expected_pins_are_frozen
- R20: test_r20_deterministic
- R21: test_r21_pure
- R22: test_r22_compatibility
- R23: test_r23_oracle_and_tamper, test_r23_later_sample_tamper
- R24: test_r24_runtime_vector
