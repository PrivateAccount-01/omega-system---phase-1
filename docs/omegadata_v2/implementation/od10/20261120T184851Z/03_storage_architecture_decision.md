# Storage architecture decision

Use existing PyArrow23.0.1 + immutable Parquet + SQLAlchemy2.0.49/SQLite transactional catalog. Arrow typed scanning covers bounded projection, predicates, scalar aggregation and stable-identity metadata joins without another dependency. DuckDB is absent in the permitted environment; its install/license/version experiment is NOT_RUN_DEPENDENCY_UNAVAILABLE. No dependency or network setting changed.

SQLite commits govern reader visibility, while no-replace file installs and retained orphans make cross-resource failure recoverable. This does not make filesystem and SQLite one atomic resource. UUID identities avoid manifest alias across catalogs; operation input digests provide idempotency within the catalog. Exchange/month partitions and 8192-row zstd groups are bounded defaults; measured snappy/zstd and group-size alternatives are retained without asserting universal optimality. See [measurements](21_performance_results.json).
