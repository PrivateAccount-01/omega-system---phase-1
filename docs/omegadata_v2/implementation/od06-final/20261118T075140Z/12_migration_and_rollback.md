# Tested development migration and production boundary
PersistentRepository.migrate creates only its separate12table od06.store/v1 schema in empty owned disposable databases, enforcesFKs/unique revision parents/indexes/append-only triggers. Empty schema drop and recreation tested on in-memory/file-backed SQLite; nonempty rollback refuses. Exception rollback and native SIGKILL recovery preserve committed history. Cross-process competing revisions serialize. Existing unrelated database schema rejected.

No legacy InstrumentMaster/ISIN keys or production migrations performed. Future production design must map FK consumers SymbolMap/SymbolChangeLog/DelistingRecord/IPORegistry/CrossListingMap plus string-ISIN PriceRecord/UniverseMembership/other models; retain old read behavior with opt-in views. Backups, restore, transaction/idempotence, additive migration rehearsals on an independently authorized target DB and reviewed rollback are mandatory before production.

Current code-only rollback: stop opt-in callers/revert only phase source changes in safe workspace, preserve evidence/databases. Do not delete test outputs automatically or roll back populated history by dropping tables. Correction/reversal appends a new knowledge revision; never overwrite accepted old facts. No production integration before incidents/platform/source gates and separate authorization.

