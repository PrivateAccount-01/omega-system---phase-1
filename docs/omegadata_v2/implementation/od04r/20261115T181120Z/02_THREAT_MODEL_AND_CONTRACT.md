# OD04R design freeze — before application corrections

RUN identity: feature/od01-source-rights @ 44090a42958869faaab57a42b65f7ad8571d924d. Same-model procedural review only.

TEST/SYN contract: read-only recovery remains an explicitly unverified inventory. Strict scan v2 refuses missing roots (NOT_FOUND), non-directory roots/namespaces and traversal failures (INTEGRITY), and zero-marker default scans (EMPTY_ARCHIVE). A caller may separately pin expected_count: nonnegative strict integer; mismatch COUNT_MISMATCH. Expected zero permits only an existing genuinely empty directory (no retained artifacts). A count does not authenticate source truth or establish a complete externally expected corpus unless supplied independently. Root disappearance after inventory refuses. Nonempty default scan verifies all discovered committed evidence without asserting historical completeness. Existing per-observation and on-disk v1 formats remain unchanged; no migration.

Threats: static links, malformed JSON, wrong bytes, bounded resource exhaustion, revoked rights, publication interruption and cooperative independent processes. Trusted private local owner boundary; no hostile parent-swap, NFS, hardware power-loss, independent host or official market truth certification. Existing R02–R17 tests will be reused only after exact-node reconciliation. Missing roots and empty results are the primary new suspected defect; no application correction before asserted failure logs. New expected_count tests specify additive behavior; missing API errors alone are not defect proof.

Gate: historical OD04_BLOCKED remains ARCH; no human exception exists. A technical pass cannot waive chronology or authorize OD05.
