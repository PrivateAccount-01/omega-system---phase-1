"""Trusted OD05V controller; original market payloads are never read or copied."""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
LOGS = HERE / 'logs'
PRIOR = ROOT / 'docs/omegadata_v2/implementation/od05t/20261116T100613Z'
OWNED = ('src/omegadata/parsers/local_archive_presence.py', 'scripts/audit_local_archive_presence.py')
TESTS = ('tests/unit/test_od05v_local_presence.py', 'tests/unit/od05v_presence_oracle.py')

def save(name, body):
    with (LOGS/name).open('x', encoding='utf-8') as f: json.dump(body, f, indent=2)

def module(path):
    spec = importlib.util.spec_from_file_location('helper', path)
    obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj

def snapshot():
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for top in ('src','tests','scripts','config','docs/omegadata_v2')
              for p in (ROOT/top).rglob('*') if p.is_file() and '__pycache__' not in p.parts
              and HERE not in p.parents and p.relative_to(ROOT).as_posix() not in TESTS}
    metadata = {p.relative_to(ROOT).as_posix(): [p.lstat().st_size,p.lstat().st_mtime_ns]
                for top in ('data','artifacts') for p in (ROOT/top).rglob('*') if p.is_file()}
    metadata.update({p.name:[p.lstat().st_size,p.lstat().st_mtime_ns] for p in ROOT.glob('*.db')})
    return {'hashes':hashes,'data_artifact_db_metadata':metadata}

def setup():
    raise RuntimeError('Historical setup retired after copy-scope violation; use safe_copies.py. Existing snapshot and red evidence must not be regenerated.')
    LOGS.mkdir()
    assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip() == '0d43a43a7df2a997b394269d6a9ebf1e64a00de1'
    save('preservation-before.json', snapshot())
    groups = json.loads((PRIOR/'logs/frozen-metadata-pins.json').read_text())['groups']
    oracle = module(ROOT/TESTS[1])
    actual = oracle.observe(ROOT, groups)
    save('precode-independent-presence.json', {'utc':datetime.now(UTC).isoformat(), 'groups':actual})
    base = Path(tempfile.mkdtemp(prefix='omega-od05v-inputs-'))
    old = json.loads((PRIOR/'logs/private-input-location.json').read_text())['root']
    shutil.copytree(old, base/'od05t_inputs')
    (base/'presence.json').write_text(json.dumps(actual),encoding='utf-8')
    (base/'groups.json').write_text(json.dumps(groups),encoding='utf-8')
    # New copies contain code and authorized pre-existing regression fixtures only.
    copy = Path(tempfile.mkdtemp(prefix='omega-od05v-copy-'))/'repo'
    module(ROOT/'docs/omegadata_v2/implementation/od05r/20261116T084526Z/control.py').copy_sources(copy)
    shutil.copytree(base/'od05t_inputs', copy/'od05t_inputs')
    (copy/'od05v_inputs').mkdir()
    for name in ('presence.json','groups.json'): shutil.copyfile(base/name,copy/'od05v_inputs'/name)
    save('locations.json',{'copy':str(copy),'inputs':str(base),'original':str(ROOT)})
    runner = (PRIOR/'verification_runner.py').read_text().replace('db087fb9ee12887d3d9c787b797bb6968ad45440','0d43a43a7df2a997b394269d6a9ebf1e64a00de1')
    runner = runner.replace('if event=="open":\n', 'if event=="open":\n            if not isinstance(args[0], int) and str(args[0]).lower().endswith((".zip", ".csv", ".gz")) and "OD05V_ORIGINAL" in os.environ:\n                original_root=Path(os.environ["OD05V_ORIGINAL"])\n                if Path(os.fsdecode(args[0])).is_absolute() and Path(os.fsdecode(args[0])).is_relative_to(original_root / "data"):\n                    deny("ORIGINAL_MARKET_PAYLOAD_READ")\n')
    (HERE/'verification_runner.py').write_text(runner,encoding='utf-8')
    for name in ('environment_probe.py','guard_probe.py'): shutil.copyfile(PRIOR/name,HERE/name)
    print(copy)

if __name__ == '__main__':
    action = sys.argv[1]
    if action=='setup': setup()
    elif action=='freeze':
        assert all(not (ROOT/p).exists() for p in OWNED)
        save('precode-freeze.json',{'utc':datetime.now(UTC).isoformat(),'application_absent':True,
             'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in TESTS},
             'oracle':hashlib.sha256((LOGS/'precode-independent-presence.json').read_bytes()).hexdigest()})
    elif action=='sync':
        dest=Path(json.loads((LOGS/'locations.json').read_text())['copy'])
        for p in (*OWNED,*TESTS):
            if (ROOT/p).exists(): shutil.copyfile(ROOT/p,dest/p)
    elif action=='preserve':
        before=json.loads((LOGS/'preservation-before.json').read_text()); after=snapshot()
        changed={kind:[p for p,v in rows.items() if after[kind].get(p)!=v] for kind,rows in before.items()}
        save('preservation-after.json',{'changed':changed,'hashed_files':len(before['hashes']),
             'stat_records':len(before['data_artifact_db_metadata']),'payload_read_scope':'See setup-deviation.json; scanner is stat-only but historical setup read payloads','signing_content_read':False})
        assert not any(changed.values())
