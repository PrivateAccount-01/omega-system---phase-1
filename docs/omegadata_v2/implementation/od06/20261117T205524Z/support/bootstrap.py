import hashlib,json,os,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od06-20261117T205524Z')
S=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
R=S.parent/'receipt-80fcf7e771f25066af133c1848778ababdf4d3f4a8718fb03dd4fca5bd73ce77.json'
raw=R.read_bytes(); assert hashlib.sha256(raw).hexdigest()=='80fcf7e771f25066af133c1848778ababdf4d3f4a8718fb03dd4fca5bd73ce77'
receipt=json.loads(raw)
assert {p.relative_to(S).as_posix() for p in S.rglob('*') if p.is_file()}=={r['path'] for r in receipt['files']}
rows=[]
for r in receipt['files']:
 p=S/r['path']; st=p.lstat(); assert not p.is_symlink() and st.st_nlink==1
 raw=p.read_bytes(); assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 rows.append({**r,'host':str(p),'device':st.st_dev,'chunk_root':str(S),'sandbox_source':'/chunks/0/'+r['path']})
for row in rows:
 if row['path']=='scripts/od05x_isolated_runner.py':
  row.pop('chunk_root'); row.pop('sandbox_source')
manifest=B/'inputs2.json'; policy=B/'policy2.json'
manifest.write_text(json.dumps({'schema_version':'od05x.inputs/v1','file_count':len(rows),'files':rows},indent=2))
canary=B/'NON_MARKET_CANARY'; canary.write_text('NON_MARKET_CANARY')
policy.write_text(json.dumps({'runtime':'/home/parilrupani/omega-od02v-37b3vimd/venv312','job':'stage_only','outside_canary':str(canary),'parent_namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','net','pid','user')}}))
argv=['/home/parilrupani/omega-od02v-37b3vimd/venv312/bin/python','-B',str(S/'scripts/od05x_isolated_runner.py'),'launch','--manifest',str(manifest),'--manifest-sha256',hashlib.sha256(manifest.read_bytes()).hexdigest(),'--policy',str(policy),'--output',str(B/'staged2')]
start=datetime.now(UTC).isoformat(); tick=time.monotonic(); r=subprocess.run(argv,capture_output=True,text=True,timeout=120)
record={'argv':argv,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),'elapsed_seconds':time.monotonic()-tick,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'prior_receipt_sha256':'80fcf7e771f25066af133c1848778ababdf4d3f4a8718fb03dd4fca5bd73ce77','files':len(rows),'source_commit':'dd007c9e33d3d4ffaefe339cb766b428944bcdee','original_repository_mounted':False}
(B/'bootstrap-result2.json').write_text(json.dumps(record,indent=2)); print(json.dumps(record)); assert r.returncode==0
