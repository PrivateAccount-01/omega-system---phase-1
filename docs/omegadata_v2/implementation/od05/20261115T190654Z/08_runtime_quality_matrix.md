# Runtime evidence reconciliation — no fresh OD05 tests

Run20261115T190654Z @bbc38716d902fe27192f80affaca29c6f51e9890. RUN=current hash/metadata/Git inspection; ARCH=OD04R executed tests; TEST/SYN=those historic fixtures. No Python command, tests, collection, linter/type/package commands or numerical oracle executed in OD05 because implementation/owner/reference gates are not satisfied. No unavailable-environment or skipped-success claim.

| Runtime | OD04R full ARCH passed/skipped/deselected | ARCH targeted passed/skipped | ARCH collection/full/targeted/Ruff/mypy/pip exits | ARCH combined coverage whole/archive | Fresh OD05 result |
|---|---|---|---|---|---|
| Windows3.14.3 |478/10/4 |367/10 | all0 |81.5624%/88.7550% | NOT RUN; gate blocked |
| Windows3.11.15 |478/10/4 |367/10 | all0 |81.5493%/88.7550% | NOT RUN; gate blocked |
| Linux3.12.3 |486/2/4 |375/2 | all0 |81.5493%/89.5582% | NOT RUN; gate blocked |

[Current evidence-integrity check](logs/od04r-evidence-check.json) verifies six current source/test hashes, eleven report hashes, accepted command metadata and raw output presence. OD04R full source identity ledger and complete exact skip reasons remain [historical](../../od04r/20261115T181120Z/logs/reviewed-current-runtime-matrix.json). This reinspection does not transform ARCH tests into new RUN execution. Earlier reports' pre-commit/local-state statements remain accurate as-of their original run; bbc38716 later committed that work.

ARCH: Windows10file-link privilege skips paired with passing Linux nodes; Linux2junction skips paired on Windows. Four realdata tests deselected, never counted as pass. Windows3.14 recorded13SQLite ResourceWarning lines; other two profiles0; warnings retained. Prior dedicated actual symlink run9pass and process proof5forced crashes plus independent18observations/13objects per OS; these prove bounded storage, not parser numeric or official-source correctness. Old failed helper/mechanical attempts remain in history; only accepted logs above counted.

Fresh current commands: branch/HEAD/tree/merge-base/main diff/working diff/index/whitespace; policy/hash/approval searches and preservation. [Command metadata](logs/) records PowerShell/Git environment and actual exits. Early interactive read attempts had an invalid PowerShell glob and incompatible Raw/TotalCount option; corrected read/search commands completed. They are inspection mistakes, not application/test failures. No test counts invented from planning templates.

Before implementation, rerun fresh protected baseline and all32red groups, then code freeze and full3runtime matrix with exact source/test/fixture identities. Existing guard helpers must be re-audited/copied into a fresh run, never invoked against normal roots or reused exclusive labels. Native Linux persistent process roots; all outputs disposable and egress/protected writes denied during collection/execution. No CI result for OD05 is asserted.

Additional RUN reinspection: [detailed old evidence assertions](logs/od04r-detailed-check.json) confirm actual stored full counts/exits/deselections, process crashes and18/13 corpus outputs, with current source hashes matching those process identities. Original-preservation check passes12,449 records/zero changes. Current final QA remains a document/scope check only.

Mechanical-QA note: the first document checker rejected the valid logs/ directory link because it checked files only. Corrected only that helper to accept existing file or folder targets, as Markdown supports both. The failed QA log remains; this was not an application/test failure or a missing evidence directory.
