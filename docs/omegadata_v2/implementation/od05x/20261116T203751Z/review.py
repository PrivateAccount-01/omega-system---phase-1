"""Trusted evidence reader; never opens original data or signing content."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).parent
OLD = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)

rows = {}
commands = []
for path in sorted(OLD.rglob('*')):
    if not path.is_file():
        continue
    raw = path.read_bytes()
    item = {'bytes': len(raw), 'sha256': digest(raw)}
    if path.suffix == '.json':
        body = json.loads(raw)
        item['structure'] = list(body) if isinstance(body, dict) else {'items': len(body)}
        if isinstance(body, dict) and 'argv' in body:
            commands.append({'log': path.relative_to(OLD).as_posix(),
                             **{k: body[k] for k in ('argv', 'exit_code', 'counts') if k in body}})
    elif path.suffix in {'.py', '.md', '.txt'}:
        item['lines'] = len(raw.decode('utf-8').splitlines())
    rows[path.relative_to(OLD).as_posix()] = item
seal = json.loads((OLD / 'evidence-sha256.json').read_bytes())['files']
assert all(rows[name]['sha256'] == value['sha256'] and rows[name]['bytes'] == value['bytes']
           for name, value in seal.items())
names = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
code = {name: digest((ROOT / name).read_bytes()) for name in names if name and
        (name.startswith(('src/', 'scripts/', 'tests/', 'config/')) or
         name in {'AGENTS.md', 'OMEGADATA_AGENTS.md', 'pyproject.toml'})}
save('logs/read-and-preservation-before.json', {'utc': datetime.now(UTC).isoformat(),
     'entire_prior_dossier': rows, 'sealed_files_verified': len(seal),
     'prior_command_results': commands, 'code_and_metadata_before': code,
     'original_payload_or_signing_content_read': False})
test = ROOT / 'tests/unit/test_od05x_isolation.py'
save('logs/negative-first-freeze.json', {'utc': datetime.now(UTC).isoformat(),
     'test': {'path': test.relative_to(ROOT).as_posix(), 'sha256': digest(test.read_bytes())},
     'implementation_absent': not (ROOT / 'scripts/od05x_isolated_runner.py').exists(),
     'application_before': code})
runtime = '/home/parilrupani/omega-od02v-37b3vimd/venv312'
argv = ['wsl.exe', '-d', 'Ubuntu', '--', '/usr/bin/bwrap', '--unshare-all',
        '--die-with-parent', '--new-session', '--clearenv', '--ro-bind', '/usr', '/usr',
        '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
        '--ro-bind', runtime, runtime, '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
        '--dir', '/work', '--chdir', '/work', '--setenv', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1',
        '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--ro-bind',
        '/mnt/e/omega system - phase 1/tests/unit/test_od05x_isolation.py', '/tests/test_x.py',
        runtime + '/bin/python', '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '/tests/test_x.py']
start = datetime.now(UTC).isoformat()
result = subprocess.run(argv, capture_output=True, text=True)
save('logs/negative-first-baseline.json', {'argv': argv, 'start_utc': start,
     'end_utc': datetime.now(UTC).isoformat(), 'exit_code': result.returncode,
     'stdout': result.stdout, 'stderr': result.stderr,
     'classification': 'NEW_FEATURE_ABSENT; native adversarial calls never reached',
     'isolation': 'namespace filesystem/network only, absent API prevents unsafe native execution'})
print(json.dumps({'prior_files_read': len(rows), 'sealed_verified': len(seal),
                  'baseline_exit': result.returncode, 'baseline_tail': result.stdout[-2200:]}))
