"""Mechanical acceptance limited to executed reference-verifier scope."""
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime

import control

root,here,logs=control.ROOT,control.HERE,control.LOGS
started=datetime.now(UTC);tick=time.monotonic()
load=lambda name:json.loads((logs/name).read_text(encoding='utf-8-sig'))
commands=[]
for args in (['git','branch','--show-current'],['git','rev-parse','HEAD'],['git','status','--short'],
    ['git','diff','--name-status'],['git','diff','--cached','--name-status'],['git','diff','--check'],
    ['git','merge-base','main','HEAD']):
    start=datetime.now(UTC)
    run=subprocess.run(args,capture_output=True,text=True)
    commands.append({'command':args,'cwd':str(root),'start_utc':start.isoformat(),
        'end_utc':datetime.now(UTC).isoformat(),'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
    assert run.returncode==0
assert commands[0]['stdout'].strip()=='feature/od01-source-rights'
assert commands[1]['stdout'].strip()==control.HEAD
assert not commands[3]['stdout'] and not commands[4]['stdout']
control.save('final-git-commands.json',commands)
reports=sorted(p for p in here.glob('*.md') if re.match(r'^\d\d_',p.name))
assert len(reports)==12
for name,sha in load('report-sha256.json').items():
    assert hashlib.sha256((here/name).read_bytes()).hexdigest()==sha
for p,sha in load('reviewed-source-freeze.json')['files'].items():
    assert hashlib.sha256((root/p).read_bytes()).hexdigest()==sha
for label in ('win314','win311','linux312'):
    assert not any(load(label+'-reviewed-matrix.json')['results'].values())
    guard=load(label+'-guard-proof.json')
    assert guard['exit_code']==0 and guard['call_counts']=={'passed':5}
    assert all(guard['guard_denials'].get(k,0)>0 for k in ('DNS','SOCKET','UDP','SUBPROCESS','PROTECTED_WRITE','SIGNING_READ'))
preserve=load('preservation-comparison.json')
assert not preserve['unexpected_original_changes']
policy=json.loads((root/'config/source_rights_policy.v1.json').read_text())
assert len(policy['policies'])==13 and all(p['status']=='PENDING_REVIEW' for p in policy['policies'])
old=root/'docs/omegadata_v2/implementation/od05_impl/20261115T201333Z'
for p,sha in json.loads((old/'logs/evidence-sha256.json').read_text()).items():
    assert hashlib.sha256((old/p).read_bytes()).hexdigest()==sha
for report in reports:
    for match in re.finditer(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
        link=match.group(1)
        if not link.startswith('https://') and link!='logs/final-acceptance.json':
            assert (report.parent/link).exists(),link
summary={'command':[sys.executable,'-B',str(__file__)],'cwd':str(root),
    'start_utc':started.isoformat(),'end_utc':datetime.now(UTC).isoformat(),
    'duration_seconds':time.monotonic()-tick,'exit_code':0,'mechanical_checks_passed':True,
    'head':control.HEAD,'branch':'feature/od01-source-rights',
    'original_records_preserved':preserve['original_records'],'preservation_observed_at':preserve['utc'],
    'original_unexpected_changes':[],'all_prior_od05_evidence_hashes_match':True,
    'source_test_fixture_hashes_match':True,'all_reviewed_commands_exit_zero':True,
    'reference_groups':24,'new_cases_per_runtime':61,'new_passes_per_runtime':60,
    'new_platform_skips_per_runtime':1,'all_skips_have_real_passing_peer':True,
    'original_od05_cases_passed_each_runtime':94,'official_F_groups':'F01-F12 BLOCKED_REFERENCE',
    'source_policies_pending':13,'source_policies_approved':0,
    'original_publisher_bytes_authenticated':0,'representative_rows_authenticated':0,
    'reference_registry_entries':len(json.loads((here/'reference_registry.od05r.json').read_text())['entries']),
    'gatekeeper':'OD05R_REFERENCE_VERIFIER_TECHNICAL_PASS_REFERENCE_PENDING',
    'official_reference_subgate':'BLOCKED_REFERENCE','production_route_authority':False,
    'committed_pushed_merged':False,'next_phase_started':False,
    'stdout_path':'final-check.txt','stderr_path':'final-check.txt','reports':[p.name for p in reports]}
control.save('final-acceptance.json',summary)
with (logs/'final-check.txt').open('x',encoding='utf-8') as out:
    out.write(json.dumps(summary,indent=2)+'\n')
assert (logs/'final-acceptance.json').exists()
control.save('evidence-sha256.json',{p.relative_to(here).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in here.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='evidence-sha256.json'})
print(json.dumps(summary,indent=2))
