# Metrics and reproduction

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

- win314-accepted: **13** unclosed SQLite ResourceWarning lines (tracemalloc hints separate). [coverage JSON](logs/win314-accepted-full-coverage.json); [source identities](logs/win314-accepted-source.json); [environment](logs/win314-accepted-environment.txt).
- win311-accepted: **0** unclosed SQLite ResourceWarning lines (tracemalloc hints separate). [coverage JSON](logs/win311-accepted-full-coverage.json); [source identities](logs/win311-accepted-source.json); [environment](logs/win311-accepted-environment.txt).
- linux312-accepted: **0** unclosed SQLite ResourceWarning lines (tracemalloc hints separate). [coverage JSON](logs/linux312-accepted-full-coverage.json); [source identities](logs/linux312-accepted-source.json); [environment](logs/linux312-accepted-environment.txt).

## win measured synthetic corpus

18 committed observations / 13 raw object files. Benchmark subset: six events / three objects (4096, 65536, 1048576 bytes), 2259705 logical file bytes including staging/links, 1129853 bytes counting unique filesystem inodes. Payload sharing avoids a second object per duplicate event. No promised throughput/SLA.

| Bytes | Put seconds | Verified read seconds | tracemalloc peak bytes |
|---:|---:|---:|---:|
| 4096 | 0.167933 | 0.030355 | 17077747 |
| 65536 | 0.211313 | 0.029875 | 17074760 |
| 1048576 | 0.257550 | 0.030392 | 17072918 |

Recovery inventory seconds: 0.072776. tracemalloc is Python allocation peak, not OS RSS/disk-allocation blocks; kernel/cache effects and small sample size prohibit comparative product-performance claims.

## linux measured synthetic corpus

18 committed observations / 13 raw object files. Benchmark subset: six events / three objects (4096, 65536, 1048576 bytes), 2259705 logical file bytes including staging/links, 1129853 bytes counting unique filesystem inodes. Payload sharing avoids a second object per duplicate event. No promised throughput/SLA.

| Bytes | Put seconds | Verified read seconds | tracemalloc peak bytes |
|---:|---:|---:|---:|
| 4096 | 0.064235 | 0.008591 | 16814050 |
| 65536 | 0.062020 | 0.007777 | 16813460 |
| 1048576 | 0.082990 | 0.014723 | 16813218 |

Recovery inventory seconds: 0.006555. tracemalloc is Python allocation peak, not OS RSS/disk-allocation blocks; kernel/cache effects and small sample size prohibit comparative product-performance claims.

Reproduction: use same installed runtime with explicit -B and this fresh runner,
sanitized copy and new unique label. `matrix.py` freezes five exact changed-file
hashes before collection and sequential commands. Never reuse labels (exclusive
log opens), install over original env, or use production roots. Exact expanded
argv/cwd/OS/UTC/exit is in per-command JSON; portable command forms:

```text
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest --collect-only -q -m 'not realdata'
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest -q <five targeted unit modules> -m 'not realdata'
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
<python> -B verification_runner.py <unique-label> <disposable-copy> ruff check --no-cache src/omegadata tests scripts
<python> -B verification_runner.py <unique-label> <disposable-copy> mypy src/omegadata
<python> -B verification_runner.py <unique-label> <disposable-copy> pip check
<python> -B process_experiments.py <disposable-copy> <unique-label>
```

Explicit trusted process runner is separate from the subprocess-denying pytest
guard. Child commands/worker hashes/actual exits accompany process logs. Independent
measure_corpus.py uses stdlib hashes/length/link verification, no service under
test to derive expected identity. Source identity all final copies must match
current working files; remaining baseline source/config/tests match Git object
hashes except expected generated packaging metadata (not original package writes).

Retained failing attempts: four baseline reds, three later adversarial reds,
initial mypy eight typing errors (platform-conditional imports, shadowed type and
Literal annotation), two process-harness failures described above. All final
gates rerun after corrections with fresh labels. Earlier all-green intermediate
runs remain ARCH within this run when source changed, not substituted for final
hash identity. No fresh CI success or upstream dependency vulnerability clearance.


## Corpus verifier correction and authoritative evidence

The first post-process Linux independent scan returned 0 observations/0 objects
after WSL removed the fresh /tmp corpus on session shutdown. This was a harness
verification defect: a missing root could pass vacuously. The retained
[old scan](logs/linux-corpus-reference.txt) and first final-preservation.json do
not prove persistent corpus completeness. The strengthened scanner requires an
existing root and exactly 18 commits/13 object files. Its
[missing-evidence negative](logs/linux-missing-corpus-negative.json) exits nonzero.
Linux process experiments were rerun in a fresh private native /home directory;
[new process commands](logs/linux-process-persistent.json) exit 0 and the
[independent persistent scan](logs/linux-corpus-persistent.txt) verifies all 18/13.
No old experiment or original data was deleted by this task. Both earlier logs
remain intact; this correction does not waive the separate Gate 2 chronology
block. Application/test source did not change for this harness correction.
