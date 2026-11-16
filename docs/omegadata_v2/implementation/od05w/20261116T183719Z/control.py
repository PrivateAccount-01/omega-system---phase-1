"""OD05W controller. Never import historical setup/copy helpers."""
import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import runpy
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGS = HERE / 'logs'
ROOT = Path.cwd()
HEAD = 'c8e7ff974e6c4a471a002d4807f268dc5d0044b1'
PRIOR = ROOT / 'docs/omegadata_v2/implementation/od05v/20261116T172401Z'
PINFILE = ROOT / 'docs/omegadata_v2/implementation/od05t/20261116T100613Z/logs/frozen-metadata-pins.json'

class GuardDenied(PermissionError, RuntimeError):
    """OSError compatibility for import/config probes, legacy RuntimeError contract."""

def save(name, value):
    path = LOGS / name
    if path.exists():
        path = LOGS / (path.stem + '-' + datetime.now(UTC).strftime('%H%M%S%f') + path.suffix)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def activate_guard(original, writable, exact_reads=()):
    """Bootstrap guard BEFORE copy. Python boundary only; no OS claim."""
    original = original.absolute(); writable = writable.absolute()
    allowed = {os.path.normcase(str(p.absolute())) for p in exact_reads}
    allowed.add(os.path.normcase(str(HERE/'control.py')))
    boundaries = (original, HERE.parents[4])
    state = {'active': True, 'denials': Counter(), 'os_isolation': 'NOT_ESTABLISHED'}
    local = threading.local()
    original_connect = socket.socket.connect
    original_pair = socket.socketpair
    def deny(kind):
        state['denials'][kind] += 1
        raise GuardDenied('OD05W_BLOCKED_' + kind)
    def canonical(path):
        return Path(os.path.abspath(os.fsdecode(path)))
    def bounded(path):
        if isinstance(path, int): return
        if not canonical(path).resolve().is_relative_to(writable): deny('WRITE')
    def audit(event, args):
        if not state['active']: return
        if event in {'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.spawn'}: deny('SUBPROCESS')
        if event in {'socket.connect', 'socket.bind', 'socket.getaddrinfo', 'socket.sendto', 'socket.sendmsg'}:
            if not (os.name == 'nt' and getattr(local, 'pair', False)): deny('NETWORK')
        if event == 'open' and not isinstance(args[0], int):
            path = canonical(args[0]); flags = args[2]
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND): bounded(path)
            elif not path.is_relative_to(writable):
                if any(path.is_relative_to(boundary) for boundary in boundaries) and not path.is_relative_to(Path(sys.prefix)):
                    if path != original and os.path.normcase(str(path)) not in allowed: deny('ORIGINAL_READ')
                elif path.name.startswith('.env') or any(p in {'gnupg','private-keys-v1.d','openpgp-revocs.d'} for p in path.parts):
                    deny('PRIVATE_READ')
                runtime = any(path.is_relative_to(Path(prefix)) for prefix in {sys.prefix,sys.base_prefix})
                public_os = path == canonical(os.devnull) or str(path) in {'/etc/localtime','/etc/timezone','/etc/os-release','/etc/debian_version','/etc/mime.types','/dev/null'} or path.is_relative_to(Path('/usr/share/zoneinfo'))
                if not (runtime or public_os or path == original or os.path.normcase(str(path)) in allowed):
                    deny('UNLISTED_READ')
                if str(path) == os.environ.get('OD05W_FORBIDDEN_CANARY'): deny('READ_PROBE')
        if event in {'os.remove', 'os.rmdir', 'os.mkdir', 'os.chmod', 'os.utime'}: bounded(args[0])
        if event in {'os.rename', 'os.link'}: bounded(args[0]); bounded(args[1])
        if event == 'os.symlink': bounded(args[1])
        if event == 'sqlite3.connect' and args[0] != ':memory:': bounded(args[0])
    def connection(self, address):
        if os.name == 'nt' and getattr(local, 'pair', False): return original_connect(self, address)
        deny('NETWORK')
    def pair(*args, **kwargs):
        local.pair = True
        try: return original_pair(*args, **kwargs)
        finally: local.pair = False
    socket.socket.connect = connection
    socket.socket.connect_ex = lambda *a, **k: deny('NETWORK')
    socket.socket.sendto = lambda *a, **k: deny('NETWORK')
    socket.getaddrinfo = lambda *a, **k: deny('NETWORK')
    socket.socketpair = pair
    sys.addaudithook(audit)
    os.environ['OD05W_GUARD_ACTIVE'] = '1'
    return state

def sources():
    names = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    result = []
    for name in names:
        if not name: continue
        p = Path(name)
        if any(part.endswith('.egg-info') for part in p.parts): continue
        if p.parts[0] in {'src','scripts','tests','config'}:
            if p.suffix in {'.py','.json','.html','.css','.js','.md'}: result.append(name)
            else: raise ValueError('UNREVIEWED_TRACKED_EXTENSION ' + name)
    for name in ('pyproject.toml','README.md','tests/unit/test_od05w_engineering.py','scripts/od05w_safe_harness.py'):
        if (ROOT/name).exists() and name not in result: result.append(name)
    return sorted(result)

def setup():
    commands = []
    for args in (['git','branch','--show-current'],['git','rev-parse','HEAD'],['git','status','--porcelain=v1'],['git','diff'],['git','diff','--cached'],['git','merge-base','main','HEAD']):
        r = subprocess.run(args, capture_output=True, text=True)
        commands.append({'argv':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert commands[0]['stdout'].strip() == 'feature/od01-source-rights'
    assert commands[1]['stdout'].strip() == HEAD
    save('entry.json', commands)
    names = sources()
    preserve = names + [str(p.relative_to(ROOT)).replace('\\','/') for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    before = {n:sha(ROOT/n) for n in preserve}
    save('preservation-before.json', before)
    test = ROOT/'tests/unit/test_od05w_engineering.py'
    save('negative-first-freeze.json', {'utc':datetime.now(UTC).isoformat(),'files':{str(test.relative_to(ROOT)):sha(test)},'application_before':{n:sha(ROOT/n) for n in ('src/omegadata/parsers/local_archive_presence.py','scripts/audit_local_archive_presence.py')},'harness_absent':not (ROOT/'scripts/od05w_safe_harness.py').exists()})
    groups = json.loads(PINFILE.read_text())['groups']
    exact = [ROOT/n for n in names] + [PINFILE, PRIOR/'logs/setup-deviation.json']
    exact += [ROOT/g['repository_root']/n for g in groups.values() for n, _, _ in g['entries']]
    base = Path(tempfile.mkdtemp(prefix='omega-od05w-')).absolute()
    dest = base/'repo'; dest.mkdir()
    state = activate_guard(ROOT, base, exact)
    sys.dont_write_bytecode = True
    # Complete stat-only preflight before first copy/open of any intended input.
    for p in exact:
        info = p.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        for parent in p.parents:
            st = parent.lstat()
            assert not stat.S_ISLNK(st.st_mode) and not getattr(st,'st_file_attributes',0)&0x400
    copied=[]
    for name in names:
        data=(ROOT/name).read_bytes(); out=dest/name
        out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
        copied.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'class':'CODE_OR_EXISTING_REGRESSION_METADATA'})
    sys.path[:0]=[str(dest/'src'),str(dest/'tests/unit'),str(dest/'scripts')]
    from omegadata.parsers.local_archive_presence import scan_presence
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
    # One fresh bounded original scan, v1 baseline. No raw payload is opened.
    start=time.monotonic(); original={}
    for label,g in groups.items(): original[label]=scan_presence(ROOT,label,expected=ExpectedMetadata(tuple(tuple(r) for r in g['entries'])))
    elapsed=time.monotonic()-start
    original_rows=[r for v in original.values() for r in v['rows']]
    counts={'seed':len(original['seed']['rows']),'cache':len(original['cache']['rows']), 'present':0,'size_matched':0,'hardlinked':0,'single_link':0,'missing':0}
    stat_records={}
    for row in original_rows:
        path=ROOT/row['payload_relative']; st=path.lstat()
        regular=stat.S_ISREG(st.st_mode)
        counts['present']+=regular; counts['size_matched']+=regular and st.st_size==row['claimed_bytes']
        counts['hardlinked']+=regular and st.st_nlink!=1; counts['single_link']+=regular and st.st_nlink==1
        counts['missing']+=not regular
        stat_records[row['payload_relative']]=[st.st_size,st.st_mtime_ns,st.st_nlink,st.st_ino]
    inventory={'phase':'OD05W','utc':datetime.now(UTC).isoformat(),'evidence_class':'LOCAL_META','counts':counts,'elapsed_seconds':elapsed,'samples':{r['date']:r for r in original_rows if r['date'] in {'2011-06-22','2020-01-02','2024-07-23'}},'payload_bytes_read':0}
    (dest/'od05w_inputs').mkdir()
    (dest/'od05w_inputs/original-stat.json').write_text(json.dumps(inventory))
    (dest/'od05w_inputs/incident.json').write_bytes((PRIOR/'logs/setup-deviation.json').read_bytes())
    protected={n:before[n] for n in names if n.startswith(('config/','tests/fixtures/')) or n in {'tests/unit/test_adjustment_reference_corpus.py','tests/unit/test_universe_manager.py','src/omegadata/track_a/raw_archive.py','src/omegadata/track_a/source_rights.py','src/omegadata/track_a/source_registry.py','src/omegadata/track_a/acquisition.py'}}
    (dest/'od05w_inputs/preservation.json').write_text(json.dumps(protected))
    (dest/'od05t_inputs').mkdir(); (dest/'od05t_inputs/pins.json').write_text(json.dumps(groups))
    (dest/'od05v_inputs').mkdir(); (dest/'od05v_inputs/groups.json').write_text(json.dumps(groups))
    canary=base/'NON_MARKET_CANARY'; canary.mkdir()
    for label,g in groups.items():
        for name,digest,length in g['entries']:
            raw=(ROOT/g['repository_root']/name).read_bytes()
            assert len(raw)==length and hashlib.sha256(raw).hexdigest()==digest
            out=dest/'od05t_inputs'/label/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            out=canary/g['repository_root']/name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            meta=json.loads(raw);payload=canary/meta['artifact_path'].replace('\\','/');payload.touch()
            with payload.open('r+b') as f:f.truncate(meta['bytes_downloaded'])
            if (ROOT/meta['artifact_path'].replace('\\','/')).lstat().st_nlink!=1:
                os.link(payload,payload.with_suffix('.NON_MARKET_CANARY'))
            copied.append({'path':'od05t_inputs/'+label+'/'+name,'sha256':digest,'bytes':length,'class':'LOCAL_META'})
    from od05v_presence_oracle import observe
    (dest/'od05v_inputs/presence.json').write_text(json.dumps(observe(canary,groups)))
    # Attempt a forbidden original read before any pytest import.
    probes={}
    try:(ROOT/'data/OD05W_NO_PAYLOAD.zip').read_bytes()
    except (PermissionError, RuntimeError):probes['original_payload_open']='DENIED_BEFORE_OPEN'
    state['active']=False
    save('copy-manifest.json',{'utc':datetime.now(UTC).isoformat(),'files':copied,'file_count':len(copied),'bytes':sum(r['bytes'] for r in copied),'guard_active_before_copy':True,'os_isolation':'NOT_ESTABLISHED','denials':dict(state['denials']),'probes':probes})
    save('original-stat.json',inventory); save('original-v1-baseline.json',original)
    save('original-payload-stat-preservation.json',stat_records)
    save('locations.json',{'base':str(base),'repo':str(dest),'canary':str(canary)})
    print(dest)

def execute(label, root, module, args):
    root=Path(root).absolute();os.chdir(root)
    platform_info=platform.platform()
    base=Path(tempfile.mkdtemp(prefix='omega-od05w-run-')).absolute()
    external_probe=Path(tempfile.mkdtemp(prefix='omega-od05w-external-probe-'))/'NON_MARKET.canary'
    external_probe.write_bytes(b'NON_MARKET_CANARY')
    os.environ['OD05W_EXTERNAL_CANARY']=str(external_probe)
    os.environ.update({'TMP':str(base),'TEMP':str(base),'TMPDIR':str(base),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1','OD05W_CORPUS_CLASS':'NON_MARKET_CANARY','OD05W_FORBIDDEN_CANARY':str(base.parent/'OD05W_FORBIDDEN_READ_CANARY'),'OD05W_FORBIDDEN_WRITE':str(root/'OD05W_FORBIDDEN_WRITE_CANARY'),'COVERAGE_FILE':str(base/'coverage.db')})
    tempfile.tempdir=str(base);sys.dont_write_bytecode=True
    for k,v in {'DB_URL':'sqlite:///'+str(base/'default.sqlite'),'VERIFICATION_DB_URL':'sqlite:///'+str(base/'verification.sqlite'),'ALERT_WEBHOOK_URL':'','API_KEY':'SOFTWARE_TEST_ONLY','RELEASE_GPG_KEY_ID':''}.items():os.environ['OMEGA_'+k]=v
    for k in ('RAW_ROOT','SEED_RAW_ROOT','PARQUET_ROOT','REPORT_ROOT','REPROCESS_ROOT','RELEASE_ROOT','RELEASE_GPG_HOME'):os.environ['OMEGA_'+k]=str(base/k)
    os.environ['OD01R_DISPOSABLE_ROOT']=os.environ['OD02V_DISPOSABLE_ROOT']=str(base)
    os.environ['OD02V_WORKTREE']=str(root)
    os.environ['OD05W_ORIGINAL_BOUNDARY']=str(HERE.parents[4])
    os.environ['OD05V_ORIGINAL']=os.environ.get('OD05W_CANARY_ROOT',str(root.parent/'NON_MARKET_CANARY'))
    sys.path[:0]=[str(root/'src'),str(root/'scripts'),str(root/'tests/unit')]
    # Original root is never used as a runtime input; only this fresh code/metadata root.
    exact=[p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.json','.toml','.md','.html','.css','.js'}]
    canary=Path(os.environ['OD05V_ORIGINAL'])
    exact += [p for p in canary.rglob('*.manifest.json')]
    reports=[];collected=[];deselected=[]
    class Evidence:
        def pytest_collection_finish(self,session):
            collected.extend({'nodeid':i.nodeid,'realdata':i.get_closest_marker('realdata') is not None} for i in session.items)
        def pytest_runtest_logreport(self,report):
            if report.when=='call' or report.failed or report.skipped:
                reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'reason':str(report.longrepr) if report.failed or report.skipped else None})
        def pytest_deselected(self,items):deselected.extend(i.nodeid for i in items)
    identity={p.relative_to(root).as_posix():sha(p) for p in exact if p.is_relative_to(root) and (p.suffix=='.py' or p.is_relative_to(root/'config'))}
    started=datetime.now(UTC).isoformat();tick=time.monotonic();state=None
    with (LOGS/(label+'.txt')).open('x',encoding='utf-8') as out,contextlib.redirect_stdout(out),contextlib.redirect_stderr(out):
        try:
            if module=='pytest':
                state=activate_guard(root,base,exact)
                # Also deny all non-manifest canary opens outside writable root.
                def canary_guard(event,a):
                    if state['active'] and event=='open' and not isinstance(a[0],int):
                        p=Path(os.path.abspath(os.fsdecode(a[0])))
                        if p.is_relative_to(canary) and not p.name.endswith('.manifest.json'):
                            raise PermissionError('OD05W_CANARY_PAYLOAD_READ_DENIED')
                sys.addaudithook(canary_guard)
                import pytest
                if args and args[0]=='@A':
                    inventory=json.loads((root/'od05w_inputs'/os.environ.get('OD05W_INVENTORY','test-inventory.json')).read_text())
                    args=[n for n,c in inventory.items() if c=='A']+args[1:]
                extra=['-p','pytest_asyncio.plugin','-p','no:cacheprovider','--log-file',str(base/'pytest.log'),'--basetemp',str(base/'pytest')]
                if any(a.startswith('--cov=') for a in args):extra+=['-p','pytest_cov.plugin','--cov-report=json:'+str(base/'coverage.json')]
                code=int(pytest.main(args+extra,plugins=[Evidence()]))
            elif module=='environment':
                print(json.dumps({'executable':sys.executable,'version':sys.version,'platform':platform_info,'packages':sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())},indent=2))
                code=0
            else:
                env={**os.environ,'MYPY_CACHE_DIR':str(base/'mypy')}
                code=subprocess.run([sys.executable,'-B','-m',module,*args],stdout=out,stderr=subprocess.STDOUT,env=env).returncode
        except Exception:
            traceback.print_exc();code=1
        finally:
            if state:state['active']=False
    record={'argv':[sys.executable,'-B',str(HERE/'control.py'),'run',label,str(root),module,*args],'cwd':str(root),'python':sys.version,'platform':platform_info,'start_utc':started,'end_utc':datetime.now(UTC).isoformat(),'elapsed_seconds':time.monotonic()-tick,'exit_code':code,'test_reports':reports,'collected':collected,'deselected':deselected,'counts':dict(Counter(r['outcome'] for r in reports)),'source_identity':identity,'runner_sha256':sha(HERE/'control.py'),'guard':{'denials':dict(state['denials']),'os_isolation':state['os_isolation']} if state else 'STATIC_TOOL_ON_NEW_CODE_COPY'}
    if (base/'coverage.json').exists():save(label+'-coverage.json',json.loads((base/'coverage.json').read_text()))
    save(label+'.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in {'test_reports','collected','deselected','argv','source_identity'}},indent=2));print((LOGS/(label+'.txt')).read_text()[-2000:])
    return code

def final_copy():
    """Exercise the new production copy contract, not the bootstrap copier."""
    loc=json.loads((LOGS/'locations.json').read_text())
    source=Path(loc['repo'])
    base=Path(tempfile.mkdtemp(prefix='omega-od05w-final-')).absolute()
    sys.path[:0]=[str(source/'src'),str(source/'scripts')]
    import od05w_safe_harness as h
    names=[];approved={};expected={}
    for path in source.rglob('*'):
        if not path.is_file() or any(p in {'__pycache__','.mypy_cache','.ruff_cache'} for p in path.parts):continue
        name=path.relative_to(source).as_posix()
        classification=('CODE' if path.suffix=='.py' else 'STATIC_UI' if path.suffix in {'.html','.css','.js'} else 'DOCUMENTATION' if path.suffix=='.md' else 'STATIC_CONFIG' if path.suffix=='.toml' or name.startswith('config/') else 'EXISTING_REGRESSION_METADATA' if name.startswith('tests/fixtures/') else 'LOCAL_META')
        names.append(name);approved[name]=classification;expected[name]=sha(path)
    state=activate_guard(source,base,[source/n for n in names])
    def probe():
        try:(source/'data/OD05W_INJECTED_PAYLOAD.zip').read_bytes()
        except (PermissionError, RuntimeError):return True
        return False
    receipt={'active':True,'probe':probe,'os_isolation':'NOT_ESTABLISHED'}
    record=h.copy_exact(source,base/'repo',names,approved,guard=receipt,expected=expected)
    state['active']=False
    save('accepted-copy-manifest.json',record)
    save('final-location.json',{'repo':str(base/'repo'),'base':str(base),'canary':loc['canary']})
    print(base/'repo')

def inventory(collection_name='win314-reviewed-collection'):
    rows=json.loads((LOGS/(collection_name+'.json')).read_text())['collected']
    b={
      'tests/unit/test_adjustment_reference_corpus.py::test_reference_corpus_official_nse_source_pack_cases',
      'tests/unit/test_universe_manager.py::test_seed_pack_backfill_reproduces_reference_snapshots',
      'tests/unit/test_universe_manager.py::test_seed_pack_preserves_knowledge_vs_effective_date_semantics',
      'tests/unit/test_universe_manager.py::test_seed_pack_backfill_works_with_production_autoflush_setting'}
    assert b.issubset({r['nodeid'] for r in rows})
    result={r['nodeid']:'C' if r['realdata'] else 'B' if r['nodeid'] in b else 'A' for r in rows}
    save('test-dependency-inventory.json',{'utc':datetime.now(UTC).isoformat(),'nodes':result,'counts':dict(Counter(result.values())),'B_dependencies':{n:'Original corporate-action .bin and referenced market ZIP path identities' if 'adjustment' in n else 'Permitted cached symbol-to-ISIN mapping ZIP inputs' for n in b},'C_status':'BLOCKED_REAL_DATA','B_status':'BLOCKED_INPUT','classification_scope':'Existing code regression + nonfinancial metadata; existing synthetic regression contributes zero real-data acceptance'})
    loc=json.loads((LOGS/'locations.json').read_text())
    state=activate_guard(ROOT,Path(loc['base']),[])
    (Path(loc['repo'])/'od05w_inputs/test-inventory.json').write_text(json.dumps(result))
    bases={}
    for n,c in result.items():
        base=n.split('[',1)[0]
        bases.setdefault(base,{'class':c,'count':0})['count']+=1
    source=Path(loc['repo'])
    contract={'functions':bases,'source_hashes':{p.relative_to(source).as_posix():sha(p) for p in (source/'tests').rglob('*.py') if '__pycache__' not in p.parts}}
    (source/'od05w_inputs/test-contract.json').write_text(json.dumps(contract))
    state['active']=False
    print(Counter(result.values()))

def package():
    import zipfile
    loc=json.loads((LOGS/'locations.json').read_text())
    source=Path(loc['repo'])
    bundle_base=Path(tempfile.mkdtemp(prefix='omega-od05w-bundle-')).absolute()
    paths=[p for p in source.rglob('*') if p.is_file() and not any(n in {'__pycache__','.mypy_cache','.ruff_cache'} for n in p.parts)]
    # Only fresh current-phase code/metadata; no retained environment/data copies.
    assert not (source/'data').exists()
    state=activate_guard(source,bundle_base,paths)
    manifest=[]
    bundle=bundle_base/'reviewed-software-metadata.bundle'
    with zipfile.ZipFile(bundle,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in paths:
            name=path.relative_to(source).as_posix()
            assert path.suffix in {'.py','.json','.toml','.md','.html','.css','.js'}
            raw=path.read_bytes();z.writestr(name,raw)
            manifest.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
    state['active']=False
    # This SHA is the newly created SOFTWARE bundle, never an original market ZIP.
    save('software-bundle.json',{'path':str(bundle),'sha256':sha(bundle),'bytes':bundle.stat().st_size,'files':manifest,'market_payloads':0})
    print(bundle)

def original_v2():
    loc=json.loads((LOGS/'locations.json').read_text())
    native=Path(loc['repo'])
    sys.path[:0]=[str(native/'src')]
    groups=json.loads(PINFILE.read_text())['groups']
    exact=[ROOT/g['repository_root']/n for g in groups.values() for n,_,_ in g['entries']]
    base=Path(tempfile.mkdtemp(prefix='omega-od05w-stat-')).absolute()
    state=activate_guard(ROOT,base,exact)
    from omegadata.parsers.local_archive_presence import scan_presence
    from omegadata.parsers.archive_candidate_inventory import ExpectedMetadata
    reports={};profiles={}
    for label,g in groups.items():
        profile={}
        reports[label]=scan_presence(ROOT,label,expected=ExpectedMetadata(tuple(tuple(r) for r in g['entries'])),version=2,profile=profile)
        profiles[label]=profile
    state['active']=False
    save('original-v2-post.json',{'utc':datetime.now(UTC).isoformat(),'class':'LOCAL_META','reports':reports,'profiles':profiles,'guard':dict(state['denials']),'os_isolation':'NOT_ESTABLISHED'})
    print(json.dumps({k:v['counts'] for k,v in reports.items()},indent=2))

if __name__=='__main__':
    if sys.argv[1]=='setup':setup()
    elif sys.argv[1]=='final-copy':final_copy()
    elif sys.argv[1]=='inventory':inventory(sys.argv[2] if len(sys.argv)>2 else 'win314-reviewed-collection')
    elif sys.argv[1]=='package':package()
    elif sys.argv[1]=='original-v2':original_v2()
    elif sys.argv[1]=='run':raise SystemExit(execute(sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5:]))
    elif sys.argv[1]=='sync':
        location=json.loads((LOGS/'locations.json').read_text())
        paths=['src/omegadata/parsers/local_archive_presence.py','scripts/audit_local_archive_presence.py','scripts/od05w_safe_harness.py','tests/unit/test_od05v_local_presence.py','tests/unit/test_od05w_engineering.py']
        state=activate_guard(ROOT,Path(location['base']),[ROOT/p for p in paths])
        records=[]
        for name in paths:
            raw=(ROOT/name).read_bytes();target=Path(location['repo'])/name
            target.write_bytes(raw);records.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
        state['active']=False
        save('sync.json',{'utc':datetime.now(UTC).isoformat(),'files':records,'guard_before_copy':True})
