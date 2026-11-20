# Disposable SQLAlchemy/SQLite
Nine additive tables: schema, definition, membership, coverage, availability, policy, context, snapshot and decision. Foreign keys bind definition/parent/policy/context/snapshot/member. Unique parent serializes corrections. Append-only UPDATE/DELETE triggers, BEGIN IMMEDIATE, identical retries and changed-ID refusal. Event/as-of indexes avoid full-ledger validation per append.

Actual tests: memory/file-backed insert/reopen, replay after restart, immutable history, two concurrent connections (one commit/one refusal), controlled rollback, FK refusal, fresh migration, empty rollback and nonempty refusal. Unknown schema/version refuses. No operational migration or destructive history rewrite.

OD06/OD07 are separate upstream stores: contexts bind immutable typed snapshots and authority state. No distributed transaction or implicit live refresh. Production needs separate ownership, backup/restore, upstream-consistency and migration rehearsal. Rollback disables the opt-in path while preserving accepted evidence; no automatic cleanup.
