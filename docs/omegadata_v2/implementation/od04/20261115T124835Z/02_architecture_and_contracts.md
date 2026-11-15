# ADR-OD04-001: bounded opt-in raw archive

Status: proposed technical design under explicit OD-04 implementation authority;
not human financial/source approval. Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182.

Before production edits: add raw_archive.py, a narrow downloader constructor/
storage branch and additive artifact identifiers, two read-only CLI utilities,
new unit/process tests. No changes to acquisition validators, rights, analytical
Parquet, ORM, existing tests/config/dependencies, releases or historical paths.

Contracts: frozen Pydantic raw-object/v1, raw-observation/v1 and raw-commit/v1.
Object identity is full SHA256 of bytes. Observation/operation ID is 32 lowercase
UUID hex, supplied explicitly for retries or generated for a distinct event.
Retry identity includes every observation field, including explicit observed UTC
time; no retry timestamp substitution. Unknown published time remains null.
Commit references canonical JSON digest of observation plus full object digest,
length and ID. JSON is bounded, rejects duplicate fields and unknown schemas.
Semantic replay includes entire immutable observation; commit time is nonfinancial.
Mode is never official/release-approved; source-reference state stays pending.

FSM: CANDIDATE -> STAGED (exclusive same-filesystem transaction directory) ->
VERIFIED -> immutable object -> immutable observation -> COMMITTED marker last.
Crashes leave retained staging/orphan objects/observations, never automatic cleanup.
Recovery is a bounded read-only inventory, not a retention/GC decision. A committed
read requires all three records to validate; corrupt or missing links refuse.

Publication alternatives to execute on both platforms:
1. fsynced staging file -> os.link exclusive final name, validate any existing
   destination, no overwrites. Selected if capability proof succeeds.
2. OS advisory lock (flock/msvcrt, auto-released on process death) + fsynced staged
   file -> rename into absent destination. Test prototype only, not two stacks.
Selected hardlink strategy also uses one OS advisory lock around bounded quota
accounting and writes. A process-local RLock covers Windows byte-lock semantics
within a process. No stale-lock deletion: kernel unlocks on close/crash; bounded
acquisition timeout fails with typed ARCHIVE_BUSY. Final reader never takes lock.
POSIX directory fsync after linking; Windows directory durability unavailable.
No unsupported power-loss/remote-filesystem durability claim. Hardlink unavailable
fails closed; no overwrite/copy fallback. Same-filesystem local trusted root only.

Root must be explicit, private, writable; no implicit setting changes. Reject
static symlinks/junctions/reparse escape at all root/metadata/object ancestors and
leaves before access; trusted ownership required throughout operation. No claim
of descriptor-atomic protection against malicious concurrent directory owners.
Bounds: 16 MiB candidate, 64 KiB JSON record, 128 MiB retained archive and 4096
filesystem entries, 5 second writer wait, four worker process test maximum.
Every stage is retained and charged to budget. Exhaustion refuses, no GC.

Source authorization precedes mkdir/write. STORE_RAW checks origin transport/host
and consumer purpose; READ_CACHED checks CACHE/SEED_CACHE and consumer purpose
before record access, then verifies source/date before object open. Policy is
refreshed before final commit. Stored decisions are evidence, never authorization.
No default source approvals or external egress change. Each actual read checks
current rights, including revoked state. Default archives cannot access pending
sources. Explicit synthetic approvals exist in tests only.

Downloader opt-in: constructor raw_archive plus optional operation_id/observed_at
on download. Fresh validated payload enters new archive, no legacy raw write.
Default cache facade retains existing checks; archive-mode legacy cache reads
return LEGACY_UNVERIFIED and no commit ID, never imports/writes. Cache miss with
cache_only refuses without fetch/storage. Archive replay requires explicit pinned
ID; never infer latest. Artifact additions observation_id/commit_id/archive_state
are optional. Public default callers remain compatible.

Errors: INPUT_INVALID, INTEGRITY, CONFLICT, STORAGE_FAILURE, ARCHIVE_BUSY,
BUDGET_EXCEEDED, NOT_COMMITTED; context contains codes only. Rights errors pass
through unchanged. Fault callbacks exist only on new service instance and execute
at before_stage/after_stage/after_object/after_observation/before_commit boundaries.
Exception mocks are distinct from forced worker death. Recovery never promotes.

Verification: independent hashlib/byte reader; existing protected runner unchanged
except fresh evidence location and baseline ID; separate trusted local worker
runner with exact executable/script/args allowlist, private root and enforced
DNS/socket/process/write denial in children. Both Windows/WSL native filesystems;
fixture exact hashes from OD02V allowlist, no new market fixtures/network.
Negative-first tests exercise unchanged downloader for hash naming/event collapse,
mutable latest, wrong existing payload and crash interruption. New API availability
failures are not counted as old-application defect proof. A01-A28 map in matrix.

Rollback: disable opt-in/new module callers, retain archive/new evidence unchanged;
no migration/backfill or deletion. Dry-run migration only reports bounded confined
synthetic legacy records and proposed hashes, origin LEGACY_UNVERIFIED. D03 is only
partially addressed for raw acquisition; canonical Parquet remains OD10.

Adversarial design addendum before correction: a direct archive caller could
declare structurally valid state for HTML. The executable red-structural-state
test demonstrates this in the first implementation. Reuse existing OD02
validate_payload/load_limits before any storage when structural validity is
claimed; require exact returned state and parser schema. HTTP_RECEIVED remains
uninterpreted raw capture, never financial certification. Add conservative media
hint and explicit source-reference warning fields without changing content ID.

Inspection API addendum: recover_staging reports UNVERIFIED marker counts only;
scan_verified performs bounded, current-rights-authorized full-byte verification
and returns sorted deterministic raw-verification/v1 evidence. Mixed source/date
roots refuse rather than silently omit records. The read-only verifier accepts
ALL as explicit scan mode in place of a pinned hex ID. No promotion or repair.
