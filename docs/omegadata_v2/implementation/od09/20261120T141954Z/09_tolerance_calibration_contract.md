# Versioned tolerance/calibration

Immutable TolerancePolicy pins source pair, venue/field/type/scope, units/metric, boundary convention, valid/knowledge intervals and calibration/review identity/cutoff. Selection requires exactly one eligible version; future calibration refused.

[calibrate](source/src/omegadata/reconciliation/tolerances.py) accepts bounded supplied samples; excludes missing/future availability, dependent lineage, wrong buckets and unsupported periods; rejects duplicates/invalid values. Pinned training nearest-rank p90/p99, no outlier deletion, separate validation labels and sample adequacy produce transparent FP/FN counts on literal controls.

Results remain PROVISIONAL_ALGORITHM_RESULT and BLOCKED_CALIBRATION authenticity. No authentic market threshold, sample independence or actual FP/FN performance is claimed. Legacy thresholds remain uncalibrated compatibility infrastructure.
