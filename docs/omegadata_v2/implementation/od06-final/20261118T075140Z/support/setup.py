import hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');P=Path('/home/parilrupani/omega-od06-20261117T205524Z');F=Path('/home/parilrupani/omega-od05-final-20261117T201612Z')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# All earlier evidence reads are limited by their sealed inventories.
read=[]
for root,pin,sealname in [(P/'delivery/docs/omegadata_v2/implementation/od06/20261117T205524Z','fa6bff81a34a2699f478475a96c80b12c910e624e97c6ae8761bcdd2281168d2','evidence-sha256.json'),(Path('/mnt/e/omega system - phase 1/docs/omegadata_v2/implementation/od05-final/20261117T201612Z'),'47ad3392051d3a867d8e0786e505522fca7a0067ec045e043d5de65659b0250d','evidence-sha256-final.json')]:
 assert sha(root/sealname)==pin
 seal=json.loads((root/sealname).read_bytes())
 for n,row in seal['files'].items():
  assert '..' not in Path(n).parts and not Path(n).is_absolute()
  p=root/n;raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
  raw.decode('utf-8');read.append({'path':str(p),'sha256':row['sha256'],'bytes':len(raw)})
(B/'prior-evidence-read.json').write_text(json.dumps(read,indent=2))
bootstrap=(P/'bootstrap.py').read_text().replace(str(P),str(B))
(B/'bootstrap.py').write_text(bootstrap)
r=subprocess.run(['/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',str(B/'bootstrap.py')],capture_output=True,text=True)
assert r.returncode==0,r.stdout+r.stderr
S=B/'staged2/repo';E=P/'delivery/docs/omegadata_v2/implementation/od06/20261117T205524Z';m=json.loads((E/'12_preservation_manifest.json').read_bytes())['changes']
for row in m:
 n=row['path'];dst=S/n;src=E/'code'/n
 assert sha(src)==row['after_sha256']
 if row['before_sha256']:assert sha(dst)==row['before_sha256']
 else:assert not dst.exists()
for row in m:
 p=S/row['path'];p.write_bytes((E/'code'/row['path']).read_bytes());assert sha(p)==row['after_sha256']
(B/'adoption.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'reviewed_HEAD':'4e663af492a96a3ff36d61a47c1e213bbf6cd740','files':m,'scope':'Applied into one new data-free development snapshot only'},indent=2))
run=(P/'run.py').read_text().replace("S=B/'staged2/repo'","S=B/'staged2/repo'").replace("'07cca6def0748ed0903461d8614e4866959f036f'","'4e663af492a96a3ff36d61a47c1e213bbf6cd740'")
# Extend only the exact approved source ledger; reject other baseline changes.
run=run.replace("'src/omegadata/parsers/nse_cm.py'}","'src/omegadata/parsers/nse_cm.py','src/omegadata/identity.py','src/omegadata/identity_adapters.py','src/omegadata/session_calendar.py'}")
run=run.replace("'tests/unit/test_od06_contracts.py']","'tests/unit/test_od06_contracts.py','src/omegadata/identity_authority.py','src/omegadata/identity_repository.py','tests/unit/test_od06_foundation.py']")
run=run.replace("Path('/home/parilrupani/omega-od05-final-20261117T201612Z/runtime-inventory.json')", "Path('/home/parilrupani/omega-od06-20261117T205524Z/runtime-inventory.json')")
# Old OD06 inventory is already explicitly classified. Only new reviewed test file is extra.
start=run.index("        reviewed={")
end=run.index("        inventory={",start)
run=run[:start]+'''        newnodes=[r['nodeid'] for r in worker['collected'] if r['nodeid'].startswith('tests/unit/test_od06_foundation.py::')]
        assert Counter(r['nodeid'].split('[',1)[0] for r in worker['collected'] if r['nodeid'] not in newnodes)==expected,'OLD_INVENTORY_CHANGED'
        for n in newnodes:classes[n.split('[',1)[0]]='A'
'''+run[end:]
(B/'run.py').write_text(run)
w=(P/'final_worker.py').read_text().replace("'od06', 'od06perf'","'od06', 'od06perf', 'foundation'")
w=w.replace("if job=='od06':", "if job=='foundation':\n        args += ['--confcutdir','/work/repo/tests/unit','tests/unit/test_od06_foundation.py']\n    elif job=='od06':")
(B/'final_worker.py').write_text(w)
for n in ['static_ruff.py','fix_ruff.py']:
 (B/n).write_text((P/n).read_text().replace(str(P),str(B)))
print(json.dumps({'adopted_files':len(m),'prior_evidence_files_read':len(read),'workspace':str(S),'bootstrap_exit':r.returncode}))
