# Canonical schema registry

[schema.py](source/src/omegadata/canonical_storage/schema.py) provides immutable physical schema fingerprints for canonical/v1 and /v2. source_observations and adjustment_results use separate RAW/DERIVED Parquet domains. instrument_identity_revisions, listing_lifecycle, session_calendar, corporate_action_revisions, universe_membership_revisions, universe_snapshots, universe_member_decisions, reconciliation_results, anomaly_records, review_revisions, correction_revisions, reprocess_requests and reprocess_completions use typed transactional metadata.

Exact domain/class whitelists prevent a parser object from masquerading as a review revision. One-to-many relationships remain nested typed references and immutable ledger records. Domain rows are not collapsed into one wide financial table. Full Arrow schema/type text and domain map are in support/schema-contract.json. No operational schema migration occurred.
