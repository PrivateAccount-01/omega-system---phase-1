"""Guarded metadata-only scan plus independent stdlib pin/count comparison."""
import hashlib
import importlib.util
import json
import os
import socket
import sys
import time
import tracemalloc
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'src'))
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata, ledger, scan_metadata

HERE=Path(__file__).resolve().parent
LOGS=HERE/'logs'
spec=importlib.util.spec_from_file_location('independent_oracle',ROOT/'tests/unit/od05t_metadata_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
groups=json.loads((LOGS/'frozen-metadata-pins.json').read_text())['groups']
started=datetime.now(UTC).isoformat()
results={}
denials=Counter()
active=False
allowed=[]

def deny(kind):
    denials[kind]+=1
    raise RuntimeError('OD05T_BLOCKED_'+kind)

def audit(event,args):
    if not active:return
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.posix_spawn'):
        deny('EGRESS_OR_PROCESS')
    if event=='open':
        path,mode,flags=args
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):deny('WRITE')
        if not isinstance(path,int):
            p=Path(os.fsdecode(path))
            if not p.name.endswith('.manifest.json') or not any(p.is_relative_to(root) for root in allowed):deny('NON_METADATA_READ')

sys.addaudithook(audit)
for label,group in groups.items():
    root=ROOT/group['repository_root'];allowed=[root]
    expected=tuple(tuple(r) for r in group['entries'])
    active=True
    tick=time.perf_counter();tracemalloc.start()
    try:
        independent=oracle.verify(root,expected)
        result=scan_metadata(root,approved_root=root,expected=ExpectedMetadata(expected))
        _,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop();active=False
    report=ledger(result)
    assert report['metadata_sha256']==independent==group['canonical_sha256']
    assert report['manifest_count']+report['malformed_count']==group['count']
    assert not result.errors
    report.pop('candidates')  # Aggregate evidence only; no raw metadata export.
    report['missing_information_counts']={field:sum(getattr(r,field) in (None,'MISSING','MISSING_INFORMATION') for r in result.rows)
        for field in ('payload_checksum_claim','artifact_relative_claim','permission_evidence','reference_evidence','reviewed_values')}
    report['rights_counts']=dict(Counter(r.rights_state for r in result.rows))
    report['independent_oracle_match']=True
    report['elapsed_seconds_including_oracle']=time.perf_counter()-tick
    report['peak_python_allocated_bytes']=peak
    results[label]=report

body={'argv':[sys.executable,'-B',str(Path(__file__))],'cwd':str(ROOT),'start_utc':started,
      'end_utc':datetime.now(UTC).isoformat(),'exit_code':0,'groups':results,'guard_denials':dict(denials),
      'payload_bytes_read':0,'market_rows_parsed':0,'market_rows_independently_verified':0,'official_reference_verified':0}
with (LOGS/'original-metadata-scan.json').open('x',encoding='utf-8') as f:json.dump(body,f,indent=2)
print(json.dumps({k:{'count':v['manifest_count'],'sha256':v['metadata_sha256'],'seconds':v['elapsed_seconds_including_oracle']} for k,v in results.items()}))
