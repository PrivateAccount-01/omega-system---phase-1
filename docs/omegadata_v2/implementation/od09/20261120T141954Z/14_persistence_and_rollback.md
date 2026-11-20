# Disposable persistence/migration

[repository.py](source/src/omegadata/reconciliation/repository.py) reuses SQLAlchemy/SQLite transaction and typed-codec conventions. Eleven additive tables cover schema, policy, context/result/anomaly, review/correction/request/completion, input index and replacement context. Foreign keys, unique roots/successors and immutable triggers retain history. BEGIN IMMEDIATE serializes writes; digest covering index supports impact lookup.

In-memory and file-backed disposable tests cover insert/retry/changed-ID refusal, restart deterministic replay, rollback, foreign keys, two-connection competing revisions, altered context/result/anomaly, additive migration/schema refusal and nonempty rollback refusal. Repository independently recalculates pinned inputs rather than trusting result lineage.

Operational schema/rows untouched. Empty disposable rollback tested; nonempty accepted history must be retained/versioned, not deleted. Restart/rollback tests do not establish crash-kill or cross-process durability certification.
