## Fixture Provenance

- `official_source/`: fixtures built from bundled official-source artifacts used for real-data-backed verification.
- `synthetic_manual/`: hand-computed synthetic cases used to pin transformational adjustment math and edge cases.
- `synthetic_seed/`: seeded synthetic packs used to test deterministic backfill and reconstruction flows.

The runtime pipeline and verification artifacts under `artifacts/verification/` should be read separately from these test fixtures.
