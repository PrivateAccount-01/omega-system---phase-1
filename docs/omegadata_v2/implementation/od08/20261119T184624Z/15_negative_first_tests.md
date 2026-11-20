# Actual frozen chronology
A new-test syntax error was corrected before executable baseline. Then63 tests failed NEW_FEATURE_ABSENT before application implementation. Review runs reproduced checksum, omitted-coverage, ordering, replay-budget, timestamp, repeated candidate-scan, authority-serialization and mutable-container defects before corrections. Passing concurrency controls are regressions, not manufactured red results. New fixture corrections (complete interval declaration, timestamp argument alignment, conflicting-member accounting) did not alter historical tests.

All command results, frozen hashes and failed sources are preserved:

```json
[
  {
    "command": "logs/od08-2d14d711d4-command.json",
    "start_utc": "2026-11-19T18:51:18.873627+00:00",
    "end_utc": "2026-11-19T18:51:23.402702+00:00",
    "test_sha256": "daa04dc4d51be019003957e22525bc3c17871ce820d756b8b9edafc3b215154d",
    "exit_code": 2,
    "counts": {},
    "failed_nodes": [],
    "collection_failure": true
  },
  {
    "command": "logs/od08-ca32cdba31-command.json",
    "start_utc": "2026-11-19T18:51:48.901812+00:00",
    "end_utc": "2026-11-19T18:51:55.039005+00:00",
    "test_sha256": "35f7f347ee54c8425aebd77d0c53935799405731b972a059c855b55c797ea973",
    "exit_code": 1,
    "counts": {
      "failed": 63
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_acceptance[U01]",
      "tests/unit/test_od08_universe.py::test_acceptance[U02]",
      "tests/unit/test_od08_universe.py::test_acceptance[U03]",
      "tests/unit/test_od08_universe.py::test_acceptance[U04]",
      "tests/unit/test_od08_universe.py::test_acceptance[U05]",
      "tests/unit/test_od08_universe.py::test_acceptance[U06]",
      "tests/unit/test_od08_universe.py::test_acceptance[U07]",
      "tests/unit/test_od08_universe.py::test_acceptance[U08]",
      "tests/unit/test_od08_universe.py::test_acceptance[U09]",
      "tests/unit/test_od08_universe.py::test_acceptance[U10]",
      "tests/unit/test_od08_universe.py::test_acceptance[I01]",
      "tests/unit/test_od08_universe.py::test_acceptance[I02]",
      "tests/unit/test_od08_universe.py::test_acceptance[I03]",
      "tests/unit/test_od08_universe.py::test_acceptance[I04]",
      "tests/unit/test_od08_universe.py::test_acceptance[I05]",
      "tests/unit/test_od08_universe.py::test_acceptance[I06]",
      "tests/unit/test_od08_universe.py::test_acceptance[C01]",
      "tests/unit/test_od08_universe.py::test_acceptance[C02]",
      "tests/unit/test_od08_universe.py::test_acceptance[C03]",
      "tests/unit/test_od08_universe.py::test_acceptance[C04]",
      "tests/unit/test_od08_universe.py::test_acceptance[C05]",
      "tests/unit/test_od08_universe.py::test_acceptance[A01]",
      "tests/unit/test_od08_universe.py::test_acceptance[A02]",
      "tests/unit/test_od08_universe.py::test_acceptance[A03]",
      "tests/unit/test_od08_universe.py::test_acceptance[A04]",
      "tests/unit/test_od08_universe.py::test_acceptance[A05]",
      "tests/unit/test_od08_universe.py::test_acceptance[L01]",
      "tests/unit/test_od08_universe.py::test_acceptance[L02]",
      "tests/unit/test_od08_universe.py::test_acceptance[L03]",
      "tests/unit/test_od08_universe.py::test_acceptance[L04]",
      "tests/unit/test_od08_universe.py::test_acceptance[L05]",
      "tests/unit/test_od08_universe.py::test_acceptance[E01]",
      "tests/unit/test_od08_universe.py::test_acceptance[E02]",
      "tests/unit/test_od08_universe.py::test_acceptance[E03]",
      "tests/unit/test_od08_universe.py::test_acceptance[E04]",
      "tests/unit/test_od08_universe.py::test_acceptance[R01]",
      "tests/unit/test_od08_universe.py::test_acceptance[R02]",
      "tests/unit/test_od08_universe.py::test_acceptance[P01]",
      "tests/unit/test_od08_universe.py::test_acceptance[P02]",
      "tests/unit/test_od08_universe.py::test_acceptance[P03]",
      "tests/unit/test_od08_universe.py::test_acceptance[P04]",
      "tests/unit/test_od08_universe.py::test_acceptance[P05]",
      "tests/unit/test_od08_universe.py::test_acceptance[P06]",
      "tests/unit/test_od08_universe.py::test_acceptance[S01]",
      "tests/unit/test_od08_universe.py::test_acceptance[S02]",
      "tests/unit/test_od08_universe.py::test_acceptance[S03]",
      "tests/unit/test_od08_universe.py::test_acceptance[S04]",
      "tests/unit/test_od08_universe.py::test_review_controls[order]",
      "tests/unit/test_od08_universe.py::test_review_controls[future-digest]",
      "tests/unit/test_od08_universe.py::test_review_controls[naive]",
      "tests/unit/test_od08_universe.py::test_review_controls[wrong-pin]",
      "tests/unit/test_od08_universe.py::test_review_controls[replay]",
      "tests/unit/test_od08_universe.py::test_review_controls[explain]",
      "tests/unit/test_od08_universe.py::test_review_controls[changed-policy]",
      "tests/unit/test_od08_universe.py::test_review_controls[unknown-schema]",
      "tests/unit/test_od08_universe.py::test_review_controls[nonempty-rollback]",
      "tests/unit/test_od08_universe.py::test_review_controls[foreign-key]",
      "tests/unit/test_od08_universe.py::test_review_controls[immutable]",
      "tests/unit/test_od08_universe.py::test_review_controls[bounds]",
      "tests/unit/test_od08_universe.py::test_review_controls[cancel-lineage]",
      "tests/unit/test_od08_universe.py::test_review_controls[provisional]",
      "tests/unit/test_od08_universe.py::test_review_controls[observation-future-digest]",
      "tests/unit/test_od08_universe.py::test_review_controls[definition-expired]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-e538e9b01d-command.json",
    "start_utc": "2026-11-19T18:58:25.158501+00:00",
    "end_utc": "2026-11-19T18:58:31.998672+00:00",
    "test_sha256": "35f7f347ee54c8425aebd77d0c53935799405731b972a059c855b55c797ea973",
    "exit_code": 1,
    "counts": {
      "failed": 30,
      "passed": 33
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_acceptance[U01]",
      "tests/unit/test_od08_universe.py::test_acceptance[U02]",
      "tests/unit/test_od08_universe.py::test_acceptance[I01]",
      "tests/unit/test_od08_universe.py::test_acceptance[I03]",
      "tests/unit/test_od08_universe.py::test_acceptance[I05]",
      "tests/unit/test_od08_universe.py::test_acceptance[I06]",
      "tests/unit/test_od08_universe.py::test_acceptance[C05]",
      "tests/unit/test_od08_universe.py::test_acceptance[A01]",
      "tests/unit/test_od08_universe.py::test_acceptance[A02]",
      "tests/unit/test_od08_universe.py::test_acceptance[A03]",
      "tests/unit/test_od08_universe.py::test_acceptance[A04]",
      "tests/unit/test_od08_universe.py::test_acceptance[A05]",
      "tests/unit/test_od08_universe.py::test_acceptance[L01]",
      "tests/unit/test_od08_universe.py::test_acceptance[L02]",
      "tests/unit/test_od08_universe.py::test_acceptance[L03]",
      "tests/unit/test_od08_universe.py::test_acceptance[L04]",
      "tests/unit/test_od08_universe.py::test_acceptance[L05]",
      "tests/unit/test_od08_universe.py::test_acceptance[E01]",
      "tests/unit/test_od08_universe.py::test_acceptance[E02]",
      "tests/unit/test_od08_universe.py::test_acceptance[R01]",
      "tests/unit/test_od08_universe.py::test_acceptance[R02]",
      "tests/unit/test_od08_universe.py::test_acceptance[P01]",
      "tests/unit/test_od08_universe.py::test_acceptance[P04]",
      "tests/unit/test_od08_universe.py::test_acceptance[P05]",
      "tests/unit/test_od08_universe.py::test_review_controls[changed-policy]",
      "tests/unit/test_od08_universe.py::test_review_controls[unknown-schema]",
      "tests/unit/test_od08_universe.py::test_review_controls[nonempty-rollback]",
      "tests/unit/test_od08_universe.py::test_review_controls[foreign-key]",
      "tests/unit/test_od08_universe.py::test_review_controls[immutable]",
      "tests/unit/test_od08_universe.py::test_review_controls[observation-future-digest]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-bd2097c2bb-command.json",
    "start_utc": "2026-11-19T18:59:28.344473+00:00",
    "end_utc": "2026-11-19T18:59:34.210432+00:00",
    "test_sha256": "b970c641640c5229b5427225ef1eacdfa3aebb9740693896b310980e094f2d75",
    "exit_code": 0,
    "counts": {
      "passed": 63
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-381896378d-command.json",
    "start_utc": "2026-11-19T19:01:24.932066+00:00",
    "end_utc": "2026-11-19T19:01:31.948039+00:00",
    "test_sha256": "20a7e32ee78f13d7f3f8543162301e38a7ef6e44df527a0c1dbf1c3cf1fc1fd3",
    "exit_code": 1,
    "counts": {
      "passed": 78,
      "failed": 4
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_independent_review[context-checksum]",
      "tests/unit/test_od08_universe.py::test_independent_review[omitted-coverage]",
      "tests/unit/test_od08_universe.py::test_independent_review[order-observations]",
      "tests/unit/test_od08_universe.py::test_independent_review[replay-bool]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-9d6ec5d433-command.json",
    "start_utc": "2026-11-19T19:02:52.140789+00:00",
    "end_utc": "2026-11-19T19:02:59.593848+00:00",
    "test_sha256": "20a7e32ee78f13d7f3f8543162301e38a7ef6e44df527a0c1dbf1c3cf1fc1fd3",
    "exit_code": 0,
    "counts": {
      "passed": 82
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-4496e949fb-command.json",
    "start_utc": "2026-11-19T19:05:45.704699+00:00",
    "end_utc": "2026-11-19T19:05:51.770982+00:00",
    "test_sha256": "3dd17ae677f8b4957697579edd9bcf7d7feecc7b68631123cb538acffe8424da",
    "exit_code": 1,
    "counts": {
      "passed": 82,
      "failed": 4
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_source_time_boundaries[future-announcement]",
      "tests/unit/test_od08_universe.py::test_source_time_boundaries[future-publication]",
      "tests/unit/test_od08_universe.py::test_source_time_boundaries[intraday-before]",
      "tests/unit/test_od08_universe.py::test_source_time_boundaries[intraday-at]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-4d056f7aaa-command.json",
    "start_utc": "2026-11-19T19:06:51.672793+00:00",
    "end_utc": "2026-11-19T19:06:58.643214+00:00",
    "test_sha256": "3dd17ae677f8b4957697579edd9bcf7d7feecc7b68631123cb538acffe8424da",
    "exit_code": 0,
    "counts": {
      "passed": 86
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-43ed59580a-command.json",
    "start_utc": "2026-11-19T19:08:01.389508+00:00",
    "end_utc": "2026-11-19T19:08:11.126408+00:00",
    "test_sha256": "89daf32bb9bb2a716d1c41db9889de422bbdf16f774aa8773779e72523346552",
    "exit_code": 0,
    "counts": {
      "passed": 86
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-7fb1a8cc95-command.json",
    "start_utc": "2026-11-19T19:09:00.301230+00:00",
    "end_utc": "2026-11-19T19:09:07.097477+00:00",
    "test_sha256": "477a2516e5a3e442262c5236b3a6a425662eb73e124cc47e85d8ee10830add23",
    "exit_code": 1,
    "counts": {
      "passed": 86,
      "failed": 1
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_identity_selection_candidate_budget"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-056df0147b-command.json",
    "start_utc": "2026-11-19T19:09:57.180632+00:00",
    "end_utc": "2026-11-19T19:10:02.777864+00:00",
    "test_sha256": "e71cc570f9d3d17aeea412b0b9fa2004f4b746ad7370f5c9f91b193d6bed88b2",
    "exit_code": 0,
    "counts": {
      "passed": 87
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-61fe74e6a4-command.json",
    "start_utc": "2026-11-19T19:10:33.894981+00:00",
    "end_utc": "2026-11-19T19:10:40.281482+00:00",
    "test_sha256": "20a467275a0e4180e18aa2b660284a01295804d4e8e39dd3f089020c17473548",
    "exit_code": 0,
    "counts": {
      "passed": 88
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-32d46ba715-command.json",
    "start_utc": "2026-11-19T19:12:23.736091+00:00",
    "end_utc": "2026-11-19T19:12:29.607347+00:00",
    "test_sha256": "20a467275a0e4180e18aa2b660284a01295804d4e8e39dd3f089020c17473548",
    "exit_code": 0,
    "counts": {
      "passed": 88
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-75f03142a7-command.json",
    "start_utc": "2026-11-19T19:15:49.675180+00:00",
    "end_utc": "2026-11-19T19:15:57.692938+00:00",
    "test_sha256": "baf89c17caf8f95e0809b4640801b3b073450dba23672fe52a60c13fb0f73480",
    "exit_code": 1,
    "counts": {
      "passed": 88,
      "failed": 3
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[source-scope]",
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[expected-identities]",
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[transitions]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-79137e77bb-command.json",
    "start_utc": "2026-11-19T19:16:20.826234+00:00",
    "end_utc": "2026-11-19T19:16:22.685736+00:00",
    "test_sha256": "14061149b55d931409a15ec99726661bd79c52b6c19acc416abf4100155884b9",
    "exit_code": 2,
    "counts": {},
    "failed_nodes": [],
    "collection_failure": true
  },
  {
    "command": "logs/od08-8fb19b7c7e-command.json",
    "start_utc": "2026-11-19T19:16:46.811287+00:00",
    "end_utc": "2026-11-19T19:16:53.171137+00:00",
    "test_sha256": "798f72d6fc5d7036970eb0f19d4dd46676867158c1d9be31595f33338014f0bd",
    "exit_code": 1,
    "counts": {
      "passed": 88,
      "failed": 4
    },
    "failed_nodes": [
      "tests/unit/test_od08_universe.py::test_od07_bound_integration[persist-authority-object]",
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[source-scope]",
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[expected-identities]",
      "tests/unit/test_od08_universe.py::test_immutable_source_contracts[transitions]"
    ],
    "collection_failure": false
  },
  {
    "command": "logs/od08-edd8b177c2-command.json",
    "start_utc": "2026-11-19T19:17:47.309449+00:00",
    "end_utc": "2026-11-19T19:17:53.516039+00:00",
    "test_sha256": "8479681e4a03ebab333f95cc907fdd0531be59c9895a7c64de8d3057aee289ae",
    "exit_code": 0,
    "counts": {
      "passed": 92
    },
    "failed_nodes": [],
    "collection_failure": false
  },
  {
    "command": "logs/od08-f5a579dec7-command.json",
    "start_utc": "2026-11-19T19:18:33.540589+00:00",
    "end_utc": "2026-11-19T19:18:41.240735+00:00",
    "test_sha256": "8479681e4a03ebab333f95cc907fdd0531be59c9895a7c64de8d3057aee289ae",
    "exit_code": 0,
    "counts": {
      "passed": 92
    },
    "failed_nodes": [],
    "collection_failure": false
  }
]
```
The first immutable freeze estimated92 cases while a helper parse failure left91 executable cases; actual logs are authoritative. The later92-case executable red showed88 pass/4 fail before correction. Helper parse/indentation and quality failures are retained, not described as implementation defects. No retroactive chronology or independent human consensus claimed.
