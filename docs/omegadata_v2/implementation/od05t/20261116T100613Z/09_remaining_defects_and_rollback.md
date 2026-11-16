OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Remaining risks and rollback

- P0 inherited signing custody and release-promotion findings remain untouched, unwaived and publication blocking. No private key contents or signatures were accessed.
- P1 actual publisher origin, scoped sample/reference rights, real row/schema/date/units/numerical expectations and historical completeness remain unverified. January 2020 routing remains unverified and unchanged; June-July 2024 reference semantics remain unresolved.
- P1 PIT knowledge-time/calendar/instrument identity and historical corrections, corporate-action revision semantics and fixed analytical Parquet versioning remain assigned to separate phases. Metadata readiness cannot waive them.
- P2 SQLite/runtime warning history remains a limitation; retained full logs describe observed warnings. Python-only guard/private-root limits and same-host Windows/WSL limitations remain. No broader P3 audit performed.

Rollback is removal of only the four new phase-owned code/test files in a separately reviewed change; no existing function/default route was modified and no data migration is required. Keep all historical and new evidence unchanged. No automatic cleanup of private copies/outputs, source-policy edits, key remediation, release work or later phase.
