# Partition and file manifests

Each exchange/month partition has an immutable UUID Parquet object. Entries bind exact relative path, SHA256, byte length, row count, schema fingerprint, partition, dataset version, min/max trade dates and known times, compression/writer and classification. Strict integer checks reject bool counts. Reader independently reconciles these semantics against actual decoded rows and Parquet compression.

Paths are manifest-only, bounded and relative; traversal, unknown names, symlinks, hardlinks, changed bytes and changed descriptor identities refuse. Linux descriptor-anchored `/proc/self/fd` opens preserve the retained Python audit guard without weakening its protected roots. Files are installed O_EXCL with fsync; existing files are never replaced. Unreferenced files cannot join a query through directory globbing. Only approved/generated code-only outputs were hashed.
