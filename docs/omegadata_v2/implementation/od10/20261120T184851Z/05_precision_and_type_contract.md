# Precision and type contract

UTC microsecond timestamps, date32 dates, int64 positive source ordinals, string IDs retaining leading zeros, nullable fields, bool eligibility and explicit list/struct lineage. Null, missing, unavailable, invalid and genuine zero are separate states.

Raw fixed Decimal128(38,12), factor fixed Decimal256(76,36); values must fit exactly. CALCULATION overflow uses a canonical coefficient string/exponent codec (bounded 1,000 digits, exponent ±9999), never a float or silent rounding. Exact rational terms are separate numerator/positive-denominator strings. Lossless coefficient/exponent retains Decimal trailing-zero quantum; optional fixed columns are independently reconciled on read. Raw unsupported precision refuses. Calculation precision and storage precision are distinct; display formatting is not a financial transform.

Literal Decimal/rational known-answer tests cover boundaries, trailing zeros, negative scalar values where allowed, null/zero, timezone normalization, physical-column tampering and nested lineage. No new market observation was created.
