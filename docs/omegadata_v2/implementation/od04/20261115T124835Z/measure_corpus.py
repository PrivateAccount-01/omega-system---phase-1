"""Independent stdlib read-only verification of this run's synthetic process corpus."""
import hashlib
import json
import sys
from pathlib import Path

root=Path(sys.argv[1]).resolve()
assert root.name.startswith('omega-od04-process-')
assert root.is_dir(), 'MISSING_EVIDENCE_ROOT'
commits=list(root.rglob('commits/*.json'))
objects=[p for p in root.rglob('objects/sha256/*/*/*') if p.is_file()]
assert len(commits)==18 and len(objects)==13, 'INCOMPLETE_EVIDENCE_CORPUS'
identities=[]
for path in commits:
    commit=json.loads(path.read_text())
    archive=path.parent.parent
    observation=archive/'observations'/(commit['observation_id']+'.json')
    raw=observation.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==commit['observation_sha256']
    obs=json.loads(raw)
    assert obs['request']['source_mode']=='SYNTHETIC_TEST_ONLY'
    obj=archive/commit['object']['relative_path']
    data=obj.read_bytes()
    assert len(data)==commit['object']['size']
    assert hashlib.sha256(data).hexdigest()==commit['object']['sha256']
    identities.append({'case':archive.parent.name,'id':commit['observation_id'],'sha256':commit['object']['sha256']})
print(json.dumps({'observations':len(commits),'objects':len(objects),
    'objects_logical_bytes':sum(p.stat().st_size for p in objects),
    'reference_verified_all_commits':True,'identities':identities},indent=2))
