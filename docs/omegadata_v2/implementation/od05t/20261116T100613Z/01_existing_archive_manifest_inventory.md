OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Actual selected-source metadata

Fresh guarded [original-metadata scan](logs/original-metadata-scan.json), independent of the inventory implementation's count/digest calculation: 3626 selected NSE CM manifest identities, zero malformed metadata or pinned-identity mismatches. Seed directory: 3596; versioned-cache directory: 30. This is narrower than OD05S's broad 3,676-manifest tree, not a claim that the remaining paths disappeared.

Exact roots: repository data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy and data/raw/nse_equity_bhavcopy. The committed [frozen metadata pins](logs/frozen-metadata-pins.json) contain only relative metadata identities/counts/SHA/length, never payloads. Canonical seed digest: `c7a8519dca8c2a68f307285b420d911124ab5461ebac24a09310eafb446f292c`; cache digest: `bd819991b1b97f17ae1df348b28a02d8f26a2244d8f1b6de873050699ded9d2d`.

Aggregates include declared modes, date/month counts, missing evidence, rights pending, same-date observations and duplicate metadata bytes. Metadata checksums and HTTPS strings remain unverified claims. Multiple same-date revisions and same-byte separate files are retained. No equality of manifest bytes implies equality or validity of market observations.
