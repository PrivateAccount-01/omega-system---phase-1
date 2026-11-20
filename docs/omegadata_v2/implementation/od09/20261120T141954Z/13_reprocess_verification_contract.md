# Exact reprocess contracts

Persisted input-index lookup derives impacted contexts from exact corrected observation digests. Requests pin correction, affected listing/session scope, source revisions, adjustment/universe references and dependency versions; unrelated records cannot be inserted/omitted silently.

ReplacementContext binds exact old/new contexts and revised inputs. Admission replays replacement results and rejects unchanged old output identities. UpstreamProof replays OD07 PinnedCalculation or OD08 UniverseContext under its cutoff. Missing downstream proof blocks completion.

REQUESTED/QUEUED/RUNNING/FAILED/BLOCKED_DEPENDENCY persist before outputs exist and never clear blocks. Successful outputs remain COMPLETED_UNVERIFIED absent independent authority. Transition to REPROCESS_VERIFIED checks persisted request/completion/review lineage and trusted attestation. No actual market reprocessing or publication. No hostile same-process tamper-resistance claimed.
