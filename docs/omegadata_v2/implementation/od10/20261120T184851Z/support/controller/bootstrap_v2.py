import hashlib,json,os,subprocess,time
from pathlib import Path
from datetime import UTC,datetime
B=Path(__file__).resolve().parent
P=Path('/home/parilrupani/omega-od09-20261120T141954Z')
S=P/'staged/repo'
D=P/'delivery/docs/omegadata_v2/implementation/od09/20261120T141954Z'
def save(name,value):
 with (B/name).open('x') as f:json.dump(value,f,indent=2)
seal_raw=(D/'evidence-final-sha256.json').read_bytes()
assert hashlib.sha256(seal_raw).hexdigest()=='361c9c46d5cd2a016afe6cee92e06ae207caec1175d53e575b1608bbf967ec79'
seal=json.loads(seal_raw)
for name,row in seal['files'].items():
 p=D/name;st=p.lstat();assert p.is_file() and not p.is_symlink() and st.st_nlink==1
 raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
pres=json.loads((D/'20_preservation_manifest.json').read_bytes())
for row in pres['combined_delivery']:
 assert hashlib.sha256((S/row['path']).read_bytes()).hexdigest()==row['after_sha256'],row['path']
assert len(pres['combined_delivery'])==51
pins=json.loads((P/'final-source-pins-final.json').read_bytes())
assert len(pins)==3852
receipt=json.loads(next((P/'staged').glob('receipt-*.json')).read_bytes())
classes={r['path']:r['class'] for r in receipt['files']}
rows=[]
for name,pin in pins.items():
 p=S/name;st=p.lstat();assert p.is_file() and not p.is_symlink() and st.st_nlink==1
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin,name
 rows.append({'path':name,'class':classes.get(name,'STATIC_CONFIG' if name.endswith('.json') else 'CODE'),'host':str(p),'device':st.st_dev,'sha256':pin,'bytes':len(raw),'chunk_root':str(S),'sandbox_source':'/chunks/0/'+name})
 if name=='scripts/od05x_isolated_runner.py':
  rows[-1].pop('chunk_root');rows[-1].pop('sandbox_source')
base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
for row in pres['combined_delivery']:
 q=base/row['path'];h=row.get('before_sha256')
 if h is None:assert not q.exists(),row['path']
 else:assert hashlib.sha256(q.read_bytes()).hexdigest()==h,row['path']
save('upstream-pins.json',pins)
save('upstream-adoption.json',{'reviewed_head':'641f1ebc54d4619e77f36afb4821b5986ef3a756','seal':hashlib.sha256(seal_raw).hexdigest(),'verified_sealed_files':len(seal['files']),'combined_files':pres['combined_delivery'],'snapshot_files':len(pins),'original_checkout_accessed':False})
save('inputs.json',{'schema_version':'od05x.inputs/v1','file_count':len(rows),'files':rows})
canary=B/'NON_MARKET_CANARY';canary.write_text('NON_MARKET_CANARY')
rt='/home/parilrupani/omega-od02v-37b3vimd/venv312'
save('policy.json',{'runtime':rt,'job':'stage_only','outside_canary':str(canary),'parent_namespaces':{n:os.readlink('/proc/self/ns/'+n) for n in ('mnt','net','pid','user')}})
argv=[rt+'/bin/python','-B',str(S/'scripts/od05x_isolated_runner.py'),'launch','--manifest',str(B/'inputs.json'),'--manifest-sha256',hashlib.sha256((B/'inputs.json').read_bytes()).hexdigest(),'--policy',str(B/'policy.json'),'--output',str(B/'staged')]
a=datetime.now(UTC).isoformat();tick=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True,timeout=180)
save('bootstrap-command.json',{'argv':argv,'start':a,'end':datetime.now(UTC).isoformat(),'seconds':time.monotonic()-tick,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
print(json.dumps({'workspace':str(B),'adopted':51,'files':len(rows),'exit':r.returncode,'stderr':r.stderr[-2000:]}));assert r.returncode==0
