# Genuine negative-first chronology

The [initial freeze](logs/negative-first-freeze.json) preceded application corrections. Initial run: 27 failed / 7 passed; count-regression expansion before code: 28 failed / 7 passed. Missing harness/v2 APIs are NEW_FEATURE_ABSENT, not legacy defects. W07 independently reproduces the old physical-count discrepancy.

First green attempt: 21 pass / 14 fail from Windows DirEntry identity handling; next focused run 35 pass. Later adversarial tests were written and run before their corresponding corrections: original-boundary 1 fail, private/junction root 2 fail, external-boundary 1 fail. Benign source instructions/new non-market sentinels were used, never actual incident payloads. Existing guard-contract regressions supplied additional failing executable evidence. No retrospective alteration of OD04/OD05V chronology or owner decision.

Final: 39 focused cases execute successfully on each runtime. W04 OS-level acceptance remains BLOCKED despite Python-layer test success. W05 cross-device checks are implemented; a hostile mount-owner/race or live cross-volume mutation experiment was not certified. W15 reports Python operation counts, not kernel syscall tracing. These limitations cannot be self-approved away.

| Group | Executed final nodes |
|---|---|
| W01 | `tests/unit/test_od05w_engineering.py::test_w01_old_helper_and_glob_rejected_before_open` |
| W02 | `tests/unit/test_od05w_engineering.py::test_w02_exact_allowlist` |
| W03 | `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.zip]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.csv]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.parquet]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.db]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[.env]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.key]`; `tests/unit/test_od05w_engineering.py::test_w03_denied_inside_allowed_tree[x.zip.py]` |
| W04 | `tests/unit/test_od05w_engineering.py::test_w04_actual_guard_denials`; `tests/unit/test_od05w_engineering.py::test_w04_original_boundary_covered`; `tests/unit/test_od05w_engineering.py::test_w04_external_retained_copy_boundary` |
| W05 | `tests/unit/test_od05w_engineering.py::test_w05_hardlinked_copy_source_refused`; `tests/unit/test_od05w_engineering.py::test_w05_copy_root_ancestors_refused[private]`; `tests/unit/test_od05w_engineering.py::test_w05_copy_root_ancestors_refused[linked_root]` |
| W06 | `tests/unit/test_od05w_engineering.py::test_w06_historical_incident_immutable` |
| W07 | `tests/unit/test_od05w_engineering.py::test_w07_hardlink_physically_present`; `tests/unit/test_od05w_engineering.py::test_w07_existing_physical_count_defect` |
| W08 | `tests/unit/test_od05w_engineering.py::test_w08_hardlink_mismatch` |
| W09 | `tests/unit/test_od05w_engineering.py::test_w09_presence_not_permission` |
| W10 | `tests/unit/test_od05w_engineering.py::test_w10_fresh_original_ledger` |
| W11 | `tests/unit/test_od05w_engineering.py::test_w11_historical_claims_unchanged` |
| W12 | `tests/unit/test_od05w_engineering.py::test_w12_unsafe_paths[../x.zip]`; `tests/unit/test_od05w_engineering.py::test_w12_unsafe_paths[//host/share/x.zip]`; `tests/unit/test_od05w_engineering.py::test_w12_unsafe_paths[C:/x.zip]`; `tests/unit/test_od05w_engineering.py::test_w12_unsafe_paths[data/raw/x.zip:ads]`; `tests/unit/test_od05w_engineering.py::test_w12_unsafe_paths[DATA/x.zip]` |
| W13 | `tests/unit/test_od05w_engineering.py::test_w13_canonical_digest_and_redaction` |
| W14 | `tests/unit/test_od05w_engineering.py::test_w14_budgets` |
| W15 | `tests/unit/test_od05w_engineering.py::test_w15_profile_without_limit_relaxation` |
| W16 | `tests/unit/test_od05w_engineering.py::test_w16_immutable_observation_invalidated` |
| W17 | `tests/unit/test_od05w_engineering.py::test_w17_native_link_refusal` |
| W18 | `tests/unit/test_od05w_engineering.py::test_w18_canary_not_financial_evidence` |
| W19 | `tests/unit/test_od05w_engineering.py::test_w19_inventory_closed_world` |
| W20 | `tests/unit/test_od05w_engineering.py::test_w20_blocked_input_not_passed` |
| W21 | `tests/unit/test_od05w_engineering.py::test_w21_diagnostic_failures_preserved` |
| W22 | `tests/unit/test_od05w_engineering.py::test_w22_integrity_refuses` |
| W23 | `tests/unit/test_od05w_engineering.py::test_w23_fresh_copy_no_overwrite` |
| W24 | `tests/unit/test_od05w_engineering.py::test_w24_test_fixture_preserved` |
