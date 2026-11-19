import hashlib,json,subprocess
from pathlib import Path
P=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
B=Path('/home/parilrupani/omega-od07-20261119T171019Z')
E=P/'delivery/docs/omegadata_v2/implementation/od06-final/20261118T075140Z'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'evidence-sha256.json')=='d0f6f03834b48037d924507435aa027122f3c4d1403ba0476bc1a146d9e655e9'
seal=json.loads((E/'evidence-sha256.json').read_bytes())
read=[]
for n,r in seal['files'].items():
 assert not Path(n).is_absolute() and '..' not in Path(n).parts
 p=E/n;raw=p.read_bytes();assert len(raw)==r['bytes'] and sha(p)==r['sha256'];raw.decode('utf-8');read.append({'path':n,**r})
(B/'upstream-evidence-read.json').write_text(json.dumps(read,indent=2))
# Reuse exact, reviewed OS-isolated canonical stage; no original checkout source discovery.
(B/'bootstrap.py').write_text((P/'bootstrap.py').read_text().replace(str(P),str(B)))
r=subprocess.run(['/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',str(B/'bootstrap.py')],capture_output=True,text=True)
assert r.returncode==0,r.stdout+r.stderr
S=B/'staged2/repo';m=json.loads((E/'01_integrated_code_manifest.json').read_bytes())['combined_delivery'];assert len(m)==16
for row in m:
 n=row['path'];src=E/'code'/n;dst=S/n
 assert sha(src)==row['after_sha256']
 if row['before_sha256']:assert sha(dst)==row['before_sha256']
 else:assert not dst.exists()
for row in m:
 dst=S/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((E/'code'/row['path']).read_bytes());assert sha(dst)==row['after_sha256']
(B/'adoption.json').write_text(json.dumps({'reviewed_HEAD':'47b7f2c5859e36bc40c5970c2316eef3d28211e8','files':m,'sealed_upstream_files_verified':len(read),'original_checkout_accessed':False},indent=2))
v=(P/'run.py').read_text().replace('4e663af492a96a3ff36d61a47c1e213bbf6cd740','47b7f2c5859e36bc40c5970c2316eef3d28211e8')
v=v.replace("NEW=[", "NEW=[")
# Allow exactly explicit new OD07 module/test paths; all previous inputs remain pinned.
new=['src/omegadata/adjustments/'+n+'.py' for n in ['__init__','contracts','factors','temporal','chains','compatibility','repository']]+['tests/unit/test_od07_adjustments.py']
v=v.replace("(B/'logs').mkdir", "NEW += "+repr(new)+"\n(B/'logs').mkdir")
a=v.index("        old=json.loads(");z=v.index("        inventory={",a)
v=v[:a]+'''        old=json.loads(Path('/home/parilrupani/omega-od06-final-20261118T075140Z/runtime-inventory.json').read_bytes())
        expected=Counter(n.split('[',1)[0] for n in old)
        classes={n.split('[',1)[0]:c for n,c in old.items()}
        newnodes=[r['nodeid'] for r in worker['collected'] if r['nodeid'].startswith('tests/unit/test_od07_adjustments.py::')]
        assert Counter(r['nodeid'].split('[',1)[0] for r in worker['collected'] if r['nodeid'] not in newnodes)==expected,'OLD_INVENTORY_CHANGED'
        frozen=json.loads((B/'reviewed-new-tests.json').read_bytes())
        assert sorted(newnodes)==sorted(frozen),'NEW_TEST_INVENTORY_NOT_REVIEWED'
        for n in newnodes:classes[n.split('[',1)[0]]='A'
'''+v[z:]
(B/'run.py').write_text(v)
w=(P/'final_worker.py').read_text().replace("'foundation'}", "'foundation', 'od07'}")
w=w.replace("    if job=='foundation':", "    if job=='od07':\n        args += ['--confcutdir','/work/repo/tests/unit','tests/unit/test_od07_adjustments.py']\n    elif job=='foundation':")
(B/'final_worker.py').write_text(w)
for n in ['static_ruff.py','fix_ruff.py']:(B/n).write_text((P/n).read_text().replace(str(P),str(B)))
print(json.dumps({'adopted':len(m),'seal_verified':len(read),'workspace':str(S)}))
