"""Explicit data-free evidence only; no original discovery or unsafe finalizer."""
import hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;S=B/'staged/repo';HEAD='38c6658a3587b93880fa6ab20e2caf841e7a47ac'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def j(v):return json.dumps(v,indent=2)+'\n'
M=load(B/'preservation-final.json');pins=load(B/'final-source-pins-final.json');inv=load(B/'sealed-classification.json');identity=load(B/'final-ref-identity.json')
assert len(M['changes'])==20 and len(M['combined_delivery'])==51 and len(pins)==3852
assert inv['classes']=={'A':1405,'B':4,'C':4} and inv['collection']==1413
assert all(sha(S/n)==h for n,h in pins.items())
assert identity['head']==HEAD and identity['branch']=='feature/od01-source-rights' and not identity['cached_index_paths']
records={p.name.removesuffix('-command.json'):(p,load(p)) for p in (B/'logs').glob('*-command.json')}
def latest(job):return max(((p,v) for p,v in records.values() if (v.get('worker_result') or {}).get('job')==job),key=lambda r:r[1]['start_utc'])
jobs=('collection','A','diagnostic','od08','stagea','od09','od07','od07final','od06','foundation','parser','mypy','pip','compile','od09perf');chosen={n:latest(n) for n in jobs}
expected={'stagea':{'passed':37},'od09':{'passed':83},'od08':{'passed':92},'od07':{'passed':100},'od07final':{'passed':84},'od06':{'passed':66},'foundation':{'passed':87},'parser':{'passed':170,'skipped':1},'A':{'passed':1393,'skipped':12},'diagnostic':{'passed':1393,'failed':4,'skipped':12}}
matrix={}
for job,(p,r) in chosen.items():
 assert r['exit_code']==(1 if job=='diagnostic' else 0),(job,r['exit_code'])
 w=r['worker_result']
 if job in expected:assert w['counts']==expected[job],(job,w['counts'])
 manifest=load(p.with_name(p.name.replace('-command.json','-manifest.json')));rows={v['path']:v for v in manifest['files']}
 assert all(rows[v['path']]['sha256']==v['after_sha256'] for v in M['changes']),job
 tag=p.name.removesuffix('-command.json');probes=load(B/tag/'output/native-probes.json')
 assert len(probes['probes'])==12 and all(v['denied'] and not v['python_hook'] for v in probes['probes']) and probes['local_ipc_control']['bytes']>0
 matrix[job]={'record':'support/logs/'+p.name,'sha256':sha(p),'launcher_argv':r['argv'],'controller_cwd':r.get('cwd','NOT_RECORDED'),'worker_cwd':r.get('worker_cwd','/work/repo (pinned worker source)'),**{k:r[k] for k in ('start_utc','end_utc','seconds','exit_code','source_manifest_sha256')},'counts':w.get('counts',{}),'python':w.get('python'),'interpreter':w.get('interpreter'),'native_probes':'support/jobs/'+tag+'/native-probes.json','native_denials':12,'local_ipc_positive':True}
A=chosen['A'][1]['worker_result'];diag=chosen['diagnostic'][1]['worker_result']
bnodes=sorted(n for n,c in inv['inventory'].items() if c=='B');cnodes=sorted(n for n,c in inv['inventory'].items() if c=='C')
assert sorted(v['nodeid'] for v in diag['reports'] if v['outcome']=='failed')==bnodes and sorted(diag['deselected'])==cnodes
assert {v['nodeid'] for v in A['reports']}=={n for n,c in inv['inventory'].items() if c=='A'}
assert not any(v['nodeid'] in cnodes for v in A['reports']+diag['reports'])
rp=max((B/'logs').glob('static-ruff-*.json'),key=lambda p:load(p)['start_utc']);rr=load(rp);assert rr['exit_code']==0
matrix['ruff']={'record':'support/logs/'+rp.name,'sha256':sha(rp),**rr}
coverage={}
for job in ('A','stagea','od09'):
 tag=chosen[job][0].name.removesuffix('-command.json');p=B/tag/'output/job/coverage.json';c=load(p)
 vals=[v['summary'] for n,v in c['files'].items() if job!='od09' or '/reconciliation/' in n]
 sums={k:sum(v.get(k,0) for v in vals) for k in ('num_statements','covered_lines','missing_lines','num_branches','covered_branches','missing_branches')}
 sums['statement_percent']=100*sums['covered_lines']/sums['num_statements'];sums['branch_percent']=100*sums['covered_branches']/sums['num_branches']
 coverage[job]={'path':'support/jobs/'+tag+'/coverage.json','sha256':sha(p),'scope':'reconciliation package' if job=='od09' else 'all job measured files',**sums}
specs=[('stagea-4cfd31bac2','REPRODUCED_DEFECT_AND_NEW_FEATURE_ABSENT','Initial exact-binding API absent; omission, precision, availability, arithmetic defects.'),('stagea-9f4c60c5da','REPRODUCED_DEFECT','Precise transition positive control.'),('stagea-d73d2b196c','REPRODUCED_DEFECT','Future announcement completion and out-of-window selection.'),('stagea-f2f6cd88f5','REPRODUCED_DEFECT','Missing/wrong snapshot instant and date-only intraday boundary.'),('stagea-d90a17b5ee','REPRODUCED_DEFECT','Median display rounding crossed exact threshold.'),('od09-3d2f6cd1d1','NEW_FEATURE_ABSENT','Reconciliation package absent.'),('od09-ea70413df6','REPRODUCED_DEFECT','Review scope and anomaly not independently bound.'),('od09-3a59d4ff8c','REPRODUCED_DEFECT_AND_NEW_FEATURE_ABSENT','Unchanged old outputs and replacement context absent.'),('od09-10c90e70e1','REPRODUCED_DEFECT','Repeated context digest work.'),('od09-22b930af04','REPRODUCED_DEFECT','Decimal authority codec and malformed budgets.'),('od09-3443e3d93a','FAIL','Implementation date import omission.'),('od09-e907679fb2','FAIL','UNC helper failure emptied only new calibration module; restored verified worker snapshot.'),('od09-431aec7fd1','NEW_FEATURE_ABSENT','Downstream proof replay absent.'),('od09-640ba11938','NEW_FEATURE_ABSENT','Optional external completion attestation path absent.'),('od09-02ef01cd5b','REPRODUCED_DEFECT','Five durable progress states required unavailable output prematurely.')]
negative=[]
for tag,kind,reason in specs:
 p,r=records[tag];name='tests/unit/test_od08_dependencies.py' if tag.startswith('stagea') else 'tests/unit/test_od09_reconciliation.py';manifest=load(p.with_name(tag+'-manifest.json'));row=next(v for v in manifest['files'] if v['path']==name);frozen=B/tag/'output/repo'/name;assert sha(frozen)==row['sha256']
 negative.append({'tag':tag,'classification':kind,'reason':reason,'start_utc':r['start_utc'],'end_utc':r['end_utc'],'exit_code':r['exit_code'],'counts':r['worker_result']['counts'],'test_path':name,'test_sha256_before_fix':row['sha256'],'frozen_source':'support/negative-first/'+tag+'/'+Path(name).name,'invocation':'support/logs/'+p.name,'failures':[v for v in r['worker_result'].get('reports',[]) if v['outcome']=='failed']})
initial=load(B/'stagea-gate.json');firstb=records['od09-3d2f6cd1d1'][1]['start_utc'];assert initial['recorded_utc']<firstb
sa=[v for v in M['changes'] if v['stage']=='A'];sb=[v for v in M['changes'] if v['stage']=='B'];assert len(sa)==7 and len(sb)==13
stagegate={'OD08_TARGETED_DEPENDENCY_GATE':'PASS','scope':'Final Linux code-only strict v2 consumer contract','criteria':{f'A{i:02}':'PASS' for i in range(1,7)},'tests':{k:matrix[k] for k in ('stagea','od08','od07','od07final','A','mypy','pip','compile','ruff')},'source_changes':sa,'source_manifest_digest':M['source_manifest_digest'],'initial_gate_preserved':'support/stagea-gate.json','initial_gate_utc':initial['recorded_utc'],'first_stageb_baseline_utc':firstb,'late_refinements':M['late_stagea_refinements'],'chronology':'Stage B began after the recorded 32-test Stage A PASS. Later adversarial controls exposed timestamp/median gaps; final acceptance withheld until all 37 and the complete fresh engineering suite passed. Initial evidence remains unchanged.'}
eng=['UPSTREAM_ADOPTION','COMPARABILITY','DISCREPANCY_MATHEMATICS','TOLERANCE_ENGINEERING','ANOMALY_ENGINEERING','HARD_BLOCK_ENFORCEMENT','SOURCE_LINEAGE','REVIEW_ENGINEERING','CORRECTION_ENGINEERING','REPROCESS_CONTRACT','PERSISTENCE','COMPATIBILITY','ENGINEERING_OVERALL']
gates={'OD08_TARGETED_DEPENDENCY_GATE':'PASS',**{'OD09_'+n:'PASS' for n in eng},'OD09_AUTHENTIC_RECONCILIATION':'BLOCKED_REAL_DATA','OD09_AUTHENTIC_CALIBRATION':'BLOCKED_REAL_DATA','OD09_INDEPENDENT_FINANCIAL_REVIEW':'BLOCKED_INPUT','OD09_PRODUCTION_INTEGRATION':'BLOCKED','OD10_CODE_ONLY_READINESS':'READY','OD10_EXECUTION_AUTHORIZATION':'NOT_GRANTED'}
gate={'gates':gates,'engineering_scope':'Tested opt-in Linux code-only development. No financial/production acceptance.','source_commit':HEAD,'source_manifest_digest':M['source_manifest_digest'],'same_agent_engineering_review':True,'independent_human_acceptance':False,'new_unresolved_P0_P1_in_tested_scope':0,'financial_rows_inspected':0,'financial_rows_independently_verified':0,'windows_native':'OS_CAPABILITY_BLOCKED (historical, not rerun)','incidents':{'OD05V':'PENDING_HUMAN_OWNER_REVIEW','OD05XR1':'PENDING_HUMAN_OWNER_REVIEW','OD05XR1_PAYLOAD_ACCESS':'UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'},'limitations':['Actual trusted human approval/completion positive path not exercised without supplied authority.','Measured coverage is not exhaustive path certification.','Two-connection/thread competition tested, not cross-process crash-kill durability.','No same-process privileged tamper-resistance claimed.'],'overall':'CONDITIONAL_CODE_ONLY_DELIVERY_EXTERNAL_ACCEPTANCE_BLOCKED'}
external={'dependencies':[{'source':a,'why_needed':b,'permission':'Existing source-rights registry and exact permitted consumer purpose; no changes made','reviewer_requirement':c,'expected_artifact':d,'affected_gate':e,'current_blocker':'NOT_SUPPLIED_OR_UNVERIFIED'} for a,b,c,d,e in [('Authenticated paired source observations','Equivalent venue/session/field, independent expected discrepancy','Independent source/domain reviewer','Sealed paired records, definitions, literal expected results','OD09_AUTHENTIC_RECONCILIATION'),('Calibration/validation samples','Market thresholds and real FP/FN','Independent calibration reviewer','Versioned authorized independent train/validation samples','OD09_AUTHENTIC_CALIBRATION'),('Correction/completion attestations','Accountable review and exact reprocess acceptance','Authorized human in trusted authority','Exact revised inputs and independent completion record','OD09_INDEPENDENT_FINANCIAL_REVIEW'),('Upstream identity/calendar/action/universe references','Economic identity/session/history/coverage binding','Independent domain reviewers','Authenticated authorized pinned references','OD09_AUTHENTIC_RECONCILIATION'),('Incident dispositions and isolated integration environment','Permit original/production integration','Accountable incident owner and operator','OD05V/OD05XR1 decisions and approved platform','OD09_PRODUCTION_INTEGRATION')]],'financial_rows_inspected':0,'financial_rows_verified':0,'financial_mismatches':None,'missing_sessions':None,'financial_coverage':'NOT_ASSESSED','archived_metadata_only':{'candidates':3626,'seed':3596,'cache':30,'physically_present':3626,'size_matched':3626,'hardlinked':2760,'single_link':866,'fresh_scan':False,'authenticity_integrity_financial_acceptance':'NOT_ESTABLISHED'}}
artifacts={}
def md(name,value):artifacts[name]=value.strip()+'\n'
def js(name,value):artifacts[name]=j(value)
md('00_scope_and_identity.md',f'''# OD08 closure and OD09 implementation

Reviewed branch `{identity['branch']}`, HEAD `{HEAD}` matched at {identity['utc']}. Cached index unchanged. Unstaged/untracked original state deliberately not scanned; no unrestricted status/diff, content refresh, commit or push.

Applied/tested normal application paths in `{S}`. Source digest `{M['source_manifest_digest']}` covers 3,852 exact code/metadata inputs. Twenty phase changes (7 Stage A,13 Stage B), 51 combined delivery files. Development integration only, not original application integration.

No original market/incident/credential/signing/operational database mounts. No OD10 or external alert dispatch. [Source](source/), [preservation](20_preservation_manifest.json), [gate](22_final_gatekeeper.json).''')
js('01_upstream_adoption_manifest.json',{'adoption':load(B/'upstream-adoption.json'),'37_before_or_absent_checks':M['before_checks'],'verified_baseline_pins':3838,'combined_delivery':M['combined_delivery'],'stage_a_changes':sa,'stage_b_changes':sb,'original_application_integrated':False,'patch_replay':load(B/'patch-replay-v2.json')})
md('02_OD08_dependency_reproductions.md','''# Targeted reproductions

Initial 18 safe controls:16 failed,2 passed. Binding API absence was NEW_FEATURE_ABSENT; observation omission, unsupported temporal precision, indiscriminate future-effectiveness refusal and nonterminating arithmetic were reproduced defects.

Strict v2 binds the exact consumed scalar and identities to OD07 raw/pin/result digests. Persisted observations are independently selected by pinned source/listing/type/session/policy scope; explicit partial exclusions remain visible. Announcements differ from completed financial observations. Timestamp coverage requires exact supported reference instant; date-only boundaries cannot invent intraday precision. Liquidity thresholds use exact rational comparisons before display rounding.

Later controls reproduced missing/wrong snapshot instants and an extreme median rounding error. Corrected in this execution; initial 32-case gate is preserved, final gate supersedes it. Original 92 OD08 tests and limited v1 helper remain unchanged. [Actual failures and frozen tests](support/negative-first.json).''')
js('03_OD08_targeted_results.json',{'targeted':matrix['stagea'],'original_od08':matrix['od08'],'coverage':coverage['stagea'],'source_changes':sa,'input_class':'NON_MARKET_STRUCTURAL_CONTROL / PURE_MATHEMATICAL_TEST','negative_first':[v for v in negative if v['tag'].startswith('stagea')]})
js('04_OD08_dependency_gate.json',stagegate)
md('05_existing_reconciliation_audit.md','''# Existing code audit

[Exact paths, hashes, functions](support/legacy-source-audit-final.json) were read as code only. No operational validator, calibration, raw backfill or alert was invoked.

| Component | Decision | Limitation and opt-in treatment |
|---|---|---|
| CrossSourceValidator | OPT_IN_REPLACEMENT | ISIN/date matching, dictionary overwrite and missing skips lack exact venue/field identity; bounded candidate groups expose duplicates/missing rows. |
| Confidence | WRAP | Legacy numerical score retained; strict eligibility preserves independent hard blocks. |
| Tolerance loader | REUSE / LEGACY_RISK_RETAINED | Mutable/hardcoded thresholds are not authentic calibration; immutable policy pins scope and knowledge. |
| ManualReviewService / review policy | OPT_IN_REPLACEMENT | Legacy mutable queue/alerts retained for callers; new append-only ledger performs no dispatch. |
| CorporateActionMatcher / discontinuity | WRAP | Similarity/price jumps do not establish economic event truth; strict explanation replays exact OD07 proof. |
| Domain/ORM | REUSE | Original tables/rows unchanged; disposable additive SQLAlchemy schema uses upstream transaction/codec conventions. |
| Source calibration scripts | BLOCKED_EXTERNAL | Code inspected, actual data/calibration not executed. |

All original APIs, test identities and financial expectations retained. Full A includes existing cross-source, confidence, manual-review, tolerance, corporate-action, identity/calendar, parser and universe regressions.''')
md('06_observation_contract.md','''# Observation and lineage

[contracts.py](source/src/omegadata/reconciliation/contracts.py) wraps OD08 AvailabilityObservation with stable security/listing/venue, reported symbol/series, publisher, parser/schema versions, row ordinal, field/unit, lineage root and optional universe reference. Unknowns remain unknown. Financial/publication/execution eligibility cannot be supplied by consumers.

The base carries artifact/record identities and independent effective, observed/completed, published, known and ingestion times, evidence and raw/adjusted references. [observation_binding.py](source/src/omegadata/universe/observation_binding.py) checks exact consumed field/value, OD07 raw/context/result IDs/digests, identity/session/venue/units/profile/basis/cutoff. Unrelated valid adjusted volume cannot certify consumed volume. Unsupported unit conversion is refused.

Results retain exact left/right IDs/digests, field/comparability, metric, policy/upstream/authority digests, valid/known cutoffs and algorithm version. Persisted replay checks actual pinned records. Original observations and PriceRecord remain unchanged.''')
md('07_comparability_contract.md','''# Economic comparability

[engine.py](source/src/omegadata/reconciliation/engine.py) uses indexed bounded candidate groups; missing and conflicting counterparts remain explicit. Check security/listing/venue, session/interval/type, basis, currency/unit and knowledge before arithmetic.

Equivalent same-venue observations may compare. Different-venue same-security price comparison needs explicit policy/identity; volume is not universally interchangeable. Venue-specific differences are not parser corruption. Adjusted observations require replayed OD07 v2 contexts and compatible profiles/bases/cutoffs.

Same upstream lineage is flagged DEPENDENT_SOURCE_LINEAGE. Agreement cannot establish independence, publisher authenticity or permission. Imputed, incompatible, unresolved or unavailable inputs yield UNCOMPARABLE. Numerical PASS does not grant financial acceptance.''')
md('08_independent_discrepancy_vectors.md','''# Independent literal mathematical vectors

PURE_MATHEMATICAL_TEST only, not market observations. Expected fractions are literal independent derivations.

| Inputs/metric | Exact result |
|---|---|
| 3,2 absolute | 1 |
| 3,2 reference-relative (right denominator) | 1/2 |
| 3,2 symmetric-relative | 2/5 |
| 2,3 signed | -1 |
| 3,2 tick size 1/4 | 4 |
| Nonzero left/zero reference | UNDEFINED_DENOMINATOR / UNCOMPARABLE |
| Both zero symmetric denominator | UNDEFINED_DENOMINATOR / UNCOMPARABLE |

Ratio difference is absolute `(left/right)-1`. Exact Fraction is authoritative; Decimal80 HALF_EVEN is display context. PASS <= warning, WARN < failure, FAIL >= failure. Ambient-context independence and finite/resource limits tested. Missing values remain distinct from zero.

Stage A 1/3,2/3 coverage and average/median thresholds use exact ratios before display; extreme-scale median control reproduced and corrected a rounding-based eligibility error.''')
md('09_tolerance_calibration_contract.md','''# Versioned tolerance/calibration

Immutable TolerancePolicy pins source pair, venue/field/type/scope, units/metric, boundary convention, valid/knowledge intervals and calibration/review identity/cutoff. Selection requires exactly one eligible version; future calibration refused.

[calibrate](source/src/omegadata/reconciliation/tolerances.py) accepts bounded supplied samples; excludes missing/future availability, dependent lineage, wrong buckets and unsupported periods; rejects duplicates/invalid values. Pinned training nearest-rank p90/p99, no outlier deletion, separate validation labels and sample adequacy produce transparent FP/FN counts on literal controls.

Results remain PROVISIONAL_ALGORITHM_RESULT and BLOCKED_CALIBRATION authenticity. No authentic market threshold, sample independence or actual FP/FN performance is claimed. Legacy thresholds remain uncalibrated compatibility infrastructure.''')
md('10_anomaly_detection_contract.md','''# Explainable anomalies

[anomalies.py](source/src/omegadata/reconciliation/anomalies.py) distinguishes structural invalidity, missing/duplicate rows, identity/time/lineage conflicts, cross-source discrepancies, expected venue differences, unexplained jumps and corporate-action explanations. OHLC ordering, negative volume and missing values are explicit findings; a large move alone is not proof of error.

Corporate-action explanation requires exact replayed OD07 UpstreamProof and matching raw observations, identity, basis, session and cutoff. Scalar factors/future context cannot certify it. Persistent directional discrepancies are diagnostic. Repository recomputes anomalies against pinned context, refusing arbitrary caller findings.

No repair, deletion, imputation or source mutation. Authentic anomaly labels remain blocked externally.''')
md('11_confidence_and_hard_blocks.md','''# Hard blocks independent of confidence

Numerical confidence, reconciliation, source, identity, availability, coverage, review and reprocess statuses are independent. Tests prove confidence=1 cannot override denied rights, unknown identity, wrong basis, future information, unresolved critical anomaly, incomplete history, unverified correction or unfinished reprocess.

UNCOMPARABLE never becomes PASS. Non-market controls remain financially/publication/execution ineligible even when exact mathematics passes. Legacy scorer unchanged; no production routing or OD11 release decision introduced.''')
md('12_review_and_correction_contract.md','''# Immutable review/correction

[reviews.py](source/src/omegadata/reconciliation/reviews.py) implements allowed OPEN/UNDER_REVIEW/AWAITING_EVIDENCE, CORRECTION_PROPOSED, APPROVED/REJECTED, REPROCESS_REQUIRED/PENDING/VERIFIED and CLOSED transitions. Revisions pin prior digest, affected scope, evidence, reason, policy, role and time.

Correction requires new evidence and changed immutable record. Persisted discrepancy context independently constrains listing/security scope. Unique parent/root constraints prevent competing children; two connections/threads racing on file-backed SQLite yield one commit and one refusal. History remains inspectable.

ReviewerAttestation uses existing EvidenceAuthority and exact reviewer/role/source/purpose/cutoff/claim linkage. No rights or roots changed. Non-market state-machine progression is explicitly nonhuman, not financial approval. Actual trusted positive human acceptance not exercised: no accountable attestation supplied. No queue/alert dispatch.''')
md('13_reprocess_verification_contract.md','''# Exact reprocess contracts

Persisted input-index lookup derives impacted contexts from exact corrected observation digests. Requests pin correction, affected listing/session scope, source revisions, adjustment/universe references and dependency versions; unrelated records cannot be inserted/omitted silently.

ReplacementContext binds exact old/new contexts and revised inputs. Admission replays replacement results and rejects unchanged old output identities. UpstreamProof replays OD07 PinnedCalculation or OD08 UniverseContext under its cutoff. Missing downstream proof blocks completion.

REQUESTED/QUEUED/RUNNING/FAILED/BLOCKED_DEPENDENCY persist before outputs exist and never clear blocks. Successful outputs remain COMPLETED_UNVERIFIED absent independent authority. Transition to REPROCESS_VERIFIED checks persisted request/completion/review lineage and trusted attestation. No actual market reprocessing or publication. No hostile same-process tamper-resistance claimed.''')
md('14_persistence_and_rollback.md','''# Disposable persistence/migration

[repository.py](source/src/omegadata/reconciliation/repository.py) reuses SQLAlchemy/SQLite transaction and typed-codec conventions. Eleven additive tables cover schema, policy, context/result/anomaly, review/correction/request/completion, input index and replacement context. Foreign keys, unique roots/successors and immutable triggers retain history. BEGIN IMMEDIATE serializes writes; digest covering index supports impact lookup.

In-memory and file-backed disposable tests cover insert/retry/changed-ID refusal, restart deterministic replay, rollback, foreign keys, two-connection competing revisions, altered context/result/anomaly, additive migration/schema refusal and nonempty rollback refusal. Repository independently recalculates pinned inputs rather than trusting result lineage.

Operational schema/rows untouched. Empty disposable rollback tested; nonempty accepted history must be retained/versioned, not deleted. Restart/rollback tests do not establish crash-kill or cross-process durability certification.''')
rows='\n'.join(f"| {v['tag']} | {v['classification']} | {v['counts']} |" for v in negative)
md('15_negative_first_tests.md',f'''# Actual negative-first chronology

Frozen source bytes, SHA-before-correction, UTC invocation, failures and exit codes: [negative-first.json](support/negative-first.json).

| Run | Classification | Actual counts |
|---|---|---|
{rows}

Final Stage A37 and OD0983 passed. Initial32-case Stage A gate preceded Stage B. Later precision/median corrections completed before final acceptance; early records unchanged. No working code broken to invent red history. Implementation date-import/UNC-helper errors and first diff syntax error preserved separately. Kernel denials are actual native evidence, not simulated exceptions.''')
js('16_targeted_test_results.json',{'jobs':{k:matrix[k] for k in ('stagea','od09','od08','od07','od07final','od06','foundation','parser')},'coverage':coverage,'negative_first':'support/negative-first.json','mandatory_groups':{'C':8,'M':4,'T':3,'N':5,'G':4,'R':6,'P':4,'S':3},'additional':'Literal metrics; admission tampering; exact scope/replacements/proofs; malformed budgets; review races; durable progress states.'})
js('17_full_engineering_matrix.json',{'source_commit':HEAD,'source_manifest_digest':M['source_manifest_digest'],'jobs':matrix,'collection':1413,'classification':inv['classes'],'A_counts':A['counts'],'full_diagnostic_counts':diag['counts'],'full_diagnostic_exit_code':1,'B_failed_nodes':bnodes,'C_not_executed':cnodes,'C_deselected':4,'platform_skips':[v for v in A['reports'] if v['outcome']=='skipped'],'coverage':coverage,'skip_handling':'Exact nodes/reasons retained; Linux counterpart engineering tests executed. Seven absent Windows native cases are blocked, not passing.','windows_native':'NOT_RUN / historical OS_CAPABILITY_BLOCKED','historical_upstream_not_current':{'collection':1293,'A':1285,'B':4,'C':4,'A_passed':1273,'A_skipped':12}})
before=records['od09perf-7fc1be8547'][1]['worker_result'];after=records['od09perf-16d73b8647'][1]['worker_result'];perf=chosen['od09perf'][1]['worker_result']
assert [v['digest'] for v in before['measurements']]==[v['digest'] for v in after['measurements']]==[v['digest'] for v in perf['measurements']]
js('18_performance_results.json',{'scope':'Anonymous bookkeeping only, no market-scale claim','baseline':before,'after_optimization':after,'final':perf,'digests_identical':True,'correction':'Compute immutable context/policy/authority digests once, not per pair. Indexed bounded matching.','unmeasured':'Authenticated market throughput, real calibration quality and sustained production concurrency','original_scan_budget_seconds':30,'original_archive_scans':0,'WSL_original_status':'Historical LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED retained.'})
js('19_external_dependencies.json',external)
js('20_preservation_manifest.json',{**M,'phase_source_changes':{'A':sa,'B':sb},'combined_patch':'implementation.patch','combined_patch_sha256':sha(B/'implementation-v2.patch'),'stage_a_patch_sha256':sha(B/'stage-a-v2.patch'),'stage_b_patch_sha256':sha(B/'stage-b-v2.patch'),'patch_replay':load(B/'patch-replay-v2.json'),'first_patch_failure':'support/patch-first-failure.json','original_ref_identity':identity,'source_policies_authority_roots_changed':False,'production_routing_release_signing_changed':False,'historical_incidents_modified':False})
criteria=[('Stage A gate','04_OD08_dependency_gate.json'),('Exact upstream adoption','01_upstream_adoption_manifest.json'),('Legacy audit','05_existing_reconciliation_audit.md'),('Typed observations','06_observation_contract.md'),('Economic comparability','07_comparability_contract.md'),('Exact metrics','08_independent_discrepancy_vectors.md'),('Four outcomes','16_targeted_test_results.json'),('Tolerance/calibration contracts','09_tolerance_calibration_contract.md'),('Venue distinctions','07_comparability_contract.md'),('Explainable anomalies','10_anomaly_detection_contract.md'),('Bound corporate-action explanation','10_anomaly_detection_contract.md'),('Independent hard blocks','11_confidence_and_hard_blocks.md'),('Exact lineage','06_observation_contract.md'),('Immutable review','12_review_and_correction_contract.md'),('New correction evidence','12_review_and_correction_contract.md'),('Exact dependency scope','13_reprocess_verification_contract.md'),('Verified completion contract','13_reprocess_verification_contract.md'),('Persistence/restart/rollback','14_persistence_and_rollback.md'),('Independent math/structural tests','15_negative_first_tests.md'),('Legacy regression','17_full_engineering_matrix.json'),('No unresolved P0/P1 in tested scope','22_final_gatekeeper.json'),('External gates retained','19_external_dependencies.json'),('OD10 handoff','23_od10_dependency_handoff.md')]
js('21_acceptance_matrix.json',{'frozen_criteria':'Current user F01-F23; no additional generalized phase','scope':'Linux code-only engineering/refusal behavior, not authentic approval','criteria':[{'id':f'F{i:02}','criterion':name,'status':'PASS','evidence':ref} for i,(name,ref) in enumerate(criteria,1)],'source_manifest_digest':M['source_manifest_digest']})
js('22_final_gatekeeper.json',gate)
md('23_od10_dependency_handoff.md','''# OD10 code-only handoff

OD10 may consume versioned observations/comparison contexts; PASS/WARN/FAIL/UNCOMPARABLE; exact source/result/policy/context digests; anomaly records; immutable review/correction lineage; exact reprocess scope/completion. These are engineering outputs, not authenticated market facts or publication authorization.

Controlling master OD10 is versioned Parquet/DuckDB/manifests. Separately authorized implementation must retain exact rows, stable IDs, valid/knowledge cutoffs, identity/calendar/adjustment/universe digests, tolerance versions and immutable revisions. Keep raw and derived bases separate. Admission must replay pinned context and account for blocked/uncomparable inputs, preserving old as-known outputs.

Proposed tests: source/manifest pins, tampered/missing-row refusal, Decimal roundtrip, temporal replay, partition completeness, schema-version refusal, atomic idempotent commits, restart/rollback and retained unresolved review/reprocess blocks. No operational migration or market reprocessing authorized.

One next action: owner review and separate authorization for bounded OD10 code-only work. Authentic references, accountable incident disposition, Windows isolation and production permission remain independent. OD10 was not executed.''')
md('24_final_report.md',f'''# Final OD08 dependency closure and OD09 delivery

**Tested Linux code-only engineering PASS. Authentic financial acceptance and production integration BLOCKED.** HEAD `{HEAD}` on `feature/od01-source-rights` matched ref metadata. Applied/tested workspace `{S}`; exact source digest `{M['source_manifest_digest']}`. Original unstaged/untracked state deliberately not scanned. No original app integration, commit or push.

## Applied implementation

37 upstream delivered files,3838 approved code/metadata pins verified. Twenty phase files changed:7 Stage A,13 Stage B. Combined delivery51 files. [Before/after hashes](20_preservation_manifest.json), [code](source/), [combined patch](implementation.patch). Corrected patch replayed in a fresh data-free before-state; all51 output hashes matched. First diff lacked EOF marker on a retained upstream test; actual syntax failure preserved, generator corrected without source changes.

Stage A exact field/numeric adjustment binding, policy-scoped persisted observation selection, precise intraday/announcement semantics and exact rational liquidity thresholds passed37 controls plus full regression. Original92 OD08 tests unchanged. Initial32-case gate preceded Stage B; later adversarial temporal/median cases were corrected before final acceptance, without rewriting that evidence.

OD09 implements canonical observations, economic comparability, bounded candidate matching, Decimal/Fraction metrics, immutable tolerance/calibration contracts, explainable anomalies, independent hard blocks, exact lineage, append-only review/correction/reprocess and eleven-table disposable SQLAlchemy/SQLite storage. Legacy APIs retained, operational mutating/alert paths not invoked. Direct authority-codec Decimal dependency fix changes no permission/root policy.

## Actual tests

Collection **1413**: A**1405**,B**4**,C**4**. A **1393 passed,12 skipped**,exit0. Unchanged diagnostic **1393 passed,4 failed,12 skipped,4 deselected**,exit1. Exact4 failures are unchanged source-dependent B tests. C not executed. Seven native Windows cases remain blocked; platform skips are not passes.

Fresh focused: Stage A**37**,OD09**83**,original OD08**92**,OD07**100**,final OD07**84**,OD06 identity**66**,foundation**87** passed; parser/reference**170 passed,1 skipped**. Ruff,mypy,pip check,compile exit0. [Actual commands/UTC/exit codes/skips](17_full_engineering_matrix.json).

OD09 package focused statement coverage **{coverage['od09']['statement_percent']:.2f}%**, branch coverage **{coverage['od09']['branch_percent']:.2f}%**. Coverage is measured, not exhaustive path certification. Real trusted human approval/completion positive path remains unexecuted without supplied authority. Genuine negative-first hashes/results and implementation errors are preserved.

## Containment, performance and data

Final Linux worker:12 native denials, positive local IPC, unchanged bwrap namespace/read-only mount/capability-drop/no_new_privs/seccomp2. Read ENOENT demonstrates non-exposure, not ACL proof. Ruff uses documented static read-only profile. No Windows-native certification.

100 anonymous bookkeeping groups/200 controls improved from **{before['measurements'][-1]['reconciliation_seconds']:.3f}s** to final **{perf['measurements'][-1]['reconciliation_seconds']:.3f}s**, exact output digests unchanged. Thirty context admissions/restart measured, covering digest index used. Small structural experiment, not authentic market throughput.

Archived physical inventory only:3626 present/size-matched paths,3596seed+30cache,2760hardlink+866single. No fresh scan/payload read. Original financial rows inspected/independently verified:**0**. Financial mismatches,missing sessions and actual coverage unknown/not assessed. No fabricated observations counted as authentic.

OD05V and OD05XR1 remain PENDING_HUMAN_OWNER_REVIEW; R1 payload extent UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED. All523 prior sealed files preserved; no self-approval. No source policies, signing material, production routing or operational databases altered.

## Final decision and stop

[All23 engineering criteria](21_acceptance_matrix.json) PASS within tested code-only scope. [Gatekeeper](22_final_gatekeeper.json): authentic reconciliation/calibration BLOCKED_REAL_DATA; independent financial review BLOCKED_INPUT; production integration BLOCKED; OD10 code-only readiness READY, authorization NOT_GRANTED.

One next action: owner review and separate authorization for bounded OD10 code-only work. No OD10, publication,release,signing,trading,commit or push executed.''')
assert len(artifacts)==25
root=B/'report-inputs';root.mkdir()
raw=j({'artifacts':artifacts}).encode();assert len(raw)<4_000_000
(root/'summary.json').write_bytes(raw)
(root/'manifest.json').write_text(j({'schema_version':'od05.final-report/v1','files':{'summary.json':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}}}))
state={'matrix':matrix,'coverage':coverage,'negative_first':negative,'artifacts':sorted(artifacts),'record_files':[str(p) for p in sorted((B/'logs').iterdir()) if p.is_file()],'chosen_tags':[p.name.removesuffix('-command.json') for p,r in chosen.values()],'package_root':str(B/'delivery/docs/omegadata_v2/implementation/od09/20261120T141954Z'),'summary_sha256':sha(root/'summary.json')}
(B/'evidence-build-state.json').write_text(j(state))
print(j({'status':'READY_FOR_ISOLATED_RENDER','files':len(artifacts),'summary_bytes':len(raw),'coverage':coverage,'results':{k:v.get('counts',v.get('exit_code')) for k,v in matrix.items()}}))