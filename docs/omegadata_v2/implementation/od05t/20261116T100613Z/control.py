"""Trusted evidence controller: metadata-only input and private disposable copies."""
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

ROOT=Path.cwd()
HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'
HEAD='db087fb9ee12887d3d9c787b797bb6968ad45440'
PRIOR=ROOT/'docs/omegadata_v2/implementation/od05r/20261116T084526Z'
SOURCES=('src/omegadata/parsers/archive_candidate_inventory.py','scripts/audit_existing_market_archive.py')
TESTS=('tests/unit/test_od05t_archive_inventory.py','tests/unit/od05t_metadata_oracle.py')

def save(name,body):
    with (LOGS/name).open('x',encoding='utf-8') as f:json.dump(body,f,indent=2)

def hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for top in ('src','tests','scripts','config','docs/omegadata_v2/implementation')
        for p in (ROOT/top).rglob('*') if p.is_file() and '__pycache__' not in p.parts
        and HERE not in p.parents}

def stat_data():
    # Never open source payloads, databases, release or signing material.
    paths=[p for top in ('data','artifacts') for p in (ROOT/top).rglob('*') if p.is_file()]
    paths+=list(ROOT.glob('*.db'))
    return {p.relative_to(ROOT).as_posix():[p.stat().st_size,p.stat().st_mtime_ns] for p in paths}

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def setup():
    LOGS.mkdir()
    commands=[]
    for args in (['git','branch','--show-current'],['git','rev-parse','HEAD'],['git','diff'],
                 ['git','diff','--cached'],['git','status','--short'],['git','merge-base','main','HEAD']):
        t=datetime.now(UTC).isoformat();r=subprocess.run(args,capture_output=True,text=True)
        commands.append(dict(argv=args,start_utc=t,end_utc=datetime.now(UTC).isoformat(),exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
        assert r.returncode==0
    assert commands[0]['stdout'].strip()=='feature/od01-source-rights' and commands[1]['stdout'].strip()==HEAD
    assert not commands[2]['stdout'] and not commands[3]['stdout']
    save('entry.json',commands)
    save('original-hashes.json',hashes());save('original-data-metadata.json',stat_data())
    oracle=load_module('oracle',ROOT/TESTS[1])
    base=Path(tempfile.mkdtemp(prefix='omega-od05t-inputs-'))
    groups={}
    for label,rel in [('seed','data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy'),('cache','data/raw/nse_equity_bhavcopy')]:
        root=ROOT/rel;entries=oracle.pins(root);assert entries
        groups[label]={'repository_root':rel,'entries':entries,'count':len(entries),'canonical_sha256':oracle.digest(entries)}
        for name,sha,length in entries:
            raw=(root/name).read_bytes();assert len(raw)==length and hashlib.sha256(raw).hexdigest()==sha
            target=base/label/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    save('frozen-metadata-pins.json',{'utc':datetime.now(UTC).isoformat(),'scope':'METADATA_ONLY_NOT_PUBLISHER_AUTHORITY','groups':groups})
    (base/'pins.json').write_text(json.dumps(groups),encoding='utf-8')
    save('private-input-location.json',{'root':str(base)})
    # Reuse reviewed guard and copy helper; do not invoke old snapshot (it hashes payloads).
    (HERE/'verification_runner.py').write_text((PRIOR/'verification_runner.py').read_text().replace('2326936860f64cadf4f4c24a968c073114598b26',HEAD),encoding='utf-8')
    shutil.copyfile(PRIOR/'environment_probe.py',HERE/'environment_probe.py')
    shutil.copyfile(PRIOR/'guard_probe.py',HERE/'guard_probe.py')
    print(json.dumps({k:{'count':v['count'],'canonical_sha256':v['canonical_sha256']} for k,v in groups.items()}))

def copies():
    old=load_module('old_control',PRIOR/'control.py')
    base=Path(json.loads((LOGS/'private-input-location.json').read_text())['root'])
    result={}
    for runtime in ('win314','win311'):
        root=Path(tempfile.mkdtemp(prefix='omega-od05t-copy-'))/'repo'
        old.copy_sources(root);shutil.copytree(base,root/'od05t_inputs');result[runtime]=str(root)
    save('copies.json',result);print(json.dumps(result))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='setup':setup()
    elif action=='copies':copies()
    elif action=='freeze':
        assert all(not (ROOT/p).exists() for p in SOURCES)
        save('precode-freeze.json',{'utc':datetime.now(UTC).isoformat(),'head':HEAD,'application_files_absent':True,'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in TESTS},'metadata_pin_sha256':hashlib.sha256((LOGS/'frozen-metadata-pins.json').read_bytes()).hexdigest()})
    elif action=='preserve':
        before=json.loads((LOGS/'original-hashes.json').read_text());after=hashes()
        changed=[p for p,h in before.items() if after.get(p)!=h and p not in TESTS]
        owned=[p for p,h in before.items() if after.get(p)!=h and p in TESTS]
        data_before=json.loads((LOGS/'original-data-metadata.json').read_text());data_after=stat_data()
        changed_data=[p for p,v in data_before.items() if data_after.get(p)!=v]
        save('preservation.json',{'original_hashed_files':len(set(before)-set(TESTS)),'changed':changed,'phase_owned_oracle_formatting_changes':owned,'original_data_metadata':len(data_before),'changed_data_metadata':changed_data,'payload_content_hashed':False,'signing_content_read':False})
        assert not changed and not changed_data
