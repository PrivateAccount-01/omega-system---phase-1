# Existing implementation audit and reuse
28 receipt-pinned code/test/consumer files reviewed; full identities and caller hits are in support/source-audit.json. Backfill scripts were read as code only, never executed against original source roots.

| Existing path/function | Observed limitation and consumer | Disposition / new proof |
|---|---|---|
| track_b/universe_manager.py:get_universe | Effective/removal dates only; no independent knowledge cutoff; missing InstrumentMaster silently continues; delisting filter affects returned rows. Used by legacy API/pipeline/proofs. | Preserve legacy; opt-in OD08 uses OD06 knowledge-aware identity. U06/U07/I03/I04. |
| remove_membership | Mutates prior removal dates, losing original knowledge state. | Append-only MembershipRevision wrapper and SQLite parent constraint. U07-U10/P06. |
| reconstruct_pre2010 | Sorts all qualifying DataFrame rows by market_cap and takes top N; repeated observations can duplicate a security; no evidenced availability or complete methodology proof. | Preserve legacy risk; provisional ranking rejects duplicate identities and unavailable inputs. R01/R02. |
| _scan_symbol_isin_map / seed helpers | Raw ZIP traversal and last-write dictionary have no bitemporal semantics. | Never called; source_backfill refusal reused and tested. |
| MembershipClaim/StrictUniverse | Accounts for supplied rows but cannot establish authentic completeness. Legacy correction validator requires identical valid bounds. | Reuse MembershipClaim unchanged inside new wrapper; correction lineage permits changed valid boundaries; coverage independent. C01-C05/U08. |
| PersistentRepository | OD06 identity/calendar storage and source authority remain valid; existing membership schema lacks OD08 coverage/policy/context semantics. | Reuse typed snapshots, SQLAlchemy transaction/ownership conventions and exact evidence identities. No production migration. |

MemoryIdentityRepository, EvidenceAuthority, VerifiedCalendar, legacy_universe_inventory and OD07 v2 contracts are reused. No new dependency, paid service or external data framework. Python standard library and existing SQLAlchemy/SQLite suffice. These audit findings are code-level facts, not verified historical financial discrepancies. New tests use anonymous controls; legacy financial expectations stay unchanged.
