# Bounded OD06 handoff ? no execution authorization

Proposed mode:OD06_CODE_ONLY_INSTRUMENT_IDENTITY_AND_CALENDAR_IMPLEMENTATION, in the approved data-free snapshot only, AFTER explicit owner authorization and acceptance of the gate-separation ADR. Begin from reviewed HEAD plus delivered OD05 patch, verify exact code pins. No execution/integration in the original mixed checkout before incident disposition. No source acquisition/policy change, restricted payloads, release/signing/trading or financial gate promotion.

Reuse parsers/contracts.py, dispatch.py, schema_catalog.py and reference_evidence.py; inspect existing track_b/isin_master.py/universe_manager.py, track_a/trading_calendar.py/source_registry.py, domain.py and DB models for compatibility. Preserve PIT and corporate-action economics. Keep new identity/calendar interfaces versioned and opt-in until source validation.

Design: immutable issuer/security/listing identities, exchange-specific symbol and series claims, versioned symbol-to-ISIN history with business-valid and knowledge intervals, explicit listing/delisting/rename/suspension/relisting and merger transitions, and authoritative calendar/session references including exceptional sessions. Never merge economic identities by symbol or ISIN alone. Unknown/conflicting mappings quarantine.

Tests: freeze code-only state/interval/refusal tests before corrections; preserve existing robustness fixtures, with zero authentic financial contribution. Cover ambiguous/overlapping/revised identity claims, as-of availability, missing mappings and boundary dates. Authentic real symbol changes, mergers, listings, holidays and sessions remain BLOCKED_INPUT until permitted independently reviewed references exist. Do not invent securities, prices, financial mappings, actions or calendars as official truth.

Use14dependency contract exactly. known_from/effective_at/ingested_at, authenticated identity facts and complete trading-session history are missing source facts, not defaults. Run exact A/B/C inventory, targeted tests, unchanged diagnostic, quality checks and native guard proof; report through the accepted constrained renderer only. No old mixed-checkout Git finalizer.

One next decision: owner approve this bounded code-only contract and ADR before starting OD06. This handoff does not approve itself or resolve incidents. Full integration remains blocked.
