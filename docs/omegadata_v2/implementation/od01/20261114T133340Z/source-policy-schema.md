# Source Policy v1 and administrative migration guide

Repository: PrivateAccount-01/omega-system---phase-1. Phase: OD-01 IMPLEMENT_OD01_ONLY.
Branch: feature/od01-source-rights. HEAD before/after: d4b5a58f0c50dc348e0d4e1150a725cc6fab5674 (no commit).
Evidence collected 2026-11-14 UTC; exact command times/exit codes in [logs](logs/). Run directory name was allocated at 13:33:40Z; approval/environment delays mean later commands ran through 15:09Z and document checks later. Owner: same-model procedural engineering reviewer, not a human rights approver.

## Runtime schema

[SourcePolicy](../../../../../src/omegadata/track_a/source_rights.py#L100), [register](../../../../../src/omegadata/track_a/source_rights.py#L268), [request](../../../../../src/omegadata/track_a/source_rights.py#L200), and [decision/error](../../../../../src/omegadata/track_a/source_rights.py#L221) are frozen Pydantic models. Schema tag is exactly `source-policy/v1`; extra fields, unknown enum values, malformed hashes, invalid/naive/non-UTC timestamps, duplicate JSON keys and malformed revisions reject. Lists are materialized as immutable tuples. No dependency or ORM change.

The [runtime register](../../../../../config/source_rights_policy.v1.json) contains exactly the currently discovered **13 keys, 13 PENDING_REVIEW, 0 APPROVED**, revision 1 per source. No permissions, allowed transports or hosts are granted. Human/terms/evidence, rate/retention/attribution/geography/credentials/cost and expiry fields are explicitly null/unknown. Creation time records initialization, not source publication or approval. Technical URLs, eras, checksum and rate/retry metadata in SOURCE_REGISTRY remain unchanged.

## State transitions and evaluation

| Latest state | Decision | Administrative next state (new revision only) |
|---|---|---|
| Missing record/file | MISSING_POLICY | Add reviewed pending record; never infer approval |
| PENDING_REVIEW | POLICY_PENDING | APPROVED only after independent human review, or DENIED |
| APPROVED, complete evidence, valid scope/time | ALLOWED for that operation only | REVOKED/DENIED/EXPIRED/PENDING; renew approval with new human evidence |
| APPROVED with incomplete evidence | EVIDENCE_INCOMPLETE | New evidence-bearing revision, no silent default |
| DENIED | POLICY_DENIED | New review/approval process, with reason |
| REVOKED | POLICY_REVOKED | New human review before fresh approval; revocation requires reason and UTC timestamp |
| EXPIRED or decision_at >= valid_until | POLICY_EXPIRED | New approval revision with a newly reviewed interval |
| Future evidence/approval/start | SCOPE_NOT_ALLOWED | Wait for valid boundary; never backdate evidence |
| Malformed file/schema/history | MALFORMED_POLICY | Correct through administrator review, preserve old decision identity |

Transitions describe the human process. The evaluator is not a workflow authorizer: it validates immutable linked records and always selects the latest revision in the supplied register, even for a request with an earlier timestamp. Revisions begin at 1, strictly increase per source, retain policy_id, link previous_revision_hash and nondecreasing created_at. Reused IDs across sources, duplicate/reordered/unlinked revisions and content-hash mismatches reject. Git plus administrative review must preserve the register's history; the file loader cannot independently detect an administrator replacing the entire register with an older otherwise valid snapshot. A protected trust/checkpoint service is not introduced in OD-01.

Canonical hash: SHA-256 of the validated model's JSON-mode body excluding revision_hash, UTF-8 with sorted keys, separators comma/colon, ensure_ascii=True. Timestamps serialize in Pydantic JSON UTC form. This detects inconsistent record content; it is **not a signature, proof of legal permission, or a substitute for a human approval**.

## Granular operations, transports and time

FETCH, READ_CACHED, STORE_RAW, DERIVE, RESEARCH, TRADE_DECISION_USE, REDISTRIBUTE, COMMERCIAL_PRODUCT are independent. Research or FETCH does not imply trading/commercial/redistribution rights. Optional consumer_purpose must be independently included in permitted_operations. This evaluator can assess downstream scopes; existing research/release/API paths do not acquire complete usage-policy integration in OD-01 (OD-11/12 deferred).

Transports: HTTPX, URLLIB, CURL, CACHE, SEED_CACHE, BROWSER. Browser is a contract enum only; no browser adapter is enabled. Host matching is exact normalized lowercase DNS with a trailing dot removed; schemes, ports, wildcards, credentials and unrelated hosts are not approved by approximation. HTTP(S) request hosts are preflight checked, including explicit discovered/bootstrap/fallback hosts. Full automatic redirect-chain/DNS/SSRF enforcement remains an OD-02 boundary, not a verified OD-01 capability.

For CACHE/SEED_CACHE, requested_host may be null: this denotes a local cached-data use decision, not a remote-host exemption for FETCH. `download(use_cache=True)` requires READ_CACHED before any cache/seed payload check. A cache miss separately requires FETCH and STORE_RAW before discovery; cache permission does not escalate. `use_cache=False` explicitly skips cached-data reads. Transport fallback requires permission for each selected transport. All requests use an explicit aware UTC decision_at; validity is [valid_from, valid_until). v1 does not allow indefinite approval: APPROVED without valid_until yields EVIDENCE_INCOMPLETE.

## Required human evidence and examples

APPROVED requires entity, credential-free terms URL, terms SHA-256/retrieved-at, independent approval_evidence_ref, approved_by/approved_at, and complete approval interval. None may be fabricated. Dates must be UTC and not future at the decision. Scope parameters must also allow the operation, host and transport. Unknown rate/retention/geography/attribution/cost metadata is preserved but lifecycle, geographic and cost-budget enforcement is deferred; an administrator must resolve applicable constraints before authorizing real use.

[policy-examples.json](policy-examples.json) contains one **SYNTHETIC_TEST_ONLY APPROVED** example and a real-source PENDING example copied from the current register. Synthetic evidence identifies example.invalid and a fake principal; it is an executable schema illustration and **must never be installed as a real source permission**. The [test fixture](../../../../../tests/conftest.py) uses explicitly injected fake approvals solely with mock transports. Production construction always loads the pending file, without dev/test bypass flags.

## Human approval process (not performed)

1. Appoint a named source-rights steward; define personal/commercial/research/trading/redistribution use separately.
2. Obtain source-specific permission and terms through a separately authorized process; record original document identity, retrieval timestamp/hash, access/rate/retention/geography/attribution/cost conditions. Do not contact a provider as part of this OD-01 run.
3. Have the human authority review and sign off through an independently reviewable administrative record. Reference that record; do not merely change status/approved_by strings and claim legal approval.
4. Append a linked higher revision containing only permissions actually granted, with finite validity, exact hosts/transports and change reason. Review its canonical hash and diff; no secrets or raw licensed data in the register.
5. Run offline validation/denial tests and check the evidence reference administratively before deployment. A source-policy file hash cannot authenticate the approver by itself. Revocation is another appended revision, not deletion of history.

## Compatibility / README migration note

This intentionally changes permissive DownloadManager behavior: all actual downloads, probes and cached/seeded payload returns now refuse pending sources. Old cache/manifest bytes are not rewritten or retroactively relabeled. Returned DownloadArtifact/SourceProbeResult and new raw manifests include policy decisions with exact ID/revision/hash. SourcePolicyError is separate from provider DownloadError and is terminal across known fallback handlers. Pipeline optional-source handling also propagates it. Private transport calls require a per-manager source scope; StockReachGraph has no dedicated registry identity and refuses UNKNOWN_SOURCE rather than borrowing another BSE feed's rights.

New keys must first join the technical registry and receive pending rights records; source approval and source acquisition remain separate human/phase decisions. Existing marked realdata tests were not altered and remain excluded; they will refuse pending sources until real source rights are approved. Public source-probe generation now fails before curl when pending. No general success claim is made for independent manual probe/developer scripts; they were not executed and are not publication authority.

