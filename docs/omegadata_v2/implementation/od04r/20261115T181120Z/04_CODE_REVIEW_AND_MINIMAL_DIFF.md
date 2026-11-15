# Code review and minimal diff

OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.


Maker/Design Reviewer froze02 before edits. Implementer corrected only after eight existing-behavior assertion failures. Code Reviewer inspected complete raw archive, downloader, acquisition, source-rights, policy, verifier/dry-run and storage paths, inherited tests and exact [application patch](logs/application.patch). Gatekeeper/Historian reconcile commands, identities and preservation. All roles are the same model.

Reproduced defects: vacuous successful scans of absent/empty/incomplete or invalid directory namespaces, and silently suppressed directory traversal error. _inventory now raises INTEGRITY on os.walk errors, preventing incomplete inventory from silently bypassing resource accounting. Missing-root recover_staging remains an explicitly UNVERIFIED read-only inventory; it is not archive completeness proof.

Strict scan checks safe directory roots/namespaces before/after inventory and after replay; missing root NOT_FOUND, invalid layout INTEGRITY, zero default evidence EMPTY_ARCHIVE. Additive strict nonnegative expected_count gives COUNT_MISMATCH when separately pinned count differs; expected0 permits only a pristine existing empty directory. Nonempty default verifies discovered committed snapshot, not exhaustive historical completeness. Output is versioned raw-verification/v2. On-disk object/observation/commit v1 and pinned replay unchanged; no migration. CLI ALL propagates optional count; non-ALL misuse rejects. Existing v1 scan clients must explicitly handle v2 and refusal; no silent compatibility downgrade.

| Component | Current review / proof |
|---|---|
| Frozen request/object/observation/commit | Extra-forbid, revalidated models; known source/era/date/UTC/ID/path/hash/length; no synthetic origin escalation; legal decision strings are consistency, not human attestation |
| put | Validate request and STORE_RAW; validate claimed structure; kernel+thread lock; full request/bytes/current-policy idempotence; bounded reservation; exclusive stage/object/observation then final policy refresh/marker-last verification |
| _publish | fsync stage, full hash check, exclusive hardlink, existing-byte equality, POSIX directory sync; no Windows directory-fsync/hardware-loss promise |
| _verified/read_verified | Current rights/purpose before IO and after replay; source/date before bytes; seed scope; JSON/schema/observation hash/object length+full hash and commit references checked |
| recover_staging | Bounded inventory, no promotion/deletion, marker count explicitly UNVERIFIED; retained stages consume quota |
| scan_verified | R01 v2 correction; mixed namespace refuses instead of silently omitting; external expected-count optional |
| DownloadManager | Opt-in archive injection preserved; legacy cache LEGACY_UNVERIFIED; cache-only miss no fetch; rights rechecks; ArchiveError propagates; unchanged legacy/default paths |
| acquisition/source_rights | Bounded strict validation, denial terminal, redirects disabled, external egress disabled; no edits |
| legacy script/storage | Dry-run reads/hashes without import/write/relabel; known fixed Parquet overwrite remains OD10 |

Only raw_archive.py and verify_raw_archive.py application edits; one new27-case test module. Initial red18-case bytes later reconstructed exactly after helper formatting/additional positives, SHA matched to frozen pre-edit ledger in [red-test-exact.py](logs/red-test-exact.py). Nine later controlled-positive/counterexample cases are not labeled pre-fix reds. Initial lint preview failed on dict style in the new test helper; formatting corrected, assertions unchanged. Old tests untouched. [Ledger](logs/reviewed-before-after-file-ledger.json), [complete tested identities](logs/reviewed-final-tested-identities.json). New critical guard/count/walk lines all execute under coverage; older rare IO/lock/model branches remain partial and reported. Rollback in08; no code migration/GC.
