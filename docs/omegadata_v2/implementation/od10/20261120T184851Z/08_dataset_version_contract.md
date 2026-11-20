# Immutable dataset versions

Dataset/version/schema/partition/file/manifest/operation identities are distinct. Exact sorted input digest binds operation retry; opaque version IDs bind a unique manifest within/across tested catalogs. Same operation plus changed inputs refuses. A correction creates a successor with validated supersession/knowledge lineage; prior bytes and manifests remain unchanged.

Manifest binds complete files/partitions/rows, schema and writer versions, scopes, exact upstream references and financial block states. STORAGE_COMMITTED means reader-visible storage only; publication is NOT_AUTHORIZED. No production release pointer exists. Development selection events are append-only and do not confer source approval.
