OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY; run 20261115T201333Z. Evaluated 2026-11-16T08:23:11.592393+00:00. Branch feature/od01-source-rights; unchanged local HEAD bf6f4894c9e5237e8c1a44b625c66b8a420b4aad. RUN=new executed checks; TEST/SYN=synthetic fixtures; ARCH=prior evidence; UNK=unverified official semantics. Same-model procedural review, not independent human/financial/legal certification.

# Additive changes and compatibility

New package only: __init__.py documents opt-in scope; contracts.py frozen contracts/limits; reference_registry.py fixed illustrative profiles, no approval authority; nse_cm.py strict CSV/ZIP/Decimal/date/identity/quarantine; dispatch.py explicit selection and optional current-rights/pinned-observation facade. Two new test files: test_od05_era_parsing.py and od05_oracle.py. Evidence helpers/docs/logs remain under this new run.

No existing application/test/fixture/config/policy/dependency/UI/script/release/signing/DB file modified. Existing PriceRecord, acquisition validator, source registry, downloader, raw archive, loader and backfill/probe behavior unchanged. No global2020→2024 replacement. Old routing known uncertainty remains outside scope. No production integration toggle was added: default production path never imports/calls the parser.

Entry handoff remains owner-owned untracked content. Environment/private signing entries remain untracked and untouched. No cleanup/stash/reset/history rewrite, migration, source fetch, signing, release, merge, commit or push. Rollback is stop explicitly calling new functions; existing consumers already use their original path. Preserve evidence even if feature is later superseded. [Exact new code/test SHA ledger](logs/final-source-freeze.json); line references resolve in current new files.

