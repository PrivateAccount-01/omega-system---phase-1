# Targeted reproductions

Initial 18 safe controls:16 failed,2 passed. Binding API absence was NEW_FEATURE_ABSENT; observation omission, unsupported temporal precision, indiscriminate future-effectiveness refusal and nonterminating arithmetic were reproduced defects.

Strict v2 binds the exact consumed scalar and identities to OD07 raw/pin/result digests. Persisted observations are independently selected by pinned source/listing/type/session/policy scope; explicit partial exclusions remain visible. Announcements differ from completed financial observations. Timestamp coverage requires exact supported reference instant; date-only boundaries cannot invent intraday precision. Liquidity thresholds use exact rational comparisons before display rounding.

Later controls reproduced missing/wrong snapshot instants and an extreme median rounding error. Corrected in this execution; initial 32-case gate is preserved, final gate supersedes it. Original 92 OD08 tests and limited v1 helper remain unchanged. [Actual failures and frozen tests](support/negative-first.json).
