import json
import stat
from pathlib import Path
here = Path(__file__).parent
m = json.loads((here / 'logs/focused-f8f140ed7ef1-manifest.json').read_bytes())
bad = []
parents = set()
for row in m['files']:
    path = Path(row['host'])
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != row['bytes'] or info.st_dev != row['device']:
        bad.append({'path': row['path'], 'nlink': info.st_nlink, 'mode': info.st_mode,
                    'bytes': info.st_size, 'expected_bytes': row['bytes'], 'device': info.st_dev,
                    'expected_device': row['device']})
    parents.update(path.parents)
for parent in parents:
    s = parent.lstat()
    if not stat.S_ISDIR(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
        bad.append({'ancestor_class': str(parent), 'mode': s.st_mode})
with (here / 'logs/preflight-refusal-diagnosis.json').open('x') as f: json.dump(bad, f, indent=2)
print(json.dumps(bad[:20]))
