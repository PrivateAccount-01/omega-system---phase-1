OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY; run 20261115T201333Z. Evaluated 2026-11-16T08:23:11.592393+00:00. Branch feature/od01-source-rights; unchanged local HEAD bf6f4894c9e5237e8c1a44b625c66b8a420b4aad. RUN=new executed checks; TEST/SYN=synthetic fixtures; ARCH=prior evidence; UNK=unverified official semantics. Same-model procedural review, not independent human/financial/legal certification.

# Executed final matrix

| Runtime | Full passed/skipped/deselected | Targeted passed/skipped | New cases | Total coverage | Parser coverage | Exits |
|---|---|---|---|---|---|---|
| win314-accepted | 572/10/4 | 461/10 | 94 PASS_SYNTHETIC | 82.1585% | 94.3700% | all 0 |
| win311-accepted | 572/10/4 | 461/10 | 94 PASS_SYNTHETIC | 82.1460% | 94.3700% | all 0 |
| linux312-accepted | 580/2/4 | 469/2 | 94 PASS_SYNTHETIC | 82.1460% | 94.3700% | all 0 |

Every accepted environment/collection/targeted/full/Ruff/mypy/pip/compilation exits0. Exact argv/executable/platform/UTC/duration/output and node-level skip/deselection evidence in logs/*-accepted-*.json/.txt; pre-command source/test/fixture hashes in *-inputs.json. [Runtime summary](logs/accepted-runtime-matrix.json); [exact skip pairing](logs/skip-pairing.json); [identities](logs/input-identity-comparison.json). All94new cases execute with no skip/xfail on every runtime. Ten Windows privilege skips have actual passing Linux nodes; two Linux junction skips have passing Windows nodes. Four realdata tests deselected per runtime, not counted passed. Coverage is combined lines+branches; no equal-percent assumption.

All attempts retained: initial75/complete78 API-absence errors (not defect proofs); first78green; new adversarial89pass/3fail then92green; lexeme1fail/1pass/92deselected then final94cases; lint9findings then scoped import/literal/format fixes; initial Windows full/collection2 due missing UI resources in sanitized copy, corrected copy not application; later reviewed92case suites successful but superseded by final94case accepted suites. Earlier broad shell read had a PowerShell brace parse error; corrected read used valid paths. An interactive PowerShell5 coverage JSON conversion failed due coverage's empty-key function mapping; Python JSON reader generated coverage summary without changing coverage data. No failed attempt is presented as pass.

Duplicate ZIP construction UserWarning retained. Windows3.14 SQLite ResourceWarnings retained in raw log (not suppressed); these predate parser scope. WSL launcher reports stale PATH drive translation warnings; Linux runtime/commands themselves execute successfully. Run prefix is initial UTC date, later command/report timestamps are actual; no wall-clock timestamp synthesized. No hosted CI or physical independent-host certificate is claimed. Full regression covers API via existing tests; pure parser does not require network service startup/browser/container rollout.

