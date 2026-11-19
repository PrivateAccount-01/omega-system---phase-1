# Actual frozen chronology
Initial63tests froze before package creation and failedNEW_FEATURE_ABSENT. Later genuine adversarial failures were executed before corresponding fixes. Already passing controls are regressions, not fabricated red results. All failed source versions and commands retained.

```json
{
  "freezes": {
    "negative-first-freeze.json": {
      "utc": "2026-11-19T17:13:45.188159+00:00",
      "path": "/home/parilrupani/omega-od07-20261119T171019Z/staged2/repo/tests/unit/test_od07_adjustments.py",
      "sha256": "5acaee3962da111142849abc84d165fbd81b4a1a17b4272f2151311c7f80e37c",
      "application_implementation_present": false,
      "class": "NON_MARKET_MATH_AND_ENGINEERING"
    },
    "review-freeze.json": {
      "utc": "2026-11-19T17:18:21.486821+00:00",
      "sha256": "98eb02d37271e4558f32c4cdfe15f130e6019c2982ea8ad42a97a59db915903c",
      "before_corrections": true
    },
    "integrity-freeze.json": {
      "utc": "2026-11-19T17:20:40.474412+00:00",
      "sha256": "50f4a577ac3f483fd1360330c96c0c79b412e77e95baa91cf71128004fbb4b3f",
      "before_corrections": true
    },
    "sql-freeze.json": {
      "utc": "2026-11-19T17:25:26.024249+00:00",
      "sha256": "6f69c4156812743c650ef53f49f2386d2160c91b1dd1d0f678dc35d4c1dcc128"
    },
    "decimal-freeze.json": {
      "utc": "2026-11-19T17:31:34.782359+00:00",
      "sha256": "26e006f8604aff55fe56302bbd09386bc4068e8c571739ab761e1b6455118051"
    }
  },
  "history": [
    {
      "command": "logs/od07-c6784bbd4e-command.json",
      "start_utc": "2026-11-19T17:13:46.183274+00:00",
      "end_utc": "2026-11-19T17:13:50.557840+00:00",
      "test_sha256": "5acaee3962da111142849abc84d165fbd81b4a1a17b4272f2151311c7f80e37c",
      "exit_code": 1,
      "counts": {
        "failed": 63
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_math_oracle[SPLIT-args0-1/2]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[SPLIT-args1-5/1]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[BONUS-args2-2/3]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[BONUS-args3-1/3]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[RIGHTS-args4-9/10]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[RIGHTS-args5-7/10]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[DIVIDEND_CASH-args6-19/20]",
        "tests/unit/test_od07_adjustments.py::test_math_oracle[DIVIDEND_SPECIAL-args7-4/5]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[M01]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[M05]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[M07]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[M08]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[M09]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T01]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T02]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T03]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T04]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T05]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T06]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[T07]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C01]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C02]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C03]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C04]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C05]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C06]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[S01]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[S02]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[S03]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[S04]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[zero]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[negative]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[nan]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[infinity]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[float]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[bonus-denominator]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[rights-currency]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[rights-exercise]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[dividend-price]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[dividend-time]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[unsupported]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[lifecycle]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[post-ex]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[forward]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[chain-limit]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[wrong-security]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[suspended]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[naive]",
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[unknown-version]",
        "tests/unit/test_od07_adjustments.py::test_persistence[restart-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[restart-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[duplicate-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[duplicate-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[rollback-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[rollback-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[append-only-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[append-only-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[revisions-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[revisions-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[foreign-key-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[foreign-key-False]",
        "tests/unit/test_od07_adjustments.py::test_persistence[migration-True]",
        "tests/unit/test_od07_adjustments.py::test_persistence[migration-False]"
      ]
    },
    {
      "command": "logs/od07-1e0d1ca9f3-command.json",
      "start_utc": "2026-11-19T17:17:15.065889+00:00",
      "end_utc": "2026-11-19T17:17:18.748475+00:00",
      "test_sha256": "5acaee3962da111142849abc84d165fbd81b4a1a17b4272f2151311c7f80e37c",
      "exit_code": 1,
      "counts": {
        "passed": 62,
        "failed": 1
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[suspended]"
      ]
    },
    {
      "command": "logs/od07-c2e4e24d97-command.json",
      "start_utc": "2026-11-19T17:18:22.363059+00:00",
      "end_utc": "2026-11-19T17:18:26.625882+00:00",
      "test_sha256": "98eb02d37271e4558f32c4cdfe15f130e6019c2982ea8ad42a97a59db915903c",
      "exit_code": 1,
      "counts": {
        "passed": 76,
        "failed": 9
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_refusal_and_boundaries[suspended]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[empty-strict]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[empty-denied]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[empty-identity]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[expired-action]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[currency-mismatch]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[nonfinite-action]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[suspension-constraint]",
        "tests/unit/test_od07_adjustments.py::test_review_refusals[result-payload-binding]"
      ]
    },
    {
      "command": "logs/od07-c8a8c41c71-command.json",
      "start_utc": "2026-11-19T17:19:07.159323+00:00",
      "end_utc": "2026-11-19T17:19:11.441422+00:00",
      "test_sha256": "98eb02d37271e4558f32c4cdfe15f130e6019c2982ea8ad42a97a59db915903c",
      "exit_code": 1,
      "counts": {
        "passed": 84,
        "failed": 1
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_review_refusals[timezone-reference]"
      ]
    },
    {
      "command": "logs/od07-64d49b0f4a-command.json",
      "start_utc": "2026-11-19T17:19:49.831420+00:00",
      "end_utc": "2026-11-19T17:19:54.286577+00:00",
      "test_sha256": "98eb02d37271e4558f32c4cdfe15f130e6019c2982ea8ad42a97a59db915903c",
      "exit_code": 0,
      "counts": {
        "passed": 85
      },
      "failed_nodes": []
    },
    {
      "command": "logs/od07-b17432b1aa-command.json",
      "start_utc": "2026-11-19T17:20:41.194951+00:00",
      "end_utc": "2026-11-19T17:20:46.071634+00:00",
      "test_sha256": "50f4a577ac3f483fd1360330c96c0c79b412e77e95baa91cf71128004fbb4b3f",
      "exit_code": 1,
      "counts": {
        "passed": 88,
        "failed": 7
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_final_integrity[future-ledger-stability]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[persisted-price-tamper]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[persisted-factor-tamper]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[partial-result]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[reverse-direction-type]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[reference-identity]",
        "tests/unit/test_od07_adjustments.py::test_final_integrity[large-result-refusal]"
      ]
    },
    {
      "command": "logs/od07-e14b668dd5-command.json",
      "start_utc": "2026-11-19T17:22:01.290860+00:00",
      "end_utc": "2026-11-19T17:22:05.874801+00:00",
      "test_sha256": "76d66976b678bde945b7e0616fcb5ac72095380200a1d3d7c85c47c2881f1a3a",
      "exit_code": 1,
      "counts": {
        "passed": 93,
        "failed": 2
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_acceptance[C01]",
        "tests/unit/test_od07_adjustments.py::test_acceptance[C02]"
      ]
    },
    {
      "command": "logs/od07-08a36fd6a8-command.json",
      "start_utc": "2026-11-19T17:22:40.697142+00:00",
      "end_utc": "2026-11-19T17:22:49.200018+00:00",
      "test_sha256": "d932dd6483e4497652e670adac99d60fc5d2beefe70bae0b748c75cee28987a9",
      "exit_code": 0,
      "counts": {
        "passed": 95
      },
      "failed_nodes": []
    },
    {
      "command": "logs/od07-092aa4671d-command.json",
      "start_utc": "2026-11-19T17:24:09.063252+00:00",
      "end_utc": "2026-11-19T17:24:14.057534+00:00",
      "test_sha256": "d932dd6483e4497652e670adac99d60fc5d2beefe70bae0b748c75cee28987a9",
      "exit_code": 0,
      "counts": {
        "passed": 95
      },
      "failed_nodes": []
    },
    {
      "command": "logs/od07-c4da9a95cd-command.json",
      "start_utc": "2026-11-19T17:25:26.578013+00:00",
      "end_utc": "2026-11-19T17:25:34.601354+00:00",
      "test_sha256": "6f69c4156812743c650ef53f49f2386d2160c91b1dd1d0f678dc35d4c1dcc128",
      "exit_code": 1,
      "counts": {
        "passed": 98,
        "failed": 1
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_sql_and_chain_integrity[persisted-order]"
      ]
    },
    {
      "command": "logs/od07-c5586de905-command.json",
      "start_utc": "2026-11-19T17:27:30.529891+00:00",
      "end_utc": "2026-11-19T17:27:35.347222+00:00",
      "test_sha256": "7c3ab6100da167d8827c2459bfcab3b8ffdd96c6490c6082b41fe58597e9224f",
      "exit_code": 0,
      "counts": {
        "passed": 99
      },
      "failed_nodes": []
    },
    {
      "command": "logs/od07-b4b50fcd55-command.json",
      "start_utc": "2026-11-19T17:31:35.694886+00:00",
      "end_utc": "2026-11-19T17:31:40.501793+00:00",
      "test_sha256": "26e006f8604aff55fe56302bbd09386bc4068e8c571739ab761e1b6455118051",
      "exit_code": 1,
      "counts": {
        "passed": 99,
        "failed": 1
      },
      "failed_nodes": [
        "tests/unit/test_od07_adjustments.py::test_decimal_environment_isolation"
      ]
    },
    {
      "command": "logs/od07-c06e2b5716-command.json",
      "start_utc": "2026-11-19T17:32:34.543225+00:00",
      "end_utc": "2026-11-19T17:32:38.774946+00:00",
      "test_sha256": "0b8d73993d546cfbda5074f354271bae8e7e51679dd301f463126ff95291e3ef",
      "exit_code": 0,
      "counts": {
        "passed": 100
      },
      "failed_nodes": []
    }
  ],
  "mandatory27family_mapping": {
    "M01": "test_acceptance[M01] + decimal_environment",
    "M02": "math_oracle[SPLIT] + forward",
    "M03": "math_oracle[BONUS]",
    "M04": "math_oracle[RIGHTS]",
    "M05": "test_acceptance[M05]",
    "M06": "math_oracle[DIVIDEND]",
    "M07": "test_acceptance[M07]",
    "M08": "test_acceptance[M08] + volume controls",
    "M09": "test_acceptance[M09]",
    "S05": "test_persistence + native SQL + competing writers",
    "T01": "test_acceptance[T01]",
    "T02": "test_acceptance[T02]",
    "T03": "test_acceptance[T03]",
    "T04": "test_acceptance[T04]",
    "T05": "test_acceptance[T05]",
    "T06": "test_acceptance[T06]",
    "T07": "test_acceptance[T07]",
    "C01": "test_acceptance[C01]",
    "C02": "test_acceptance[C02]",
    "C03": "test_acceptance[C03]",
    "C04": "test_acceptance[C04]",
    "C05": "test_acceptance[C05]",
    "C06": "test_acceptance[C06]",
    "S01": "test_acceptance[S01]",
    "S02": "test_acceptance[S02]",
    "S03": "test_acceptance[S03]",
    "S04": "test_acceptance[S04]"
  }
}
```
Final100testsPASS. Formatter-cache refusal,static/type failures and corrections preserved. Same-agent review; executable independent oracles do not imply human approval.
