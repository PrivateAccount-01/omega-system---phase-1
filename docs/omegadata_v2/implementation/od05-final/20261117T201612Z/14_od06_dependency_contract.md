# OD06 dependency contract (handoff only)

- **source_id**: ParseResult/ParsedBar.source_key.
- **format_era**: ParseResult.format_id, illustrative only; no official era inferred.
- **schema_version**: schema_catalog lookup by exact format_id:od05.illustrative-cm/v1.
- **parser_version**: ParseResult.parser_version pinned syn-v1.
- **exchange**: ParsedBar.exchange.
- **source_venue**: Catalogue NSE_CM, unverified metadata.
- **trade_date**: ParsedBar.trade_date.
- **symbol_as_reported**: ParsedBar.symbol, original text retained.
- **series**: ParsedBar.series, opaque illustrative value.
- **isin_if_available**: ParsedBar.isin optional, not authenticated identity.
- **instrument_attributes**: Not established; downstream source-backed enrichment or quarantine required.
- **source_artifact_identity**: ParseResult.raw_sha256 plus optional observation_id; hash is not publisher truth.
- **data_quality_status**: PARSED_UNVERIFIED or QUARANTINED, never financially accepted.
- **source_authentication_status**: SYNTHETIC_TEST_ONLY/UNVERIFIED.
- **source_rights_status**: No real grant; registry remains pending.
- **known_from**: Unknown/None; never infer from trade_date.
- **effective_at**: Unknown/None; requires verified identity/event evidence.
- **ingested_at**: Unknown/None; trusted ingestion observation must supply it.

Consumer invariants: reject QUARANTINED and unsupported/official claims. Preserve source row ordinal, original lexemes, raw identity and exact source/format/parser versions. PARSED_UNVERIFIED alone cannot certify an instrument, PIT universe, financial release or economic research. Never fill availability timestamps or ISIN from guesses. Results are immutable; separate versioned enrichment must retain lineage. Financial/source-dependent facts stay unknown/quarantined until permitted evidence exists.
