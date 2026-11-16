"""Native Linux materialization of verified software/manifest metadata bundle."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
bundle=Path(sys.argv[1]);meta=json.loads((LOGS/'software-pack.json').read_text())
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==meta['sha256']
root=Path(tempfile.mkdtemp(prefix='omega-od05v-safe-',dir='/home/parilrupani'))/'repo';root.mkdir()
with zipfile.ZipFile(bundle) as archive:
    entries=archive.infolist()
    assert len(entries)<10000 and sum(e.file_size for e in entries)<100_000_000
    for entry in entries:
        p=PurePosixPath(entry.filename)
        assert not p.is_absolute() and '..' not in p.parts and p.parts[0] not in {'data','artifacts'}
        target=root/p;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f:f.write(archive.read(entry))
with (LOGS/'linux-location.json').open('x',encoding='utf-8') as f:
    json.dump({'root':str(root),'python':sys.executable,'version':sys.version,'original_archive_stat_root':'/mnt/e/omega system - phase 1','market_payloads_copied':0,'transport':'Verified software/manifest-only bundle'},f,indent=2)
print(root)
