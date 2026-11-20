# Independent valid and knowledge time
get_universe_as_of requires explicit valid date or aware timestamp, aware known cutoff, consumer policy and exact source_snapshot_id. Date and knowledge intervals are half-open. Corrections preserve opaque economic-event lineage while allowing changed valid dates, identity and classification. Parent must exist, revision increment one, knowledge strictly increase; duplicate/competing children refuse. Cancellation supersedes prior knowledge without rewriting the parent.

Source-date semantics do not invent a market-open instant. Explicit timestamps use exact economic start/end; date-only queries over timestamp-specific claims remain blocked for availability. Exchange-local business date uses Asia/Kolkata, independent of host timezone. SQL uses UTC-normalized knowledge/effective timestamps.

Known future announcements are separate upcoming outputs, never current constituents. Unknown availability, future publication/announcement and denied sources remain explicit. Future-known revisions cannot change an earlier snapshot digest. Historical states can be replayed and compared; no current-clock fallback.
