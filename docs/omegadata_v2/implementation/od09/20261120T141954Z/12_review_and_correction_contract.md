# Immutable review/correction

[reviews.py](source/src/omegadata/reconciliation/reviews.py) implements allowed OPEN/UNDER_REVIEW/AWAITING_EVIDENCE, CORRECTION_PROPOSED, APPROVED/REJECTED, REPROCESS_REQUIRED/PENDING/VERIFIED and CLOSED transitions. Revisions pin prior digest, affected scope, evidence, reason, policy, role and time.

Correction requires new evidence and changed immutable record. Persisted discrepancy context independently constrains listing/security scope. Unique parent/root constraints prevent competing children; two connections/threads racing on file-backed SQLite yield one commit and one refusal. History remains inspectable.

ReviewerAttestation uses existing EvidenceAuthority and exact reviewer/role/source/purpose/cutoff/claim linkage. No rights or roots changed. Non-market state-machine progression is explicitly nonhuman, not financial approval. Actual trusted positive human acceptance not exercised: no accountable attestation supplied. No queue/alert dispatch.
