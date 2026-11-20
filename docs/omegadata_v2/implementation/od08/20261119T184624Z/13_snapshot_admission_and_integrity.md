# Immutable snapshots and independently reconciled admission
Bind definition, valid/known query, source snapshot, visible membership ledger, coverage, consumer/availability/liquidity policies, relevant identity/calendar/authority and OD07 contexts. Irrelevant future-known inputs do not enter earlier identities. Input ordering is canonicalized; decisions/reasons have deterministic digests.

Repository pinning independently selects required revisions using indexed SQL temporal predicates and reconciles every selected decision. Full visible persisted membership and coverage ledgers must match supplied inputs; omitted members or coverage refuse. Definition, policy and evidence bytes must match stored records. Verify context checksum before admission/replay. Submitted snapshot must match immutable pinned expectation; altered decisions, digests and references refuse atomically.

This is trusted internal-service admission plus independent SQL accounting, not protection against unrestricted same-process code or a DB administrator. Separate literal-set tests verify semantics. No independent human review claimed.
