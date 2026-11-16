OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Fresh accepted runtime matrix

| Runtime | Full pass / skip / realdata excluded | New metadata pass / skip | Global / new-module coverage |
|---|---|---|---|
| win314 Python 3.14.3 | 678 / 13 / 4 | 46 / 2 | 82.55% / 84.44% |
| win311 Python 3.11.15 | 678 / 13 / 4 | 46 / 2 | 82.54% / 84.44% |
| linux312 Python 3.12.3 | 687 / 4 / 4 | 47 / 1 | 82.54% / 84.44% |

All accepted environment/collection/new/targeted/full/guard/performance/Ruff/strict-mypy/pip/compile commands exit 0. [Actual argv index](logs/accepted-command-index.json) and per-command JSON/text retain exact executable, cwd, platform, UTC start/end, exit, raw warnings, skips and realdata exclusions. Four live-marked tests are excluded per full runtime, never called verified. Inherited legacy tests are engineering regression only.

[Skip pairing](logs/skip-pairing.json) requires each exact skipped node to pass on another OS, including actual Linux links and Windows junctions; no privilege skip is a pass. WSL uses native Linux storage but shares the Windows physical host; no hosted CI result or independent host certification. WSL inherited stale PATH translation warnings occurred during preparation/launch, retained in the tool transcript. Full logs retain duplicate-ZIP and any runtime cleanup warnings.

M16 measures 1/8/32 copied real manifest metadata files with elapsed time and tracemalloc allocations; three passes each runtime. Raw values are in *-accepted-performance.txt. These are Python allocation measurements, not RSS or financial throughput. The original guarded metadata scan also records end-to-end time including the separate oracle and peak Python allocations; this combined duration is not the production scan's 30-second deadline or a market-price processing benchmark.

Initial Windows *-final matrices are superseded after the two pin-reader tests/correction. Only *-accepted results support this verdict. Compilation writes bytecode only into disposable copies; no package installation or original-environment replacement.
