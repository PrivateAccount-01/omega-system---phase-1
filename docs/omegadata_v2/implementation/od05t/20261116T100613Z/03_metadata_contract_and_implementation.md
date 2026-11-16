OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Additive contract and reuse decision

Added [archive_candidate_inventory.py](../../../../../src/omegadata/parsers/archive_candidate_inventory.py), [CLI](../../../../../scripts/audit_existing_market_archive.py), [engineering tests](../../../../../tests/unit/test_od05t_archive_inventory.py) and [stdlib oracle](../../../../../tests/unit/od05t_metadata_oracle.py). Exact final identities are [frozen](logs/accepted-source-freeze.json), with per-command matching hashes. No existing application/test/config file was edited.

Frozen ExpectedMetadata pins relative manifest names, full SHA and length. Nonempty corpus, exact expected names/count and bytes are checked; untrusted index contents cannot set their own pass threshold. The oracle froze these metadata expectations before application code, but they are not independent human publisher or row attestations. Inventory rows are frozen and canonical identity is enumeration/OS independent.

Metadata-only authority is an explicit caller-controlled root; CLI limits its production entry point to the two named NSE CM directories. It never dereferences declared artifact paths. Reuse OD05R no_links/read_file for lstat/reparse/hardlink and descriptor identity checks, plus duplicate-key refusal. Stdlib dataclasses/hashlib/json/pathlib and the existing dependency stack suffice; no new packages, copied downloader, Pandera or transport client. No external repository/advisory/license-clearance claim is made.

Limits: 5,000 manifests, 20,000 entries, depth 12, 65,536 bytes per manifest, 64 MB total manifest bytes, 30 seconds per production scan; strict bounded caller reductions only. Separate pin JSON cap 2 MB. Code-only public errors, URL scheme categories only, unsafe absolute artifact claims redacted. Caller permission/reviewer strings stay PRESENT_UNVERIFIED/RIGHTS_PENDING and never grant payload use.

CLI requires --manifest-root, separately supplied --expected-pins and --metadata-only. Source/date filters, --dry-run and fresh external --output-dir supported. Success exit 0 means metadata engineering only; --require-real-data always exits 3; unsafe/incomplete/error requests exit 2. Help/usage are argparse exits. No operational default imports/integration added.

Separate reviewed-attestation design: an accountable external human must bind exact original document/sample/expected-value hashes, publisher receipt, role/date and granular operation rights to independently held pins. This tool only exposes missing declarations; it has no trust anchor, cannot ingest a self-approved authority, and does not mint DOCUMENT_IDENTITY_PINNED, reference approval, source permission or release eligibility.
