import hashlib,json,subprocess
from pathlib import Path
P=Path('/home/parilrupani/omega-od07-20261119T171019Z');B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z')
E=P/'delivery/docs/omegadata_v2/implementation/od07/20261119T171019Z'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(E/'evidence-sha256.json')=='a41c429361fa4971db6bd288eea0a124cf221d48f95bfd5e5f93173e83703b96'
read=[]
for n,row in json.loads((E/'evidence-sha256.json').read_bytes())['files'].items():
 assert not Path(n).is_absolute() and '..' not in Path(n).parts
 p=E/n;raw=p.read_bytes();assert len(raw)==row['bytes'] and sha(p)==row['sha256'];raw.decode('utf-8');read.append({'path':n,**row})
(B/'prior-evidence-read.json').write_text(json.dumps(read,indent=2))
(B/'bootstrap.py').write_text((P/'bootstrap.py').read_text().replace(str(P),str(B)))
r=subprocess.run(['/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',str(B/'bootstrap.py')],capture_output=True,text=True)
assert r.returncode==0,r.stdout+r.stderr
S=B/'staged2/repo';rows=json.loads((E/'14_preservation_manifest.json').read_bytes())['combined_delivery'];assert len(rows)==24
for row in rows:
 n=row['path'];dst=S/n;src=E/'code'/n;assert sha(src)==row['after_sha256']
 if row['before_sha256']:assert sha(dst)==row['before_sha256']
 else:assert not dst.exists()
for row in rows:
 dst=S/row['path'];dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((E/'code'/row['path']).read_bytes());assert sha(dst)==row['after_sha256']
(B/'adoption.json').write_text(json.dumps({'reviewed_HEAD':'91a0030094c0132b6a5586ce277ed1e56eb5e396','files':rows,'sealed_prior_files_verified':len(read),'original_checkout_integrated':False},indent=2))
v=(P/'run.py').read_text().replace('47b7f2c5859e36bc40c5970c2316eef3d28211e8','91a0030094c0132b6a5586ce277ed1e56eb5e396')
new=['src/omegadata/adjustments/'+n+'.py' for n in ['bound_contracts','bound_chain','admission']]+['tests/unit/test_od07_final.py']
v=v.replace("(B/'logs').mkdir",'NEW += '+repr(new)+"\n(B/'logs').mkdir")
a=v.index('        old=json.loads(');z=v.index('        inventory={',a)
v=v[:a]+'''        old=json.loads(Path('/home/parilrupani/omega-od07-20261119T171019Z/runtime-inventory.json').read_bytes())
        expected=Counter(n.split('[',1)[0] for n in old)
        classes={n.split('[',1)[0]:c for n,c in old.items()}
        newnodes=[r['nodeid'] for r in worker['collected'] if r['nodeid'].startswith('tests/unit/test_od07_final.py::')]
        assert Counter(r['nodeid'].split('[',1)[0] for r in worker['collected'] if r['nodeid'] not in newnodes)==expected,'OLD_INVENTORY_CHANGED'
        frozen=json.loads((B/'reviewed-new-tests.json').read_bytes())
        assert sorted(newnodes)==sorted(frozen),'UNREVIEWED_NEW_TESTS'
        for n in newnodes:classes[n.split('[',1)[0]]='A'
'''+v[z:]
(B/'run.py').write_text(v)
w=(P/'final_worker.py').read_text().replace("'od07'}", "'od07','od07final'}").replace("'od07',\n", "'od07', 'od07final',\n")
# Formatting changed the accepted-job set; require an exact known insertion.
if "'od07final'" not in w and '"od07final"' not in w:
 w=w.replace('"od07"}', '"od07", "od07final"}').replace('"od07",','"od07", "od07final",',1)
w=w.replace("    if job=='od07':", "    if job=='od07final':\n        args += ['--confcutdir','/work/repo/tests/unit','tests/unit/test_od07_final.py']\n    elif job=='od07':")
(B/'final_worker.py').write_text(w)
for n in ['static_ruff.py','format_code.py']:(B/n).write_text((P/n).read_text().replace(str(P),str(B)))
print(json.dumps({'adopted_files':len(rows),'prior_evidence_verified':len(read),'workspace':str(S)}))
