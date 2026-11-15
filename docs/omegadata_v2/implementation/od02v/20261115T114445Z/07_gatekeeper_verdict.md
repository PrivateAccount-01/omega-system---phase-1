# OD-02V Gatekeeper: OD02V_OFFLINE_PORTABILITY_PASS

OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `feature/od01-source-rights`, unchanged reviewed HEAD `eaedac1bddc35867f9089486beffa3bb38cb11f4`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.


**OD02V_OFFLINE_PORTABILITY_PASS** for the required local offline runtime matrix and bounded remediation, valid only with [final mechanical gate](logs/final-check-accepted.json) passing. This does not approve live acquisition, financial truth, production release or later phases.

| Acceptance criterion | Executed evidence |
|---|---|
| Exact reviewed Git baseline / preservation | Required branch and eaedac1bddc35867f9089486beffa3bb38cb11f4 verified; original content/metadata preserved except two justified application hunks; staged index empty, no Git mutation |
| Original three skipped file-symlink cases | All actually execute/pass on native Linux, unmodified; observed real links true and outside reads 0; dedicated proof 4 pass/0 skip/exit 0 includes positive smoke |
| Required targeted/full runtime matrix | Windows 3.14.3 **282 targeted / 393 full passed**, 10 documented symlink skips; Windows 3.11.15 same; Linux 3.12.3 **290 targeted / 401 full passed**, 2 Windows-junction skips; all final exits 0 |
| No denominator omission | Full collection 403/407 selected; four intentionally excluded realdata tests never labeled pass. Every Windows skipped file-link case passes on Linux; Linux junction skips have actual Windows coverage |
| Lint/type/package checks | Ruff, mypy (48 source files), pip check on all three runtimes exit 0; exact versions/constraints/source-copy hashes recorded |
| Defects tested before correction | Seven confidentiality red cases exit 1 before source edit, then green and entire matrix exit 0; only two application files edited |
| Source rights / network / security | Real policies remain 13 pending/0 approved; actual HTTPX/urllib/curl provider egress OFF. Guard-negative tests execute; no signing/release/provider/paid operation |
| Warnings / known limits | 13 temporary SQLite ResourceWarnings retained on 3.14, not hidden. Windows symlink privilege still absent; WSL is same physical host. Hostile filesystem syscall race and official source authenticity not certified |
| Inherited P0 / independent review | D-01/D-04 OPEN; financial/rights/official-era review PENDING. Same-model roles only; independent human/security review recommended before new production capabilities |

The original OD-02 missing-environment and three-unexecuted-symlink blockers are closed by actual execution. Earlier OD-02/OD-01R reports remain immutable historical records, not rewritten to replace their original verdicts. Current verdict supersedes only that incomplete offline portability evidence, not independent source/financial/signing/release restrictions.

Coverage combined statement/branch: Windows 3.14 **81.0265%**, Windows 3.11 **81.0125%**, Linux 3.12 **80.9564%**; acquisition module **93.6709%** each. This is measured partial coverage, not full correctness. Failed setup/harness/negative attempts are retained and correctly excluded from final successful command claims; [complete runtime matrix](03_runtime_test_matrix.md), [security review](06_security_regression.md), [source ledger](05_implementation_diff.md).

**STOP after OD-02V.** No commit, push, merge, CI edit, source approval or OD-03/04 execution. The only proposed next approval is [the scoped next request](08_next_phase_request.md).


## Final evidence-check correction

The retained [first mechanical check](logs/final-check.json) exited 1. It
identified a patch link checked before the patch had been created, and two
Windows 3.14 overlay hashes equal to the empty-file hash. Those hashes were
captured during a concurrent copy operation; the original Windows 3.14 matrix
therefore does not establish exact tested-source identity. No empty-file test
result is accepted as an identity proof. The sequential `win314-reviewed`
collection, targeted and complete regression commands replace that matrix as
authoritative evidence and record fresh source hashes. The first check and
all earlier command logs remain unchanged. The already-created patch is now
byte-compared with the current source diff, and the [reviewed final check](logs/final-check-accepted.json)
must pass before the Gatekeeper verdict is valid. No application or test
changes were made for this evidence correction.
