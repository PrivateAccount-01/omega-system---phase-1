"""Prepare approved report data from exact native data-free inputs. No Git."""
import ast,difflib,hashlib,json
from collections import Counter
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od05-final-20261117T201612Z');S=B/'staged2/repo';OLD=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
commands=[]
for p in (B/'logs').glob('*-command.json'):
 r=load(p);r['log']='logs/'+p.name;commands.append(r)
latest={}
for r in sorted(commands,key=lambda r:r['end_utc']):latest[r['job']]=r
for n in ['finalfocus','parser','focused','presence','W','A','mypy','pip','compile','environment','profile','type']:assert latest[n]['exit_code']==0,n
assert latest['diagnostic']['exit_code']==1
inventory=load(B/'runtime-inventory.json');assert Counter(inventory.values())=={'A':856,'B':4,'C':4}
Bnodes={n for n,c in inventory.items() if c=='B'}
assert {r['nodeid'] for r in latest['diagnostic']['worker_result']['reports'] if r['outcome']=='failed'}==Bnodes
assert set(latest['diagnostic']['worker_result']['deselected'])=={n for n,c in inventory.items() if c=='C'}
ruff=max((load(p) for p in (B/'logs').glob('static-ruff-*.json')),key=lambda r:r['end_utc']);assert ruff['exit_code']==0
changes=['src/omegadata/parsers/contracts.py','src/omegadata/parsers/dispatch.py','src/omegadata/parsers/nse_cm.py','src/omegadata/parsers/schema_catalog.py','scripts/od05_final_report.py','tests/unit/test_od05_final_contracts.py']
base=load(next((B/'staged2').glob('receipt-*.json')));preserved=[]
for r in base['files']:
 if r['path'] not in changes:assert sha(S/r['path'])==r['sha256'];preserved.append(r['path'])
assert {p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file()}=={r['path'] for r in base['files']}|set(changes)
change_rows=[];patch=[]
for n in changes:
 raw=(S/n).read_bytes();old=(OLD/n).read_bytes() if (OLD/n).exists() else b''
 change_rows.append({'path':n,'before_sha256':hashlib.sha256(old).hexdigest() if old else None,'after_sha256':hashlib.sha256(raw).hexdigest(),'applied_to_original_checkout':False})
 patch.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),raw.decode().splitlines(keepends=True),fromfile='a/'+n if old else '/dev/null',tofile='b/'+n))
(B/'implementation.patch').write_text(''.join(patch));(B/'code-delivery-manifest.json').write_text(json.dumps(change_rows,indent=2))
freeze=load(B/'negative-first-freeze.json');red=next(r for r in commands if r['job']=='finalfocus' and r['exit_code']==1)
assert red['worker_result']['counts']=={'failed':15,'passed':1}
assert freeze['sha256']==sha(S/'tests/unit/test_od05_final_contracts.py')
prior=load(B/'prior-read.json');outputs={}
def put(n,v):outputs[n]=v+'\n' if isinstance(v,str) else json.dumps(v,indent=2)+'\n'
def cmd(n):
 r=latest[n];w=r['worker_result'];return {'command_id':Path(r['log']).stem,'command':r['argv'],'working_directory':r['cwd'],'platform':'Linux WSL/native','python_version':w['python'],'source_commit':r['source_commit'],'source_manifest_sha256':r['source_manifest_sha256'],'start_utc':r['start_utc'],'end_utc':r['end_utc'],'exit_code':r['exit_code'],'counts':w.get('counts',{}),'deselected':w.get('deselected',[]),'stdout_stderr_log':r['log'],'original_repository_mounted':False}
coverage={}
for n in ['finalfocus','parser','A','diagnostic']:
 p=B/latest[n]['log'].replace('-command.json','-coverage.json');coverage[n]={'totals':load(p)['totals'],'log':str(p.relative_to(B))}
policies=load(S/'config/source_rights_policy.v1.json')['policies'];assert not any(p['status']=='APPROVED' for p in policies)
formats=[]
for fid,columns in [('legacy-illustrative',['SYMBOL','SERIES','ISIN','TIMESTAMP','OPEN','HIGH','LOW','CLOSE','TOTTRDQTY']),('udiff-illustrative',['TckrSymb','SctySrs','ISIN','TradDt','BizDt','OpnPric','HghPric','LwPric','ClsPric','TtlTradgVol'])]:
 formats.append(dict(source_id='NSE_EQUITY_BHAVCOPY',source_venue='NSE_CM',source_format='CSV_OR_SINGLE_MEMBER_ZIP',format_id=fid,format_era='ILLUSTRATIVE_NOT_OFFICIAL',effective_start=None,effective_end=None,schema_version='od05.illustrative-cm/v1',parser_version='syn-v1',encoding_rules='UTF8_STRICT_CRLF_OR_LF',date_rules='EXACT_REQUESTED_ISO_DATE',numeric_rules='Decimal fixed-point 12 integer/8 fraction; nonnegative int64 quantity',required_columns=columns,optional_columns=[],nullable_values=['ISIN'],unknown_column_policy='PRESERVE_NOT_INTERPRETED',source_authentication_state='UNVERIFIED',content_permission_state='REGRESSION_ONLY_NO_SOURCE_GRANT'))
titles=['Schema/era catalogue','Source-specific selection','Authentic golden corpus','Missing required columns','Unknown columns preserved uninterpreted','Wrong date','Duplicate/ambiguous keys','Invalid numeric values','Missing versus zero','OHLC constraints','Volume bounds','Intraday timestamp ordering','Encoding','Corrupt ZIP','Archive traversal','Resource limits','HTML challenge','Unsupported era','Output versioning','Deterministic digest','Input immutability','Rights before read','No rows on failure','Authentic expected/actual field reconciliation']
features=[]
for i,title in enumerate(titles,1):
 state='BLOCKED_EXTERNAL' if i in {3,24} else 'OUT_OF_OD05_SCOPE' if i==12 else 'COMPLETE_AND_VERIFIED'
 features.append(dict(feature_id='P%02d'%i,feature=title,source_file='src/omegadata/parsers/schema_catalog.py' if i==1 else 'src/omegadata/parsers/nse_cm.py' if i in {4,5,6,7,8,9,10,11,13,14,15,16,17,20} else 'src/omegadata/parsers/dispatch.py',implementation_state=state,test_coverage='170 parser/reference cases plus16 final security/schema cases; exact nodes in command logs',required_input_class='APPROVED_AUTHENTIC_SOURCE' if state=='BLOCKED_EXTERNAL' else 'EXISTING_REGRESSION_FIXTURE_OR_NON_MARKET_CANARY',current_failure='BLOCKED_INPUT' if state=='BLOCKED_EXTERNAL' else None,financial_dependency=state=='BLOCKED_EXTERNAL',security_dependency='Approved Linux worker; independent platform/incident gates',reuse_decision='EXTEND_EXISTING_CONTRACT',next_action='Supply permitted authenticated reference bytes and independent rows' if state=='BLOCKED_EXTERNAL' else 'EOD has no intraday timestamp ordering contract' if i==12 else 'Retain tested scope'))
put('03_parser_implementation_inventory.json',{'features':features,'inspected_modules':load(B/'source-implementation-inspection.json'),'scope':'Pure illustrative NSE CM decoders only; official financial-era expansion BLOCKED_EXTERNAL','report_renderer':{'source_file':'scripts/od05_final_report.py','implementation_state':'COMPLETE_AND_VERIFIED','coverage':'16 security/schema cases and actual OS probes'}})
registered=[]
for n in ast.walk(ast.parse((S/'src/omegadata/track_a/source_registry.py').read_bytes())):
 if isinstance(n,ast.AnnAssign) and getattr(n.target,'id',None)=='SOURCE_REGISTRY':registered=[k.value for k in n.value.keys]
put('04_supported_source_era_matrix.json',{'implemented_profiles':formats,'registered_acquisition_families':registered,'other_families':'Acquisition registration is not versioned pure decoder support; no new JSON/BSE/FO/other financial parser claim','official_NSE_BSE_eras':'BLOCKED_REFERENCE','production_2020_and_2024_routes':'UNCHANGED; no inferred cutover','policy_status_counts':dict(Counter(p['status'] for p in policies))})
put('07_focused_test_results.json',{'new_tests':cmd('finalfocus'),'parser_reference_tests':cmd('parser'),'X':cmd('focused'),'V':cmd('presence'),'W':cmd('W'),'R1_actual_A_subset':dict(Counter(r['outcome'] for r in latest['A']['worker_result']['reports'] if 'test_od05xr1_windows_contract.py::' in r['nodeid'])),'red':{'freeze':freeze,'log':red['log'],'counts':red['worker_result']['counts']},'financial_acceptance':0})
put('08_cross_platform_engineering_matrix.json',{'Linux312':{n:cmd(n) for n in latest},'Ruff':ruff,'coverage':coverage,'runtime_inventory':'runtime-inventory.json','collected':864,'classes':dict(Counter(inventory.values())),'A_skips':[r for r in latest['A']['worker_result']['reports'] if r['outcome']=='skipped'],'B_nodes':sorted(Bnodes),'C_nodes':[n for n,c in inventory.items() if c=='C'],'Windows314':'NOT_RUN_WINDOWS_OS_CAPABILITY_BLOCKED; old static results ARCH','Windows311':'NOT_RUN_WINDOWS_OS_CAPABILITY_BLOCKED; old static results ARCH','platform_requirement_waived':False})
put('09_golden_corpus_coverage.json',{'formats':[{'format_id':p['format_id'],'input_class':'EXISTING_REGRESSION_FIXTURE','authentic_golden_state':'BLOCKED_AUTHENTIC_SOURCE_VALIDATION','permitted_real_rows_inspected':0,'independently_verified_real_rows':0,'expected_real_rows':None,'actual_real_rows':None,'field_mismatches':None,'date_coverage':None,'independent_reference':'Existing synthetic oracle for software only','parser_version':p['parser_version']} for p in formats],'source_rights':'All13policies pending review; no approved authentic corpus in permitted inputs','publisher_origin_verified':False,'real_total_row_count':'UNKNOWN_NOT_INSPECTED','synthetic_financial_contribution':0})
put('10_original_archive_metadata_scorecard.json',{'evidence_class':'ARCH_SOURCE_METADATA_ONLY','fresh_original_scan':False,'manifest_candidates':3626,'seed':3596,'cache':30,'present':3626,'size_matched':3626,'hardlinked':2760,'single_link':866,'missing':0,'original_WSL_performance':'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED','budget_seconds':30,'real_rows_verified':0,'raw_content_authenticity_rights':'NOT_ESTABLISHED_BY_METADATA'})
put('11_preservation_and_change_manifest.json',{'reviewed_commit':'dd007c9e33d3d4ffaefe339cb766b428944bcdee','changes':change_rows,'patch_applied_to_original':False,'unchanged_snapshot_baseline_entries':len(preserved),'old_test_assertions_unchanged':True,'negative_test_source_hash_unchanged':True,'prior_evidence_read_record':'prior-read.json','original_payload_or_signing_byte_hashing':False,'source_policy_production_routing_pit_ca_db_release_changes':False,'rollback':'Review/revert only delivered changes in data-free workspace; no cleanup or historical evidence rewriting'})
gate={'execution_mode':'OD05_FINAL_CONSOLIDATED_IMPLEMENTATION_AND_GATE_CLOSURE','reviewed_HEAD':'dd007c9e33d3d4ffaefe339cb766b428944bcdee','source_state':'DATA_FREE_SNAPSHOT_PLUS_DELIVERED_PATCH_NOT_APPLIED_TO_ORIGINAL','OD05_PARSER_ENGINEERING':'PASS','parser_PASS_scope':'Only existing declared illustrative NSE-CM CSV/ZIP contracts; official era certification BLOCKED_EXTERNAL','OD05_AUTHENTIC_SOURCE_VALIDATION':'BLOCKED','authentic_exact_status':'BLOCKED_AUTHENTIC_SOURCE_VALIDATION','OD05_TRUSTED_CONTROLLER':'PASS','controller_PASS_scope':'New pinned-bundle renderer inside actual Linux OS boundary; not historical incident clearance','OD05_PLATFORM_ASSURANCE':'PARTIAL','Linux_worker':'PASS_SCOPED','Windows_worker':'WINDOWS_OS_CAPABILITY_BLOCKED','incident_disposition':{'OD05V':'PENDING_HUMAN_OWNER_REVIEW','OD05XR1':'PENDING_HUMAN_OWNER_REVIEW','OD05XR1_PAYLOAD_ACCESS':'UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'},'OD05_FINANCIAL_RELEASE':'BLOCKED_REAL_DATA','OD05_OVERALL':'CONDITIONAL','outcome':'B_SCOPED_CODE_DELIVERED_EXTERNAL_ACCEPTANCE_BLOCKED','OD06_CODE_ONLY_READINESS':'READY','code_only_scope':'Interface/design readiness in isolated snapshot only; separate owner authorization and gate-separation ADR acceptance required before execution','OD06_FULL_INTEGRATION_READINESS':'BLOCKED','original_checkout_integration':'BLOCKED_PENDING_INCIDENT_DISPOSITION','financial_rows_verified':0,'A':latest['A']['worker_result']['counts'],'full_diagnostic_exit':1,'full_diagnostic':latest['diagnostic']['worker_result']['counts'],'Windows_requirement_waived':False,'commit_push_release_sign_OD06':'NOT_PERFORMED','review_independence':'Same-agent review plus actual independent OS mechanisms; no human approval invented','one_next_action':'Owner review/approve bounded OD06 code-only handoff and ADR; original mixed checkout remains incident-blocked'}
put('13_final_gatekeeper.json',gate)
put('00_final_scope_and_identity.md',f'''# Final consolidated OD05 scope

Reviewed branch feature/od01-source-rights, HEAD dd007c9e33d3d4ffaefe339cb766b428944bcdee matched local ref-only and remote metadata at entry. No unrestricted Git/status/diff/content refresh against the mixed checkout. No commit, push, merge, release, signing, acquisition or OD06 execution.

Data-free workspace: {B}. Source came only from the verified canonical R1 tree, receipt80fcf7e...; every approved file/hash was checked, then unchanged Linux stage/native proof created a fresh snapshot. The original repository, archive roots, retained incident copies and private directories were never mounted. Runtime/public OS files remain a trusted assumption. Bootstrap's first launcher mount failed and was corrected; failure remains.

All six tested changes are delivered as implementation.patch and code/, NOT APPLIED to the original mixed checkout while incident decisions remain pending. Source identity is reviewed HEAD plus delivered patch hashes. The original worktree is preserved. This is one final consolidated pass, not a new expanding remediation phase.''')
put('01_prior_phase_consolidation.md',f'''# Retained implementation and evidence

Complete approved V/W/X/R1 evidence was read, including recorded failures, incident ledgers, runtime inventories and source hashes. File counts: {[(k,len(v)) for k,v in prior.items()]}. The full reading/hash record is prior-read.json. Actual current implementation was inspected in the pinned snapshot; module/function identities are in03inventory. Old results remain ARCH unless freshly reproduced.

Retain pure parser/Decimal/digest contracts, reference validator, rights-before-read RawArchive integration, presence v1/v2 meaning, Linux namespace/seccomp/stage, Windows fail-closed contracts, original tests and financial expectations. No production source policy/routing or financial semantics were edited.

Coordinator setup initially duplicated a runtime-inventory path after collection. The canonical launcher refused MANIFEST_SCOPE before staging; all attempts remain. Replacing that one exact entry fixed setup. A Windows command-length rejection prevented one report-preparation process from starting; split writes fixed it without any original-data operation. Historical finalizers were never imported or executed.''')
put('02_incident_and_security_boundaries.md','''# Independent containment and incident gates

OD05V_INCIDENT=PENDING_HUMAN_OWNER_REVIEW. OD05XR1_INCIDENT=PENDING_HUMAN_OWNER_REVIEW. OD05XR1_PAYLOAD_ACCESS=UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED. HISTORICAL_FINALIZER=DO_NOT_RERUN. No zero-read certificate, owner approval or retrospective waiver is created. Original/retained payloads were not opened to reconstruct incidents.

The new report renderer accepts only externally pinned manifest/summary JSON in its explicit data-free /work bundle. Exact input set, hashes, file/descriptor identities, no-follow opens, bounded sizes and exclusive fresh output are checked. Unknown files, links, forged pins, duplicate JSON, command keys and output traversal fail closed. No Git, subprocess, unbounded directory discovery, fallback or cleanup interface exists.

The actual accepted report worker uses unchanged Linux namespace/read-only mounts/dropped capabilities/seccomp/native denial probes and controlled private IPC before staging/reporting. Original roots are not exposed. A harmless fake .git directory tests that old Git behavior cannot be reached; kernel child/network/file probes provide independent OS evidence beyond Python instrumentation. Trusted launcher/runtime/public system support and no hostile host administrator remain explicit assumptions.

Windows inherited limits are retained, not re-probed/retried or waived. No Windows native tests run unguarded. The original scanner thirty-second budget is unchanged; no original-mounted performance scan was repeated. Current final-pass restricted-payload reads are zero by reviewed data-free input/boundary scope; historical R1 access remains UNKNOWN.''')
put('05_schema_contracts_and_error_taxonomy.md','''# Supported schema contracts and errors

Only legacy-illustrative and udiff-illustrative are pure CSV/ZIP profiles, explicitly parser syn-v1, reference synthetic-v1, mode SYNTHETIC_TEST_ONLY. See04matrix and schema_catalog.supported_formats(). Era dates are unknown/None, not official NSE publication boundaries. No production2020/2024 cutover change or generic JSON financial fallback.

UTF8 strict; LF/CRLF; one exact synthetic.csv ZIP member; bounded compressed/uncompressed bytes, ratio, rows, columns and values; archive corruption, path traversal, nested/unsafe entries and HTML denials rejected. Required and duplicate columns, exact requested trade/business date, duplicate/ambiguous record keys, missing versus zero, fixed-point Decimal precision, signed-int64 nonnegative quantity and illustrative OHLC constraints are enforced. ISIN value may be empty while its column is required. Unknown columns are explicitly preserved as uninterpreted lexemes and contribute to digest; they do not acquire financial meaning. P12intraday ordering is not applicable to date-only EOD schemas; it is not reported as passed.

New ParseResult.failure_code adds stable classifications while retaining old reasons: PARSER_UNSUPPORTED_ERA, PARSER_SOURCE_UNVERIFIED, PARSER_INPUT_CHANGED, PARSER_REQUIRED_COLUMN_MISSING, PARSER_DUPLICATE_COLUMN, PARSER_INVALID_CSV, PARSER_DUPLICATE_OR_INVALID_KEY, PARSER_WRONG_DATE, PARSER_INVALID_PRICE, PARSER_INVALID_OHLC, PARSER_INVALID_VOLUME, PARSER_ARCHIVE_UNSAFE, PARSER_ARCHIVE_CORRUPT, PARSER_RESOURCE_LIMIT, PARSER_INVALID_ROW, PARSER_RECORD_COUNT_MISMATCH, PARSER_HTML_CHALLENGE, PARSER_INVALID_ENCODING. Rights refusals remain SourcePolicyError before archive reads, never an accepted dataset. All decoder quarantines have zero rows.

No official series enumeration, authenticated ISIN, exchange-specific price exception or financial unit is invented. Those reference-dependent official schema cases remain blocked. Published/known/effective/ingested times are not inferred by the pure parser.''')
put('06_negative_first_parser_tests.md',f'''# Genuine chronology

Freeze SHA {freeze['sha256']} preceded implementation. Actual baseline {red['log']}:15failed/1passed,exit1. Missing public failure code/catalogue/report APIs are NEW_FEATURE_ABSENT, not historical financial defects. Existing native boundary check passed; code was never broken to manufacture red.

Final new tests:16passed,exit0 in {latest['finalfocus']['log']}; frozen test source unchanged. Separate parser/reference subset:170passed/1Windows-platformskip in {latest['parser']['log']}. Original T01-T32 and OD05R history is retained. Existing synthetic fixtures/oracle support software only. No new financial records, OHLC, prices, volumes, identifiers, actions or returns were generated. Authentic P03/P24 remain blocked.

PUBLIC_FAILURES import spacing initially failed Ruff; corrected without semantic changes, final Ruff passes. Bootstrap and coordinator manifest refusals remain recorded. All P01-P24 completion states and the EOD-specific exclusion are explicit in03inventory. No prior negative-first sequence is rewritten.''')
put('12_unresolved_external_dependencies.md','''# Minimal acceptance dependencies and ADR

1. Accountable owner disposition of OD05V and R1 incidents before resuming execution/integration in the original mixed checkout. R1 payload extent remains unknown. The agent cannot self-approve.
2. Authorized authentic historical schema documents and original golden source bytes with publisher provenance, usage rights and independently reviewed exact expected rows for source-dependent financial acceptance. All13policy records in the permitted snapshot are pending; no approved authentic corpus exists there. No new generic permission packet or live endpoint request.
3. Operator-approved isolated Windows Python3.14/3.11 environment for the inherited cross-platform requirement, OR explicit owner acceptance of the proposed gate-separation ADR. Neither is silently waived.

ADR awaiting owner acceptance: report parser software, authentic golden correctness, trusted-controller confinement, platform assurance and incident disposition separately. Retain inherited mandatory requirements for full OD05 acceptance. Separately authorize only code-only OD06 development in the verified data-free snapshot while external gates are blocked. This does not authorize original checkout integration, financial consumption/publication, source-policy changes, signing or production readiness. It does not retrospectively clear incidents or certify Windows.''')
fields={'source_id':'ParseResult/ParsedBar.source_key','format_era':'ParseResult.format_id, illustrative only; no official era inferred','schema_version':'schema_catalog lookup by exact format_id:od05.illustrative-cm/v1','parser_version':'ParseResult.parser_version pinned syn-v1','exchange':'ParsedBar.exchange','source_venue':'Catalogue NSE_CM, unverified metadata','trade_date':'ParsedBar.trade_date','symbol_as_reported':'ParsedBar.symbol, original text retained','series':'ParsedBar.series, opaque illustrative value','isin_if_available':'ParsedBar.isin optional, not authenticated identity','instrument_attributes':'Not established; downstream source-backed enrichment or quarantine required','source_artifact_identity':'ParseResult.raw_sha256 plus optional observation_id; hash is not publisher truth','data_quality_status':'PARSED_UNVERIFIED or QUARANTINED, never financially accepted','source_authentication_status':'SYNTHETIC_TEST_ONLY/UNVERIFIED','source_rights_status':'No real grant; registry remains pending','known_from':'Unknown/None; never infer from trade_date','effective_at':'Unknown/None; requires verified identity/event evidence','ingested_at':'Unknown/None; trusted ingestion observation must supply it'}
put('14_od06_dependency_contract.md','# OD06 dependency contract (handoff only)\n\n'+'\n'.join('- **'+k+'**: '+v+'.' for k,v in fields.items())+'''

Consumer invariants: reject QUARANTINED and unsupported/official claims. Preserve source row ordinal, original lexemes, raw identity and exact source/format/parser versions. PARSED_UNVERIFIED alone cannot certify an instrument, PIT universe, financial release or economic research. Never fill availability timestamps or ISIN from guesses. Results are immutable; separate versioned enrichment must retain lineage. Financial/source-dependent facts stay unknown/quarantined until permitted evidence exists.''')
put('15_od06_implementation_handoff.md','''# Bounded OD06 handoff ? no execution authorization

Proposed mode:OD06_CODE_ONLY_INSTRUMENT_IDENTITY_AND_CALENDAR_IMPLEMENTATION, in the approved data-free snapshot only, AFTER explicit owner authorization and acceptance of the gate-separation ADR. Begin from reviewed HEAD plus delivered OD05 patch, verify exact code pins. No execution/integration in the original mixed checkout before incident disposition. No source acquisition/policy change, restricted payloads, release/signing/trading or financial gate promotion.

Reuse parsers/contracts.py, dispatch.py, schema_catalog.py and reference_evidence.py; inspect existing track_b/isin_master.py/universe_manager.py, track_a/trading_calendar.py/source_registry.py, domain.py and DB models for compatibility. Preserve PIT and corporate-action economics. Keep new identity/calendar interfaces versioned and opt-in until source validation.

Design: immutable issuer/security/listing identities, exchange-specific symbol and series claims, versioned symbol-to-ISIN history with business-valid and knowledge intervals, explicit listing/delisting/rename/suspension/relisting and merger transitions, and authoritative calendar/session references including exceptional sessions. Never merge economic identities by symbol or ISIN alone. Unknown/conflicting mappings quarantine.

Tests: freeze code-only state/interval/refusal tests before corrections; preserve existing robustness fixtures, with zero authentic financial contribution. Cover ambiguous/overlapping/revised identity claims, as-of availability, missing mappings and boundary dates. Authentic real symbol changes, mergers, listings, holidays and sessions remain BLOCKED_INPUT until permitted independently reviewed references exist. Do not invent securities, prices, financial mappings, actions or calendars as official truth.

Use14dependency contract exactly. known_from/effective_at/ingested_at, authenticated identity facts and complete trading-session history are missing source facts, not defaults. Run exact A/B/C inventory, targeted tests, unchanged diagnostic, quality checks and native guard proof; report through the accepted constrained renderer only. No old mixed-checkout Git finalizer.

One next decision: owner approve this bounded code-only contract and ADR before starting OD06. This handoff does not approve itself or resolve incidents. Full integration remains blocked.''')
put('16_final_report.md','''# Final consolidated OD05: scoped engineering delivered; external acceptance blocked

Reviewed branch feature/od01-source-rights, HEAD dd007c9e33d3d4ffaefe339cb766b428944bcdee. The original mixed worktree remains preserved. Six tested changes are delivered in implementation.patch/code and retained in the native data-free snapshot; NOT applied, committed or pushed. No OD06, acquisition, policy/routing, release/signing or production action.

Implemented an explicit schema catalogue, additive public parser failure codes with precise encoding/HTML/OHLC/resource classifications preserving legacy reasons, and a pinned-bundle OS-constrained renderer. Retained existing pure parser, exact Decimal/digest, ZIP/CSV validation, rights-before-read, original tests, Linux sandbox/stage and Windows admission contracts. No new financial observations were generated.

| Fresh Linux scope | Result |
|---|---|
| Collection |864=A856+B4+C4|
| New focused cases |16passed,exit0; baseline15failed/1passed before implementation|
| Separate parser/reference subset |170passed/1platformskip,exit0|
| Existing X/V/W |33pass /40pass+1skip /39pass|
| R1 within A |33pass+7explicit native blocks/skips|
| A engineering |844passed/12skipped,exit0|
| Full unchanged non-realdata diagnostic |844passed/4Bfailed/12skipped,C4deselected,exit1|
| Ruff/mypy/pip/compile/report strict typing |exit0|

Twelve A skips are five unchanged Windows-specific nodes plus seven blocked native requirements. No skip becomes a pass; B expectations remain unchanged and C4remain unexecuted. Windows current execution NOT_RUN; old Windows static evidence ARCH only. Actual commands, source pins, stdout/stderr and coverage are in08matrix. P01-P24completion in03inventory; authentic P03/P24 blocked, intraday P12not applicable to EOD.

Authentic permitted golden comparisons:0rows. Total unverified financial row count UNKNOWN, not zero. Archived3626present/size-matched paths,seed3596/cache30,hardlinks2760/single866 remain metadata evidence only. No original scan or payload integrity check ran. Official NSE historical/BSE schemas and source validation remain reference/rights-blocked; no guessed2020/2024cutover or production routing change. Original WSL performance remains blocked at unchanged30seconds.

The new accepted renderer executes under actual Linux containment, with no original mount or Git/subprocess/discovery/fallback/cleanup API. Input pins/identities and fresh outputs are enforced. Historical OD05V/R1 incidents remain pending human review; R1access extentUNKNOWN. No zero-read certificate, incident waiver or Windows certification is invented. This final pass performed no restricted market-payload access.

Gates: parser engineeringPASS only for existing declared illustrative profiles; authentic-source validationBLOCKED; new trusted rendererPASS scoped to Linux; platformPARTIAL, Windows requirement not waived; financialBLOCKED_REAL_DATA; overallCONDITIONAL, NOT full OD05 acceptance/APPROVE_FOR_NEXT_PHASE. OD06 code-only interface/design readinessREADY in the isolated snapshot, subject to separate explicit authorization/ADR approval; full integrationBLOCKED. See13Gatekeeper.

One next required action: owner review/approve the bounded OD06 code-only handoff and gate-separation ADR. Original checkout integration remains incident-blocked. Full source-backed/platform acceptance still requires12external dependencies. No new OD05 remediation phase is proposed. STOP after final OD05.''')
assert len(outputs)==17
I=B/'report-inputs';I.mkdir()
raw=json.dumps({'artifacts':outputs},ensure_ascii=True).encode();(I/'summary.json').write_bytes(raw)
spec={'schema_version':'od05.final-report/v1','files':{'summary.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}};(I/'manifest.json').write_text(json.dumps(spec));(B/'report-input-index.json').write_text(json.dumps(['manifest.json','summary.json']))
(B/'report-preparation.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'files':list(outputs),'manifest_sha256':sha(I/'manifest.json'),'input_sha256':sha(I/'summary.json'),'changes':change_rows,'original_access':False},indent=2))
print(json.dumps({'prepared_reports':len(outputs),'source_changes':len(changes),'preserved_entries':len(preserved),'coverage':coverage,'gates':gate}))
