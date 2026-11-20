# Dependency and reprocess impact

Exact (kind,identity,digest) edges bind source/identity/calendar/action/adjustment/universe/reconciliation/review/correction/reprocess references to storage versions and intermediate metadata. Full-body typed pins include dependencies, so an identical ID cannot silently acquire changed edges. Reverse indexes and bounded transitive queries return all registered matching historical outputs, not only the currently selected version.

Unknown knowledge time is not inferred. Future-known metadata is excluded at the requested cutoff. Later corrections do not invalidate legitimate earlier as-known files. Coverage remains DEPENDENCY_UNKNOWN: registered edges are searchable but missing upstream registration cannot self-certify complete reprocess impact. No repair/recompute job runs automatically. OD11 must combine these exact references with OD09 independently verified completion requirements.
