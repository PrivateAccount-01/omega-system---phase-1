"""Trusted fixed offline worker; no arbitrary expressions or executable arguments."""
from __future__ import annotations
import importlib.util
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
copy,base,mode,identity,phase=sys.argv[1:]
base=Path(base).resolve()
assert mode in {'publish','crash','guard','reader'}
assert len(identity)==32 and all(x in '0123456789abcdef' for x in identity)
assert phase in {'same','different','before_stage','after_stage','after_object','after_observation','before_commit'}
os.environ['TMP']=os.environ['TEMP']=os.environ['TMPDIR']=str(base)
os.environ['OMEGA_DB_URL']='sqlite:///'+str(base/'worker.sqlite')
os.environ['OMEGA_RELEASE_GPG_HOME']=str(base/'unused-gpg')
os.chdir(copy)
sys.path.insert(0,str(Path(copy)/'src'))
from process_guard import install
install(base)
from omegadata.track_a.raw_archive import RawArchive, ObservationRequest, ArchiveError
spec=importlib.util.spec_from_file_location('synthetic_fixtures',Path(copy)/'tests/conftest.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
provider=fixtures.synthetic_source_policy_provider.__wrapped__()

def fault(at):
    if mode=='crash' and at==phase:
        (base/'ready').write_text(at)
        while True:time.sleep(.05)

archive=RawArchive(base/'archive',policy_provider=provider,fault=fault)
req=ObservationRequest(source_key='NSE_EQUITY_BHAVCOPY',business_date=date(2026,4,10),
    observed_at=datetime(2026,11,15,12,tzinfo=UTC),operation_id=identity,source_era='2019_present',
    source_mode='SYNTHETIC_TEST_ONLY',parser_schema='test/v1',payload_state='HTTP_RECEIVED',
    transport='HTTPX',original_url='https://example.invalid/file',final_url='https://example.invalid/file',
    origin_ref='SYNTHETIC_TEST_ONLY')
if mode=='reader':
    deadline=time.monotonic()+15
    seen=set()
    while time.monotonic()<deadline and len(seen)<3:
        for path in (base/'archive/commits').glob('*.json'):
            actual,obs=archive.read_verified(path.stem,req.source_key,req.business_date)
            expected=b'SYNTHETIC_TEST_ONLY-raw' if phase=='same' else path.stem.encode()
            assert actual==expected
            seen.add(path.stem)
        time.sleep(.005)
    assert len(seen)==3
    print('CONCURRENT_READER_VERIFIED_THREE_COMMITS',flush=True)
elif mode=='guard':
    import socket
    import subprocess
    for call in [lambda:socket.getaddrinfo('example.invalid',443),
                 lambda:socket.socket().connect(('127.0.0.1',1)),
                 lambda:subprocess.run([sys.executable,'--version']),
                 lambda:Path(copy,'must-not-write').write_text('no')]:
        try:call()
        except RuntimeError:pass
        else:raise AssertionError('guard did not refuse')
    print('FOUR_GUARD_NEGATIVES_PASS',flush=True)
else:
    body=b'SYNTHETIC_TEST_ONLY-raw' if phase!='different' else identity.encode()
    try:
        result=archive.put(body,req)
        actual,obs=archive.read_verified(identity,req.source_key,req.business_date)
        assert actual==body
        print(result.model_dump_json(),flush=True)
    except ArchiveError as exc:
        print(exc.reason_code,flush=True)
        raise SystemExit(2)

