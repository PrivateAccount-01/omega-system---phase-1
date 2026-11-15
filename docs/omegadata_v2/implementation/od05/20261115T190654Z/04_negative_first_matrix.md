# Complete proposed OD05-T01–T32 matrix — NOT EXECUTED

Audit/plan only @bbc38716d902fe27192f80affaca29c6f51e9890; run20261115T190654Z. RUN=inspection; ARCH=inherited tests; TEST/SYN=planned synthetic cases; UNK=missing reference. **No OD05 test-source file, fixture or executable test was authored or run.** Every row below is BLOCKED_OWNER/AUTHORIZATION, not skipped green, red or complete. Planning this matrix does not satisfy Gate2.

| Group | Frozen future cases and asserted invariant | Reference/oracle dependency | Current execution |
|---|---|---|---|
| T01 | Explicit source/date/raw SHA/parser+format+reference selects reproducible immutable typed rows | Separate frozen source rows and expected columns | NOT RUN; gates blocked |
| T02 | Repeat exact bytes twice, identical semantic digest with operational timestamps excluded | Independently canonicalized expected object | NOT RUN |
| T03 | Same date/different bytes gives distinct raw/version identity; old outputs unchanged | Pin both raw SHA and row digests independently | NOT RUN |
| T04 | Legacy2019 field-by-field mapping, correct units/date/identity | Authenticated legacy spec+representative rows; synthetic alone cannot certify | BLOCKED_REFERENCE and owner gate |
| T05 | Plausible disputed2020 legacy bytes not forced into UDiFF solely by year; unsupported modern2020 cannot self-certify | Freeze disputed format cases only after source research; distinguish real assertion defect from missing API | NOT RUN; no reproduced defect claimed |
| T06 | Both sides of2024-07-08, June24 and verified adjacent sessions; parallel forms explicit | Verified calendar amendments/format transition corpus | BLOCKED_REFERENCE |
| T07 | UDiFF final ZIP candidate/header/required+optional fields exact | Versioned catalogue and row/sample alignment | BLOCKED_REFERENCE |
| T08 | Unknown/intermediate/overlapping era returns ERA_UNKNOWN/REFERENCE_PENDING without guessing | Ambiguity expected table maintained outside implementation | NOT RUN |
| T09 | BSE modern filename/member/source/date/field contract | Separate authenticated BSE specification and rows | BLOCKED_REFERENCE |
| T10 | Unproven historical BSE quarantined; official flag cannot bypass | Negative missing-proof and misleading-label fixtures | NOT RUN |
| T11 | Missing/unknown required headers, duplicate/normalized collisions reject; benign extras retained inert | Per-format required/optional/unknown distinction | NOT RUN |
| T12 | Bad quotes/escapes, trailing extra field, truncated record refuse file-wide | Raw byte fixtures with independent record-count expectations | NOT RUN |
| T13 | ZIP traversal/absolute/directory/symlink/nested/bomb/duplicate candidates refuse | Bounded manufactured archives, no external paths | NOT RUN |
| T14 | HTML/JSON denial/empty never becomes trusted rows | Synthetic status/body fixtures | NOT RUN |
| T15 | Wrong trade/filename dates and unsupported encoding reject; BizDt semantics not assumed equal | Date meaning from exact spec; ambiguous layouts negative | NOT RUN |
| T16 | Zero volume retained; empty/negative/fractional/overflow refuse | Independent integer-lexeme and frozen volume ceiling policy | NOT RUN |
| T17 | Decimal precision exact, small/large magnitudes and trailing scale preserved with lexemes, no float round-trip | Independent scaled-integer expected values | NOT RUN |
| T18 | Nonfinite/negative/inconsistent OHLC reject; source-specific legitimate exceptions explicit | Per-format numeric bounds/zero-price semantics | NOT RUN |
| T19 | Duplicates by exchange+symbol+series+ISIN+date detected; distinct legitimate series not collapsed | Verified identity key policy and rows | NOT RUN |
| T20 | Leading-zero scrip code/ISIN/symbol preserved exactly, no numeric conversion | Literal expected strings; BSE support still pending | NOT RUN |
| T21 | Missing series/ISIN follows exact era rule or quarantines; no inferred substitutions | Verified nullable/identity policy | BLOCKED_REFERENCE |
| T22 | Trade/business date distinct from published/observed/ingested; null publication retained | Synthetic multi-time fixtures and field spec | NOT RUN |
| T23 | Wrong raw SHA, missing required observation/ref, tampered bytes fail before parsing | Independent digest and rights-aware pinned archive reader | NOT RUN |
| T24 | Cached/seed/synthetic cannot become official through caller flags/filenames | Reference capability/status separate from parse flags | NOT RUN |
| T25 | Pending/revoked/wrong-purpose denies protected read before parser invocation | Existing policy fixture injected only into controlled test contexts | NOT RUN |
| T26 | Every parser refusal causes zero DB/Parquet/raw/archive/release/policy writes | Write/process/network spies plus sandbox audit | NOT RUN |
| T27 | Repeat pinned input/version gives bit-for-bit canonical proof; wall clock excluded | Separately serialized expected JSON/digests | NOT RUN |
| T28 | Old acquisition/loader and all inherited tests preserved, default adapter OFF | Freeze old test hashes; supported behavior unchanged | NOT RUN; existing results only ARCH |
| T29 | Paths/separators/case/CRLF/LF/ZIP timestamps/locale do not alter meaning unexpectedly | Same frozen bytes across all3runtimes; no locale guessing | NOT RUN |
| T30 | Bytes/rows/ZIP entries/expansion/CPU and numeric token limits enforced early | Independently pinned budgets and allocation probes | NOT RUN |
| T31 | Separate oracle compares every numeric/identity/date/row-index field, not just counts | Authenticated golden subset or explicitly synthetic arithmetic subset | NOT RUN; no numerical result claimed |
| T32 | Collection/targeted/full/Ruff/mypy/pip3platforms; pair exact link skips, retain warnings | Fresh protected clean rooms/native Linux; exact source hashes | NOT RUN |

Future execution discipline: author/freeze **all32groups before any application edit**, including property/integration cases; check every listed assertion actually executes. Log each red with exact source/test/fixture SHA, time, argv,cwd,exit and environment. Categories: genuine old-behavior assertion defect; new API absent (not defect proof); missing official reference/rights (BLOCKED, not pass); harness/fixture error (fix before classification). A group missing its official corpus cannot count green. New discoveries later need honest chronology and scope amendment, never retroactive relabeling.
