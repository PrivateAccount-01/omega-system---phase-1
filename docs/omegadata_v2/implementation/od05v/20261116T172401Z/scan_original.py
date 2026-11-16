"""Guarded original-manifest/stat scan against separately frozen oracle."""
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
sys.path.insert(0,str(ROOT/'src'))
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
from omegadata.parsers.local_archive_presence import scan_presence

groups=json.loads((ROOT/'docs/omegadata_v2/implementation/od05t/20261116T100613Z/logs/frozen-metadata-pins.json').read_text())['groups']
frozen=json.loads((LOGS/'precode-independent-presence.json').read_text())['groups']
active=False;attempts=[];allowed_descriptors=set()
original_open=os.open
def tracked_open(path,flags,*args,**kwargs):
    fd=original_open(path,flags,*args,**kwargs)
    if active:allowed_descriptors.add(fd)
    return fd
os.open=tracked_open
def audit(event,args):
    if not active:return
    if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.posix_spawn'}:raise RuntimeError('EGRESS_DENIED')
    if event=='open':
        path,mode,flags=args
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise RuntimeError('WRITE_DENIED')
        if isinstance(path,int):
            if path not in allowed_descriptors:raise RuntimeError('DESCRIPTOR_READ_DENIED')
            return
        p=Path(os.fsdecode(path))
        attempts.append(p.relative_to(ROOT).as_posix())
        if not p.name.endswith('.manifest.json') or not any(p.is_relative_to(ROOT/g['repository_root']) for g in groups.values()):raise RuntimeError('NON_METADATA_READ_DENIED')
sys.addaudithook(audit)
results={};started=datetime.now(UTC).isoformat()
for label,group in groups.items():
    active=True;tick=time.monotonic()
    try:report=scan_presence(ROOT,label,expected=ExpectedMetadata(tuple(tuple(r) for r in group['entries'])))
    finally:active=False
    expected=frozen[label]
    assert report['manifest_count']==len(expected)
    assert report['counts']['present']==sum(r['present'] for r in expected)
    assert report['counts']['size_matches_manifest']==sum(r['size_match'] for r in expected)
    report['elapsed_seconds']=time.monotonic()-tick
    report['frozen_oracle_match']=True
    results[label]=report
with (LOGS/'original-presence-scan.json').open('x',encoding='utf-8') as f:
    json.dump({'command':[sys.executable,'-B',str(Path(__file__))],'cwd':str(ROOT),'start_utc':started,'end_utc':datetime.now(UTC).isoformat(),
               'exit_code':0,'manifest_read_attempts':len(attempts),'only_manifest_reads':True,'payload_bytes_read':0,'groups':results},f,indent=2)
print(json.dumps({k:v['counts'] for k,v in results.items()}))
