"""Mechanical gate; never supplies a human process exception."""
import hashlib
import json
import re
import subprocess
from datetime import UTC,datetime
from pathlib import Path
import control

ROOT=control.ROOT;HERE=control.HERE;LOGS=control.LOGS
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==control.HEAD
assert subprocess.check_output(['git','branch','--show-current']).decode().strip()=='feature/od01-source-rights'
assert not subprocess.check_output(['git','diff','--cached','--name-only']).strip()
changed=subprocess.check_output(['git','diff','--name-only']).decode().splitlines()
assert sorted(changed)==['scripts/verify_raw_archive.py','src/omegadata/track_a/raw_archive.py']
assert subprocess.check_output(['git','diff','--','src/omegadata/track_a/raw_archive.py','scripts/verify_raw_archive.py'])==(LOGS/'application.patch').read_bytes()
names=['00_PREFLIGHT_AND_IDENTITY.md','01_PRIOR_EVIDENCE_INDEPENDENT_RECONCILIATION.md',
 '02_THREAT_MODEL_AND_CONTRACT.md','03_NEW_RED_GREEN_TEST_MATRIX.md','04_CODE_REVIEW_AND_MINIMAL_DIFF.md',
 '05_PROCESS_CRASH_AND_INDEPENDENT_ORACLE.md','06_CROSS_PLATFORM_REGRESSION.md','07_RIGHTS_SECURITY_AND_REUSE_DECISION.md',
 '08_REMAINING_DEFECTS_AND_ROLLBACK.md','09_GATEKEEPER_VERDICT.md','10_OWNER_EXCEPTION_DECISION_REQUEST.md']
broken=[]
for name in names:
 text=(HERE/name).read_text(encoding='utf-8-sig')
 assert text.strip(),name
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http:','https:','#')):continue
  target=target.split('#')[0]
  # This exact self-reference is created exclusively after all checks below.
  if target=='logs/final-acceptance.json':continue
  if not (HERE/target).is_file():broken.append((name,target))
assert not broken,broken
matrix=read(LOGS/'reviewed-current-runtime-matrix.json')
expected_pass={'win314-reviewed':478,'win311-reviewed':478,'linux312-reviewed':486}
node_maps={}
for runtime in matrix:
 label=runtime['label'];full=read(LOGS/(label+'-full.json'))
 assert full['exit_code']==0 and full['call_counts']['passed']==expected_pass[label]
 assert len(full['deselected'])==4
 reports=full['test_reports'];node_maps[label]={r['nodeid']:r['outcome'] for r in reports}
 for module,n in [('test_od04_raw_archive.py',58),('test_od04r_adversarial.py',27)]:
  selected=[r for r in reports if module+'::' in r['nodeid'] and r['when']=='call']
  assert len(selected)==n and all(r['outcome']=='passed' for r in selected)
 for gate,row in runtime['commands'].items():
  assert row['exit_code']==0 and (LOGS/row['output']).is_file()
 cov=read(LOGS/(label+'-full-coverage.json'))
 acov=next(v for k,v in cov['files'].items() if k.replace('\\','/').endswith('track_a/raw_archive.py'))
 assert not [line for line in acov['missing_lines'] if line>=441], 'Uncovered new critical guard'
 assert 287 not in acov['missing_lines'], 'Walk error guard coverage review required'
for label in ['win314-reviewed','win311-reviewed']:
 for node,result in node_maps[label].items():
  if result=='skipped':assert node_maps['linux312-reviewed'][node]=='passed',node
for node,result in node_maps['linux312-reviewed'].items():
 if result=='skipped':assert node_maps['win314-reviewed'][node]=='passed' and node_maps['win311-reviewed'][node]=='passed'
symlinks=read(LOGS/'linux312-symlink-proof.json')
assert symlinks['exit_code']==0 and symlinks['call_counts']=={'passed':9}
actual=[r for r in symlinks['symlink_observations'] if r['is_actual_symlink']]
assert len(actual)==3 and all(r['outside_read_calls']==0 for r in actual)
identities=read(LOGS/'reviewed-final-tested-identities.json')
overlay=read(LOGS/'win314-reviewed-source.json')
for p,h in overlay.items():assert sha(ROOT/p)==h
for kind in ['win','linux']:
 result=read(LOGS/(kind+'-process-result.json'))
 assert result['passed'] and result['forced_crashes']==5
 for p,h in result['source_hashes'].items():assert sha(ROOT/p)==h
 for suffix,rc in [('oracle-missing-negative',1),('oracle-moved-negative',1),('oracle-moved-positive',0)]:
  assert read(LOGS/(kind+'-'+suffix+'.json'))['exit_code']==rc
 raw=(LOGS/(kind+'-oracle-moved-positive.txt')).read_text();oracle=json.loads(raw[raw.index('{'):])
 assert oracle['observations']==18 and oracle['objects']==13
before=read(LOGS/'preservation-before.json');after=control.snapshot()
deltas=[p for p,v in before.items() if after.get(p)!=v]
assert sorted(deltas)==sorted(changed)
policies=read(ROOT/'config/source_rights_policy.v1.json')['policies']
assert len(policies)==13 and all(p['status']=='PENDING_REVIEW' for p in policies)
assert not any(p['permitted_operations'] for p in policies)
oldgate=ROOT/'docs/omegadata_v2/implementation/od04/20261115T124835Z/09_gatekeeper_verdict.md'
assert 'OD04_BLOCKED' in oldgate.read_text()
assert sha(oldgate)==before[oldgate.relative_to(ROOT).as_posix()]['sha256']
red=read(LOGS/'red-classification.json')
assert len(red['asserted_existing_defects'])==8 and len(red['additive_missing_api_not_defect_proof'])==7
assert sha(LOGS/'red-test-exact.py')==read(LOGS/'red-source-identity.json')['tests/unit/test_od04r_adversarial.py']['working']
command_index={}
for p in sorted(LOGS.glob('*.json')):
 row=read(p)
 if isinstance(row,dict) and 'command' in row and 'exit_code' in row:
  command_index[p.name]={k:row.get(k) for k in ['command','cwd','start_utc','end_utc','elapsed_seconds','exit_code','output']}
control.save('command-index.json',command_index)
control.save('final-preservation.json',after)
control.save('report-sha256.json',{name:sha(HERE/name) for name in names})
control.save('final-acceptance.json',{'utc':datetime.now(UTC).isoformat(),'mechanical_checks_passed':True,
 'branch':'feature/od01-source-rights','head':control.HEAD,'index_empty':True,'changed_original_files':changed,
 'original_records_compared':len(before),'unexpected_original_changes':[],'old_evidence_unchanged':True,
 'required_reports':names,'missing_or_broken_links':broken,'tested_files':len(identities['win314']['files']),
 'per_runtime_full_pass':expected_pass,'all_final_acceptance_commands_exit_zero':True,'new_archive_tests':27,
 'original_archive_tests':58,'negative_first_asserted_defects':8,'missing_api_errors_not_defect_proof':7,
 'policy_pending':13,'policy_approved':0,'process_crashes_each_os':5,'independent_observations_objects_each_os':[18,13],
 'signing':'metadata unchanged; content never opened/hashed/copied','human_exception_approved':False,
 'gatekeeper':'OD04R_TECHNICALLY_REVERIFIED_PROCESS_EXCEPTION_PENDING','later_phase_authorized':False})
print('Final mechanical acceptance passed; human process exception remains NO.')
assert (LOGS/'final-acceptance.json').is_file()
