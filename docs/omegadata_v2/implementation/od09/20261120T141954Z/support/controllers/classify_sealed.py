import json,hashlib
from pathlib import Path
from collections import Counter
B=Path(__file__).resolve().parent
old=json.loads((B/'runtime-inventory.json').read_bytes())
with (B/'intermediate-36-stagea-inventory.json').open('x') as f:json.dump(old,f,indent=2)
record=json.loads((B/'logs/collection-9bd409d5ee-command.json').read_bytes());rows=record['worker_result']['collected'];nodes={r['nodeid'] for r in rows}
assert set(old).issubset(nodes)
extra=nodes-set(old);assert len(extra)==1 and all(n.startswith('tests/unit/test_od08_dependencies.py::') for n in extra)
new={**old,**{n:'A' for n in extra}}
assert all((new[r['nodeid']]=='C')==r['realdata'] for r in rows)
manifest=json.loads((B/'logs/collection-9bd409d5ee-manifest.json').read_bytes())
review={'collection':len(new),'classes':dict(Counter(new.values())),'inventory':new,'classification_scope':'Engineering non-market controls only; no authentic-source acceptance','test_source_hashes':{r['path']:r['sha256'] for r in manifest['files'] if r['path'].startswith('tests/')},'B':[n for n,v in new.items() if v=='B'],'C':[n for n,v in new.items() if v=='C']}
with (B/'sealed-classification.json').open('x') as f:json.dump(review,f,indent=2)
(B/'runtime-inventory.json').write_text(json.dumps(new,indent=2))
print(json.dumps({'collection':len(new),'classes':dict(Counter(new.values()))}))
