"""Prepare a bounded code-only OD07 final report. No Git or original checkout."""
import hashlib,json,difflib
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,UTC
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo'
P=Path('/home/parilrupani/omega-od07-20261119T171019Z');E=P/'delivery/docs/omegadata_v2/implementation/od07/20261119T171019Z'
HEAD='91a0030094c0132b6a5586ce277ed1e56eb5e396'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pretty(x):return json.dumps(x,indent=2)+'\n'
commands=[(p,load(p)) for p in (B/'logs').glob('*-command.json')]
def latest(job):return max(((p,c) for p,c in commands if c['job']==job),key=lambda r:r[1]['end_utc'])
required={j:latest(j) for j in ['collection','od07final','od07','od06','foundation','parser','A','diagnostic','mypy','pip','compile']}
for j,(p,c) in required.items():assert c['exit_code']==(1 if j=='diagnostic' else 0),(j,c['exit_code'])
ruffpath=max((B/'logs').glob('static-ruff-*.json'),key=lambda p:p.stat().st_mtime_ns);assert load(ruffpath)['exit_code']==0
inv=load(B/'runtime-inventory.json');classes=Counter(inv.values());A=required['A'][1]['worker_result'];diag=required['diagnostic'][1]['worker_result'];target=required['od07final'][1]['worker_result']
assert target['counts']=={'passed':84};assert classes=={'A':1193,'B':4,'C':4}
assert A['counts']=={'passed':1181,'skipped':12};assert diag['counts']=={'passed':1181,'failed':4,'skipped':12}
assert {r['nodeid'] for r in diag['reports'] if r['outcome']=='failed'}=={n for n,v in inv.items() if v=='B'}
base=load(next((B/'staged2').glob('receipt-*.json')))
baseline={r['path']:r['sha256'] for r in base['files']}
for row in load(B/'adoption.json')['files']:baseline[row['path']]=row['after_sha256']
modified=['src/omegadata/identity.py','src/omegadata/identity_authority.py','src/omegadata/adjustments/contracts.py','src/omegadata/adjustments/temporal.py','src/omegadata/adjustments/repository.py']
new=['src/omegadata/adjustments/bound_contracts.py','src/omegadata/adjustments/bound_chain.py','src/omegadata/adjustments/admission.py','tests/unit/test_od07_final.py']
changes=[]
for n in modified+new:changes.append({'path':n,'before_sha256':baseline.get(n),'after_sha256':sha(S/n),'bytes':(S/n).stat().st_size,'applied_in_safe_snapshot':True,'applied_to_original_checkout':False})
for n,pin in baseline.items():
 if n not in modified:assert sha(S/n)==pin,('UNEXPECTED_CHANGE',n)
for j,(p,c) in required.items():
 pins={r['path']:r['sha256'] for r in load(p.with_name(p.name.replace('-command.json','-manifest.json')))['files']}
 for row in changes:assert pins[row['path']]==row['after_sha256'],('STALE_RESULT',j,row['path'])
# Check all historical sealed evidence again; no original archive inspection.
prior=load(E/'evidence-sha256.json')
for n,row in prior['files'].items():assert sha(E/n)==row['sha256'] and (E/n).stat().st_size==row['bytes']
combined=load(B/'adoption.json')['files']
for row in combined:
 row.update(after_sha256=sha(S/row['path']),bytes=(S/row['path']).stat().st_size)
for row in changes:
 if row['path'] in new:combined.append(row)
assert len(combined)==28
snapshot={**baseline,**{r['path']:r['after_sha256'] for r in changes}}
snapshot_digest=hashlib.sha256(pretty(dict(sorted(snapshot.items()))).encode()).hexdigest()
for name,value in [('final-source-manifest.json',snapshot),('phase-source-changes.json',changes),('combined-delivery-manifest.json',combined)]:
 with (B/name).open('x') as f:f.write(pretty(value))
basepath=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo');patch=[];phasepatch=[]
for row in sorted(combined,key=lambda r:r['path']):
 n=row['path'];before='' if row['before_sha256'] is None else (basepath/n).read_text()
 if row['before_sha256'] is not None:assert sha(basepath/n)==row['before_sha256']
 patch.extend(difflib.unified_diff(before.splitlines(True),(S/n).read_text().splitlines(True),fromfile='/dev/null' if row['before_sha256'] is None else 'a/'+n,tofile='b/'+n))
for row in changes:
 n=row['path'];before='' if n in new else (E/'code'/n).read_text();phasepatch.extend(difflib.unified_diff(before.splitlines(True),(S/n).read_text().splitlines(True),fromfile='/dev/null' if n in new else 'a/'+n,tofile='b/'+n))
(B/'implementation.patch').write_text(''.join(patch));(B/'phase-only.patch').write_text(''.join(phasepatch))
proofpath=required['od07final'][0].with_name(required['od07final'][0].name.replace('-command.json','-native-probes.json'));proof=load(proofpath)
assert proof['boundary']['verified'] and proof['boundary']['seccomp_mode']==2 and len(proof['probes'])==12 and all(p['denied'] and not p['python_hook'] for p in proof['probes']) and proof['local_ipc_control']['bytes']>0
cov=load(required['od07final'][0].with_name(required['od07final'][0].name.replace('-command.json','-coverage.json')))
selected={n:v['summary'] for n,v in cov['files'].items() if '/adjustments/' in n}
totals={k:sum(v.get(k,0) for v in selected.values()) for k in ['covered_lines','num_statements','covered_branches','num_branches']}
totals.update(statement_percent=100*totals['covered_lines']/totals['num_statements'],branch_percent=100*totals['covered_branches']/totals['num_branches'])
oldcov=load(required['od07'][0].with_name(required['od07'][0].name.replace('-command.json','-coverage.json')))
union_totals={'covered_lines':0,'num_statements':0,'covered_branches':0,'num_branches':0}
union_modules={}
for n,item in cov['files'].items():
 if '/adjustments/' not in n:continue
 other=oldcov['files'][n]
 assert item['summary']['num_statements']==other['summary']['num_statements']
 assert item['summary']['num_branches']==other['summary']['num_branches']
 lines=(set(item['executed_lines'])|set(other['executed_lines']))-set(item.get('excluded_lines',[]))
 branches={tuple(v) for v in item.get('executed_branches',[])}|{tuple(v) for v in other.get('executed_branches',[])}
 assert len(lines)<=item['summary']['num_statements']
 row={'covered_lines':len(lines),'num_statements':item['summary']['num_statements'],'covered_branches':len(branches),'num_branches':item['summary']['num_branches']}
 union_modules[n]=row
 for key in union_totals:union_totals[key]+=row[key]
union_totals['statement_percent']=100*union_totals['covered_lines']/union_totals['num_statements']
union_totals['branch_percent']=100*union_totals['covered_branches']/union_totals['num_branches']
records=[]
for j,(p,c) in required.items():
 w=c['worker_result'];records.append({'job':j,'command_id':p.stem,'launcher_argv':c['argv'],'working_directory':c['cwd'],'platform':'Ubuntu/WSL Linux','python':w['python'],'interpreter':w.get('interpreter'),'start_utc':c['start_utc'],'end_utc':c['end_utc'],'elapsed_seconds':c['elapsed_seconds'],'exit_code':c['exit_code'],'counts':w['counts'],'stdout_stderr':'logs/'+p.name,'input_manifest_sha256':c['source_manifest_sha256'],'input_manifest':'logs/'+p.name.replace('-command.json','-manifest.json')})
records.append({'job':'ruff','command':load(ruffpath)['argv'],'exit_code':0,'stdout_stderr':'logs/'+ruffpath.name,'scope':load(ruffpath)['scope']})
history=[]
for p,c in sorted(commands,key=lambda row:row[1]['start_utc']):
 if c['job']=='od07final':
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')));testpin=next(r['sha256'] for r in m['files'] if r['path']=='tests/unit/test_od07_final.py')
  history.append({'command':'logs/'+p.name,'start_utc':c['start_utc'],'end_utc':c['end_utc'],'test_sha256':testpin,'exit_code':c['exit_code'],'counts':c['worker_result']['counts'],'failed_nodes':[r['nodeid'] for r in c['worker_result']['reports'] if r['outcome']=='failed']})
byfile=defaultdict(Counter)
for row in A['reports']:byfile[row['nodeid'].split('::')[0]][row['outcome']]+=1
families=[f'R{i:02}' for i in range(1,7)]+[f'I{i:02}' for i in range(1,5)]+[f'H{i:02}' for i in range(1,5)]+[f'P{i:02}' for i in range(1,5)]+[f'E{i:02}' for i in range(1,4)]+[f'K{i:02}' for i in range(1,4)]+[f'D{i:02}' for i in range(1,5)]
assert len(families)==28
verdict={n:'PASS' for n in ['OD07_UPSTREAM_ADOPTION','OD07_REFERENCE_IDENTITY','OD07_IDENTITY_CONTINUITY','OD07_ACTION_HISTORY_COMPLETENESS','OD07_RESULT_INTEGRITY','OD07_EXECUTION_CONTRACT','OD07_PARAMETER_KNOWLEDGE','OD07_ADJUSTMENT_BASIS','OD07_MATHEMATICAL_CORRECTNESS','OD07_PERSISTENCE','OD07_ENGINEERING_OVERALL']}
verdict.update(OD07_AUTHENTIC_FINANCIAL_VALIDATION='BLOCKED_REAL_DATA',OD07_PRODUCTION_INTEGRATION='BLOCKED',OD08_CODE_ONLY_READINESS='READY',OD08_EXECUTION_AUTHORIZATION='NOT_GRANTED',scope='Versioned opt-in code-only engineering and mathematical controls; not financial-source certification',Windows='OS_CAPABILITY_BLOCKED',incident_disposition='PENDING_HUMAN_OWNER_REVIEW',independent_review='Same agent; separate literal Fraction oracle, SQLite and native kernel controls. No human approval claimed',new_unresolved_P0_P1_in_tested_scope=0,full_diagnostic='FAIL_FOUR_UNCHANGED_SOURCE_DEPENDENCIES')
art={}
def md(n,s):art[n]=s.strip()+'\n'
def js(n,v):art[n]=pretty(v)
md('00_scope_and_identity.md',f'''# Targeted OD07 closure
Repository PrivateAccount-01/omega-system---phase-1, branch feature/od01-source-rights. Reviewed local/remote HEAD {HEAD}; ref-only preflight, no original mixed worktree content refresh/status/diff. Original working state was deliberately not scanned. No reset, commit or push.

Live applied development: {S}. Snapshot digest {snapshot_digest}, {len(snapshot)} approved files. Exact24file sealed delivery adopted after before/null and after checks. All374sealed prior evidence files verified/read and preserved. Nine phase changes(five modified,four new);28combined delivery files. Original application not integrated. Only approved receipt/code evidence used; no recursive mixed checkout copy.

All execution through accepted Linux data-free isolation except read-only bounded source preparation/static formatting and lint. No original archive,incident copy,credential,signing or production database mounts. No real financial observation generated,read or verified. No OD08 execution.''')
js('01_upstream_adoption_manifest.json',{'adoption':load(B/'adoption.json'),'prior_seal_sha256':sha(E/'evidence-sha256.json'),'prior_sealed_files_unchanged':len(prior['files']),'baseline_count':len(baseline),'unchanged_baseline_count':len(baseline)-len(modified),'final_snapshot_count':len(snapshot),'final_snapshot_sha256':snapshot_digest,'changes':changes,'combined_delivery':combined})
md('02_confirmed_defect_reproduction.md','''# Actual reproduced gaps and chronology
Initial67cases executed before implementation:66NEW_FEATURE_ABSENT and one actual legacy rename refusal. The legacy raw/action eligibility required an old ticker at the later valid date; stable listing lookup fixes it. Missing v2 reference/history/parameter/execution/basis APIs are new contracts, not invented legacy security exploits.

The existing FORWARD operation intentionally inverts factors over the pre-ex window. It remains unchanged as v1 compatibility and is explicitly INVERSE_FACTOR_COMPARISON in v2. Conventional forward basis conversion is additive.

Review probes actually reproduced missing independent numerical/provenance admission, future parameter contradiction, unknown quantity convention, future basis horizon, displayed factor/status and exact calendar-link reconciliation. Fixes are narrow and recorded in frozen red/green sources. A compound test initially mislabeled Bonus parameters as SPLIT; corrected new fixture tag to BONUS, numerical40/120expectations unchanged. This was a test defect, not a production defect. Original100test source never modified.

See11_targeted_test_results.json for every actual command and failure. Ruff parse/type failures and their corrections remain in logs. No retroactive negative-first claim for preexisting passing functions.''')
md('03_reference_observation_contract.md','''# ReferenceObservation od07.reference/v2
Frozen explicit original scalar Reference plus observation/record IDs,row ordinal,security/listing,exchange,as-reported symbol/series,unit,basis,type,knowledge upper bound,observed/published time andversion. Price,currency,session,lower known bound,artifact/source/evidence are preserved from the original reference, never inferred from enclosing action.

Strict bound path checks security or reviewed successor security,listing andvenue,positivefinite Decimal,raw basis,units/currency,type,record/row/source identity,reference knowledge/publication/observation cutoff,independent reported-identifier resolution andauthority. Rights uses RAW_CLOSE on actual verified prior session;dividend requires REINVESTMENT_PRICE on explicit ex-close session;successor requires SUCCESSOR_VALUATION. Unbound scalar References remain v1 mathematical inputs only. No cross-listing substitution or adjusted-as-raw fallback. Real positive authority path remainsBLOCKED_INPUT.''')
md('04_identity_continuity_contract.md','''# Stable listing continuity; minimal OD07 dependency fix
MemoryIdentityRepository.resolve_listing_id is an additive opt-in query. It filters valid/knowledge intervals,supersession and stable listing;then reuses existing authority/conflict resolver. Raw identifiers resolve at observation date; subsequent state resolves through that listing,not the oldticker. No ticker guess,ISIN-derived continuity,active-only filter or ORM migration.

Renames and series changes preserve SAME_LISTING_CONTINUITY. Symbol reuse/wrongvenue/ambiguous mapping cannot merge securities. Historical delisted/suspended research data may remain HISTORICALLY_VALID_BUT_NOT_TRADABLE;execution status independently blocks. Missing/unreviewed security conversion remainsIDENTITY_TRANSITION_BLOCKED. Future-known correction excluded from earlier digest. Persistent OD06 repository unchanged;its immutable typed snapshots can feed the existing memory query contract. Lifecycle evidence is not manufactured.''')
md('05_action_history_completeness.md','''# HistorySnapshot od07.action-history/v2
Immutable declared security/listing/source scope,half-open valid range,explicit knowledge cutoff,complete action revisions/selected digest,coverage/evidence/source/policy versions and reviewed economic-event IDs. COMPLETE_FOR_DECLARED_SCOPE is necessary,not self-authenticating;STRICT coverage requires EvidenceAuthority. PARTIAL/UNKNOWN/CONFLICTING/SOURCE_BLOCKED refuse bound trusted calculation.

Selection verifies exact IDs/hash,scope,parents/supersession,duplicates,known revision and same-day order. Empty mathematical history can calculate only as explicit nonfinancial control;cannot prove no real actions. Repository context pin reconciles full selected history against separately persisted scoped action ledger,including omitted or fabricated-empty chains. Complete external scope still requires authorized authentic coverage evidence. No fuzzy duplicate suppression.''')
md('06_result_admission_integrity.md','''# Exact upstream state and separate admission
PinnedCalculation binds raw observation identity/digest,history snapshot/digest/selected revisions,actual identity records/resolution,version-filtered knowncalendar records,source authority bundle/root/policy digest,parameter state,cutoff/valid/basis dates,consumer/algorithm/rounding versions. Authority snapshot is read-only;no policy grant. Future-known action/identity/parameter records do not rewrite an earlier as-known result.

pin_context uses independently persisted action rows and separately derived reconciliation inputs,not result.inputs. Independent Fraction formulas validate individual factors/status,chain arithmetic,final rounding,ordered action set,raw/profile/cutoff/source artifacts,identity andexactcalendar lineage. append_bound_result then requires exact immutable context/result matching and rechecks arithmetic/provenance. Changed raw/revision/source/knowledge/calendar/identity/profile/factor/reused digest refuses atomically.

Legacy append_result remains an unverified mathematical/internal API. v2 nonmarket result publication remainsFalse. This is a trusted internal service,not protection against unrestricted same-process code execution or an attacker controlling the database/filesystem. Caller cannot create financial eligibility merely through labels.''')
md('07_execution_eligibility_contract.md','''# Basis is separate from eligibility
BoundResult reports raw_price_basis_preserved,mathematical status,identity/calendar/tradability/execution states and init-disabled eligibility flags. EXECUTION/RAW requireRAW_UNADJUSTED. Mathematical CALCULATED never by itself means executable or publishable.

Declared execution scope requires actual raw session,listing lifecycle,known evidence-backed security/listing/venue/session constraints,positive integer lot,positive whole-unit lot-multiple quantity,explicit settlement policy andCLEARrestrictions. Unknown calendar,closure,suspension,delisting,unknownlot/settlement/convention or future observation blocks. Anonymous controls alwaysBLOCKED_NON_MARKET_CONTROL even when structurally complete. No order routing,broker integration or invented settlement specification. Positive authentic execution acceptance remainsblocked.''')
md('08_parameter_availability.md','''# ParameterSet od07.parameter-availability/v2
Each relevant action requires explicit parameter revision,exact parameter digest,evidence and aware half-open known bounds. No fallback from ex-date,ingestion,wall-clock or action announcement. Unknown lower bound,future parameters,expired/revoked evidence,incomplete digest/revision or contradictory future action parameter timestamp refuses. Exact cutoff is inclusive.

Later amended rights/dividend/split/bonus/merger terms require new immutable action/parameter revisions. Earlier as-known selected parameters and digests remain unchanged. Explicit zero subscription is legitimate when evidenced;missing is never zero. Scalar factor math remains usable without temporal promotion. Tests use anonymous structural controls only.''')
md('09_adjustment_basis_semantics.md','''# BasisPolicy od07.basis-policy/v2
BACKWARD_ADJUSTED selects observation_date<ex_date<=basis_date and applies split1/S. FORWARD_ADJUSTED selects basis_date<ex_date<=observation_date and appliesS. Ex-date itself is post-action. INVERSE_FACTOR_COMPARISON explicitly retains oldpre-ex inversion semantics. RAW_UNADJUSTED preserves observations. TOTAL_RETURN_INDEX refuses without a complete index-base/reinvestment methodology.

Basis/observation cannot exceed declared valid horizon. Conventional forward currently supports split,reverse andbonus only;rights/dividend forward requests returnUNSUPPORTED_POLICY rather than invent economic transformations. Existing gross ex-close total-return andprice-return dividend separation retained. Same-day events require explicit unique order. Exactintermediate terms/final versioned Decimal rounding reused;raw unchanged.''')
md('10_independent_reference_vectors.md','''# Mathematical controls, not market observations
Literal known answers,independent Fraction reconciliation,no authentic prices/events/securities represented. SplitS2:pre120->backward60;post60->forward120. Ex-date/post observations unchanged on backward postbasis;pre observations unchanged onforward prebasis. ReverseS.5:pre120->backward240;post240->forward120. Split2 thenbonus1per2:factor1/3;120->40,forward40->120. Inverse comparison pre120->240 explicitly differs from conventional forward. RightsN4,R1,P100,S50:TERP90,factor.9;mathematical120->108. Explicitissue0givesfactor.8;120->96.

The independent admission oracle uses Fraction directly rather than the production factor function. Existing100tests retain previous split/bonus/rights/dividend precision,immutability andtemporal vectors. New controls contributezero to authentic financial validation. No source-method certification inferred.''')
js('11_targeted_test_results.json',{'mandatory_families':{n:f'test_targeted_contract[{n}]' for n in families},'final_counts':target['counts'],'command':next(r for r in records if r['job']=='od07final'),'chronology':history,'frozen_sources':{n:load(B/n) for n in ['negative-first-freeze.json','review-freeze.json','scope-freeze.json','factor-review-freeze.json']},'focused_coverage':{'module_summaries':selected,'weighted':totals,'scope':'New84targeted cases only;alladjustmentsmodules measured;not financial coverage'},'old_suite':required['od07'][1]['worker_result']['counts'],'combined_exact_source_coverage':{'weighted':union_totals,'modules':union_modules,'method':'Set union of executed lines/branches from final84 and unchanged100 suites; same exact source pins, not a separate command or financial metric'}})
js('12_full_engineering_matrix.json',{'collection':len(inv),'classes':dict(classes),'commands':records,'A':A['counts'],'diagnostic':diag['counts'],'diagnostic_exit':1,'B_failures':[r for r in diag['reports'] if r['outcome']=='failed'],'C_not_run':[n for n,v in inv.items() if v=='C'],'skips':[r for r in A['reports'] if r['outcome']=='skipped'],'by_test_file':dict(byfile),'Windows314':'NOT_RUN_OS_CAPABILITY_BLOCKED','Windows311':'NOT_RUN_OS_CAPABILITY_BLOCKED','failed_attempts_preserved':True})
md('13_persistence_and_rollback.md','''# Additive SQLite od07.store/v2
Preserves four v1 tables/rows andadds od07_calculation_context plus od07_result_context FK. Exactrecognized old/new schemas only. Migration retainsv1 marker andappendsv2;unknown/partialschema refuses. Append-only UPDATE/DELETE triggers,BEGIN IMMEDIATE transactions,uniqueimmutablecontext/result IDs,idempotent matching retry andFKs retained. Context cannot bind to a different result/rawidentity. Populatedrollback refuses;no acceptedhistory deleted.

Actual tests:legacy fourtable migration,file-backed boundcontext/result commit/reopen,immutable changed-context refusal,invalidschema refusal,omittedaction and13tampered-resultcases. Existing100tests rerun nativeSQL constraints,rollback,competing successor connections andv1reopen. No productiondatabase touched;no new hardware-powerloss/processkill claim. Rollbackcode disablesopt-inv2consumers while retainingacceptedhistory. Production migration/restore rehearsal requires separate authorization.''')
js('14_preservation_manifest.json',{'reviewed_HEAD':HEAD,'snapshot_sha256':snapshot_digest,'baseline_files':len(baseline),'unchanged_baseline_files':len(baseline)-len(modified),'changes':changes,'combined_delivery':combined,'patch_sha256':sha(B/'implementation.patch'),'phase_patch_sha256':sha(B/'phase-only.patch'),'prior_sealed_files_unchanged':len(prior['files']),'prior_seal_sha256':sha(E/'evidence-sha256.json'),'original_checkout_integrated':False,'original_worktree_content_scanned':False,'new_original_market_payload_reads_hashes_copies':0,'source_policy_changes':0,'production_DB_writes':0,'commit_push_merge_release_sign_trade':False,'native_proof':'logs/'+proofpath.name,'native_proof_sha256':sha(proofpath),'native_boundary':proof['boundary'],'native_probe_count':len(proof['probes']),'local_ipc':proof['local_ipc_control']})
js('15_external_dependencies.json',{'authentic_observations_inspected':0,'financial_comparisons':0,'real_financial_validation':'BLOCKED_REAL_DATA','missing':['Authorized authenticated original reference/action corpus and independently reviewed real expected values','Reviewed scope-complete action coverage and exact economic event identity','Trusted identity/listing continuity and authoritative versioned calendar coverage','Parameter/reference availability attestations and applicable source-purpose rights','Reviewed successor economic allocation andexecutionlot/settlement/restriction references'],'historical_archive_metadata_ONLY':{'candidate_count':3626,'seed':3596,'cache':30,'present_size_matches':3626,'hardlinks':2760,'single_link':866,'fresh_scan':'NOT_RUN'},'incidents':{'OD05V':'PENDING_HUMAN_OWNER_REVIEW;39files6135515recordedbytes','OD05XR1':'PENDING_HUMAN_OWNER_REVIEW;payloadextentUNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'},'Windows':'Approved isolatedWindowsenvironment absent;no certification orwaiver','production_integration':'Not authorized','source_approvals_changed':False})
criteria=['Exact24fileadoption','Referenceidentity/venue/basis/evidence','Historicalstableidentitycontinuity','Explicitcomplete/incompletehistory','Independentfullcontextadmission','Math/executionseparation','Requiredparameteravailability','Correctbasis/windows','Oldmathematicsretained','Immutablehistoricalreproducibility','Persistence/migration/rollback','OD05/06/07regression','No new unresolvedP0/P1testeddefect','Externalacceptancehonesty','OD08handoff']
js('16_acceptance_matrix.json',[{'id':f'F{i+1:02}','criterion':v,'result':'PASS_CODE_ONLY','authentic_financial_acceptance':'BLOCKED_REAL_DATA','evidence':['11_targeted_test_results.json','12_full_engineering_matrix.json','14_preservation_manifest.json','17_final_gatekeeper.json']} for i,v in enumerate(criteria)])
js('17_final_gatekeeper.json',verdict)
md('18_od08_dependency_handoff.md','''# OD08 code-only readiness READY; execution not authorized
Consume adopted OD06 identity/calendar/PITinterfaces andopt-inv2 RawObservation,ReferenceObservation,HistorySnapshot,ParameterSet,BasisPolicy,PinnedCalculation,BoundResult andSQLite pin_context/append_bound_result. Preserveexactraw/as-reportedsymbols,stableIDs,valid/knownbounds,completehistory/evidence/identity/calendar digests,policy/basis/algorithm/roundingversions andallblockedstates.

v1FORWARD meansinversecomparison;newconsumer mustnameconventionalforwardexplicitly. Never use scalar/unboundv1math asauthenticfinancialacceptance. Never infer execution fromrawbasis orCALCULATED. Fullsource-backed history,identity/reference authority andfinancial eligibility remainquarantined. OD08 must account for unavailable/provisional information and selected membership coverage,not silentlypromote parsing/mathsuccess.

One next development action:owner review andexplicit boundedOD08code-onlyauthorization. No newgenericOD07phase proposed. Productionintegration stillrequires separate incidentdisposition,platform andsource gates. No OD08 code executed.''')
md('19_final_report.md',f'''# OD07 targeted engineering PASS; financial and production gates BLOCKED

Reviewed commit: {HEAD}. Branch: feature/od01-source-rights. Applied workspace: {S}. Source snapshot SHA256: {snapshot_digest}.

The exact 24-file upstream delivery was adopted and verified. This phase changes nine files: five modified modules and four new code/test files. The combined delivery contains 28 files. These are applied and tested at normal application paths in the safe snapshot; they are not integrated into the original mixed checkout.

All six targeted areas are implemented: bound reference identity; stable listing continuity through renames; explicit complete action history and independently pinned result admission; raw execution basis separated from eligibility; explicit parameter knowledge; and correct forward/backward temporal windows. The existing Decimal factor engine and 100-test suite are preserved. The old inverse-comparison operation remains compatible and explicitly named. Two additive SQLite context tables preserve the original four-table history.

The independent Fraction admission oracle checks individual displayed factors, factor status, final arithmetic, ordered action revisions and exact upstream/calendar lineage. Negative-first commands, frozen test sources, actual failures and corrections are retained. The new D04 fixture initially mislabeled a bonus as a split; that test metadata correction did not change its numerical expectations or any historical test.

| Fresh Linux verification | Result |
|---|---|
| New targeted correctness suite | 84 passed |
| Existing OD07 suite | 100 passed |
| OD06 identity contracts | 66 passed |
| OD06 foundation/persistence | 87 passed |
| OD05 parser/reference regressions | 170 passed, 1 skipped |
| Collection | 1,201: A 1,193; B 4; C 4 |
| Engineering A | 1,181 passed, 12 skipped; exit 0 |
| Unchanged non-realdata diagnostic | 1,181 passed, 4 failed, 12 skipped, 4 deselected; exit 1 |
| Ruff, mypy, pip check, compilation | All exit 0 |

The four diagnostic failures remain the original source-dependent B cases. Real-data C cases were not executed. Twelve skips retain Windows-specific reasons; Linux results do not certify Windows containment.

New-suite statement coverage across all adjustment modules: {totals['statement_percent']:.2f}%; branch coverage: {totals['branch_percent']:.2f}%. The derived exact-source union with the unchanged 100-test suite covers {union_totals['statement_percent']:.2f}% of statements and {union_totals['branch_percent']:.2f}% of branches. This union is calculated from executed line/branch sets, not a separate command or a financial validation metric. Full module counts and commands are in the test reports.

Canonical Linux bwrap namespaces, exact read-only staging, dropped capabilities, no_new_privs and seccomp mode 2 were verified with 12 native denial probes and a local IPC positive control. Read ENOENT demonstrates an unmapped harmless canary, not an ACL denial. Write EROFS and process/network EPERM are recorded. Original market, incident and credential roots were not mounted. Reporting uses the unchanged allowlisted bundle renderer without Git discovery.

All 374 prior sealed evidence entries remain unchanged. No new unresolved P0/P1 defect was found in the tested opt-in scope. Review was performed by the coding agent with separate mathematical, SQL and native-kernel oracles; no independent human acceptance is claimed.

Authentic financial observations inspected or compared: zero. Mathematical and structural controls contribute zero to real-data acceptance. Source policies are unchanged. Historical archive presence counts remain archived metadata only, with no fresh scan or payload hash. Both historical incidents remain pending human review; the R1 access extent remains unknown. Windows isolation and production integration remain blocked.

Gatekeeper: targeted code-only engineering PASS; authentic financial validation BLOCKED_REAL_DATA; production integration BLOCKED. OD08 code-only contract READY, but execution is not authorized. Next development action: owner review and a separate explicit bounded OD08 invocation. No commit, push, merge, release, signing, trading, restricted-data access or OD08 execution occurred.
''')
assert len(art)==20
root=B/'report-inputs';root.mkdir()
(root/'summary.json').write_text(pretty({'artifacts':art}))
(root/'manifest.json').write_text(pretty({'schema_version':'od05.final-report/v1','files':{'summary.json':{'bytes':(root/'summary.json').stat().st_size,'sha256':sha(root/'summary.json')}}}))
assert (root/'summary.json').stat().st_size<4_000_000
(B/'report-input-index.json').write_text(pretty(['manifest.json','summary.json']))
(B/'report-preparation.json').write_text(pretty({'utc':datetime.now(UTC).isoformat(),'files':sorted(art),'changes':changes,'delivery':combined,'snapshot_sha256':snapshot_digest,'coverage':totals,'source_file_count':len(snapshot)}))
print(pretty({'reports':len(art),'phase_files':len(changes),'combined_files':len(combined),'coverage':totals,'snapshot_sha256':snapshot_digest}))
