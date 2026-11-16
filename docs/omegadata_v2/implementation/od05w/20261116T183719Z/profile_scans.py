"""Bounded code/metadata measurements. Counts Python operations, not kernel traces."""
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

here=Path(__file__).resolve().parent
label,worktree,corpus=sys.argv[1:4]
worktree=Path(worktree);corpus=Path(corpus)
sys.path[:0]=[str(worktree/'src')]
from omegadata.parsers import local_archive_presence as p
from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
spec=importlib.util.spec_from_file_location('control',here/'control.py')
control=importlib.util.module_from_spec(spec);spec.loader.exec_module(control)
groups=json.loads((worktree/'od05v_inputs/groups.json').read_text())
allowed=[corpus/g['repository_root']/name for g in groups.values() for name,_,_ in g['entries']]
state=control.activate_guard(corpus,Path(tempfile.mkdtemp(prefix='omega-od05w-profile-')),allowed)
calls=Counter();oldstat=Path.lstat;oldscan=os.scandir;oldread=p.read_file
def lstat(*args,**kwargs):calls['Path.lstat']+=1;return oldstat(*args,**kwargs)
def scandir(*args,**kwargs):calls['os.scandir']+=1;return oldscan(*args,**kwargs)
def read(*args,**kwargs):calls['pinned_metadata_read']+=1;return oldread(*args,**kwargs)
Path.lstat=lstat;os.scandir=scandir;p.read_file=read
results={}
try:
    for root,g in groups.items():
        expected=ExpectedMetadata(tuple(tuple(r) for r in g['entries']))
        for version in (1,2):
            calls.clear();profile={};tick=time.monotonic()
            report=p.scan_presence(corpus,root,expected=expected,version=version,profile=profile)
            results[root+'-v'+str(version)]={'elapsed_seconds':time.monotonic()-tick,'python_operations':dict(calls),'profile':profile,'report_sha256':hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        calls.clear();tick=time.monotonic()
        observation=p.PresenceObservation(corpus,root,expected,version=1)
        for _ in range(5):observation.get()
        results[root+'-five-reused-observations']={'elapsed_seconds':time.monotonic()-tick,'scan_count':observation.scan_count,'python_operations':dict(calls),'metadata_reads_not_five_scans':calls['pinned_metadata_read']==len(expected.files)}
finally:
    Path.lstat=oldstat;os.scandir=oldscan;p.read_file=oldread;state['active']=False
control.save(label+'-scan-profile.json',{'class':'NON_MARKET_CANARY','corpus_market_rows':0,'measurements':'Python API operation counters, NOT a kernel syscall trace','results':results})
print(json.dumps(results,indent=2))
