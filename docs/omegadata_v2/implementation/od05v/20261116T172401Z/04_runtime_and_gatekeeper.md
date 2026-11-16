# OD-05V: separate technical and financial decisions

Reviewed branch `feature/od01-source-rights`, HEAD `0d43a43a7df2a997b394269d6a9ebf1e64a00de1`.

File-presence result: **OD05V_FILE_PRESENCE_BLOCKED**. Overall result: **BLOCKED**, including the setup-scope deviation (not self-approved) and incomplete unrestricted regression acceptance. Financial correctness is not proven. No OD06 or release authorization.

| Runtime | Focused calls | Full calls | Live tests deselected |
|---|---|---|---|
| win314-safe | {'passed': 40, 'skipped': 1} | {'passed': 714, 'failed': 4, 'skipped': 14} | 4 |
| win311-safe | {'passed': 40, 'skipped': 1} | {'passed': 714, 'failed': 4, 'skipped': 14} | 4 |
| linux312-safe | {'failed': 5, 'passed': 35, 'skipped': 1} | {'passed': 718, 'failed': 9, 'skipped': 5} | 4 |

[Exact commands and exits](command-index.json), [matrix](runtime-matrix.json), [full failures](full-regression-failures.json), [skip counterparts](skip-counterparts.json), [P01-P18](P01-P18-results.json), [scorecard](real-data-scorecard.json), [Gatekeeper](gatekeeper.json). Exit 1 is a failure; blocked input access is not relabeled PASS or hidden with deselection. Only four pre-existing realdata-marked tests are excluded from the full commands.

Windows 3.14/3.11 and native Ubuntu Python 3.12 code/test storage share one physical host. Original file-presence checks on Linux use the mounted original Windows archive; filesystem trap tests use disposable native Linux storage. No remote hardware/CI/power-loss guarantee. Ruff, strict mypy, pip consistency, compilation, environment and guard results are individually recorded. Pip check is not a CVE/licensing audit. Existing synthetic suites contribute zero financial acceptance.

All three runtimes returned exit 0 for Ruff, strict mypy (58 source files), pip check, compilation, environment inspection and seven guard probes. Every exact skipped node has a passing counterpart on another OS; a skip is not relabeled a pass. Windows full failures: one absent corporate-action snapshot and three missing seed symbol/ISIN mapping inputs. Linux adds five BUDGET failures for bulk seed scanning through the mounted Windows filesystem. The 30-second bound is unchanged. [Coverage](coverage-summary.json) is approximately 81.74–81.77% globally and 84.43–84.91% for the new module; these are measurements from failing input-restricted full runs, not financial acceptance or an all-green regression claim.

All 27 final commands used matching [frozen source identities](runtime-source-identity.json); JSON evidence validation and skip-pair reconciliation passed. The [original scan](logs/original-presence-scan.json) confirms 3,626 existing regular-file paths, zero missing files, all 3,626 filesystem lengths matching manifest claims, and 2,760 hardlink refusals. The 866 singly linked size-matching files remain unverified market candidates. No financial observation is independently accepted. Matching Phase-2 committed blob IDs for 2011 and 2020 add repository lineage only.

Initial `*-final` commands were interrupted after the copy-scope discovery and are not accepted matrices. `*-safe` records use copies with no data directory, strengthened raw-read guards and unchanged legacy tests. All initial logs remain. Preservation checks stat originals without rereading payload or signing bytes; see [preservation](logs/preservation-after.json).
