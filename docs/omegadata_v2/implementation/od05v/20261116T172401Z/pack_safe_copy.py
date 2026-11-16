"""Pack software and manifest metadata to avoid slow per-file WSL mount copies."""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
root=Path(json.loads((LOGS/'safe-copy-location.json').read_text())['root'])
assert not (root/'data').exists()
dest=Path(tempfile.mkdtemp(prefix='omega-od05v-software-'))/'software-metadata-only.zip'
with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        if not path.is_file() or any(p in {'__pycache__','.mypy_cache','.ruff_cache'} for p in path.parts):continue
        name=path.relative_to(root).as_posix()
        assert not name.startswith(('data/','artifacts/'))
        archive.write(path,name)
with (LOGS/'software-pack.json').open('x',encoding='utf-8') as f:
    json.dump({'path':str(dest),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'contains_market_payloads':False},f,indent=2)
print(dest)
