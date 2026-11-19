# Immutable domain v1
Frozen Action/Reference/Raw/Context/Policy/Factor/Link/Result. Typed Split,Bonus,Rights,Dividend,Merger,Demerger,Conversion,Lifecycle parameters. Action records security/listing,exchange,source/evidence/artifact,announcement/publication/ex/effective/record/known/ingested times,version,revision,parent,review and optional established sequence. Unknown timestamps remainNone. Ex-date is comparison boundary, not inferred knowledge or legal effective time.

Inputs finite Decimal <=64digits/exponent64, never float. Query requires valid_at,aware known_at and identity/evidence/calendar/policy versions. Half-open knowledge interval, unique IDs, increasing same-event correction lineage. Missing/unrelated parent or competing child refuses. Consumer profile always explicit.

Statuses: CALCULATED,NOT_APPLICABLE,BLOCKED_EVIDENCE,BLOCKED_KNOWLEDGE,BLOCKED_IDENTITY,BLOCKED_CALENDAR,INVALID_PARAMETERS,CONFLICTING_ACTIONS,UNSUPPORTED_POLICY. Failure cannot emit partial accepted factors/prices. Invalid constructor/timezone contracts raise ValueError. No I/O/network in pure modules.
