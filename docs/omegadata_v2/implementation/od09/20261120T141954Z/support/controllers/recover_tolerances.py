import hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent
name='src/omegadata/reconciliation/tolerances.py'
manifest=json.loads((B/'logs/mypy-2bcc16438d-manifest.json').read_bytes())
expected=next(r['sha256'] for r in manifest['files'] if r['path']==name)
source=B/'mypy-2bcc16438d/output/repo'/name
raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
current=B/'staged/repo'/name
with (B/'tolerance-empty-attempt.bin.txt').open('xb') as f:f.write(current.read_bytes())
s=raw.decode('utf-8-sig').replace('from datetime import datetime','from datetime import date, datetime')
assert 'class CalibrationSample:' in s and 'valid_at: date' in s
current.write_text(s)
with (B/'tolerance-recovery.json').open('x') as f:json.dump({'restored_from':str(source),'verified_source_sha256':expected,'recovered_sha256':hashlib.sha256(current.read_bytes()).hexdigest(),'original_checkout_touched':False},f,indent=2)
print('Restored sealed calibration module and required date import')
