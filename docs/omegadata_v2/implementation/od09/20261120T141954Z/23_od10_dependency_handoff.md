# OD10 code-only handoff

OD10 may consume versioned observations/comparison contexts; PASS/WARN/FAIL/UNCOMPARABLE; exact source/result/policy/context digests; anomaly records; immutable review/correction lineage; exact reprocess scope/completion. These are engineering outputs, not authenticated market facts or publication authorization.

Controlling master OD10 is versioned Parquet/DuckDB/manifests. Separately authorized implementation must retain exact rows, stable IDs, valid/knowledge cutoffs, identity/calendar/adjustment/universe digests, tolerance versions and immutable revisions. Keep raw and derived bases separate. Admission must replay pinned context and account for blocked/uncomparable inputs, preserving old as-known outputs.

Proposed tests: source/manifest pins, tampered/missing-row refusal, Decimal roundtrip, temporal replay, partition completeness, schema-version refusal, atomic idempotent commits, restart/rollback and retained unresolved review/reprocess blocks. No operational migration or market reprocessing authorized.

One next action: owner review and separate authorization for bounded OD10 code-only work. Authentic references, accountable incident disposition, Windows isolation and production permission remain independent. OD10 was not executed.
