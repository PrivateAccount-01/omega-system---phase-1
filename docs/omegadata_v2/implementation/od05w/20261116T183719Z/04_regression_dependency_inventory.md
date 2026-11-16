# Exact dependency inventory

[Runtime-specific exact inventories](test-dependency-inventory.json), [full diagnostic failures](full-diagnostic-failures.json), [skip pairing](skip-counterparts.json).

Final collection: **775 = A 767 + B 4 + C 4** on every runtime. Classification is pinned to reviewed test source hashes, exact function identities/cardinalities and exact runtime node IDs; unknown identities/cardinalities fail closed. Three old acquisition parameter IDs embed compressed existing robustness-fixture bytes that differ with interpreter/zlib. The first Windows 3.11 A attempt correctly failed node selection (exit 4); the harness now freezes each runtime's exact IDs against the same unchanged source/function contract. No test assertion or synthetic financial fixture was rewritten to normalize IDs.

| Class | Status | Dependency |
|---|---|---|
| A: 767 | Executed engineering scope | Code/nonfinancial metadata and existing software robustness fixtures; zero real-market acceptance |
| B: official reference-corpus case | BLOCKED_INPUT; diagnostic FAIL | Missing original corporate-action .bin snapshot and original ZIP path identities |
| B: three seed backfill/PIT/autoflush cases | BLOCKED_INPUT; diagnostic FAIL | Missing permitted cached symbol-to-ISIN mapping inputs |
| C: 4 realdata-marked tests | BLOCKED_REAL_DATA, NOT_RUN | External/real source authority absent |

The four B names and economic assertions are unchanged. Each unchanged full `pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing` diagnostic actually executes and fails those four cases on all runtimes. B is not counted as passed or executed in A. C alone is deselected in the full diagnostic. No -k filter, added skip/xfail marker, invented snapshot or financial mapping was used.

The first Windows diagnostic additionally failed two legacy guard tests because they expected RuntimeError; guard denial initially used PermissionError. The dual-compatible exception fixes the harness, retaining the security assertions. The stricter external-read guard then refused the known non-market Linux system MIME map; the exact public OS configuration path was added, without general /etc access. A standalone API recheck still hit an existing module-level database environment override and was correctly denied a code-root database write; it is retained as FAIL, not financial/application remediation evidence. Full-suite disposable database initialization supplies its normal A context.

All early failures and preliminary matrices remain. Some preliminary matrices overlapped a later phase-owned test sync; they are not the frozen final acceptance matrix. Only the `*-r3-accepted-*` commands supply final totals and source identities.
