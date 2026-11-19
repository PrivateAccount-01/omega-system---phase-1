"""Bounded data-free evidence preparation. No Git, raw data, cleanup or discovery."""
import difflib,hashlib,json
from collections import Counter,defaultdict
from datetime import UTC,datetime
from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
HEAD='47b7f2c5859e36bc40c5970c2316eef3d28211e8'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pretty(v):return json.dumps(v,indent=2)+'\n'
commands=[(p,load(p)) for p in (B/'logs').glob('*-command.json')]
def latest(job):return max(((p,c) for p,c in commands if c['job']==job),key=lambda pair:pair[1]['end_utc'])
required={job:latest(job) for job in ['collection','od07','A','diagnostic','mypy','pip','compile']}
for job,(p,c) in required.items():assert c['exit_code']==(1 if job=='diagnostic' else 0)
ruffpath=max((B/'logs').glob('static-ruff-*.json'),key=lambda p:p.stat().st_mtime_ns);ruff=load(ruffpath);assert ruff['exit_code']==0
A=required['A'][1]['worker_result'];diag=required['diagnostic'][1]['worker_result'];focused=required['od07'][1]['worker_result']
assert focused['counts']=={'passed':100}
assert A['counts']=={'passed':1097,'skipped':12}
assert diag['counts']=={'passed':1097,'failed':4,'skipped':12}
inv=load(B/'runtime-inventory.json');assert Counter(inv.values())=={'A':1109,'B':4,'C':4}
assert {r['nodeid'] for r in diag['reports'] if r['outcome']=='failed'}=={n for n,c in inv.items() if c=='B'}
upstream=load(B/'upstream-manifest.json')
for n,pin in upstream.items():assert sha(S/n)==pin,n
phase_paths=['src/omegadata/adjustments/'+n+'.py' for n in ['__init__','contracts','factors','temporal','chains','compatibility','repository']]+['tests/unit/test_od07_adjustments.py']
changes=[{'path':n,'before_sha256':None,'after_sha256':sha(S/n),'bytes':(S/n).stat().st_size,'applied_in_safe_snapshot':True,'applied_to_original_checkout':False} for n in phase_paths]
for job,(p,c) in required.items():
 manifest=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
 pins={r['path']:r['sha256'] for r in manifest['files']}
 for row in changes:assert pins[row['path']]==row['after_sha256'],(job,row['path'])
proofpath=required['od07'][0].with_name(required['od07'][0].name.replace('-command.json','-native-probes.json'));proof=load(proofpath)
assert proof['boundary']['verified'] and proof['boundary']['seccomp_mode']==2 and len(proof['probes'])==12 and all(p['denied'] and not p['python_hook'] for p in proof['probes']) and proof['local_ipc_control']['bytes']>0
cov=load(required['od07'][0].with_name(required['od07'][0].name.replace('-command.json','-coverage.json')))
selected={n:v['summary'] for n,v in cov['files'].items() if '/adjustments/' in n}
totals={k:sum(v.get(k,0) for v in selected.values()) for k in ['covered_lines','num_statements','covered_branches','num_branches']}
totals['statement_percent']=100*totals['covered_lines']/totals['num_statements'];totals['branch_percent']=100*totals['covered_branches']/totals['num_branches']
byfile=defaultdict(Counter)
for row in A['reports']:byfile[row['nodeid'].split('::')[0]][row['outcome']]+=1
families={'M01':'test_acceptance[M01] + decimal_environment','M02':'math_oracle[SPLIT] + forward','M03':'math_oracle[BONUS]','M04':'math_oracle[RIGHTS]','M05':'test_acceptance[M05]','M06':'math_oracle[DIVIDEND]','M07':'test_acceptance[M07]','M08':'test_acceptance[M08] + volume controls','M09':'test_acceptance[M09]','S05':'test_persistence + native SQL + competing writers'}
for prefix,count in [('T',7),('C',6),('S',4)]:
 for i in range(1,count+1):families[f'{prefix}{i:02}']=f'test_acceptance[{prefix}{i:02}]'
assert len(families)==27
history=[]
for p,c in sorted(commands,key=lambda pair:pair[1]['start_utc']):
 if c['job']=='od07':
  m=load(p.with_name(p.name.replace('-command.json','-manifest.json')))
  pin=next(r['sha256'] for r in m['files'] if r['path']=='tests/unit/test_od07_adjustments.py')
  history.append({'command':'logs/'+p.name,'start_utc':c['start_utc'],'end_utc':c['end_utc'],'test_sha256':pin,'exit_code':c['exit_code'],'counts':c['worker_result']['counts'],'failed_nodes':[r['nodeid'] for r in c['worker_result']['reports'] if r['outcome']=='failed']})
freezes={n:load(B/n) for n in ['negative-first-freeze.json','review-freeze.json','integrity-freeze.json','sql-freeze.json','decimal-freeze.json']}
combined=load(B/'adoption.json')['files']+changes;assert len(combined)==24
base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo');patch=[]
for row in sorted(combined,key=lambda r:r['path']):
 n=row['path'];before='' if row['before_sha256'] is None else (base/n).read_text()
 if row['before_sha256'] is not None:assert sha(base/n)==row['before_sha256']
 patch.extend(difflib.unified_diff(before.splitlines(keepends=True),(S/n).read_text().splitlines(keepends=True),fromfile='/dev/null' if row['before_sha256'] is None else 'a/'+n,tofile='b/'+n))
(B/'implementation.patch').write_text(''.join(patch))
snapshot={**upstream,**{r['path']:r['after_sha256'] for r in changes}}
snapshot_digest=hashlib.sha256(pretty(dict(sorted(snapshot.items()))).encode()).hexdigest()
(B/'final-source-manifest.json').write_text(pretty(snapshot));(B/'phase-source-changes.json').write_text(pretty(changes));(B/'combined-delivery-manifest.json').write_text(pretty(combined))
records=[]
for job,(p,c) in required.items():
 w=c['worker_result'];records.append({'command_id':p.stem,'launcher_argv':c['argv'],'cwd':c['cwd'],'job':job,'platform':'Linux/WSL Ubuntu','python':w['python'],'interpreter':w.get('interpreter'),'start_utc':c['start_utc'],'end_utc':c['end_utc'],'exit_code':c['exit_code'],'elapsed_seconds':c['elapsed_seconds'],'counts':w['counts'],'stdout_stderr':'logs/'+p.name,'input_manifest':'logs/'+p.name.replace('-command.json','-manifest.json'),'input_manifest_sha256':c['source_manifest_sha256']})
records.append({'job':'ruff','command':ruff['argv'],'exit_code':ruff['exit_code'],'stdout_stderr':'logs/'+ruffpath.name,'scope':ruff['scope']})
verdict={name:'PASS' for name in ['OD07_UPSTREAM_ADOPTION','OD07_MATHEMATICAL_CORRECTNESS','OD07_PIT_CORRECTNESS','OD07_ADJUSTMENT_PROFILES','OD07_IMMUTABILITY','OD07_PERSISTENCE','OD07_COMPATIBILITY','OD07_ENGINEERING_OVERALL']}
verdict.update(OD07_AUTHENTIC_FINANCIAL_VALIDATION='BLOCKED_REAL_DATA',OD07_PRODUCTION_INTEGRATION='BLOCKED',OD08_CODE_ONLY_READINESS='READY',OD08_EXECUTION_AUTHORIZATION='NOT_GRANTED',scope='Opt-in Linux data-free engineering and mathematical controls only',multi_security_economic_policy='BLOCKED_INPUT; no arbitrary scalar allocation',strict_authentic_positive_path='BLOCKED_INPUT; no owner-authenticated source roots/corpus',Windows='OS_CAPABILITY_BLOCKED',historical_incidents='PENDING_HUMAN_OWNER_REVIEW',review_independence='Same-agent review; executed Fraction known-answer, SQLite constraint and native kernel oracles; no human approval claimed',new_unresolved_P0_P1_in_tested_scope=0,full_diagnostic='FAIL_4_PRESERVED_SOURCE_DEPENDENT_CASES')
art={}
def md(n,v):art[n]=v.strip()+'\n'
def js(n,v):art[n]=pretty(v)
md('00_scope_and_identity.md',f'''# OD07 code-only implementation
Repository PrivateAccount-01/omega-system---phase-1, branch feature/od01-source-rights, reviewed local/remote HEAD {HEAD}. Ref-only Git verified; original mixed worktree content refresh prohibited and not performed. Original worktree contents/untracked files not scanned. No reset, integration, commit or push.

Applied development snapshot: {S}. Snapshot manifest digest {snapshot_digest}; {len(snapshot)} permitted files. Sixteen sealed upstream files adopted with exact before/after checks through unchanged canonical Linux stage. All572sealed prior evidence files verified/read. Eight new OD07 code/test files; all3817upstream hashes unchanged. Code runs at normal module paths in this safe snapshot. Combined24file delivery and patch are for future separately authorized integration, not installed original checkout.

Mathematical vectors and anonymous invariant inputs only. No authentic financial observations or securities generated/validated. No original market bytes, incident copies, credentials, databases or signing assets read/copied/mounted. No OD08 execution.''')
js('01_upstream_code_manifest.json',{'adoption':load(B/'adoption.json'),'final_snapshot_sha256':snapshot_digest,'snapshot_file_count':len(snapshot),'upstream_preserved_count':len(upstream),'upstream':'support/upstream-manifest.json','changes':changes,'combined_delivery':combined})
md('02_existing_engine_audit.md','''# Reuse and legacy audit
153receipt-pinned code files read;76caller references in support/legacy-audit-source-inventory.json. Inspected corporate_actions,corporate_action_matching,adjustment_engine,manual_review,ORM/domain,OD06 contracts/authority/repository/calendar and relevant tests. Legacy source/assertions unchanged.

- recompute_adjusted_series: LEGACY_RISK_RETAINED / OPT_IN_REPLACEMENT. Intentionally updates adjusted PriceRecord fields and serializes Decimal metadata through float. Existing tests execute in disposable DBs in A. New chains are frozen and retain exact factor terms, never write ORM rows.
- Rights zero subscription fallback is explicitly expected by an existing legacy test, retained for compatibility. test_legacy_risk_reproduction executes mathematical100,4:1,missing issue price =>.8 fallback, and proves calendar-minus-one misses a prior canary session. NewM05/T06 refuse missing subscription and require verified actual previous session.
- refresh_demerger_actuals: LEGACY_RISK_RETAINED. Source inspection confirms mutable later-price enrichment without historical cutoff argument; never automatically invoked by new code. T03 verifies later valuation refusal in new API. No assertion that a real historical incident was reproduced.
- Legacy dividend/lifecycle/unsupported None is retained; new outcomes distinguish NOT_APPLICABLE, unsupported policy, invalid parameters and evidence/knowledge/calendar blocks. Total-return policy is separate.
- CorporateActionService: REUSE staging/review concepts, OPT_IN_REPLACEMENT append-only correction history. Confirmation and cross-source agreement are not source authenticity. CorporateActionMatcher: REUSE for matching only; no authority from tolerances. ManualReviewService: REUSE workflow only; no auto queue, alert or reprocessing.
- OD06: REUSE exact typed identity, EvidenceAuthority configured owner roots plus canonical source-rights oracle, and VerifiedCalendar. Persistent upstream stores may provide reviewed immutable typed snapshots, not arbitrary resolver flags.

New reproduced defects corrected within this execution: empty-chain gates, expired revisions, currency/reference validation, suspension execution refusal, partial/nonfinite output, persisted action/factor/arithmetic/order binding, future-correction digest stability, ambient Decimal-context inheritance. Legacy risks remain behind production integration block. Same-agent review, not independent human consensus.''')
md('03_corporate_action_contracts.md','''# Immutable domain v1
Frozen Action/Reference/Raw/Context/Policy/Factor/Link/Result. Typed Split,Bonus,Rights,Dividend,Merger,Demerger,Conversion,Lifecycle parameters. Action records security/listing,exchange,source/evidence/artifact,announcement/publication/ex/effective/record/known/ingested times,version,revision,parent,review and optional established sequence. Unknown timestamps remainNone. Ex-date is comparison boundary, not inferred knowledge or legal effective time.

Inputs finite Decimal <=64digits/exponent64, never float. Query requires valid_at,aware known_at and identity/evidence/calendar/policy versions. Half-open knowledge interval, unique IDs, increasing same-event correction lineage. Missing/unrelated parent or competing child refuses. Consumer profile always explicit.

Statuses: CALCULATED,NOT_APPLICABLE,BLOCKED_EVIDENCE,BLOCKED_KNOWLEDGE,BLOCKED_IDENTITY,BLOCKED_CALENDAR,INVALID_PARAMETERS,CONFLICTING_ACTIONS,UNSUPPORTED_POLICY. Failure cannot emit partial accepted factors/prices. Invalid constructor/timezone contracts raise ValueError. No I/O/network in pure modules.''')
md('04_adjustment_profiles.md','''# Policy od07.policy/v1
RAW preserves original price/volume. EXECUTION also preserves raw basis and rejects unresolved/suspended/delisted identity or explicit blocking lifecycle. This does not certify settlement,lot size or authentic tradability; missing execution references remain blocked.

PRICE_RETURN applies share-changing comparisons and explicit fully-exercised theoretical rightsTERP. Ordinary/special cash distributions remain separate (NOT_APPLICABLE,factor1), preserving pure price return. This does not claim every vendor's special-distribution convention matches.

TOTAL_RETURN adds gross same-security ex-close reinvestment: cashD at eligible referenceQ gives quantity1+D/Q, backward price factorQ/(Q+D). Explicit EX_CLOSE_GROSS,currency,reference identity/session/knowledge required. No inferred price,tax,FX,fees or realized-return claim. VOLUME normalizes split/bonus quantities; rights/cash distributions leave traded volume unchanged under v1. Forward comparisons invert specified factors over the same event window. Backward comparisons apply only raw.trade_date<ex_date<=valid_at.

Methodological context reviewed2026-11-19: S&P DJI Index Mathematics Methodology https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf distinguishes price return and reinvested distributions. Its index-wide reinvestment differs from this explicit single-security contract. Context only, not NSE/BSE certification or source-use permission. No exchange endpoint accessed.''')
md('05_independent_math_vectors.md','''# NON_MARKET_MATH known answers
No authentic observations/events/securities represented. Expected outputs are literal Fraction ratios plus independent Decimal evaluation, never the production function generating its own expected result.

| Input | Backward factor |
|---|---|
| splitS2 |1/2|
| reverseS1/5 |5|
| bonusnew1/existing2 |2/3|
| bonusnew2/existing1 |1/3|
| rightsN4,R1,P100,S50 |(400+50)/(5*100)=9/10|
| rightsN3,R2,P120,S30 |(360+60)/(5*120)=7/10|
| cash5,ex-close95 |95/(95+5)=19/20|
| specialcash20,ex-close80 |80/(80+20)=4/5|

Split2 then bonus1:2 =>1/3; mathematical120=>40. Established split2 then split3 =>1/6;120=>20. Forward inverse,volume reciprocity,missing versus legitimate zero and final rounding tested.

Fully pinned Decimal context, exact intermediate budget20480digits with Inexact trap (exhaustion refuses). Final division80digits ROUND_HALF_EVEN; price1e-6/volume1e-4 ROUND_HALF_UP. Each numerator/denominator retained; rounded factor approximations are not multiplied. Max128actions; oversized result quantization refuses. External rounding/traps cannot alter output. No financial accuracy percentage from these vectors.''')
md('06_temporal_eligibility.md','''# Point-in-time selection
No current-clock/ex-date-as-known default. Unknown/future raw/action/reference availability blocks. Announcement/publication/parameter availability,revocation and expired revisions checked. Append-only A?B?C history; selected as-known state is digest input so later corrections cannot alter earlier result. Lower known bound inclusive,upper exclusive; no superseded revival on revocation.

Resolve exact OD06 identity for raw and requested valid dates. Wrong security/listing,ambiguity/missing relationship refuses. Version-pinned ex-calendar; rights requires actual preceding session plus intervening authoritative coverage,never yesterday. Reference currency/date/identity/knowledge checked. STRICT requires configured owner authority and existing source-rights for raw/action/reference and upstream identity/calendar; caller labels or bundle pins cannot self-approve. Authentic positive path remainsBLOCKED_INPUT with current empty roots.

NON_MARKET_MATH uses explicit CANARY_ONLY and never financial eligibility. Unknown/unsupported economic allocation remains refused. No source policy changes.''')
md('07_adjustment_chain.md','''# Immutable chain
Frozen Link binds revision,full canonical action parameters,source artifact,identity resolution,calendar reference,raw observation,calculation/profile/rounding versions and cutoff. Frozen Result binds raw basis,cumulative factors,adjusted values,version-pinned inputs and SHA256 canonical JSON digest. All Decimal evidence strings, no floats.

Same-day events require unique explicit sequence; order not guessed. Any failed link discards partial outputs. Merger/demerger/conversion terms retained but arbitrary scalar allocation returnsUNSUPPORTED_POLICY until independently reviewed continuity and economic method/terms exist; later successor values also require actual known time.

Persistent storage rechecks arithmetic,factor-to-stored-action payload and canonical chain order. No raw observations mutated; corrections create new immutable results. Publication eligibility is init-disabled and remainsFalse pending independent source/release acceptance.''')
md('08_negative_first_tests.md','# Actual frozen chronology\nInitial63tests froze before package creation and failedNEW_FEATURE_ABSENT. Later genuine adversarial failures were executed before corresponding fixes. Already passing controls are regressions, not fabricated red results. All failed source versions and commands retained.\n\n```json\n'+pretty({'freezes':freezes,'history':history,'mandatory27family_mapping':families})+'```\nFinal100testsPASS. Formatter-cache refusal,static/type failures and corrections preserved. Same-agent review; executable independent oracles do not imply human approval.')
js('09_focused_test_results.json',{'final_focused':next(r for r in records if r['job']=='od07'),'required_families':families,'coverage':{'modules':selected,'weighted':totals,'scope':'Focused OD07 engineering only'},'earlier_session_upstream_focused':{j:{'counts':latest(j)[1]['worker_result']['counts'],'command':'logs/'+latest(j)[0].name} for j in ['od06','foundation','parser']},'final_A_by_test_file':dict(byfile)})
js('10_full_engineering_matrix.json',{'collection':len(inv),'classes':dict(Counter(inv.values())),'commands':records,'A':A['counts'],'unchanged_diagnostic':diag['counts'],'diagnostic_exit':1,'B_failures':[r for r in diag['reports'] if r['outcome']=='failed'],'C_not_run':[n for n,c in inv.items() if c=='C'],'skips':[r for r in A['reports'] if r['outcome']=='skipped'],'Windows314':'NOT_RUN_OS_CAPABILITY_BLOCKED','Windows311':'NOT_RUN_OS_CAPABILITY_BLOCKED','source_manifest':'support/final-source-manifest.json','coverage':totals,'failed_attempts_preserved':True})
md('11_persistence_and_rollback.md','''# Additive SQLite od07.store/v1
SQLAlchemy reused,no dependency added. Four tables:od07_schema,od07_action(unique parent FK),od07_result(canonical digest),od07_result_action(composite result/action FKs). Typed canonical action payload and SHA256 verified on read. Append-only UPDATE/DELETE triggers. BEGIN IMMEDIATE,atomic commit/rollback,idempotent identical retries,changed duplicate/competing successor refusal. Result validates exact stored action,math,factor,order and references before append.

Actual isolated tests:in-memory/file-backed insert/read,reopen,correction history,duplicates,two competing file-backed connections(one commit/one refusal),interrupted transaction rollback,nativeSQL FK rejection,append-only denial,empty migration/drop/recreate,populated rollback refusal and unrelated-schema rejection. No new OD07 native process-kill or hardware powerloss certification claimed; OD06 evidence remains historical.

Explicit owned disposable_root and SQLite only; path/link escapes/unrelated schema refuse. No legacy ORM or operational DB migration. Production requires separate reviewed ownership,backup/restore,consumer mapping,rehearsal and rollback authorization. Code-only rollback disables opt-in calls/reverts new source while preserving history/evidence; no cleanup or populatedDROP.''')
js('12_compatibility_results.json',{'legacy_sources_unchanged':True,'upstream_preserved_files':len(upstream),'inventory':'support/legacy-audit-source-inventory.json','adapter':'src/omegadata/adjustments/compatibility.py:legacy_action','behavior':'Read-only snapshot; unknown knowledge retained; confirmation cannot self-promote; BLOCKED_EVIDENCE','actual_A_by_file':dict(byfile),'operational_DB_touched':False,'legacy_recompute_refresh_auto_invoked':False})
js('13_source_dependencies.json',{'authentic_observations_inspected':0,'authentic_actions_verified':0,'financial_comparisons':0,'synthetic_financial_acceptance_contribution':0,'verdict':'BLOCKED_REAL_DATA','required_inputs':['Permitted,authenticated original action terms/documents and exact artifact identity','Owner-reviewed source-use purpose,trust roots and independent reviewer attestations','Independent expected real parameters/calculations and reference observations','Authenticated security/listing continuity and bitemporal mappings','Authoritative versioned ex/prior/reinvestment sessions and coverage','Reference prices,units,currency and evidenced availability','Reviewed multi-security legal/economic allocation method','Execution lot/settlement/tradability constraints'],'original_archive_METADATA_ARCH_only':{'candidates':3626,'seed':3596,'cache':30,'present_size_matches':3626,'hardlinks':2760,'single_links':866,'new_payload_reads':0,'new_original_scan':'NOT_RUN'},'incidents':{'OD05V':'PENDING_HUMAN_OWNER_REVIEW;39files/6135515recordedbytes','OD05XR1':'PENDING_HUMAN_OWNER_REVIEW;extentUNKNOWN_NOT_INDEPENDENTLY_EXCLUDED'},'Windows':'Approved OS isolation unavailable;no waiver','new_source_approvals':0})
js('14_preservation_manifest.json',{'reviewed_HEAD':HEAD,'snapshot_sha256':snapshot_digest,'upstream_preserved_count':len(upstream),'upstream':'support/upstream-manifest.json','changes':changes,'combined_delivery':combined,'patch_sha256':sha(B/'implementation.patch'),'live_safe_application_paths':True,'original_checkout_integrated':False,'original_market_payload_reads_hashes_copies':0,'historical_evidence_rewritten':False,'source_policy_changes':0,'production_DB_writes':0,'signing_release_operations':0,'commit_push_merge':False,'native_proof':{'path':'logs/'+proofpath.name,'sha256':sha(proofpath),'probes':len(proof['probes']),'boundary':proof['boundary'],'local_ipc':proof['local_ipc_control']},'proof_limit':'ReadENOENT proves unmapped canary nonexposure,not ACL denial;writeEROFS,exec/networkEPERM. No original bytes used in canaries.'})
js('15_gatekeeper.json',verdict)
md('16_od08_handoff.md','''# OD08 code-only contract READY,not authorized
OD08 concerns point-in-time universe/information availability. Consume unchanged OD06 identity,membership,calendar and new OD07 versioned Raw/Action/Context/Policy/Result/Link through opt-in APIs. Pin source/evidence/identity/calendar/action/policy/calculation versions and independent valid/known cutoffs. Mathematical success never grants source authority,complete universe coverage,tradability or publication.

Retain as-reported identifiers,effective/known membership bounds,official/provisional status,lifecycle,all unresolved/excluded selected entries and explicit coverage. Compare only matching profile/basis;execution staysraw. Preserve immutable chain/output references and block unknown authority/availability/coverage. Legacy mutable recomputation is not an implicit dependency.

Anonymous invariant development may proceed under the existing isolated workflow after separate authorization. Authentic constituent transitions,availability history,complete membership references and source permissions remainBLOCKED_INPUT. Production also requires outstanding incident disposition,platform conditions and reviewed migration/consumer integration. No OD08 execution here.

One next development action:owner review of this dossier,then explicit bounded OD08 code-only invocation. No additional generic OD07 remediation phase proposed.''')
md('17_final_report.md',f'''# OD07 engineering PASS;authentic financial/production BLOCKED
Reviewed{HEAD},feature/od01-source-rights. Applied only in{S}. Exact16upstream adoption,eight new files(seven modules and100case tests),all3817upstream files preserved. Combined24file delivery/patch provided,not original application integration.

Typed immutable revisions,split/reverse/bonus/rightsTERP,distinct raw/execution/price-return/gross-ex-close-total-return/volume profiles,fully pinned Decimal context,exact factor terms,verified prior-session/identity/authority refusal,PIT corrections and deterministic immutable digests. Four-table append-only SQLAlchemy store with reopen,rollback,nativeFK,competing-writer,stored arithmetic/factor/order tests. Legacy APIs/expectations unchanged;read-only adapter retains unknown knowledge.

FinalLinux3.12:100OD07PASS. Collection1117=A1109+B4+C4. A1097passed12skipped,exit0. Unchanged diagnostic1097passed4failed12skipped,C4deselected,exit1. Ruff/mypy/pip/compileexit0. Earlier session OD06focused66PASS,foundation87PASS,parser170PASS1skip;finalA reruns these with final source pins. Twelve skips=five Windows-specific plusseven explicitly blocked Windows-native controls. Windows runtimesNOT_RUN,noLinux-based certification.

Focused coverage{totals['statement_percent']:.2f}%statements/{totals['branch_percent']:.2f}%branches;per-module/counts in09. Linux bwrap namespaces,read-only exact staging,dropped capabilities,no_new_privs,seccomp2;12native denials andIPCpositivecontrol. ReadENOENT is unmounted harmless-canary nonexposure,notACLproof;writeEROFS,exec/networkEPERM. Original market/incident/credential roots unmapped. Reporting uses unchanged isolated pinned-bundle renderer,noGit or mixed-checkout discovery.

Actual negative-first sources/failures preserved,including initial63missing-feature failures,review/integrity/order and ambient Decimal defects. All corrected within this execution;no manufactured red history or independent human approval claimed. Zero new unresolvedP0/P1 in tested opt-in scope. Legacy risks remain behind integration block.

Actual independently verified financial observations/actions/comparisons:0. Mathematical vectors contributezero. Multi-security scalar allocation remainsUNSUPPORTED_POLICY/BLOCKED_INPUT pending reviewed terms/method. Caller labels cannot grant source authority. Historical presence remainsARCHmetadataonly,notZIP/hash/row acceptance. Incidents pendinghumanreview,R1extentunknown,Windows and original-mounted performance limits unchanged.

Gatekeeper:code-only engineeringPASS,authenticfinancialBLOCKED_REAL_DATA,productionBLOCKED. OD08code-onlycontractREADY,executionNOT_GRANTED. No commit,push,merge,release,signing,trading,restricted-source access or OD08. Nextaction:ownerreview and explicit boundedOD08authorization.''')
criteria=['Exact upstream baseline','Existing engine audit','Typed revisions','Source/knowledge eligibility','Distinct profiles','Independent supported formulas','Unsupported/incomplete refusal','Future information exclusion','Reproducible corrections','Deterministic chains','Raw immutability','Versioned lineage','Persistence/rollback','Legacy compatibility','Code-only regression','No new unresolvedP0/P1 tested defects','Source-dependent classification','OD08 handoff']
js('18_acceptance_matrix.json',[{'id':f'F{i+1:02}','criterion':name,'result':'PASS_CODE_ONLY','authentic_acceptance':'BLOCKED_REAL_DATA','evidence':['09_focused_test_results.json','10_full_engineering_matrix.json','14_preservation_manifest.json','15_gatekeeper.json']} for i,name in enumerate(criteria)])
js('19_review_and_limits.json',{'review':'same-agent','executed_oracles':['literalFraction answers','SQLite constraints/transactions','kernel seccomp/namespaces'],'not_claimed':['Independent human acceptance','Exchange certification','Windows isolation','Hardware powerloss durability','Realized multi-security returns','Production readiness'],'P2':['Legacy mutating/fallback paths retained;opt-in routing required','Authentic positive path blocked by empty owner roots','SQLite append consistency loads history;no market-scale claim'],'new_P0_P1_in_tested_scope':0,'static_failures':'All original failures retained;finalexit0','historical_finalizer_calls':0,'host_preparation_failure':'One oversized PowerShell command rejected before process creation;split into bounded writes;no application or payload access'})
assert len(art)==20
root=B/'report-inputs';root.mkdir()
(root/'summary.json').write_text(pretty({'artifacts':art}))
(root/'manifest.json').write_text(pretty({'schema_version':'od05.final-report/v1','files':{'summary.json':{'bytes':(root/'summary.json').stat().st_size,'sha256':sha(root/'summary.json')}}}))
assert (root/'summary.json').stat().st_size<4_000_000
(B/'report-input-index.json').write_text(pretty(['manifest.json','summary.json']))
(B/'report-preparation.json').write_text(pretty({'utc':datetime.now(UTC).isoformat(),'files':sorted(art),'changes':changes,'delivery':combined,'snapshot_sha256':snapshot_digest,'coverage':totals,'source_file_count':len(snapshot)}))
print(pretty({'reports':len(art),'phase_files':len(changes),'combined_files':len(combined),'coverage':totals,'snapshot_sha256':snapshot_digest}))
