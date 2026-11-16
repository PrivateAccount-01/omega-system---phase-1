OD05R_REFERENCE_AND_PARSER_VERIFICATION_ONLY; run20261116T084526Z; evaluated 2026-11-16T09:18:44.511483+00:00. Branch feature/od01-source-rights; HEAD 2326936860f64cadf4f4c24a968c073114598b26. RUN=fresh commands; TEST/SYN=synthetic; ARCH=prior evidence; REF-DOC=indexed documentary lead only; UNK=unverified. Same-model procedural review, no independent human/legal/financial certification.

# Fresh final verification

| Runtime | Full pass/skip/deselect | Targeted pass/skip | OD05R pass/skip | Original OD05 | Coverage total/new verifier | Quality exits |
|---|---|---|---|---|---|---|
| win314-reviewed | 632/11/4 | 521/11 | 60/1 | 94 pass | 82.4763% / 88.4706% | all 0 |
| win311-reviewed | 632/11/4 | 521/11 | 60/1 | 94 pass | 82.4645% / 88.4706% | all 0 |
| linux312-reviewed | 640/3/4 | 529/3 | 60/1 | 94 pass | 82.4645% / 88.4706% | all 0 |

Every reviewed environment/collection/targeted/full/Ruff/mypy/pip/compile exit0; all61new cases are accounted for with one actual platform skip per runtime. Original94OD05cases execute unchanged. [Runtime metadata](logs/runtime-matrix.json), [skip pairing](logs/skip-pairing.json), [input identities](logs/cross-runtime-inputs.json). Full stdout/stderr and argv/executable/cwd/UTC/exit/source/fixture hashes are immutable logs/*-reviewed-*.json/.txt and *-inputs.json. Four realdata deselections are not passes. Windows new file-link skip runs on Linux; Linux new junction skip runs on Windows; inherited ten/two skips likewise paired.

Initial accepted-labelled59case full matrices passed but are superseded by final reviewed61case matrices after two additional demonstrated defects. No current claim uses their stale source hashes. Preliminary Ruff9findings/import/semicolon issues corrected only in new files; current qualitychecks pass. DuplicateZIPwarning and Windows3.14SQLite ResourceWarnings retained; no suppression. WSL stale PATH translation messages are launcher warnings, not hidden command errors. Native Linux test copy on /home filesystem; same physical host, no independent CI certificate claimed. No current hosted branch CI success was established by this offline run.

Guard5cases each and performance3cases Windows/Linux pass separately, not added to full regression totals. Exact measured allocations/time in [performance summary](logs/performance-summary.json). Initial imports missingnewAPI, later actual3+2new-code failures, formatting attempts and successful corrected runs remain chronological; no retroactive pre-code claim.
