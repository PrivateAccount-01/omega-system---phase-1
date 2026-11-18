"""Exact data-free source coordinator. No mixed checkout, Git or cleanup."""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

B=Path(__file__).resolve().parent
S=B/'staged2/repo'
RUNTIME='/home/parilrupani/omega-od02v-37b3vimd/venv312'
BASE=json.loads(next((B/'staged2').glob('receipt-*.json')).read_bytes())
CHANGED={'src/omegadata/parsers/contracts.py','src/omegadata/parsers/dispatch.py','src/omegadata/parsers/nse_cm.py','src/omegadata/identity.py','src/omegadata/identity_adapters.py','src/omegadata/session_calendar.py'}
NEW=['src/omegadata/parsers/schema_catalog.py','scripts/od05_final_report.py','tests/unit/test_od05_final_contracts.py','src/omegadata/identity.py','src/omegadata/identity_adapters.py','src/omegadata/session_calendar.py','tests/unit/test_od06_contracts.py','src/omegadata/identity_authority.py','src/omegadata/identity_repository.py','tests/unit/test_od06_foundation.py','scripts/od06_database_experiments.py']
(B/'logs').mkdir(exist_ok=True)

def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2)

for job in sys.argv[1:]:
    tag=job+'-'+uuid.uuid4().hex[:10]
    base=B/tag;base.mkdir(mode=0o700)
    canary=base/'NON_MARKET_CANARY';canary.write_text('NON_MARKET_CANARY')
    rows=[]
    for entry in BASE['files']:
        n=entry['path']
        if n=='od05x_inputs/runtime-inventory.json' and (B/'runtime-inventory.json').exists():
            continue
        p=S/n;st=p.lstat()
        assert not p.is_symlink() and st.st_nlink==1
        raw=p.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
        assert n in CHANGED or digest==entry['sha256'],('UNREVIEWED_CHANGE',n)
        row={'path':n,'class':entry['class'],'host':str(p),'device':st.st_dev,
             'sha256':digest,'bytes':len(raw),'chunk_root':str(S),'sandbox_source':'/chunks/0/'+n}
        if n=='scripts/od05x_isolated_runner.py':
            row.pop('chunk_root');row.pop('sandbox_source')
        elif n=='scripts/od05x_worker_jobs.py':
            p=B/'final_worker.py';raw=p.read_bytes()
            row={'path':n,'class':'CODE','host':str(p),'device':p.lstat().st_dev,
                 'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        rows.append(row)
    additions={n:S/n for n in NEW if (S/n).exists()}
    if (B/'runtime-inventory.json').exists():additions['od05x_inputs/runtime-inventory.json']=B/'runtime-inventory.json'
    if (B/'report-input-index.json').exists():
        for n in json.loads((B/'report-input-index.json').read_bytes()):
            additions['final_inputs/'+n]=B/'report-inputs'/n
    for n,p in additions.items():
        raw=p.read_bytes();rows.append({'path':n,'class':'LOCAL_META' if n.endswith('.json') else 'CODE',
            'host':str(p),'device':p.lstat().st_dev,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    manifest=B/'logs'/(tag+'-manifest.json');policy=B/'logs'/(tag+'-policy.json')
    save(manifest,{'schema_version':'od05x.inputs/v1','file_count':len(rows),'files':rows})
    save(policy,{'runtime':RUNTIME,'job':job,'outside_canary':str(canary),
        'parent_namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','net','pid','user')}})
    argv=[RUNTIME+'/bin/python','-B',str(B/'launch_shared.py'),'launch',
          '--manifest',str(manifest),'--manifest-sha256',hashlib.sha256(manifest.read_bytes()).hexdigest(),
          '--policy',str(policy),'--output',str(base/'output')]
    start,tick=datetime.now(UTC).isoformat(),time.monotonic()
    result=subprocess.run(argv,capture_output=True,text=True,timeout=600)
    worker=None
    for name in ['job/result.json','job/coverage.json','native-probes.json','launcher-result.json','job/native-profile.json','job/identity-diagnostics.json']:
        p=base/'output'/name
        if p.exists():
            body=json.loads(p.read_bytes());save(B/'logs'/(tag+'-'+p.name),body)
            if name=='job/result.json':worker=body
    record={'argv':argv,'cwd':str(B),'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),
        'elapsed_seconds':time.monotonic()-tick,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
        'worker_result':worker,'job':job,'source_commit':'4e663af492a96a3ff36d61a47c1e213bbf6cd740',
        'source_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
    save(B/'logs'/(tag+'-command.json'),record)
    print(json.dumps({'job':job,'tag':tag,'exit':result.returncode,'counts':worker.get('counts') if worker else None,
        'failure_tail':worker.get('stdout_stderr','')[-1800:] if worker and result.returncode else result.stderr[-1000:]}),flush=True)
    if result.returncode==2 and worker is None:
        break
    if job=='collection' and worker and not worker['exit_code']:
        old=json.loads(Path('/home/parilrupani/omega-od06-20261117T205524Z/runtime-inventory.json').read_bytes())
        expected=Counter(n.split('[',1)[0] for n in old)
        classes={n.split('[',1)[0]:c for n,c in old.items()}
        newnodes=[r['nodeid'] for r in worker['collected'] if r['nodeid'].startswith('tests/unit/test_od06_foundation.py::')]
        assert Counter(r['nodeid'].split('[',1)[0] for r in worker['collected'] if r['nodeid'] not in newnodes)==expected,'OLD_INVENTORY_CHANGED'
        for n in newnodes:classes[n.split('[',1)[0]]='A'
        inventory={r['nodeid']:classes[r['nodeid'].split('[',1)[0]] for r in worker['collected']}
        assert all((inventory[r['nodeid']]=='C')==r['realdata'] for r in worker['collected'])
        target=B/'runtime-inventory.json'
        if target.exists():
            previous=json.loads(target.read_bytes());save(B/'logs'/(tag+'-previous-inventory.json'),previous)
            target.write_text(json.dumps(inventory,indent=2))
        else:save(target,inventory)
        save(B/'logs'/(tag+'-source-bound-inventory.json'),{'inventory':inventory,
            'test_hashes':{r['path']:r['sha256'] for r in rows if r['path'].startswith('tests/')}})
        print(json.dumps({'collection':len(inventory),'classes':dict(Counter(inventory.values()))}),flush=True)
