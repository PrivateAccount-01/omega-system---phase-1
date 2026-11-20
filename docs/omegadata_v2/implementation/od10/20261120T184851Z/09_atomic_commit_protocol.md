# Atomic reader-visible commit

Pin definition/rows/operation/parent/expected partition set. Write private attempt files. Decode and reconcile every staged typed value. Install immutable files without replacement. In BEGIN IMMEDIATE, recheck operation identity and expected parent, bind complete file/partition/dependency/manifest metadata and commit catalog. Reopen committed version through the normal verified reader.

Concurrent incompatible successors are refused, not silently last-writer-wins. Installed files before a failed transaction remain orphans. A postcommit/preack retry returns the original operation identity. File fsync and directory fsync support local process-crash recovery; this is not hardware power-loss certification. Supported readers see committed manifests only. [Process results](10_concurrency_verification.json) and [fault evidence](11_crash_recovery_and_orphan_accounting.md) preserve exact tested guarantees.
