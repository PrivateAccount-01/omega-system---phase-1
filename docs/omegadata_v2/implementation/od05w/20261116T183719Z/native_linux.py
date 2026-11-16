"""Unpack the pinned SOFTWARE/METADATA bundle under an active guard."""
import hashlib
import importlib.util
import json
import os
import stat
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('od05w_control',here/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
receipt=json.loads(Path(sys.argv[2]).read_text())
bundle=Path(sys.argv[1])
base=Path(tempfile.mkdtemp(prefix='omega-od05w-',dir='/home/parilrupani'))
state=control.activate_guard(here.parents[4],base,[bundle])
assert hashlib.sha256(bundle.read_bytes()).hexdigest()==receipt['sha256']
manifest={r['path']:r for r in receipt['files']}
with zipfile.ZipFile(bundle) as archive:
    assert set(archive.namelist())==set(manifest) and len(archive.namelist())==len(manifest)
    for item in archive.infolist():
        name=item.filename
        assert not name.startswith(('/','data/','artifacts/')) and '..' not in Path(name).parts
        assert item.file_size==manifest[name]['bytes'] and not stat.S_ISLNK(item.external_attr>>16)
        raw=archive.read(name)
        assert hashlib.sha256(raw).hexdigest()==manifest[name]['sha256']
        out=base/'repo'/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
groups=json.loads((base/'repo/od05v_inputs/groups.json').read_text())
canary=base/'NON_MARKET_CANARY'
old=json.loads((base/'repo/od05v_inputs/presence.json').read_text())
for label,group in groups.items():
    legacy={r['manifest']:r for r in old[label]}
    for name,sha,length in group['entries']:
        raw=(base/'repo/od05t_inputs'/label/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==sha and len(raw)==length
        meta=json.loads(raw)
        out=canary/group['repository_root']/name
        out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
        payload=canary/meta['artifact_path'].replace('\\','/')
        payload.touch()
        with payload.open('r+b') as stream:stream.truncate(meta['bytes_downloaded'])
        if not legacy[name]['present']:
            os.link(payload,payload.with_suffix('.NON_MARKET_CANARY'))
state['active']=False
control.save('linux-location.json',{'utc':datetime.now(UTC).isoformat(),'repo':str(base/'repo'),'base':str(base),'canary':str(canary),'classification':'NON_MARKET_CANARY','software_bundle_hash_verified':True,'original_market_payloads_copied':0,'guard_before_copy':True,'os_isolation':'NOT_ESTABLISHED'})
print(base/'repo')
