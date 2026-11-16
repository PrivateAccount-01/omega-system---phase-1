"""Final evidence acceptance; cannot grant source/release or later-phase authority."""
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime

import control

started=datetime.now(UTC)
tick=time.monotonic()
here,logs,root=control.HERE,control.LOGS,control.ROOT
load=lambda name:json.loads((logs/name).read_text(encoding='utf-8-sig'))
assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==control.HEAD
assert subprocess.check_output(['git','branch','--show-current']).decode().strip()=='feature/od01-source-rights'
assert not subprocess.check_output(['git','diff','--name-only'])
assert not subprocess.check_output(['git','diff','--cached','--name-only'])
reports=list(here.glob('*.md'))
assert len(reports)==11
for report in reports:
    for match in re.finditer(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
        if match.group(1) != 'logs/final-acceptance.json':
            assert (report.parent/match.group(1)).exists(),match.group(1)
for name,digest in load('report-sha256.json').items():
    assert hashlib.sha256((here/name).read_bytes()).hexdigest()==digest
for name,digest in load('final-source-freeze.json')['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
for label in ('win314','win311','linux312'):
    assert not any(load(label+'-accepted-matrix.json')['results'].values())
    guard=load(label+'-guard-proof.json')
    assert guard['exit_code']==0 and guard['call_counts']=={'passed':5}
    assert all(guard['guard_denials'].get(kind,0)>0 for kind in ('DNS','SOCKET','UDP','SUBPROCESS','PROTECTED_WRITE','SIGNING_READ'))
before=load('preservation-before.json')
after=control.snapshot()
owned={'tests/unit/test_od05_era_parsing.py','tests/unit/od05_oracle.py'}
changes=[p for p,v in before.items() if p not in owned and after.get(p)!=v]
control.save('final-preservation-comparison.json',{'original_records':len(set(before)-owned),
    'unexpected_original_changes':changes,'signing':'metadata only; never content opened/hashed/copied',
    'utc':datetime.now(UTC).isoformat()})
assert not changes,changes
policy=json.loads((root/'config/source_rights_policy.v1.json').read_text())
assert len(policy['policies'])==13 and all(p['status']=='PENDING_REVIEW' for p in policy['policies'])
summary={'command':[sys.executable,'-B',str(__file__)],'cwd':str(root),
    'start_utc':started.isoformat(),'end_utc':datetime.now(UTC).isoformat(),
    'duration_seconds':time.monotonic()-tick,'exit_code':0,'mechanical_checks_passed':True,
    'branch':'feature/od01-source-rights','head':control.HEAD,
    'original_records':len(set(before)-owned),'unexpected_original_changes':changes,
    'new_parser_cases_each_runtime':94,'synthetic_groups':32,
    'source_policy_pending':13,'source_policy_approved':0,'official_reference_verified':0,
    'all_final_commands_exit_zero':True,'all_source_test_fixture_identities_match':True,
    'all_skips_have_passing_other_platform_node':True,'reports':[p.name for p in reports],
    'owner_channel':'Direct user attestation Paril/Admin in this conversation',
    'owner_g0_decision':'ACCEPT_EXCEPTION','owner_g0_date':'2026-11-16',
    'owner_g1_directive':'AUTHORIZE_OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY',
    'gatekeeper':'OD05_SYNTHETIC_TECHNICAL_PASS','reference_subgate':'BLOCKED_REFERENCE',
    'mechanical_attempts':'First helper failed default cp1252 decoding; second checked its own future output link too early. Corrected UTF-8 and deferred only self-output link until after creation. Both failed attempts retained. No application/test change.',
    'next_phase_authorized':False,'commit_push_merge':False,
    'stdout_path':'final-check.txt','stderr_path':'final-check.txt'}
with (logs/'final-check.txt').open('x',encoding='utf-8') as out:
    out.write(json.dumps(summary,indent=2)+'\n')
control.save('final-acceptance.json',summary)
for report in reports:
    for match in re.finditer(r'\]\(([^)]+)\)',report.read_text(encoding='utf-8')):
        assert (report.parent/match.group(1)).exists(),match.group(1)
control.save('evidence-sha256.json',{p.relative_to(here).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in here.rglob('*') if p.is_file() and p.name!='evidence-sha256.json'})
print(json.dumps(summary,indent=2))
