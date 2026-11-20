# Economic comparability

[engine.py](source/src/omegadata/reconciliation/engine.py) uses indexed bounded candidate groups; missing and conflicting counterparts remain explicit. Check security/listing/venue, session/interval/type, basis, currency/unit and knowledge before arithmetic.

Equivalent same-venue observations may compare. Different-venue same-security price comparison needs explicit policy/identity; volume is not universally interchangeable. Venue-specific differences are not parser corruption. Adjusted observations require replayed OD07 v2 contexts and compatible profiles/bases/cutoffs.

Same upstream lineage is flagged DEPENDENT_SOURCE_LINEAGE. Agreement cannot establish independence, publisher authenticity or permission. Imputed, incompatible, unresolved or unavailable inputs yield UNCOMPARABLE. Numerical PASS does not grant financial acceptance.
