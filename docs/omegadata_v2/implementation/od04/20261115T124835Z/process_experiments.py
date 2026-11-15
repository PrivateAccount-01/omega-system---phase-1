"""Independent processes, forced death, reference hashes and two publish pilots."""
from __future__ import annotations
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
copy=Path(sys.argv[1]).resolve()
label=sys.argv[2]
root=Path(tempfile.mkdtemp(prefix='omega-od04-process-',dir='/home/parilrupani' if os.name!='nt' else None)).resolve()
started=datetime.now(UTC).isoformat();platform_name=platform.platform()
rows=[]
issued=[]
worker=HERE/'process_worker.py'
worker_hash=hashlib.sha256(worker.read_bytes()).hexdigest()
def launch(mode,base,identity,phase):
    base.mkdir(exist_ok=True)
    command=[sys.executable,'-B',str(worker),str(copy),str(base),mode,identity,phase]
    issued.append(command)
    assert hashlib.sha256(worker.read_bytes()).hexdigest()==worker_hash
    tick=time.monotonic()
    process=subprocess.Popen(command,executable=sys.executable,cwd=copy,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    rows.append(dict(command=command,pid=process.pid,start_utc=datetime.now(UTC).isoformat(),tick=tick))
    return process
def finish(process,expected=0):
    output=process.communicate(timeout=20)[0].decode(errors='replace')
    row=next(r for r in rows if r['pid']==process.pid)
    row.update(exit_code=process.returncode,elapsed_seconds=time.monotonic()-row.pop('tick'),output=output)
    assert process.returncode==expected,(process.returncode,output)
    return output

# Parent's process audit permits exactly our documented executable and worker;
# child never permits process creation. All mutations stay in the private root.
def allow(args):
    argv=args[1]
    return (isinstance(argv,list) and len(argv)==9 and argv[:3]==[sys.executable,'-B',str(worker)]
            and argv[3]==str(copy) and Path(argv[4]).resolve().is_relative_to(root)
            and argv[5] in {'publish','crash','guard'}
            and len(argv[6])==32 and argv[7] in {'same','different','before_stage','after_stage','after_object','after_observation','before_commit'})

# There are eight argv entries (executable, -B, script, copy, root, mode, ID, phase).
def allowed(args):
    argv=args[1]
    return args[0]==sys.executable and any(argv==(subprocess.list2cmdline(command) if os.name=='nt' else command) for command in issued)
from process_guard import install
install(root,allowed)
try:
    finish(launch('guard',root/'guard','0'*32,'same'))
    for flavor in ('same','different'):
        base=root/flavor
        reader=launch('reader',base,'0'*32,flavor)
        workers=[launch('publish',base,f'{n:032x}',flavor) for n in range(1,4)]
        for process in workers:finish(process)
        finish(reader)
        assert len(list((base/'archive/commits').glob('*.json')))==3
        for path in (base/'archive/commits').glob('*.json'):
            commit=json.loads(path.read_text());obj=base/'archive'/commit['object']['relative_path']
            assert hashlib.sha256(obj.read_bytes()).hexdigest()==commit['object']['sha256']
            obs=base/'archive/observations'/(commit['observation_id']+'.json')
            assert hashlib.sha256(obs.read_bytes()).hexdigest()==commit['observation_sha256']
    # Reusing one operation ID with different candidates is never two successes.
    base=root/'conflict'
    workers=[launch('publish',base,'6'*32,phase) for phase in ['same','different']]
    for process in workers:process.wait(timeout=20)
    assert sorted(p.returncode for p in workers)==[0,2]
    for process in workers:finish(process,expected=process.returncode)
    assert len(list((base/'archive/commits').glob('*.json')))==1
    for phase in ('before_stage','after_stage','after_object','after_observation','before_commit'):
        base=root/phase
        process=launch('crash',base,'5'*32,phase)
        deadline=time.monotonic()+15
        while not (base/'ready').exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        assert (base/'ready').is_file(),phase
        process.kill()  # only the exact disposable worker we just created
        finish(process,expected=1 if os.name=='nt' else -9)
        assert not list((base/'archive/commits').glob('*.json'))
        finish(launch('publish',base,'5'*32,'same'))
    # Two viable local publish prototypes; never publish incomplete bytes.
    pilot=root/'pilots';pilot.mkdir()
    body=b'SYNTHETIC_TEST_ONLY'
    for strategy in ('hardlink','kernel_lock_rename'):
        stage=pilot/(strategy+'.stage');stage.write_bytes(body)
        with stage.open('r+b') as handle:os.fsync(handle.fileno())
        final=pilot/strategy
        if strategy=='hardlink':os.link(stage,final)
        else:
            with (pilot/'lock').open('a+b') as lock:
                lock.write(b'0');lock.flush();lock.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
                assert not final.exists();os.rename(stage,final)
        assert final.read_bytes()==body
    # Bounded local measurements; include physical hardlink-aware bytes.
    sys.path.insert(0,str(copy/'src'))
    from omegadata.track_a.raw_archive import RawArchive, ObservationRequest
    tick=time.perf_counter();inventory=RawArchive(root/'same/archive').recover_staging();recovery=time.perf_counter()-tick
    tracemalloc.start();tick=time.perf_counter()
    for path in (root/'same/archive/objects').rglob('*'):
        if path.is_file():assert hashlib.sha256(path.read_bytes()).hexdigest()==path.name
    read_seconds=time.perf_counter()-tick;peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    import importlib.util
    spec=importlib.util.spec_from_file_location('synthetic_fixtures',copy/'tests/conftest.py')
    fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
    provider=fixtures.synthetic_source_policy_provider.__wrapped__()
    obs=json.loads(next((root/'same/archive/observations').glob('*.json')).read_text())
    req=ObservationRequest.model_validate(obs['request'])
    measured=[]
    archive=RawArchive(root/'benchmark',policy_provider=provider)
    for n,size in enumerate([4096,65536,1048576]):
        payload=b'SYNTHETIC_TEST_ONLY'*(size//19+1);payload=payload[:size]
        tracemalloc.start();tick=time.perf_counter()
        first=archive.put(payload,req.model_copy(update={'operation_id':f'{100+n*2:032x}'}))
        put_seconds=time.perf_counter()-tick
        second=archive.put(payload,req.model_copy(update={'operation_id':f'{101+n*2:032x}'}))
        tick=time.perf_counter()
        actual,_=archive.read_verified(first.observation_id,req.source_key,req.business_date)
        assert actual==payload and first.object==second.object
        read_elapsed=time.perf_counter()-tick
        peak_bytes=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        measured.append(dict(bytes=len(payload),put_seconds=put_seconds,verified_read_seconds=read_elapsed,peak_bytes=peak_bytes))
    files=[p for p in (root/'benchmark').rglob('*') if p.is_file()]
    physical={}
    for p in files:
        stat=p.stat();physical[(stat.st_dev,stat.st_ino)]=stat.st_size
    result=dict(passed=True,root=str(root),python=sys.version,platform=platform_name,
        start_utc=started,end_utc=datetime.now(UTC).isoformat(),workers=rows,
        exact_worker_sha256=worker_hash,publish_strategies=['hardlink','kernel_lock_rename'],
        forced_crashes=5,reference_verified_commits=6,inventory=inventory,
        benchmark=dict(payload_bytes=len(b'SYNTHETIC_TEST_ONLY-raw'),observations=3,objects=1,duplicate_object_bytes_avoided=2*len(b'SYNTHETIC_TEST_ONLY-raw'),
            read_verify_seconds=read_seconds,recovery_seconds=recovery,tracemalloc_peak_bytes=peak,
            larger_samples=measured,larger_observations=6,larger_objects=3,
            logical_bytes=sum(p.stat().st_size for p in files),hardlink_unique_bytes=sum(physical.values())),
        source_hashes={p:hashlib.sha256((copy/p).read_bytes()).hexdigest() for p in ['src/omegadata/track_a/raw_archive.py','src/omegadata/track_a/download_manager.py']})
except BaseException as exc:
    import traceback
    result=dict(passed=False,root=str(root),workers=rows,error=repr(exc),traceback=traceback.format_exc())
# Parent guard remains active; emit bounded evidence to caller which logs it.
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
