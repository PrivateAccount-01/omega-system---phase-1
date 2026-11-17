"""Trusted read-only code/evidence inspection; never opens original payloads."""
import ctypes
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
OLD = ROOT / 'docs/omegadata_v2/implementation/od05x/20261116T203751Z'
W = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'

def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def command(argv):
    start = datetime.now(UTC).isoformat()
    r = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return dict(argv=argv, start_utc=start, end_utc=datetime.now(UTC).isoformat(),
                exit_code=r.returncode, stdout=r.stdout, stderr=r.stderr)

history = {}
for label, folder in [('OD05W', W), ('OD05X', OLD)]:
    records = {}
    commands = []
    for p in sorted(folder.rglob('*')):
        if not p.is_file():
            continue
        raw = p.read_bytes()
        record = {'sha256': sha(raw), 'bytes': len(raw)}
        if p.suffix == '.json':
            body = json.loads(raw)
            record['shape'] = list(body)[:30] if isinstance(body, dict) else len(body)
            if isinstance(body, dict) and 'exit_code' in body:
                commands.append({'path': p.relative_to(folder).as_posix(),
                                 'exit_code': body['exit_code'],
                                 'counts': body.get('counts', {})})
        elif p.suffix in {'.py', '.md', '.txt'}:
            record['lines_read'] = len(raw.decode('utf-8-sig', errors='replace').splitlines())
        records[p.relative_to(folder).as_posix()] = record
    seal_name = 'evidence-sha256-final.json' if label == 'OD05X' else 'evidence-sha256.json'
    seal = json.loads((folder / seal_name).read_bytes())
    sealed = seal['files']
    for name, pin in sealed.items():
        expected = pin['sha256'] if isinstance(pin, dict) else pin
        assert records[name]['sha256'] == expected, (label, name)
    history[label] = {'files': records, 'sealed_verified': len(sealed),
                      'commands_reviewed': commands, 'evidence_class': 'ARCH'}
save('logs/prior-evidence-read-and-verified.json', history)

selection = json.loads((OLD / 'logs/reviewed-source-selection-v2.json').read_bytes())['files']
code_pins = {}
for row in selection:
    n = row['source']
    if n.startswith(('src/', 'scripts/', 'tests/', 'config/')) or n in {'pyproject.toml', 'README.md'}:
        code_pins[n] = sha((ROOT / n).read_bytes())
save('inputs/code-preservation-before.json', code_pins)

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
adv = ctypes.WinDLL('advapi32', use_last_error=True)
kernel.GetCurrentProcess.restype = ctypes.c_void_p
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
adv.OpenProcessToken.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
adv.GetTokenInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
                                   ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
handle = ctypes.c_void_p()
assert adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(handle))
token = {}
for label, number in [('is_appcontainer', 29), ('elevated', 20), ('integrity_level', 25)]:
    buf = ctypes.create_string_buffer(512)
    size = ctypes.c_uint()
    ok = adv.GetTokenInformation(handle, number, buf, len(buf), ctypes.byref(size))
    token[label] = {'query_success': bool(ok), 'native_error': 0 if ok else ctypes.get_last_error()}
    if ok and number != 25:
        token[label]['value'] = ctypes.cast(buf, ctypes.POINTER(ctypes.c_uint)).contents.value
kernel.CloseHandle(handle)
exports = {}
for dll, names in {'advapi32': ['CreateRestrictedToken', 'IsTokenRestricted'],
                   'kernel32': ['CreateJobObjectW', 'SetProcessMitigationPolicy', 'GetFileInformationByHandleEx'],
                   'userenv': ['CreateAppContainerProfile']}.items():
    lib = ctypes.WinDLL(dll)
    exports[dll] = {n: hasattr(lib, n) for n in names}
ps = "$ErrorActionPreference='Continue'; [pscustomobject]@{OS=(Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OperatingSystemSKU);Computer=(Get-CimInstance Win32_ComputerSystem | Select-Object HypervisorPresent);CPU=(Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled,SecondLevelAddressTranslationExtensions,VMMonitorModeExtensions);VMCommands=@(Get-Command WindowsSandbox.exe,Get-VM,VBoxManage.exe,vmrun.exe -ErrorAction SilentlyContinue | Select-Object Name,Source);HyperVModule=@(Get-Module -ListAvailable Hyper-V | Select-Object Name,Version);VMService=@(Get-Service vmms -ErrorAction SilentlyContinue | Select-Object Name,Status)} | ConvertTo-Json -Depth 5"
os_query = command(['powershell', '-NoProfile', '-Command', ps])
win311 = json.loads((W / 'logs/win311-r3-accepted-environment.txt').read_bytes())['executable']
runtimes = {}
for label, exe in [('win314', sys.executable), ('win311', win311)]:
    runtimes[label] = command([exe, '-B', '-c', 'import sys,importlib.metadata,json; print(json.dumps({"version":sys.version,"executable":sys.executable,"packages":sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())}))'])
record = {'utc': datetime.now(UTC).isoformat(), 'platform': platform.platform(),
          'os_query': os_query, 'sandbox_executable': shutil.which('WindowsSandbox.exe'),
          'native_token': token, 'native_exports_supported_not_proven': exports,
          'approved_VM_configuration': 'NOT_SUPPLIED', 'VM_files_searched': False,
          'private_VM_directories_inspected': False,
          'worker_enforcement_configured': False, 'native_denials_proven': False,
          'current_privilege_not_modified': True, 'host_features_changed': False,
          'offline_runtime_inventory': runtimes,
          'verdict': 'OS_ISOLATION_CAPABILITY_BLOCKED',
          'limits': 'VM inventory limited to installed command/module/service surfaces; no arbitrary private-directory search or assumed absence of all VMs'}
save('02_windows_capability_assessment.json', record)
print(json.dumps({'historical_files_read': {k: len(v['files']) for k,v in history.items()},
                  'seals_verified': {k: v['sealed_verified'] for k,v in history.items()},
                  'existing_code_pins': len(code_pins), 'os': json.loads(os_query['stdout']),
                  'sandbox': record['sandbox_executable'], 'token': token}))
