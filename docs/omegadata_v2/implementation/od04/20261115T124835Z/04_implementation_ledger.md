# Exact implementation ledger

Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.

Only one original application file changed: download_manager.py, additive optional
archive integration and artifact IDs, early return before legacy writes, legacy
cache label. New files: raw_archive.py; tests/unit/test_od04_raw_archive.py;
scripts/verify_raw_archive.py (pinned or ALL scoped verification); scripts/plan_legacy_raw_import.py
(single validated legacy candidate, dry-run mapping only); repository decision and
this fresh eleven-report evidence directory with narrowly scoped helpers/logs.

raw_archive: frozen strict schemas; full SHA paths, separate UUID events; immutable
request/policy identity; kernel lock timeout and quota reservation; same-filesystem
exclusive stage + fsync + hardlink; marker last; current rights before IO and commit;
verified replay/scan; read-only recovery inventory; conservative source-reference
warning and unknown published time. Structural validity requires actual OD02 validator.

First implementation corrections were driven by executable adversarial reds:
synthetic-origin relabeling refused; policy revision hash included in retry identity;
claimed structural validity reruns existing bounded validator and matches schema.
No changes to acquisition.py, source_rights.py, policies, analytical paths, ORM,
dependencies, config, workflows, old tests/evidence, actual data/releases/keys.

[Final patch](logs/implementation.patch) includes tracked diff and new source/test/
CLI content. [Final preservation](logs/final-preservation-reviewed.json) verifies original
records and each final runtime's exact overlay hashes. [Design before code](02_architecture_and_contracts.md)
records interfaces, state machine, limits, risks and rollback. The ADR is technical
proposal, not external administrative approval. Code remains uncommitted/unstaged.
Rollback is opt-in removal/disablement after review, retain archive/evidence;
no deletion, migration or rollback executed.
