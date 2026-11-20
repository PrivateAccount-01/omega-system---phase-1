# Independent literal mathematical vectors

PURE_MATHEMATICAL_TEST only, not market observations. Expected fractions are literal independent derivations.

| Inputs/metric | Exact result |
|---|---|
| 3,2 absolute | 1 |
| 3,2 reference-relative (right denominator) | 1/2 |
| 3,2 symmetric-relative | 2/5 |
| 2,3 signed | -1 |
| 3,2 tick size 1/4 | 4 |
| Nonzero left/zero reference | UNDEFINED_DENOMINATOR / UNCOMPARABLE |
| Both zero symmetric denominator | UNDEFINED_DENOMINATOR / UNCOMPARABLE |

Ratio difference is absolute `(left/right)-1`. Exact Fraction is authoritative; Decimal80 HALF_EVEN is display context. PASS <= warning, WARN < failure, FAIL >= failure. Ambient-context independence and finite/resource limits tested. Missing values remain distinct from zero.

Stage A 1/3,2/3 coverage and average/median thresholds use exact ratios before display; extreme-scale median control reproduced and corrected a rounding-based eligibility error.
