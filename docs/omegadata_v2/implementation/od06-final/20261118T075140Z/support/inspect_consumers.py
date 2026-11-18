import ast,hashlib,json,re
from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
base=json.loads(next((B/'staged2').glob('receipt-*.json')).read_bytes())
paths={r['path'] for r in base['files']}
paths|={r['path'] for r in json.loads((B/'adoption.json').read_bytes())['files']}
paths|={'src/omegadata/identity_authority.py','src/omegadata/identity_repository.py','scripts/od06_database_experiments.py','scripts/od06_experiment_contract.py','tests/unit/test_od06_foundation.py','config/identity_authority_roots.v1.json'}
tokens=('ISINMasterService','PointInTimeUniverseManager','TradingCalendar','SymbolMap','InstrumentMaster')
refs=[];read=[]
for n in sorted(paths):
 if not n.endswith('.py'):continue
 raw=(S/n).read_bytes();text=raw.decode();ast.parse(text)
 read.append({'path':n,'sha256':hashlib.sha256(raw).hexdigest()})
 for line,body in enumerate(text.splitlines(),1):
  matched=[t for t in tokens if re.search(r'\b'+t+r'\b',body)]
  if matched:refs.append({'path':n,'line':line,'symbols':matched,'source':body.strip()})
for n in ['AGENTS.md','OMEGADATA_AGENTS.md','docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md']:
 raw=(Path('/mnt/e/omega system - phase 1')/n).read_bytes();raw.decode();read.append({'path':n,'sha256':hashlib.sha256(raw).hexdigest()})
json.dump({'scope':'Exact allowlisted source paths only, no mixed checkout scan','files_read':read,'references':refs,'legacy_consumers_modified':False},(B/'complete-consumer-inventory.json').open('x'),indent=2)
print(json.dumps({'code_files_read':len(read),'consumer_references':len(refs)}))
