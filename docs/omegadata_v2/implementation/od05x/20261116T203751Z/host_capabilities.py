"""Read-only Windows API availability and kernel-tool package identities."""
import ctypes
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
exports = {}
for library, names in {
    'advapi32': ['CreateRestrictedToken', 'IsTokenRestricted'],
    'userenv': ['CreateAppContainerProfile', 'DeleteAppContainerProfile'],
    'kernel32': ['SetProcessMitigationPolicy', 'CreateJobObjectW'],
}.items():
    dll = ctypes.WinDLL(library)
    exports[library] = {name: hasattr(dll, name) for name in names}
argv = ['wsl.exe', '-d', 'Ubuntu', '--', 'dpkg-query', '-W', 'bubblewrap', 'libseccomp2']
r = subprocess.run(argv, capture_output=True, text=True)
record = {'utc': datetime.now(UTC).isoformat(), 'host': platform.platform(),
          'Windows_API_export_presence_only': exports,
          'exports_are_not_configured_isolation': True,
          'Linux_tool_identity_command': {'argv': argv, 'exit_code': r.returncode,
                                          'stdout': r.stdout, 'stderr': r.stderr},
          'system_configuration_or_installation_changed': False}
with (here / 'logs/host-api-capabilities.json').open('x') as f: json.dump(record, f, indent=2)
print(json.dumps(record))
