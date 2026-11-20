import json,collections
from pathlib import Path
B=Path(__file__).parent
p=sorted((B/'logs').glob('collection-*-command.json'),key=lambda p:p.stat().st_mtime)[-1]
r=json.loads(p.read_bytes());assert r['exit_code']==0
old=json.loads((B/'runtime-inventory.json').read_bytes());new={}
for item in r['worker_result']['collected']:
 n=item['nodeid']
 if n in old:new[n]=old[n]
 else:
  assert n.startswith('tests/unit/test_od10_canonical_storage.py::') and not item['realdata'],n
  new[n]='A'
assert set(old)<=set(new) and collections.Counter(new.values())['B']==4 and collections.Counter(new.values())['C']==4
(B/'runtime-inventory-before-final.json').write_text(json.dumps(old,indent=2))
(B/'runtime-inventory.json').write_text(json.dumps(new,indent=2))
print(dict(collections.Counter(new.values())))