"""Bounded data-free OD08 report inputs. No Git or original checkout discovery."""
import json,hashlib,difflib
from pathlib import Path
from datetime import UTC,datetime
from collections import Counter,defaultdict
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');S=B/'staged2/repo';P=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');E=P/'delivery/docs/omegadata_v2/implementation/od07-final/20261119T175351Z';HEAD='d81657666238bf20f093cec54bb9cb3788feea99'
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pretty(v):return json.dumps(v,indent=2)+'\n'
commands=[(p,load(p)) for p in (B/'logs').glob('*-command.json')]
def latest(job):return max(((p,c) for p,c in commands if c['job']==job),key=lambda r:r[1]['end_utc'])
required={j:latest(j) for j in ['collection','od08','od07','od07final','od06','foundation','parser','mypy','pip','compile','od08perf','A','diagnostic']}
for j,(p,r) in required.items():assert r['exit_code']==(1 if j=='diagnostic' else 0),(j,r['exit_code'])
inv=load(B/'runtime-inventory.json');classes=Counter(inv.values());A=required['A'][1]['worker_result'];diag=required['diagnostic'][1]['worker_result'];focus=required['od08'][1]['worker_result'];perf=required['od08perf'][1]['worker_result']
assert focus['counts']=={'passed':92};assert classes=={'A':1285,'B':4,'C':4};assert A['counts']=={'passed':1273,'skipped':12};assert diag['counts']=={'passed':1273,'failed':4,'skipped':12}
assert {r['nodeid'] for r in diag['reports'] if r['outcome']=='failed'}=={n for n,v in inv.items() if v=='B'}
ruffpath=max((B/'logs').glob('static-ruff-*.json'),key=lambda p:p.stat().st_mtime_ns);assert load(ruffpath)['exit_code']==0
baseline=load(B/'upstream-manifest.json')
for n,pin in baseline.items():assert sha(S/n)==pin,('UPSTREAM_CHANGED',n)
new=['src/omegadata/universe/'+n+'.py' for n in ['__init__','contracts','temporal','eligibility','snapshots','repository','compatibility']]+['scripts/od08_structural_experiments.py','tests/unit/test_od08_universe.py']
changes=[{'path':n,'before_sha256':None,'after_sha256':sha(S/n),'bytes':(S/n).stat().st_size,'applied_in_safe_snapshot':True,'applied_to_original_checkout':False} for n in new]
for j,(p,r) in required.items():
 pins={v['path']:v['sha256'] for v in load(p.with_name(p.name.replace('-command.json','-manifest.json')))['files']}
 for row in changes:assert pins[row['path']]==row['after_sha256'],('STALE_RESULT',j,row['path'])
prior=load(E/'evidence-sha256.json')
for n,row in prior['files'].items():assert sha(E/n)==row['sha256'] and (E/n).stat().st_size==row['bytes']
combined=load(B/'adoption.json')['files']+changes;assert len(combined)==37
snapshot={**baseline,**{r['path']:r['after_sha256'] for r in changes}};snapshot_digest=hashlib.sha256(pretty(dict(sorted(snapshot.items()))).encode()).hexdigest()
for n,v in [('final-source-manifest.json',snapshot),('phase-source-changes.json',changes),('combined-delivery-manifest.json',combined)]:
 with (B/n).open('x') as f:f.write(pretty(v))
base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo');patch=[];phase=[]
for row in sorted(combined,key=lambda v:v['path']):
 n=row['path'];before='' if row['before_sha256'] is None else (base/n).read_text()
 if row['before_sha256'] is not None:assert sha(base/n)==row['before_sha256']
 patch.extend(difflib.unified_diff(before.splitlines(True),(S/n).read_text().splitlines(True),fromfile='/dev/null' if row['before_sha256'] is None else 'a/'+n,tofile='b/'+n))
for n in new:phase.extend(difflib.unified_diff([], (S/n).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+n))
(B/'implementation.patch').write_text(''.join(patch));(B/'phase-only.patch').write_text(''.join(phase))
proofpath=required['od08'][0].with_name(required['od08'][0].name.replace('-command.json','-native-probes.json'));proof=load(proofpath)
assert proof['boundary']['verified'] and proof['boundary']['seccomp_mode']==2 and len(proof['probes'])==12 and all(v['denied'] and not v['python_hook'] for v in proof['probes']) and proof['local_ipc_control']['bytes']>0
cov=load(required['od08'][0].with_name(required['od08'][0].name.replace('-command.json','-coverage.json')));covmodules={n:v['summary'] for n,v in cov['files'].items() if '/universe/' in n}
totals={k:sum(v.get(k,0) for v in covmodules.values()) for k in ['covered_lines','num_statements','covered_branches','num_branches']};totals.update(statement_percent=100*totals['covered_lines']/totals['num_statements'],branch_percent=100*totals['covered_branches']/totals['num_branches'])
records=[]
for j,(p,r) in required.items():
 w=r['worker_result'];records.append({'job':j,'command_id':p.stem,'launcher_argv':r['argv'],'working_directory':r['cwd'],'source_commit':HEAD,'platform':'Ubuntu/WSL Linux','python':w['python'],'interpreter':w.get('interpreter'),'start_utc':r['start_utc'],'end_utc':r['end_utc'],'elapsed_seconds':r['elapsed_seconds'],'exit_code':r['exit_code'],'counts':w['counts'],'stdout_stderr':'logs/'+p.name,'source_manifest_sha256':r['source_manifest_sha256'],'source_manifest':'logs/'+p.name.replace('-command.json','-manifest.json')})
records.append({'job':'ruff','command':load(ruffpath)['argv'],'exit_code':0,'stdout_stderr':'logs/'+ruffpath.name,'scope':load(ruffpath)['scope']})
history=[]
for p,r in sorted(commands,key=lambda v:v[1]['start_utc']):
 if r['job']=='od08':
  manifest=load(p.with_name(p.name.replace('-command.json','-manifest.json')));pin=next(v['sha256'] for v in manifest['files'] if v['path']=='tests/unit/test_od08_universe.py');w=r['worker_result']
  history.append({'command':'logs/'+p.name,'start_utc':r['start_utc'],'end_utc':r['end_utc'],'test_sha256':pin,'exit_code':r['exit_code'],'counts':w['counts'],'failed_nodes':[v['nodeid'] for v in w.get('reports',[]) if v['outcome']=='failed'],'collection_failure':not bool(w['counts']) and r['exit_code']!=0})
byfile=defaultdict(Counter)
for r in A['reports']:byfile[r['nodeid'].split('::')[0]][r['outcome']]+=1
families=[f'{prefix}{i:02}' for prefix,n in [('U',10),('I',6),('C',5),('A',5),('L',5),('E',4),('R',2),('P',6),('S',4)] for i in range(1,n+1)];assert len(families)==47
verdict={n:'PASS' for n in ['OD08_UPSTREAM_ADOPTION','OD08_MEMBERSHIP_ENGINEERING','OD08_BITEMPORAL_CORRECTNESS','OD08_INFORMATION_AVAILABILITY','OD08_SURVIVORSHIP_PROTECTION','OD08_CONSTITUENT_RECONCILIATION','OD08_COVERAGE_INTEGRITY','OD08_LIQUIDITY_ENGINEERING','OD08_TRADABILITY_ENGINEERING','OD08_ADJUSTMENT_CONTEXT_INTEGRATION','OD08_SNAPSHOT_INTEGRITY','OD08_PERSISTENCE','OD08_REPLAY_ENGINEERING','OD08_COMPATIBILITY','OD08_ENGINEERING_OVERALL']}
verdict.update(OD08_AUTHENTIC_CONSTITUENT_VALIDATION='BLOCKED_REAL_DATA',OD08_AUTHENTIC_AVAILABILITY_VALIDATION='BLOCKED_REAL_DATA',OD08_PRODUCTION_INTEGRATION='BLOCKED',OD09_CODE_ONLY_READINESS='READY',OD09_EXECUTION_AUTHORIZATION='NOT_GRANTED',scope='Opt-in Linux data-free software invariants, literal nonmarket expected sets and scalar integration controls only',new_unresolved_P0_P1_in_tested_scope=0,review='Same coding agent with separately derived literal expectations, independent SQL accounting, SQLite constraints and native kernel controls; no independent human review claimed',Windows='OS_CAPABILITY_BLOCKED',incidents='PENDING_HUMAN_OWNER_REVIEW',unchanged_full_diagnostic='FAIL_FOUR_PRESERVED_SOURCE_DEPENDENT_CASES')
art={}
def md(n,s):art[n]=s.strip()+'\n'
def js(n,v):art[n]=pretty(v)
