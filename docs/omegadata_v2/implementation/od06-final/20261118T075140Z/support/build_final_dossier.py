"""OD06 final report preparation from exact data-free sources and executed logs."""
import ast,difflib,hashlib,json
from collections import Counter
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
P=Path('/home/parilrupani/omega-od06-20261117T205524Z/staged2/repo')
OLD=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
HEAD='4e663af492a96a3ff36d61a47c1e213bbf6cd740'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2)
commands=[dict(load(p),log='logs/'+p.name) for p in (B/'logs').glob('*-command.json')];latest={}
for r in sorted(commands,key=lambda r:r['end_utc']):latest[r['job']]=r
mandatory=['foundation','od06','parser','collection','A','mypy','pip','compile','foundationperf']
for job in mandatory:assert latest[job]['exit_code']==0,(job,latest[job]['exit_code'])
assert latest['foundation']['worker_result']['counts']=={'passed':87}
assert latest['od06']['worker_result']['counts']=={'passed':66}
assert latest['A']['worker_result']['counts']=={'passed':997,'skipped':12}
assert latest['diagnostic']['exit_code']==1
inventory=load(B/'runtime-inventory.json');assert Counter(inventory.values())=={'A':1009,'B':4,'C':4}
Bnodes={n for n,c in inventory.items() if c=='B'}
assert {r['nodeid'] for r in latest['diagnostic']['worker_result']['reports'] if r['outcome']=='failed'}==Bnodes
assert set(latest['diagnostic']['worker_result']['deselected'])=={n for n,c in inventory.items() if c=='C'}
ruff=max((load(p) for p in (B/'logs').glob('static-ruff-*.json')),key=lambda r:r['end_utc']);assert ruff['exit_code']==0
accepted=load(B/'accepted-process-experiments.json');assert accepted['status']=='PASS'
assert sorted(accepted['records'][n]['worker_result']['status'] for n in ['dbcompete-a','dbcompete-b'])==['COMMITTED','REFUSED_COMPETING_SUCCESSOR']
assert accepted['records']['dbcrash']['crash']['native_returncode']==-9
adoption=load(B/'adoption.json');adopted=[r['path'] for r in adoption['files']]
modified=['src/omegadata/identity.py','src/omegadata/identity_adapters.py','src/omegadata/session_calendar.py']
new=['src/omegadata/identity_authority.py','src/omegadata/identity_repository.py','scripts/od06_database_experiments.py','scripts/od06_experiment_contract.py','tests/unit/test_od06_foundation.py','config/identity_authority_roots.v1.json']
changed=modified+new
for row in adoption['files']:
 assert sha(P/row['path'])==row['after_sha256']
 if row['path'] not in modified:assert sha(S/row['path'])==row['after_sha256']
base=load(next((B/'staged2').glob('receipt-*.json')));preserved=[]
for row in base['files']:
 if row['path'] not in adopted:
  assert sha(S/row['path'])==row['sha256'];preserved.append(row['path'])
assert {p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file()}=={r['path'] for r in base['files']}|set(adopted+new)
for job in mandatory+['diagnostic']:
 manifest=load(B/latest[job]['log'].replace('-command.json','-manifest.json'))
 by_name={r['path']:r for r in manifest['files']}
 for n in changed:assert by_name[n]['sha256']==sha(S/n),(job,n,'NOT_FINAL_SOURCE')
 assert by_name['config/identity_authority_roots.v1.json']['class']=='STATIC_CONFIG'
for item in accepted['records'].values():
 manifest=load(B/('logs/'+item['command_log'].replace('-command.json','-manifest.json')))
 by_name={r['path']:r for r in manifest['files']}
 for n in changed:assert by_name[n]['sha256']==sha(S/n)
phase=[];delivery=[];patch=[]
for n in sorted(set(adopted+new)):
 current=(S/n).read_bytes();prior=(P/n).read_bytes() if (P/n).exists() else b'';before=(OLD/n).read_bytes() if (OLD/n).exists() else b''
 row={'path':n,'before_sha256':hashlib.sha256(before).hexdigest() if before else None,'after_sha256':sha(S/n),'applied_in_development':True,'applied_to_original_checkout':False}
 delivery.append(row)
 if n in changed:phase.append(dict(row,before_phase_sha256=hashlib.sha256(prior).hexdigest() if prior else None,change='MODIFIED' if prior else 'ADDED'))
 patch.extend(difflib.unified_diff(before.decode().splitlines(keepends=True),current.decode().splitlines(keepends=True),fromfile='a/'+n if before else '/dev/null',tofile='b/'+n))
with (B/'implementation.patch').open('x') as f:f.write(''.join(patch))
save(B/'source-changes.json',phase);save(B/'combined-delivery-manifest.json',delivery)

def summary(job):
 r=latest[job];w=r['worker_result'] or {}
 return dict(command_id=Path(r['log']).stem,command=r['argv'],working_directory=r['cwd'],platform='Ubuntu WSL Linux native data-free snapshot',python=w.get('python'),source_commit=HEAD,source_manifest_sha256=r['source_manifest_sha256'],start_utc=r['start_utc'],end_utc=r['end_utc'],elapsed_seconds=r['elapsed_seconds'],exit_code=r['exit_code'],counts=w.get('counts'),deselected=w.get('deselected'),stdout_stderr_log=r['log'])
coverage={}
for n in ['foundation','A']:
 cov=load(B/latest[n]['log'].replace('-command.json','-coverage.json'))
 coverage[n]={'totals':cov['totals'],'foundation_components':{name:v['summary'] for name,v in cov['files'].items() if name.endswith(tuple(modified+new[:2]))}}
negative=[]
for r in sorted(commands,key=lambda r:r['end_utc']):
 if r['job']=='foundation' and r['exit_code']!=0 and r['worker_result']:
  manifest=load(B/r['log'].replace('-command.json','-manifest.json'))
  pin=next(row['sha256'] for row in manifest['files'] if row['path']=='tests/unit/test_od06_foundation.py')
  for report in r['worker_result']['reports']:
   if report['outcome']=='failed':negative.append(dict(nodeid=report['nodeid'],test_source_sha256=pin,command=r['log'],start_utc=r['start_utc'],reason=report['reason'],final_result='PASS',final_log=latest['foundation']['log']))
assert any(r['worker_result'] and r['worker_result']['counts']=={'failed':55,'passed':2} for r in commands if r['job']=='foundation')
source_rights=load(S/'config/source_rights_policy.v1.json')['policies'];assert not any(p['status']=='APPROVED' for p in source_rights)
roots=load(S/'config/identity_authority_roots.v1.json');assert roots['roots']==[]
outputs={}
def put(n,value):outputs[n]=value+'\n' if isinstance(value,str) else json.dumps(value,indent=2)+'\n'
put('00_scope_and_source_identity.md',f'''# OD06 foundation completion
Reviewed branch feature/od01-source-rights, HEAD {HEAD}, verified using ref-only Git. Original mixed worktree contents intentionally not refreshed; no unrestricted Git/status/diff/finalizer. Unknown original user changes preserved.

One integrated applied-and-tested development snapshot: {S}. Verified canonical staging from3804file R1 receipt, followed by exact ten-file OD05/OD06 adoption. Full adopted before/after hashes verified against sealed prior dossier. The original application tree is not integrated. This dossier records nine phase code/config changes and a combined16file source delivery, not a claim of production application.

Execution only OD06_FOUNDATION_COMPLETION_AND_ACCEPTANCE. No OD05 reopening, OD07 execution, original dataset/incident/production database mounts, restricted acquisitions, signing, release, commit/push or merge. Prior OD05V/R1 incident dispositions remain pending. All tests disposable; new identifiers/calendar dates are anonymous nonmarket structural controls with zero financial acceptance contribution.
''')
put('01_integrated_code_manifest.json',dict(reviewed_HEAD=HEAD,development_snapshot=str(S),adoption=adoption,phase_changes=phase,combined_delivery=delivery,source_file_count=len(base['files'])+len([n for n in set(adopted+new) if n not in {r['path'] for r in base['files']}]),root_receipt_sha256=sha(next((B/'staged2').glob('receipt-*.json'))),prior_evidence_files_read=len(load(B/'prior-evidence-read.json')),original_checkout_integrated=False))
put('02_existing_implementation_audit.md','''# Audit and reuse
Reused original pure parser API and all six delivered OD05 files unchanged. Reused OD06 issuer/security/listing and explicit date/knowledge contracts, opt-in adapters and calendar. Corrected: plain-label authority, caller-writable financial flags, unrelated-listing correction, mutable event identity collection, unknown lifecycle handling, missing calendar-version selection, source-bound authority hashing after derived revision closure, event idempotency and missing artifact digest syntax. Actual negative-first records are retained.

SQLAlchemy existing dependency supplies a separate additive Core metadata schema. No new dependencies, distributed services or external calendar library. Existing source-rights authorize_source/PolicyRequest remain the ONLY permission gate; new owner-root register is reference-authenticity trust configuration, not a source permission grant. Existing RawArchive/provenance contracts and raw identities are not bypassed or opened. Identity claims bind exact artifact/document/source/review metadata and exact canonical claim digest.

Complete consumer inventory:156allowed code/instruction files,172 textual references to ISINMasterService/PointInTimeUniverseManager/TradingCalendar/SymbolMap/InstrumentMaster, with file hashes/line contexts in support. Legacy APIs, ORM schema, calendar config, source registry/rights, financial expectations and previous tests unchanged. No raw backfill used by new APIs. Full unchanged B diagnostic attempts remain failures inside unmapped disposable roots; original source contents inaccessible.

Same-agent adversarial review, not independent human consensus. Independent executed checks: SQL constraints/triggers, OS probes, separate-process recovery/competing writers, canonical hashes and explicit interval predicate tests. Founder skill/external products not invented or adopted.
''')
put('03_persistent_identity_schema.md','''# Durable opt-in schema: od06.store/v1
Separate SQLAlchemy Core metadata: od06_schema; od06_identity_id; od06_issuer; od06_security; od06_listing; od06_evidence; od06_claim; od06_event; od06_event_identity; od06_session; od06_calendar_coverage; od06_membership. Claim rows ARE immutable revisions; parent IDs form lineage, no destructive replacement table. Global opaque IDs distinguish issuer/security/listing; ISIN/ticker are not primary identity keys. Evidence/claim IDs unique, all identity/evidence/parent links FK-enforced, parent successor unique.

PRAGMA foreign_keys=ON, busy_timeout5000ms. BEGIN IMMEDIATE serializes each write; rollback on BaseException. Canonical payload JSON plus digest checked on each record read, independently typed reconstruction and canonical reserialization. Immutable UPDATE/DELETE triggers on every additive table; nonempty schema rollback refuses. Idempotent retries accept identical canonical record only, changed duplicate rejects. Explicit valid/known columns, version-pinned identity queries and deterministic history/revision ordering. Corrections retain original stored bytes; query temporal closure derived separately, preserving authority hash identity.

Indexes: exchange/symbol/series/valid_from/known_from lookup; candidate listing-history; calendar exchange/date/version. Point lookups load candidate listing histories rather than scanning the complete identity store. Append consistency currently validates complete ledger O(n); measured and documented, not claimed production-scale. get_identity_history/get_claim_revisions/validate_identity_consistency/serialize_history expose audit history. append_event stores relationships without automatic identity mutation; append_session/coverage/membership keep explicit versions/knowledge.

Only SQLite in-memory or owned file-backed databases under explicit disposable_root. Existing unrelated schemas, non-SQLite URLs, path escapes and symlinks refuse. Public engine/transaction hooks are trusted development interfaces, not an SQL service for untrusted consumers. No production migration or legacy PK/FK mutation.
''')
put('04_evidence_authority_contract.md','''# Trust boundary, not caller attestation
Evidence labels remain untrusted metadata. STRICT no longer accepts SOURCE_DOCUMENT/VERIFIED/PERMITTED/review_reference alone. EvidenceAuthority checks pinned bundle bytes/schema/unique evidence IDs, exact source and reviewer records, canonical claim relationship, artifact SHA256/publisher/document version, review and availability times, purpose, revocation/supersession, and the existing source-rights decision for READ_CACHED plus downstream purpose.

A caller-supplied bundle hash proves identity only. An independently configured owner-reviewed root is ALSO required. config/identity_authority_roots.v1.json is empty and hash-pinned by source code; no human approvals were generated. A caller cannot choose this root through claim/query labels. Tampering/missing/wrong root denies. Future actual root changes require separate owner-reviewed configuration/code pins, independent reviewer identity, recorded-time evidence and revocation checks. No signing material touched. Same-process arbitrary code execution is outside this data-contract boundary; workers have real OS restrictions.

A reproduced final adversarial case mocked only the rights oracle (no policy entry written) and showed an unreviewed caller pin could self-qualify. It failed before the owner-root fix and passes afterwards. All hostile labels in that test are explicitly NON_MARKET canaries, never publisher approvals. Actual policies remain13pending_review.

Resolution/session/universe financial flags are init-disabled and derived internally; intake remains false. CANARY_ONLY is never financially eligible. Universe selected-set completeness does not prove complete authoritative index coverage; authoritative_coverage remains false absent independent upstream proof. No API accepts a consumer-created AuthorityDecision as an authorization input. Positive authentic financial validation remains BLOCKED_REAL_DATA: there is no approved owner root, authentic reviewed mapping/calendar corpus or permitted source pack.
''')
put('05_bitemporal_and_lifecycle_tests.json',dict(focused=summary('foundation'),preserved_OD06=summary('od06'),negative_first=negative,contracts=['Half-open valid/known intervals; missing knowledge quarantines','A-B-C and reversal preserve historical as-known states','Same-time/competing/unrelated/missing-parent corrections refuse','Conflict/ambiguity/source blocking explicit; no active-only filtering','Unknown lifecycle availability quarantines; lifecycle contradictions refuse','Merger/demerger cannot auto-merge identities'],coverage=coverage))
put('06_universe_and_calendar_tests.json',dict(focused=summary('foundation'),PIT=['Every selected membership counted once','Duplicate IDs/intervals/revision lineage checked','Unknown masters/ISINs retained, provisional reconstruction never promoted','Future correction invisible, removal boundary half-open','Selected-set completeness separate from authoritative source coverage'],calendar=['Explicit regular/closure/weekend controls','Unknown day/year/partial coverage, no weekday/year completeness inference','Independent known axis, later corrections and competing claims','Optional explicit calendar_version query','Timezone/hours validation; missing hours remain unknown','Strict previous/next and explicit coverage; unchanged bounded arithmetic','Persistent sessions/coverage survive reconnect'],financial_context='Anonymous CANARY-X invariant controls only; no actual session or mapping verified'))
put('07_database_restart_rollback_tests.json',dict(focused=summary('foundation'),accepted_process_experiments=accepted,in_memory_and_file_backed=True,atomicity='Controlled exception rollback and actual separate-process SIGKILL after insert/before commit; subsequent SQLite reopen preserved committed history and excluded uncommitted revision',concurrency='Two independent isolated processes, exactly one committed successor and one refused',foreign_key_and_append_only='Actual native SQLite constraint/trigger failures asserted as IntegrityError',migration='Create/drop/recreate EMPTY additive schema on disposable databases; nonempty rollback refused',limits='No hardware power-loss durability or production migration certificate'))
put('08_compatibility_results.json',dict(consumer_inventory='support/complete-consumer-inventory-final.json',existing_tests_unchanged=True,legacy_models_and_calls_unchanged=True,final_A=summary('A'),old_OD06=summary('od06'),parser=summary('parser'),V_W_X_R1_in_final_A={token:dict(Counter(r['outcome'] for r in latest['A']['worker_result']['reports'] if token in r['nodeid'])) for token in ['test_od05v_local_presence.py','test_od05w_engineering.py','test_od05x_isolation.py','test_od05x_native_extensions.py','test_od05xr1_windows_contract.py']},compatibility_changes=[dict(interface='STRICT evidence resolution',before='Caller labels could qualify',after='Owner-root and source-policy verified evidence required',impact='Intentional fail-closed opt-in correction',rollback='Revert only data-free code, never promote old insecure authority'),dict(interface='Financial flags',before='Writable dataclass constructor fields',after='Init-disabled derived results',impact='Explicit manual flag setting now refuses'),dict(interface='Repository/calendar/universe persistence',before='Memory-only contracts',after='Additive disposable SQLAlchemy repository, optional calendar-version query and membership corrections',impact='Legacy production ORM/callers unchanged')]))
put('09_security_and_boundary_evidence.json',dict(backend='Unchanged OD05X bwrap mount/user/network/PID namespaces, capability drop, seccomp and exact staging; native12denials plus IPCpositive control',source_pins='All final mandatory command manifests match final nine phase code/config hashes',shared_database_mount='Exact newly-created mode0700 nonmarket SQLite fixture only; explicit file whitelist/marker, no source or incident mounts added',accepted_process_proof=accepted,original_financial_payload_reads_in_verified_workers=0,old_incidents=dict(OD05V='PENDING_HUMAN_OWNER_REVIEW',OD05XR1='PENDING_HUMAN_OWNER_REVIEW;PAYLOAD_ACCESS_UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'),Windows='WINDOWS_OS_CAPABILITY_BLOCKED;no waiver or new Windows certification',original_WSL_scan='PERFORMANCE_BLOCKED;30second budgetunchanged;notrerun',failed_attempts='All logs retained; staging PATH_UNSAFE and dependent experimental failures not accepted; strict controller now rejects failed/missing native proofs',controller='Final renderer consumes only pinned flat evidence input under actual Linux boundary; no Git/original discovery/fallback/cleanup'))
put('10_full_engineering_matrix.json',dict(reviewed_HEAD=HEAD,collected=len(inventory),classes=dict(Counter(inventory.values())),final_commands={job:summary(job) for job in mandatory+['diagnostic']},ruff=ruff,coverage=coverage,A_skips=[r for r in latest['A']['worker_result']['reports'] if r['outcome']=='skipped'],B_nodes=sorted(Bnodes),C_nodes=sorted(n for n,c in inventory.items() if c=='C'),all_attempts=[dict(job=r['job'],exit_code=r['exit_code'],counts=(r['worker_result'] or {}).get('counts'),log=r['log']) for r in sorted(commands,key=lambda r:r['end_utc'])],Windows314='NOT_RUN_OS_ISOLATION_UNAVAILABLE',Windows311='NOT_RUN_OS_ISOLATION_UNAVAILABLE',diagnostic_state='FAIL_4_PRESERVED_SOURCE_DEPENDENCIES;never inferred from A PASS'))
put('11_financial_source_dependencies.json',dict(verdict='BLOCKED_REAL_DATA',authentic_financial_rows_verified=0,real_identity_mappings_verified=0,actual_exchange_sessions_verified=0,source_policy_counts=dict(Counter(p['status'] for p in source_rights)),approved_owner_roots=0,required=['Separately owner-reviewed source-reference trust root and independently authenticated publisher/document/artifact provenance','Permitted identity/lifecycle/ISIN/listing reference claims with independently reviewed valid and knowledge intervals','Authorized exchange calendar completeness/closures/special sessions and independently frozen expected sessions','Independent complete PIT-index coverage and constituent expectations, not just selected membership count'],no_financial_substitutes=True,archive_counts='ARCH_ONLY3626present/size-matched;3596seed30cache;2760hardlink866single;not freshly inspected',original_row_count='UNKNOWN_NOT_INSPECTED',incidents='OD05V and OD05XR1 pending human disposition;technical approval does not waive them'))
put('12_migration_and_rollback.md','''# Tested development migration and production boundary
PersistentRepository.migrate creates only its separate12table od06.store/v1 schema in empty owned disposable databases, enforcesFKs/unique revision parents/indexes/append-only triggers. Empty schema drop and recreation tested on in-memory/file-backed SQLite; nonempty rollback refuses. Exception rollback and native SIGKILL recovery preserve committed history. Cross-process competing revisions serialize. Existing unrelated database schema rejected.

No legacy InstrumentMaster/ISIN keys or production migrations performed. Future production design must map FK consumers SymbolMap/SymbolChangeLog/DelistingRecord/IPORegistry/CrossListingMap plus string-ISIN PriceRecord/UniverseMembership/other models; retain old read behavior with opt-in views. Backups, restore, transaction/idempotence, additive migration rehearsals on an independently authorized target DB and reviewed rollback are mandatory before production.

Current code-only rollback: stop opt-in callers/revert only phase source changes in safe workspace, preserve evidence/databases. Do not delete test outputs automatically or roll back populated history by dropping tables. Correction/reversal appends a new knowledge revision; never overwrite accepted old facts. No production integration before incidents/platform/source gates and separate authorization.
''')
gates={key:'PASS' for key in ['OD06_SOURCE_ADOPTION','OD06_IDENTITY_ENGINEERING','OD06_PERSISTENCE','OD06_EVIDENCE_AUTHORITY','OD06_PIT_CORRECTNESS','OD06_CALENDAR_ENGINEERING','OD06_COMPATIBILITY','OD06_ENGINEERING_OVERALL']}
gates.update(OD06_AUTHENTIC_FINANCIAL_VALIDATION='BLOCKED_REAL_DATA',OD06_PRODUCTION_INTEGRATION='BLOCKED',OD07_CODE_ONLY_READINESS='READY',OD07_EXECUTION_AUTHORIZATION='NOT_GRANTED',scope='Applied/tested opt-in code-only Linux foundation; not original mixed checkout or full platform/financial certification',positive_authentic_authority_path='BLOCKED_INPUT;no approved real owner roots or financial source/reference corpus',full_diagnostic='FAIL_4_PRESERVED_B',Windows='OS_CAPABILITY_BLOCKED',incident_disposition='PENDING_HUMAN_OWNER_REVIEW',new_unresolved_P0_P1_in_tested_scope=0,review_independence='Same-agent review plus separately executed kernel, SQL, cross-process and primitive-oracle checks;no human approval invented')
put('13_final_gatekeeper.json',gates)
put('14_od07_dependency_handoff.md','''# OD07 code-only dependency handoff: READY, not authorized
Reusable upstream: exact adopted parser contracts; identity.py immutable identities/half-open knowledge; identity_repository.py append-only source-pinned history; identity_authority.py configured owner roots + existing source-rights decisions; identity_adapters.py unverified intake and exhaustive PIT accounting; session_calendar.py explicit version/as-known session and coverage claims.

OD07 must preserve issuer/security/listing distinctions, original identifiers/provenance and exact Decimal/raw price basis. Resolve by listing and independent known cutoff, never current master. Source references, reviews and events alone do not certify economics. Check derived eligibility and coverage; unknown or blocked evidence stays quarantined. No arbitrary financial flag assignment. Lifecycle events cannot imply merger continuity or price adjustment rules.

Pure code-only development may use anonymous invariant controls under the same data-free OS boundary and stable module versions. Actual corporate-action terms, real identifiers/sessions, source permissions and independent reference calculations remain separate source-dependent gates. No fictional financial observations or synthetic financial acceptance. Review migration/consumer compatibility before original integration. Historical incidents/Windows conditions not waived.

A separate explicit owner invocation of bounded OD07 is required by the project. This run does not execute OD07 or grant that authorization. Production/full financial integration remains blocked.
''')
criteria=['Integrated ten-file baseline','Stable separate identities','Durable insert/restart/revision/rollback','Reproducible bitemporal history','Conflict/ambiguity refusal','No plain-label evidence self-attestation','Lifecycle consistency','Exhaustive PIT accounting','Calendar authority/coverage/revisions','Durable calendar restart','Legacy compatibility','No original data exposure in workers','Required engineering checks','External dependencies accurately recorded','No new unresolved P0/P1 tested defects']
put('16_acceptance_matrix.json',[{'id':f'F{i:02d}','criterion':name,'result':'PASS_CODE_ONLY','evidence':['01_integrated_code_manifest.json','05_bitemporal_and_lifecycle_tests.json','06_universe_and_calendar_tests.json','07_database_restart_rollback_tests.json','08_compatibility_results.json','09_security_and_boundary_evidence.json','10_full_engineering_matrix.json','11_financial_source_dependencies.json','13_final_gatekeeper.json']} for i,name in enumerate(criteria,1)])
put('17_preservation_manifest.json',dict(phase_changes=phase,combined_delivery=delivery,unchanged_baseline_receipt_entries=len(preserved),old_tests_and_expectations_unchanged=True,existing_source_policy_registry_ORM_calendar_config_unchanged=True,previous_dossiers_read_verified_and_unchanged=530,original_data_signing_incident_payload_hashing=False,original_checkout_integration=False,source_preservation_scope='Allowed code/nonmarket metadata only, no fresh original raw-integrity certificate'))
put('18_negative_first_history.json',dict(cases=negative,final_focused=summary('foundation'),chronology='55fail2pass baseline;77pass3fail review;80pass2fail reliability;82pass2fail semantic;84pass2fail controller;86pass1fail owner-root bypass, then87pass. Formatting-only failures also preserved, not counted as desired negative-first proofs.',frozen_sources='support/*freeze*.json and negative-sources snapshots',control_failures=['One experiment-helper syntax regression during style cleanup, caught and corrected','Staging refusals while source/inventory changed; no fallback, no acceptance','Old experiment controller continued after failed init; strict stage predicate and serial collection barrier corrected it','Initial consumer-inspection instruction lookup absent from minimal snapshot; explicitly authorized instruction files read separately;original attempt retained']))
put('19_performance_results.json',latest['foundationperf']['worker_result'])
put('15_final_report.md',f'''# OD06 foundation completion: engineering PASS; financial and production BLOCKED
Reviewed {HEAD}, feature/od01-source-rights. One integrated data-free development snapshot: {S}. Ten pinned OD05/OD06 sources adopted; this phase modified3existing modules and added6files (authority/repository,2experiment helpers,87case test file,empty owner-root config). Combined16file delivery is applied/tested in the safe snapshot, not integrated into original application checkout.

Durable SQLAlchemy12table append-only identity/evidence/event/claim/session/coverage/membership schema; file/in-memory restart/rollback, nativeFK and mutation refusal, canonical serialization, idempotency, three-step/reversal history and indexed candidate-listing queries. Real SIGKILL after insert/before commit, new-process SQLite recovery and competing process revisions independently verified on anonymous disposable DB. Owner-root AND exact evidence/provenance/review AND existing source-rights required; caller labels/hash cannot self-attest. Empty owner-root register grants nothing. Strict PIT count reconciliation, unknown identity/lifecycle quarantine, versioned explicit calendar coverage and session queries retained; legacy APIs/ORM/policies/data unchanged.

Fresh Linux3.12:87foundation and66preservedOD06 tests PASS. Parser170pass1skip; finalA includes existingV/W/X/R1cases. Collection1017=A1009+B4+C4. A997pass12skip,exit0; unchanged nonrealdata diagnostic997pass4failed12skip,C4deselected,exit1. Ruff/mypy/pip/compileexit0. Twelve skips retain5platform and7Windows-native blocked nodes. Windows3.14/3.11 notrun withoutapprovedisolation; no waiver. Coverage/commands/actual performance in10/19; no100%or market-scale claim. Final stage manifests bound to final source hashes. Historical failures and all negative-first sources preserved.

F01-F15 PASS within tested code-only scope. EngineeringoverallPASS. Actual independently verified financial rows/mappings/sessions:0; authentic validationBLOCKED_REAL_DATA. Actualtrustedownerroots:0;sourcepolicies13pending. No original market payloads opened/hashed/copied by workers, originalmountedscan notrerun, no signing/release/data changes. OD05V/R1incidents remainpendinghumanreview, originalR1extentunknown. ProductionintegrationBLOCKED; SQLite foundation migration is NOT production migration approval. No commit/push/merge/OD07.

OD07 code-only dependency contract READY, separate explicit owner authorization required. Full integration needs accountable incident disposition, approved platform conditions, authenticated permitted identity/calendar/PIT completeness references and separately reviewed migration/consumer plan. No generic additional OD06 phase proposed. STOPafterthisfoundationexecution.
''')
R=B/'report-inputs';R.mkdir()
raw=json.dumps({'artifacts':outputs},sort_keys=True).encode();(R/'summary.json').write_bytes(raw)
(R/'manifest.json').write_text(json.dumps({'schema_version':'od05.final-report/v1','files':{'summary.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}}))
save(B/'report-input-index.json',['manifest.json','summary.json'])
save(B/'report-preparation.json',dict(files=list(outputs),phase_changes=phase,delivery=delivery,coverage=coverage,utc=datetime.now(UTC).isoformat()))
print(json.dumps({'reports':len(outputs),'phase_changes':len(phase),'delivery_files':len(delivery),'gates':gates,'coverage':coverage['A']['foundation_components']}))
