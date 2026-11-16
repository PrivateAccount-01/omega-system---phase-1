OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.

# Independent metadata comparator

The stdlib-only oracle imports no application inventory/validator methods. Before application creation it enumerated only *.manifest.json under two explicit real source directories, pinned names/count/SHA/length, and computed a canonical digest. Positive count is mandatory. Tests compare independently frozen counts and digests, check original bytes against those pins, and reject missing/moved/empty/tampered/count-mismatched corpora and duplicate/mutable/unsafe expected pins.

[Frozen original metadata pins](logs/frozen-metadata-pins.json), [pre-code identities](logs/precode-freeze.json), [fresh original-scan comparison](logs/original-metadata-scan.json) and final runtime node results establish metadata reproducibility. Identical semantic code/tests are SHA-checked before every accepted command. Actual Linux and Windows inputs derive from the same private copied original metadata and pins.

This is a separately implemented mechanical comparator authored by the same agent, not an independent human financial review. It verifies neither publisher provenance nor payload hash/schema/numerical values. Metadata SHA matches never enter financial correctness metrics.
