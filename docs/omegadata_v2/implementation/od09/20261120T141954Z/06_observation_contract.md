# Observation and lineage

[contracts.py](source/src/omegadata/reconciliation/contracts.py) wraps OD08 AvailabilityObservation with stable security/listing/venue, reported symbol/series, publisher, parser/schema versions, row ordinal, field/unit, lineage root and optional universe reference. Unknowns remain unknown. Financial/publication/execution eligibility cannot be supplied by consumers.

The base carries artifact/record identities and independent effective, observed/completed, published, known and ingestion times, evidence and raw/adjusted references. [observation_binding.py](source/src/omegadata/universe/observation_binding.py) checks exact consumed field/value, OD07 raw/context/result IDs/digests, identity/session/venue/units/profile/basis/cutoff. Unrelated valid adjusted volume cannot certify consumed volume. Unsupported unit conversion is refused.

Results retain exact left/right IDs/digests, field/comparability, metric, policy/upstream/authority digests, valid/known cutoffs and algorithm version. Persisted replay checks actual pinned records. Original observations and PriceRecord remain unchanged.
