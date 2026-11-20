import json,hashlib
from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');S=B/'staged2/repo';pins=json.loads((B/'upstream-manifest.json').read_bytes());rows=[]
terms=['get_universe','UniverseMembership','strict_universe','MembershipClaim','ISINMasterService','TradingCalendar','SymbolMap','InstrumentMaster']
for n,pin in pins.items():
 if not n.endswith('.py'):continue
 raw=(S/n).read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 body=raw.decode('utf8')
 if any(t in body for t in terms) or n in ['scripts/backfill_pit_universe.py','src/omegadata/domain.py']:
  rows.append({'path':n,'sha256':pin,'lines':len(body.splitlines()),'hits':[{'line':i+1,'text':line.strip()} for i,line in enumerate(body.splitlines()) if any(t in line for t in terms)]})
(B/'source-audit.json').write_text(json.dumps(rows,indent=2));print(json.dumps({'files_read':len(rows),'paths':[r['path'] for r in rows]}))
