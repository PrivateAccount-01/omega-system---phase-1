import hashlib,json,subprocess
from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');P=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');E=P/'delivery/docs/omegadata_v2/implementation/od07-final/20261119T175351Z'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'evidence-sha256.json')=='1b0039f2696287f71dd77a73d0720f1498702d46886dfd529c6751d681e91249'
read=[]
for n,row in json.loads((E/'evidence-sha256.json').read_bytes())['files'].items():
 p=E/n;raw=p.read_bytes();assert len(raw)==row['bytes'] and sha(p)==row['sha256'];raw.decode('utf8');read.append({'path':n,**row})
(B/'prior-evidence-read.json').write_text(json.dumps(read,indent=2))
(B/'bootstrap.py').write_text((P/'bootstrap.py').read_text().replace(str(P),str(B)))
r=subprocess.run(['/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',str(B/'bootstrap.py')],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
S=B/'staged2/repo';rows=json.loads((E/'14_preservation_manifest.json').read_bytes())['combined_delivery'];assert len(rows)==28
for row in rows:
 n=row['path'];dst=S/n;assert sha(E/'code'/n)==row['after_sha256']
 if row['before_sha256']:assert sha(dst)==row['before_sha256']
 else:assert not dst.exists()
for row in rows:
 dst=S/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((E/'code'/row['path']).read_bytes());assert sha(dst)==row['after_sha256']
(B/'adoption.json').write_text(json.dumps({'HEAD':'d81657666238bf20f093cec54bb9cb3788feea99','files':rows,'prior_sealed_files_verified':len(read),'original_checkout_integrated':False},indent=2))
base=json.loads(next((B/'staged2').glob('receipt-*.json')).read_bytes());pins={r['path']:r['sha256'] for r in base['files']};pins.update({r['path']:r['after_sha256'] for r in rows});(B/'upstream-manifest.json').write_text(json.dumps(pins,indent=2))
v=(P/'run.py').read_text().replace(str(P),str(B)).replace('91a0030094c0132b6a5586ce277ed1e56eb5e396','d81657666238bf20f093cec54bb9cb3788feea99')
v=v.replace("(B/'logs').mkdir", "NEW += ['src/omegadata/universe/'+n+'.py' for n in ['__init__','contracts','temporal','eligibility','snapshots','repository','compatibility']] + ['tests/unit/test_od08_universe.py']\n(B/'logs').mkdir")
a=v.index('        old=json.loads(');z=v.index('        inventory={',a)
v=v[:a]+'''        old=json.loads(Path('/home/parilrupani/omega-od07-final-20261119T175351Z/runtime-inventory.json').read_bytes())
        expected=Counter(n.split('[',1)[0] for n in old);classes={n.split('[',1)[0]:c for n,c in old.items()}
        newnodes=[r['nodeid'] for r in worker['collected'] if r['nodeid'].startswith('tests/unit/test_od08_universe.py::')]
        assert Counter(r['nodeid'].split('[',1)[0] for r in worker['collected'] if r['nodeid'] not in newnodes)==expected,'OLD_INVENTORY_CHANGED'
        frozen=json.loads((B/'reviewed-new-tests.json').read_bytes());assert sorted(newnodes)==sorted(frozen),'UNREVIEWED_TESTS'
        for n in newnodes:classes[n.split('[',1)[0]]='A'
'''+v[z:]
(B/'run.py').write_text(v)
w=(P/'final_worker.py').read_text().replace("'od07final'}","'od07final','od08'}").replace("    if job=='od07final':","    if job=='od08':\n        args += ['--confcutdir','/work/repo/tests/unit','tests/unit/test_od08_universe.py']\n    elif job=='od07final':")
assert "'od08'" in w;(B/'final_worker.py').write_text(w)
(B/'static_ruff.py').write_text((P/'static_ruff.py').read_text().replace(str(P),str(B)))
print(json.dumps({'adopted':len(rows),'prior_evidence_read':len(read),'baseline_files':len(pins),'workspace':str(S)}))
