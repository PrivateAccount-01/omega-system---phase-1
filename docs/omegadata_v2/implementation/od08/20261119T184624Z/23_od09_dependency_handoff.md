# OD09 code-only dependency contract READY; execution not authorized
OD09 concerns cross-source price/metadata reconciliation, anomaly handling and review. It may consume exact OD05 parser provenance, OD06 stable identities/calendar, OD07 bound adjustments and OD08 immutable universe snapshots/decisions. Preserve valid/known timestamps, permissions, venue/listing identity, raw versus adjusted bases, methodology and all digest/policy versions.

Proposed opt-in interfaces: comparable_observation_pair, reconciliation_result(PASS/WARN/FAIL/UNCOMPARABLE), source-specific versioned tolerance, discrepancy lineage and immutable reviewed correction/reprocess request. Different exchanges/price bases are not automatically comparable. Agreement cannot confer authenticity; confidence cannot mask a hard block. Preserve provisional, unresolved, coverage and availability states. Anonymous controls can test false-positive/false-negative behavior; authentic thresholds require permitted references.

Reusable modules: universe.contracts/temporal/snapshots/repository, identity, session_calendar and adjustments v2. Audit existing track_b/cross_source_validation.py, confidence.py and manual_review.py before editing. No OD09 implementation occurred.

One next development action: owner review and explicit bounded OD09 code-only invocation. Authentic constituent/availability acceptance, source rights, incident disposition, Windows assurance and original-checkout migration remain separate blocked requirements. Readiness is not production approval.
