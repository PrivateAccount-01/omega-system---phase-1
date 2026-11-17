"""Collect only SHA-verified, phase-authored code from this phase's data-free copy."""
import hashlib
import json
from pathlib import Path
here = Path(__file__).parent
root = here.parents[4]
out = here / 'source-snapshots'
out.mkdir()
old = json.loads((here / '11_preservation_and_source_hashes.json').read_bytes())['new_source_pins']
command = json.loads((here / 'logs/A-26809b35f963-command.json').read_bytes())
base = Path(command['argv'][command['argv'].index('--output') + 1]) / 'repo'
assert str(base).startswith('/home/parilrupani/omega-od05x-')
for name, expected in old.items():
    path = base / name
    assert path.lstat().st_nlink == 1 and not path.is_symlink()
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    with (out / (expected + '.py')).open('xb') as f: f.write(raw)
for name in old:
    raw = (root / name).read_bytes()
    expected = hashlib.sha256(raw).hexdigest()
    path = out / (expected + '.py')
    if path.exists():
        assert path.read_bytes() == raw
    else:
        with path.open('xb') as f: f.write(raw)
print(json.dumps({'code_snapshots': len(list(out.glob('*.py'))),
                  'scope': 'Only four phase-authored code/test paths, earlier and final source revisions; no market/key content'}))
