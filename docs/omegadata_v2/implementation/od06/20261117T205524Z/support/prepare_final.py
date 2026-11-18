"""Exact-source OD06 final evidence builder; no original checkout or Git access."""
import ast,difflib,hashlib,json
from collections import Counter
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-20261117T205524Z'); S=B/'staged2/repo'
OLD=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
HEAD='07cca6def0748ed0903461d8614e4866959f036f'
def load(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
 with p.open('x') as f: json.dump(v,f,indent=2)
commands=[dict(load(p),log='logs/'+p.name) for p in (B/'logs').glob('*-command.json')];latest={}
for r in sorted(commands,key=lambda r:r['end_utc']):latest[r['job']]=r
for n in ['od06','collection','A','mypy','pip','compile','od06perf','parser','focused','presence','W']:assert latest[n]['exit_code']==0,n
inventory=load(B/'runtime-inventory.json');assert Counter(inventory.values())=={'A':922,'B':4,'C':4}
bnodes={n for n,c in inventory.items() if c=='B'}
assert latest['diagnostic']['exit_code']==1
assert {r['nodeid'] for r in latest['diagnostic']['worker_result']['reports'] if r['outcome']=='failed'}==bnodes
assert set(latest['diagnostic']['worker_result']['deselected'])=={n for n,c in inventory.items() if c=='C'}
ruff=max((load(p) for p in (B/'logs').glob('static-ruff-*.json')),key=lambda r:r['end_utc']);assert ruff['exit_code']==0
adoption=load(B/'adoption.json')
if isinstance(adoption['files'],dict):
 assert set(adoption['files'])=={'value','Count'} and adoption['files']['Count']==6
 adoption['files']=adoption['files']['value']
for r in adoption['files']:assert sha(S/r['path'])==r['after_sha256']
adopted=[r['path'] for r in adoption['files']]
new=['src/omegadata/identity.py','src/omegadata/identity_adapters.py','src/omegadata/session_calendar.py','tests/unit/test_od06_contracts.py']
base=load(next((B/'staged2').glob('receipt-*.json')));preserved=[]
for r in base['files']:
 if r['path'] not in adopted:
  assert sha(S/r['path'])==r['sha256'],r['path'];preserved.append(r['path'])
assert {p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file()}=={r['path'] for r in base['files']}|set(adopted+new)
changes=[];patch=[]
for n in adopted+new:
 before=(OLD/n).read_bytes() if (OLD/n).exists() else b'';after=(S/n).read_bytes()
 changes.append(dict(path=n,before_sha256=hashlib.sha256(before).hexdigest() if before else None,after_sha256=sha(S/n),scope='ADOPTED_OD05' if n in adopted else 'NEW_OD06',applied_in_data_free_snapshot=True,applied_to_original=False))
 patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
with (B/'implementation.patch').open('x') as f:f.write(''.join(patch))
save(B/'source-changes.json',changes)
def summary(n):
 r=latest[n];w=r['worker_result'] or {}
 return dict(command_id=Path(r['log']).stem,command=r['argv'],working_directory=r['cwd'],source_commit=HEAD,source_manifest_sha256=r['source_manifest_sha256'],platform='Ubuntu WSL native data-free snapshot',python=w.get('python'),start_utc=r['start_utc'],end_utc=r['end_utc'],elapsed_seconds=r['elapsed_seconds'],exit_code=r['exit_code'],counts=w.get('counts'),deselected=w.get('deselected'),stdout_stderr_log=r['log'],boundary=w.get('boundary'))
coverage={}
for n in ['od06','A']:
 c=load(B/latest[n]['log'].replace('-command.json','-coverage.json'))
 coverage[n]={'totals':c['totals'],'OD06_files':{k:v['summary'] for k,v in c['files'].items() if k.endswith(tuple(new[:3]))}}
negative=[]
for r in sorted(commands,key=lambda r:r['end_utc']):
 if r['job']=='od06' and r['exit_code']==1 and r['worker_result']:
  manifest=load(B/r['log'].replace('-command.json','-manifest.json'));pin=next(x['sha256'] for x in manifest['files'] if x['path']==new[-1])
  for t in r['worker_result']['reports']:
   if t['outcome']=='failed':negative.append(dict(nodeid=t['nodeid'],test_source_sha256=pin,command=r['log'],start_utc=r['start_utc'],classification='NEW_FEATURE_ABSENT' if r['worker_result']['counts']=={'failed':33} else 'REPRODUCED_DEFECT_OR_ADAPTER_ABSENT',correction='Corresponding opt-in identity/adapters/calendar API or validation; source changes in12preservation',final_result='PASS; see final66case log'))
assert len([r for r in negative if r['classification']=='NEW_FEATURE_ABSENT'])==33
outputs={}
def put(n,v):outputs[n]=(v+'\n') if isinstance(v,str) else json.dumps(v,indent=2)+'\n'
put('00_identity_and_scope.md',f'''# OD06 bounded implementation
Reviewed branch feature/od01-source-rights HEAD {HEAD}, confirmed by ref-only Git. Original mixed worktree content intentionally not refreshed; unknown user work preserved. No unrestricted Git, original data reads, incident disposition, commit/push, release or later phase.
Current owner invocation authorizes code-only OD06 and six-file OD05 adoption in verified data-free workspace {S}. OD05 approval record scope retained. Canonical stage began from receipt-pinned3804file R1 snapshot; no recursive original copy or original/private/incident/database/Git-object-store mounts. New code is actually applied and tested in this snapshot, not merely a patch; original checkout remains unintegrated.
''')
put('01_od05_patch_adoption.json',dict(adoption,verified_after_hashes=True,prior_receipt_sha256='80fcf7e771f25066af133c1848778ababdf4d3f4a8718fb03dd4fca5bd73ce77',parser_interface_freeze=latest['od06perf']['worker_result']['parser_interface_fields'],tests={n:summary(n) for n in ['parser','focused','presence','W']},R1_A=dict(Counter(r['outcome'] for r in latest['A']['worker_result']['reports'] if 'test_od05xr1_windows_contract.py::' in r['nodeid']))))
put('02_existing_code_reuse_inventory.md','''# Reuse/compatibility
EXTEND opt-in pure domain/adapters; no new dependency or paid service.
Existing parser contracts/dispatch/nse_cm/reference_registry/schema_catalog adopted exactly; no official-era promotion. Existing ISINMasterService.validate_isin reused solely for optional ISIN syntax, not ownership evidence. Original creation/IPO/symbol-change/cross-listing/delisting retained.
PointInTimeUniverseManager and raw helpers unchanged. New strict_universe accounts for every selected typed claim; legacy_universe_inventory accounts for every selected ORM membership, missing masters included, no active-only filter. Existing seed/raw helper methods not used by new APIs; source_backfill refuses before filesystem access. Full unchanged diagnostic attempts preserved legacy B workflows only inside unmapped disposable roots; original source bytes cannot be accessed.
TradingCalendar remains unchanged; legacy_session reuses coverage checks but returns provisional/unknown. VerifiedCalendar adds explicit authority/as-known sessions without generating weekdays/hours. External calendar library deferred: would not establish missing authenticated reference evidence.
ORM/domain/source_registry/source_rights remain unchanged. ISIN primary keys/inclusive legacy dates are preserved. New legacy_symbol_inventory returns all matches, explicit exclusive-end conversion and unknown knowledge/series, never automatically creates listing/security IDs. MemoryIdentityRepository implements versioned protocol.
Existing consumer compatibility exercised by unchanged A tests including ISIN/calendar/universe. Four B source-dependent expectations retained. Linux canonical stage/native probes reused unchanged; Windows gate stays blocked. Founder skill/external libraries not required or invented.
''')
put('03_identity_domain_contracts.md','''# Identity v1
Issuer, Security and Listing have separate immutable opaque record IDs. Multiple securities/listings are explicit relationships; matching symbols or ISIN never merge identities. Missing relationship None yields quarantine, not invented association. record_id uses namespaced UUID5 of a persisted immutable ledger key and kind, never a derived mutable ticker. IDs are bookkeeping, not official external identifiers.
IdentifierClaim retains original exchange/symbol/series, optional reported ISIN, valid/known intervals, evidence, listing and lifecycle. Repository validates tuple immutability, unique IDs, referential integrity, versions and lineage. States RESOLVED/UNKNOWN/AMBIGUOUS/CONFLICTING/QUARANTINED/SOURCE_BLOCKED, no first-row choice or current-active filter.
Evidence is a caller-supplied independently governed review attestation, NOT a publisher-authentication engine or source permission grant. STRICT requires SOURCE_DOCUMENT/VERIFIED/PERMITTED/review_reference. CANARY_ONLY is NON_MARKET_CANARY for invariant testing and always financially ineligible. Conflicting evidence quarantines.
IdentityIntake preserves exact ParseResult/ParsedBar and exposes PRESENT/ABSENT/UNVERIFIED/CONFLICTING/FORBIDDEN field states, including version/source/format/lexemes/ordinal/provenance and unknown timestamps. Catalogue metadata requires exact source/format/parser match. Intake financial_eligible is init-disabled False; parsing cannot self-promote. No normalization overwrites reported fields.
''')
put('04_bitemporal_resolution_contract.md','''# Independent temporal axes
[valid_from,valid_to) uses business dates; [known_from,known_to) uses aware timestamps. None end is unbounded, None knowledge start is unknown/quarantined. Queries require explicit aware known_at; never infer it from trade date, updated_at, publication date or clock. Exact exchange/symbol/series required. Candidate records deterministic sorted; ambiguity/conflict never resolved by arbitrary tie-break.
Corrections append a new immutable revision, retain old bytes and derive effective knowledge closure. Parent required, strictly later known_from, matching exchange and exact valid interval, single-successor lineage. Earlier as-known query keeps old claim; later query sees correction. Arbitrary interval repartitioning is not guessed and requires separately modeled revisions.
Legacy inclusive valid_to converts explicitly by +1day; date.max overflow refuses. Legacy rows do not supply authoritative knowledge/series and remain unverified. No production conversion or migration.
''')
put('05_lifecycle_events.md','''# Lifecycle contracts
Version od06.lifecycle/v1 supports LISTING, DELISTING, SYMBOL_CHANGE, SERIES_CHANGE, SUSPENSION, RELISTING, CROSS_LISTING, SECURITY_RECLASSIFICATION, ISSUER_CHANGE, MERGER_IDENTITY_TRANSITION, DEMERGER_IDENTITY_TRANSITION, IDENTIFIER_CORRECTION and SOURCE_SUPERSESSION.
Events carry IDs, affected identities, Evidence/source/authentication, optional publication/effective/known/ingested times, supersession and validation status. Unknown times stay None. Duplicate IDs, invalid status/parent, branched or non-increasing knowledge, disjoint supersession and contradictory same-time lifecycle events refuse. Suspension is not delisting. Merger/demerger requires multiple affected identities and explicit continuity review, without automatic identity continuity or economics. Relisting can use an explicitly linked new listing.
Events do not automatically mutate claims or financial records; reviewed claim intervals govern lookup. No actual lifecycle or merger verified in this run.
''')
put('06_calendar_contract.md','''# Explicit calendar v1
SessionClaim: exact exchange/date/type, Asia/Kolkata, calendar version, authority Evidence, independent known bounds, optional open/close, supersession. Unknown hours never filled; supplied hours aware/date-consistent/ordered, CLOSED has none. Immutable tuple ledger, exact dates/exchanges, explicit corrections.
Query states AUTHORITATIVE_SESSION/VERIFIED_SPECIAL_SESSION/KNOWN_CLOSURE/COVERAGE_UNKNOWN/CONFLICTING_CALENDAR/PROVISIONAL/SOURCE_BLOCKED. Operational labels under CANARY_ONLY describe invariant controls and remain financial_eligible=False, never genuine exchange sessions. Explicit weekend special claim is independent of weekday logic. Missing sessions including weekends/year gaps refuse; no inferred closure. Missing/invalid legacy config unknown, configured coverage provisional.
add_business_days excludes anchor, nonnegative integer count, explicit coverage for anchor and every examined day, fixed max3660dates. Unknown/conflicting/provisional coverage refuses. Date boundary/consecutive closure/year transition tested only as anonymous software controls; no historical calendar was invented or financially validated.
''')
put('07_negative_first_tests.md','# Genuine chronology\n\n33groups failed NEW_FEATURE_ABSENT before APIs. Additional21cases:48pass/6fail then54pass. Review10:60pass/4fail then64pass. Intake2:64pass/2fail then66pass. Source hashes/commands for every red case follow; final source hash in12. Frozen snapshots of executed test sources retained with each isolated output. Ruff later only sorted imports/literal style, no expectation relaxation.\n\nInitial collector failed with coverage.NoDataError, no result JSON; launcher stderr preserved, fixed before actual33fail baseline. One pre-worker diagnostic PATH_UNSAFE refusal retained; exact triggering path unknown, subsequent serialized launches passed. Intermediate diagnostic had6fail (original4B + new2intake failures), preserved. First report builder rejected PowerShell value/count wrapper. A premature report failed with no output. Windows UNC transport then timed out during reader edit and an empty preparation script was written; no application/evidence/data source modified. Empty controller preserved; new native preparation path used with strict error handling. No failed report promoted toPASS.\n\n'+json.dumps(negative,indent=2))
put('08_targeted_test_results.json',dict(commands={n:summary(n) for n in ['od06','parser','focused','presence','W','od06perf']},R1_actual_A=dict(Counter(r['outcome'] for r in latest['A']['worker_result']['reports'] if 'test_od05xr1_windows_contract.py::' in r['nodeid'])),coverage=coverage,performance=latest['od06perf']['worker_result'],independent_oracle='128 comparisons against an independently stated interval predicate; anonymous nonmarket records, no financial oracle'))
put('09_full_engineering_matrix.json',dict(reviewed_HEAD=HEAD,collected=len(inventory),classes=dict(Counter(inventory.values())),latest_commands={n:summary(n) for n in latest},ruff=ruff,coverage=coverage,A_skips=[r for r in latest['A']['worker_result']['reports'] if r['outcome']=='skipped'],B_nodes=sorted(bnodes),C_nodes=[n for n,c in inventory.items() if c=='C'],all_attempts=[dict(job=r['job'],exit_code=r['exit_code'],counts=(r['worker_result'] or {}).get('counts'),log=r['log']) for r in sorted(commands,key=lambda r:r['end_utc'])],Windows314='NOT_RUN_WINDOWS_OS_CAPABILITY_BLOCKED',Windows311='NOT_RUN_WINDOWS_OS_CAPABILITY_BLOCKED',skip_reconciliation='5existing platform nodes +7Windows-native capability blocks; historical counterpart evidence unchanged, no fresh Windows claim'))
policies=load(S/'config/source_rights_policy.v1.json')['policies']
put('10_financial_source_dependencies.json',dict(financial_verdict='BLOCKED_REAL_DATA',real_rows_independently_verified=0,real_identity_claims_verified=0,actual_authoritative_sessions_verified=0,synthetic_financial_contribution=0,source_policy_states=dict(Counter(p['status'] for p in policies)),required_inputs=['Permitted authenticated issuer/security/listing and exact symbol/series/ISIN claims with independent knowledge and valid intervals','Independently reviewed lifecycle/correction lineage and frozen expected identity observations','Authorized versioned exchange calendar authority and independently reviewed special/closure/as-known sessions'],original_inventory='ARCH_ONLY3626present/size-matched,3596seed+30cache,2760hardlink+866single; no fresh original payload/ZIP/row inspection',incidents=dict(OD05V='PENDING_HUMAN_OWNER_REVIEW; archived39files/6135515bytes',OD05XR1='PENDING_HUMAN_OWNER_REVIEW;payload extentUNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'),original_WSL_performance='BLOCKED;30secondbudgetunchanged;notrerun',unknown_original_financial_row_count=True))
put('11_database_migration_proposal.md','''# Future additive migration; NOT executed/authorized
Preserve InstrumentMaster ISIN PK and legacy reads. FK consumers SymbolMap/SymbolChangeLog/DelistingRecord/IPORegistry/CrossListingMap, plus string-ISIN consumers PriceRecord/UniverseMembership/other source tables, need explicit reconciliation. No ORM or production DDL changed.
Propose additive issuer/security/listing opaque PKs, identifier_claim with exact reported identifiers/exchange/series/evidence/valid-known intervals/supersession, lifecycle_event and session_claim. Evidence/version FKs, unique claims and single-successor constraints, ordered interval checks and query indexes(exchange,symbol,series,valid_from,known_from). Overlap/contradiction reviewed or quarantined, never first-row SQL choice. Transactional append-only revisions and derived knowledge closure.
Prerequisites: enumerate all consumers; authorized backup/restore plan; disposable target-schema rehearsal; idempotence/transaction/rollback tests; inclusive-to-exclusive boundaries and date.max; unknown knowledge quarantined; duplicate symbols/multi-listings/ISIN exceptions; dual-read opt-in compatibility. No ID from ticker or ISIN, no timestamp backfill from updated_at. Production rows untouched.
This run verified legacy read adapters using disposable SQLite in-memory existing schemas and anonymous rows. No target-table migration exists or was rehearsed. Migration readiness PROPOSAL_ONLY; no production migration approval. Current rollback: stop opt-in calls/revert only additive code in safe workspace, no data cleanup.
''')
put('12_preservation_manifest.json',dict(reviewed_commit=HEAD,changes=changes,unchanged_baseline_entries=len(preserved),receipt_sha256=sha(next((B/'staged2').glob('receipt-*.json'))),existing_tests_unchanged=True,source_policies_registry_config_ORM_unchanged=True,original_data_incident_signing_payloads_not_mounted=True,original_payload_hashing=False,original_checkout_integration=False,commit_push_release=False,scope='Allowed code/nonmarket metadata hashes only, not a fresh original raw-integrity certificate'))
gates=dict(G1_OD05_ADOPTION='PASS_DATA_FREE_SNAPSHOT',G2_IDENTITY_ENGINEERING='PASS_CODE_ONLY',G3_CALENDAR_ENGINEERING='PASS_CODE_ONLY',G4_REGRESSION_SAFETY='PASS_A_WITH_12_EXPLICIT_SKIPS;FULL_DIAGNOSTIC_FAIL_4_B',G5_CONTAINMENT='PASS_SCOPED_LINUX;WINDOWS_OS_CAPABILITY_BLOCKED',G6_FINANCIAL_CORRECTNESS='BLOCKED_REAL_DATA',G7_PRODUCTION_INTEGRATION='BLOCKED_INCIDENT_SOURCE_PLATFORM_GATES',OD06_CODE_ONLY_ENGINEERING='PASS',OD06_OVERALL='CONDITIONAL',OD07_AUTHORIZATION='NOT_GRANTED',new_unresolved_P0_P1_in_tested_code_only_scope=0,legacy_P1_risks='Unchanged legacy missing knowledge and silent membership drop remain; opt-in APIs quarantine/account',review_independence='Same-agent review plus independent executed kernel mechanisms and explicit primitive interval predicate, no human review invented',original_checkout_integration=False)
put('13_gatekeeper.json',gates)
put('14_final_implementation_report.md',f'''# OD06: CONDITIONAL development completion
Reviewed {HEAD}, feature/od01-source-rights. Six OD05 files actually adopted in verified data-free snapshot, three new modules and one new test file implemented/tested there. Original mixed checkout not integrated/refreshed; no commit/push/merge/OD07/release/sign/trading/restricted payload access.
Identity ledger/resolver/events, strict universe+legacy read adapters, typed parser intake and explicit as-known session calendar are opt-in. Existing parser/ISIN/universe/calendar/ORM/source/policy functionality preserved. Ten-file manifest and combined patch delivered.
Fresh Linux3.12:66newtestsPASS; parser/reference170pass+1skip;X33pass,V40pass+1skip,W39pass. Collection930=A922+B4+C4; A910passed/12skipped,exit0. Full unchanged nonrealdata diagnostic910passed/4failed/12skipped,C4deselected,exit1. Four Bfailures remain FAIL, Cnotrun;12skips=5platform+7nativeWindowsblocks. R1scoped actual outcomes/coverage in08/09. Ruff/mypy/pip/compileexit0. Native12denials and IPCpositive controls accompany launchlogs. No100%coverageclaim.
All33negative-first groups plus targeted adversarial corrections preserved. Final66pass. Initial coverage collector, preworker PATH_UNSAFE, intermediate6failure diagnostic, lint errors and report-controller/UNC transport failures retained, not reclassified asPASS.
Actual financial rows, real identity mappings and authoritative actual sessions independently verified:0. No newly generated financial observations; anonymous controls only and unchanged regression fixtures software-only.13sourcepoliciespending; real expected mappings/calendar/reference provenance unavailable. Archived physical3626size-matches not financial evidence. Incidentspending; Windowssandboxunavailable; originalWSLperformanceblocked at30sec.
EngineeringPASS within tested opt-in Linux scope; financialBLOCKED_REAL_DATA; productionintegrationBLOCKED. No target database migration executed; proposal and disposable legacy-schema adapter tests only. Before fullintegration: accountable incident disposition, approved platform conditions, separately permitted authenticated identity/calendar evidence with independent expected claims and reviewed migration/consumer plan. STOPafterOD06; no next-phaseexecution.
''')
R=B/'report-inputs';R.mkdir()
raw=json.dumps({'artifacts':outputs},sort_keys=True).encode();(R/'summary.json').write_bytes(raw)
spec={'schema_version':'od05.final-report/v1','files':{'summary.json':{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}}};(R/'manifest.json').write_text(json.dumps(spec))
save(B/'report-input-index.json',['manifest.json','summary.json']);save(B/'report-preparation.json',dict(artifacts=list(outputs),changes=changes,coverage=coverage,utc=datetime.now(UTC).isoformat()))
print(json.dumps(dict(reports=len(outputs),changes=len(changes),coverage=coverage['A']['OD06_files'])))
