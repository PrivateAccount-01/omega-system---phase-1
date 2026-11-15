# Preflight and identity

OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.


Actual branch and starting HEAD exactly match the requested identities; both remain unchanged. Main remains d4b5a58f0c50dc348e0d4e1150a725cc6fab5674. Before edits tracked tree was clean; untracked .venv-linux, phase prompt and three signing-path items were already present. No reset/stash/checkout/index/commit/push/merge. [Initial status](logs/git-status.txt), [history](logs/git-history.txt), [main...HEAD comparison](logs/main-diff.txt), [final status](logs/final-status.txt). Main comparison was recorded after edits, but both commits were unchanged and main...HEAD excludes working edits.

Before application correction: full [preservation snapshot](logs/preservation-before.json), [exact Git-blob copy/47-fixture allowlist](logs/copy.json), [red source/test hashes](logs/red-source-identity.json), [prior accepted hash comparison](logs/accepted-old-identity-match.json), [design freeze](02_THREAT_MODEL_AND_CONTRACT.md) and asserted red run existed. This narrative report was assembled after verification; no claim it existed earlier. Five pre-edit working hashes match all prior accepted final source/test hashes. Initial red copy matches reviewed source.

Authorized changes: reproduced raw scan/inventory defects, read-only verifier semantics, one new test module and fresh evidence/helpers. Downloader unchanged. No config/policy/registry/dependency/ORM/Parquet/release/CI/signing change. Previous Gatekeeper ARCH OD04_BLOCKED; no owner exception.

Fresh clean rooms contain exact tracked src/scripts/tests/config plus README/pyproject; only 47 previously approved root fixture paths added after SHA match. No .env, environments, production DB, keys, releases or unknown raw directory copied. Fixture labels remain historical claims, not authenticated financial truth. [All 146 tested source/config/test files](logs/reviewed-final-tested-identities.json) match on all three copies; exact additional fixture list is in copy.json. Separate Windows3.14/Windows3.11/Linux copies prevent concurrent overlay races. Existing runtimes3.14.3/3.11.15/3.12.3 reused; no installs. [Runtime matrix](logs/current-runtime-matrix.json) records executable/OS/UTC/versions/packages/argv/cwd. Linux process roots are native persistent /home/parilrupani; pytest writes only disposable storage. Filesystem type is recorded only where actually probed; no remote/NFS or hardware durability certification.

[Preservation](logs/reviewed-preservation-comparison.json):12,137 original records compared; only two authorized application files differ. All old tests/evidence/data/DBs/releases/config bytes unchanged. Signing metadata unchanged; key contents never opened/hashed/copied. Pre-existing untracked environment contents were not exhaustively hashed; no command mutates them. The untracked phase prompt was read only. [Before/after ledger](logs/reviewed-before-after-file-ledger.json).

RUN final filesystem identity: Windows tested C:/E: volumes NTFS; Linux native/home stat reports ext2/ext3 family. Exact probes in [Windows](logs/windows-filesystem.json) and [Linux](logs/linux-filesystem.json). Narrative assembly follows actual verification and does not retroactively assert a pre-edit report creation time.
