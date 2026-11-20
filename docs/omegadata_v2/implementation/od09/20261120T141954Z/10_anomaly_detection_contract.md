# Explainable anomalies

[anomalies.py](source/src/omegadata/reconciliation/anomalies.py) distinguishes structural invalidity, missing/duplicate rows, identity/time/lineage conflicts, cross-source discrepancies, expected venue differences, unexplained jumps and corporate-action explanations. OHLC ordering, negative volume and missing values are explicit findings; a large move alone is not proof of error.

Corporate-action explanation requires exact replayed OD07 UpstreamProof and matching raw observations, identity, basis, session and cutoff. Scalar factors/future context cannot certify it. Persistent directional discrepancies are diagnostic. Repository recomputes anomalies against pinned context, refusing arbitrary caller findings.

No repair, deletion, imputation or source mutation. Authentic anomaly labels remain blocked externally.
