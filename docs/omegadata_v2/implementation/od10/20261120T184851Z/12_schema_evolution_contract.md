# Schema evolution

canonical/v2 adds nullable source_note without changing canonical/v1. Physical types plus semantic version metadata have immutable fingerprints. Conversion decodes verified historical bytes and writes a new version, referencing its parent; previous files remain intact. Unknown schemas and unsupported/reverse lossy conversion refuse rather than relying on an Arrow cast.

Increasing precision or changing financial semantics requires a new explicit implementation/version; it is not silently treated as compatible. The bounded current converter is the tested v1→v2 additive path; arbitrary conversions are unsupported. Original and converted query results, restart, old manifest and byte identities were checked on disposable storage.
