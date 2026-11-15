"""Read-only clean-room source identity; excludes data and environment files."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
rows={}
for part in ['src','scripts','tests','config']:
 for p in sorted((root/part).rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts:
   rows[p.relative_to(root).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
for part in ['pyproject.toml','README.md']:
 rows[part]=hashlib.sha256((root/part).read_bytes()).hexdigest()
print(json.dumps(rows,indent=2))
