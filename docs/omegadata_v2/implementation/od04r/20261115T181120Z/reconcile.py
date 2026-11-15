"""Fresh reconciliation, preservation and exact execution ledgers."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import control

ROOT=control.ROOT; HERE=control.HERE; LOGS=control.LOGS
OLD=ROOT/'docs/omegadata_v2/implementation/od04/20261115T124835Z'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
exclusive_save=control.save
def save_immutable(name,value):
 path=LOGS/name
 if path.exists():
  assert read(path)==value, name
 else:exclusive_save(name,value)
control.save=save_immutable
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(row):return dict(Counter(r['outcome'] for r in row.get('test_reports',[]) if r['when']=='call' or r['outcome']=='skipped'))
copy=read(LOGS/'copy.json'); overlay=read(LOGS/'win314-final-source.json')
expected={r['path']:r['sha256'] for r in copy['files']};expected.update(overlay)
identities={}
for label in ['win314','win311','linux312']:
 raw=(LOGS/(label+'-all-source-final.txt')).read_text();rows=json.loads(raw[raw.index('{'):])
 assert rows==expected,(label,'source mismatch')
 identities[label]={'all_files_match':True,'files':rows}
control.save('final-tested-identities.json',identities)
assert all(sha(ROOT/p)==h for p,h in overlay.items())
archived=[]
for label in ['win314-accepted','win311-accepted','linux312-accepted']:
 assert read(OLD/'logs'/f'{label}-source.json')==read(OLD/'logs/final-preservation-reviewed.json')['source_hashes']
 row={'label':label,'source_identity_match':True,'gates':{}}
 for gate in ['collection','targeted','full','ruff','mypy','pip']:
  path=OLD/'logs'/f'{label}-{gate}.json';data=read(path)
  output=OLD/'logs'/data['output'];assert data['exit_code']==0 and output.is_file()
  row['gates'][gate]={'metadata':str(path.relative_to(ROOT)),'metadata_sha256':sha(path),'raw_sha256':sha(output),
   'actual_exit':data['exit_code'],'start_utc':data['start_utc'],'end_utc':data['end_utc'],'counts':counts(data),'deselected':data.get('deselected',[])}
 archived.append(row)
nodes=[r['nodeid'] for r in read(OLD/'logs/linux312-accepted-targeted.json')['test_reports'] if r['when']=='call' and 'test_od04_raw_archive.py::' in r['nodeid']]
arows=[]
for prior in read(OLD/'logs/acceptance-matrix.json'):
 token=prior['id'].lower()
 exact=sorted(set(n for n in nodes if token in n.split('::')[-1].split('[')[0].split('_')))
 arows.append({'requirement':prior['id'],'requirement_text':prior['requirement'],'old_attribution':prior['nodes'],
  'exact_function_token_nodes':exact,'chronology':'ARCH BLOCKED; no retroactive negative-first claim'})
control.save('prior-evidence-reconciled.json',{'runtime_checks':archived,'A01_A28':arows,
 'A25_contradiction':'sha256 parameter matched a25 substring; that object-model node does not prove platform execution',
 'attribution_limits':'Grouped names over-attribute individual parameters; exact assertions and process logs govern.',
 'historical_gate':'OD04_BLOCKED','human_exception':False})
oldprocess=[]
for label in ['win-process-accepted','linux-process-persistent','win-corpus-reference','linux-corpus-persistent','linux-missing-corpus-negative','linux-corpus-reference']:
 path=OLD/'logs'/(label+'.json');raw=OLD/'logs'/(label+'.txt');assert path.is_file() and raw.is_file()
 oldprocess.append({'label':label,'metadata':read(path),'raw_sha256':sha(raw)})
control.save('prior-process-reconciled.json',oldprocess)
matrix=[]
for label in ['win314-final','win311-final','linux312-final']:
 gates={}
 for gate in ['environment','collection','targeted','full','ruff','mypy','pip']:
  row=read(LOGS/(label+'-'+gate+'.json'));assert row['exit_code']==0
  gates[gate]={k:row[k] for k in ['command','cwd','python','platform','start_utc','end_utc','elapsed_seconds','exit_code','output']}
  if gate in ['targeted','full']:
   gates[gate].update(counts=counts(row),deselected=row['deselected'],skips=[r for r in row['test_reports'] if r['outcome']=='skipped'])
 cov=read(LOGS/(label+'-full-coverage.json'));acov=next(v for k,v in cov['files'].items() if k.replace('\\','/').endswith('track_a/raw_archive.py'))
 matrix.append({'label':label,'commands':gates,'coverage':cov['totals'],'archive_coverage':acov['summary'],
  'archive_missing_lines':acov['missing_lines'],'sqlite_resource_warning_lines':(LOGS/(label+'-full.txt')).read_text().count('ResourceWarning: unclosed database')})
control.save('current-runtime-matrix.json',matrix)
red=read(LOGS/'win314-red.json');failed=[r for r in red['test_reports'] if r['outcome']=='failed']
assert red['exit_code']==1 and len(failed)==15
assert sum('DID NOT RAISE' in (r['reason'] or '') for r in failed)==8
assert sha(LOGS/'red-test-exact.py')==read(LOGS/'red-source-identity.json')['tests/unit/test_od04r_adversarial.py']['working']
control.save('red-classification.json',{
 'asserted_existing_defects':[r['nodeid'] for r in failed if 'DID NOT RAISE' in r['reason']],
 'additive_missing_api_not_defect_proof':[r['nodeid'] for r in failed if 'TypeError' in r['reason']],
 'unchanged_counterexamples':[r['nodeid'] for r in red['test_reports'] if r['outcome']=='passed'],
 'later_controlled_positive_tests':['test_r12_marker_link_failure_preserves_existing_evidence','test_r01_cli_count_and_read_only'],
 'red_snapshot':'Reconstructed from initial authored text after formatting/additional positive tests; exact SHA matches frozen pre-edit ledger'})
for kind in ['win','linux']:
 assert read(LOGS/(kind+'-process-result.json'))['passed']
 for suffix,rc in [('oracle-missing-negative',1),('oracle-moved-negative',1),('oracle-moved-positive',0)]:
  assert read(LOGS/(kind+'-'+suffix+'.json'))['exit_code']==rc
 raw=(LOGS/(kind+'-oracle-moved-positive.txt')).read_text();oracle=json.loads(raw[raw.index('{'):])
 assert oracle['observations']==18 and oracle['objects']==13
before=read(LOGS/'preservation-before.json');after=control.snapshot()
control.save('preservation-after.json',after)
changes=[p for p,v in before.items() if after.get(p)!=v]
assert sorted(changes)==['scripts/verify_raw_archive.py','src/omegadata/track_a/raw_archive.py'],changes
control.save('preservation-comparison.json',{'original_records':len(before),'changed_originals':changes,
 'unexpected_original_changes':[],'signing':'metadata only; content never opened, hashed or copied',
 'historical_evidence_unchanged':True,'source_identity_file_count':len(expected)})
control.save('before-after-file-ledger.json',{p:{'before':before.get(p),'after':after.get(p),'working_sha256':sha(ROOT/p)} for p in overlay})
policies=read(ROOT/'config/source_rights_policy.v1.json')['policies']
assert len(policies)==13 and all(p['status']=='PENDING_REVIEW' and not p['permitted_operations'] for p in policies)
control.save('production-policy-status.json',{'approved':0,'pending':13,'records':[{k:p[k] for k in ['source_key','status','revision_hash']} for p in policies]})
print(json.dumps({'reconciled':True,'original_records':len(before),'tested_files':len(expected),'matrix':[{r['label']:r['commands']['full']['counts']} for r in matrix]}))
