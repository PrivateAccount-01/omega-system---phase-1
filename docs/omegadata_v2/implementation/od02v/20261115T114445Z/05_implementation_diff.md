# OD-02V exact implementation ledger

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


Application changes were made **only after** [seven executable negative-first failures](logs/confidentiality-negative.txt) and [pre-code design](remediation_design.md). They do not change source approvals, transport URLs, fetch authorization, parser contracts, archive bytes, retries, release/signing or business calculations.

| Path | Reason / impact |
|---|---|
| [acquisition.py](../../../../../src/omegadata/track_a/acquisition.py) | `safe_url`: preserve ordinary paths, redact explicit credential field/value segments (including encoded field labels), keep query/fragment/userinfo removal; malformed evidence URL returns conservative placeholder |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | One cached artifact exposed `used_url` now uses the same sanitizer; historical manifests/raw bytes not rewritten |
| [test_od02v_portability.py](../../../../../tests/unit/test_od02v_portability.py) (new) | 17 canonical pytest cases: real symlink capability, raw/seed directory/file/broken/loop/retarget confinement; network/process/write guard incl POSIX descriptor-relative denial; seven URL confidentiality proofs |
| This fresh OD-02V directory (new) | Nine required reports, design note, bounded environment/copy/fixture/bootstrap/runner/matrix/capability/review helpers and raw/JSON evidence |

No inherited test, tracked requirement, config, policy, workflow, source-era registry, warehouse, pipeline math, historical data/evidence or signing material is changed. The supplied OD-02V prompt remains untracked and unmodified. No commit/push/merge/stage.

[Implementation patch](logs/implementation.patch) contains the two tracked source diffs and new test content; [final preservation/checks](logs/final-check-accepted.json) identifies exact original deltas and verifies every tested copy overlay hash. All other code/test/config copy hashes match reviewed HEAD (editable-generated package metadata explicitly excluded). Line endings are accounted for; no blanket tree formatting occurred.

The source changes are stdlib and platform-neutral, tested under actual 3.11/3.12/3.14. Safe URL display is deliberately conservative for recognized credential labels; arbitrary unlabeled opaque secrets cannot be inferred reliably, so embedding credentials in those paths is still prohibited. Egress remains OFF. Selective rollback would reverse only these documented hunks after review, retaining new reports/tests/evidence and leaving provider jobs disabled; no rollback is performed.
