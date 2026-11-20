# Catalog and rollback

Thirteen additive catalog tables cover schema versions, definitions, versions, physical files, partition references, operations, dependencies, selection events, typed references, source indexes, comparison scopes and catalog version. FKs, unique IDs, BEGIN IMMEDIATE, synchronous FULL and immutable UPDATE/DELETE triggers preserve accepted facts. Typed payload codec reuses existing upstream persistence conventions; it is not pickle or arbitrary dynamic module loading.

Read-only consumers use SQLite query_only plus explicit write refusal; opening a reader does not acquire the initialization writer transaction. This is an API/SQL read-only guarantee inside the worker, not protection from arbitrary same-process access to its engine or host admin writes.

Rollback selects the exact old committed manifest with an append-only development event. Empty disposable schema rollback is tested; any nonempty fact/object/manifest refuses destructive rollback. No accepted history is deleted. The catalog is tested in owned disposable file-backed SQLite; upstream in-memory repository regressions remain separately passing. No operational migration was performed.
