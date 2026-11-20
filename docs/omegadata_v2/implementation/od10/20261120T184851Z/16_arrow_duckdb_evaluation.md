# Arrow and DuckDB evaluation

Arrow23.0.1 was already permitted and passes exact Decimal/date/timestamp/string/list lineage roundtrip, versioned manifests, stable filters, projection, exact scalar aggregation and metadata joins. The scanner uses Parquet fragments from verified buffers; partition/date pruning chooses only catalog-approved members. Independent literal expected row counts and sums were checked at 1k/10k/100k structural scales.

DuckDB is not installed. No unrestricted network/install was enabled, no version/license adoption was claimed, and no DuckDB performance result exists. Therefore retain Arrow. This is a dependency-constrained comparison, not a claim that Arrow outperforms an unexecuted engine. Actual timings, RSS, file sizes, compression alternatives and query-plan evidence are in [performance](21_performance_results.json).
