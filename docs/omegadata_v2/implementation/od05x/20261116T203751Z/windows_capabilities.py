"""Read-only Windows capability assessment and no-staging refusal checks."""
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path.cwd()
previous = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z/logs'
native = ctypes.WinDLL('advapi32', use_last_error=True)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
token = ctypes.c_void_p()
kernel.GetCurrentProcess.restype = ctypes.c_void_p
native.OpenProcessToken.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
native.GetTokenInformation.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
kernel.CloseHandle.argtypes = [ctypes.c_void_p]
assert native.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token))
appcontainer = ctypes.c_uint()
returned = ctypes.c_uint()
ok = native.GetTokenInformation(token, 29, ctypes.byref(appcontainer), 4, ctypes.byref(returned))
kernel.CloseHandle(token)
record = {'utc': datetime.now(UTC).isoformat(), 'platform': platform.platform(),
          'WindowsSandbox': shutil.which('WindowsSandbox.exe'),
          'current_token_is_AppContainer': bool(appcontainer.value) if ok else 'QUERY_FAILED',
          'dedicated_VM_operator_configuration': 'NOT_SUPPLIED',
          'restricted_token_ACL_egress_child_policy': 'NOT_ESTABLISHED',
          'API_availability_is_not_enforcement': True,
          'configuration_changes_or_privileged_installation': False,
          'verdict': 'OS_ISOLATION_CAPABILITY_BLOCKED', 'runtime_refusals': []}
for label, exe in [('win314', sys.executable), ('win311', json.loads((previous / 'win311-r3-accepted-environment.txt').read_text())['executable'])]:
    base = Path(tempfile.mkdtemp(prefix='omega-od05x-refusal-'))
    argv = [exe, '-B', str(ROOT / 'scripts/od05x_isolated_runner.py'), 'launch',
            '--manifest', str(base / 'not-opened.json'), '--manifest-sha256', '0' * 64,
            '--policy', str(base / 'not-opened-policy.json'), '--output', str(base / 'not-created')]
    tick = time.monotonic()
    r = subprocess.run(argv, capture_output=True, text=True)
    assert r.returncode == 2 and not (base / 'not-created').exists()
    record['runtime_refusals'].append({'runtime': label, 'argv': argv, 'exit_code': r.returncode,
        'stdout': r.stdout, 'stderr': r.stderr, 'elapsed_seconds': time.monotonic() - tick,
        'destination_created': False, 'copied_inputs': 0, 'suites': 'NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED'})
with (HERE / 'logs/windows-capabilities.json').open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2)
print(json.dumps(record, indent=2))
