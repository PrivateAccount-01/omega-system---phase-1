import hashlib,json,re
from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
receipt=json.loads(next((B/'staged2').glob('receipt-*.json')).read_bytes())
adoption=json.loads((B/'adoption.json').read_bytes())
upstream={r['path']:r['sha256'] for r in receipt['files']}
upstream.update({r['path']:r['after_sha256'] for r in adoption['files']})
read=[];hits=[]
names=['CorporateActionService','CorporateActionMatcher','PriceAdjustmentEngine','ManualReviewService','recompute_adjusted_series','refresh_demerger_actuals']
for n,pin in upstream.items():
 p=S/n
 if n.startswith(('src/','scripts/','tests/')) and n.endswith('.py'):
  raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
  body=raw.decode('utf-8');read.append({'path':n,'sha256':pin,'bytes':len(raw)})
  for i,line in enumerate(body.splitlines(),1):
   if any(name in line for name in names):hits.append({'path':n,'line':i,'text':line})
# Explicit preservation check over all previously authorized data-free input identities.
for n,pin in upstream.items():assert hashlib.sha256((S/n).read_bytes()).hexdigest()==pin,n
(B/'legacy-audit-source-inventory.json').write_text(json.dumps({'files_read':read,'caller_references':hits,'preserved_upstream_files':len(upstream),'scope':'Only receipt-pinned data-free code; no original checkout traversal'},indent=2))
(B/'upstream-manifest.json').write_text(json.dumps(upstream,indent=2))
print(json.dumps({'pinned_code_files_read':len(read),'caller_references':len(hits),'preserved_upstream_files':len(upstream)}))
