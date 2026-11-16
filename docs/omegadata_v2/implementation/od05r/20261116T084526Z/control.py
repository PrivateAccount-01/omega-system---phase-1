"""Bounded OD05 evidence controller; no signing content or provider access."""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
LOGS = HERE / 'logs'
HEAD = '2326936860f64cadf4f4c24a968c073114598b26'
OLD = ROOT / 'docs/omegadata_v2/implementation/od04r/20261115T181120Z'


def save(name, body):
    with (LOGS / name).open('x', encoding='utf-8') as f:
        json.dump(body, f, indent=2)


def snapshot():
    spec = importlib.util.spec_from_file_location('prior', ROOT / 'docs/omegadata_v2/implementation/od02/20261115T084441Z/verification_runner.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.snapshot()


def copy_sources(target):
    target.mkdir(parents=True, exist_ok=False)
    for p in [*ROOT.joinpath('src').rglob('*.py'), *ROOT.joinpath('tests').rglob('*.py'), *ROOT.joinpath('scripts').rglob('*.py'), *ROOT.joinpath('config').glob('*.json'), ROOT / 'pyproject.toml', ROOT / 'README.md']:
        if '__pycache__' in p.parts:
            continue
        out = target / p.relative_to(ROOT)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(p.read_bytes())
    for p in (ROOT / 'tests/fixtures').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            out = target / p.relative_to(ROOT)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(p.read_bytes())
    # Retain tracked UI/static resources used during API test collection.
    for name in subprocess.check_output(['git','ls-files','-z']).decode().split('\0'):
        p=Path(name)
        if not name or p.parts[0] not in {'src','scripts','tests','config'}:
            continue
        out=target/p
        if not out.exists():
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes((ROOT/p).read_bytes())
    fixture_manifest = ROOT / 'docs/omegadata_v2/implementation/od02v/20261115T114445Z/logs/fixture-allowlist.json'
    for row in json.loads(fixture_manifest.read_text())['files']:
        raw = (ROOT / row['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        out = target / row['path']
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)


def preflight():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == HEAD
    save('preservation-before.json', snapshot())
    body = (OLD / 'verification_runner.py').read_text().replace('44090a42958869faaab57a42b65f7ad8571d924d', HEAD)
    (HERE / 'verification_runner.py').write_text(body, encoding='utf-8')
    shutil.copyfile(OLD / 'environment_probe.py', HERE / 'environment_probe.py')
    target = Path(tempfile.mkdtemp(prefix='omega-od05-copy-')) / 'repo'
    copy_sources(target)
    save('copy.json', {'root': str(target), 'utc': datetime.now(UTC).isoformat()})
    print(target)


if __name__ == '__main__':
    if sys.argv[1] == 'preflight':
        preflight()
    elif sys.argv[1] == 'sync':
        target = Path(json.loads((LOGS / 'copy.json').read_text())['root'])
        for folder in ('src/omegadata/parsers', 'tests/unit'):
            for p in (ROOT / folder).glob('*.py'):
                if folder == 'tests/unit' and not p.name.startswith('od05r_') and p.name != 'test_od05r_reference_evidence.py':
                    continue
                out = target / p.relative_to(ROOT)
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, out)
    elif sys.argv[1] == 'freeze':
        files = [ROOT / 'tests/unit/test_od05r_reference_evidence.py', ROOT / 'tests/unit/od05r_reference_oracle.py']
        assert not (ROOT / 'src/omegadata/parsers/reference_evidence.py').exists()
        save('preimplementation-freeze.json', {'utc': datetime.now(UTC).isoformat(), 'head': HEAD, 'application_package_absent': True, 'files': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})
    elif sys.argv[1] == 'preserve':
        before = json.loads((LOGS / 'preservation-before.json').read_text())
        after = snapshot()
        changed = [p for p, value in before.items() if after.get(p) != value]
        # These phase-owned tests were written before this inventory, deliberately
        # frozen before parser code, then expanded with honestly labeled later cases.
        owned = {'tests/unit/test_od05r_reference_evidence.py', 'tests/unit/od05r_reference_oracle.py'}
        unexpected = [p for p in changed if p not in owned]
        save('preservation-comparison.json', {'inventory_records': len(before),
            'original_records': len(set(before)-owned), 'phase_owned_test_deltas': [p for p in changed if p in owned],
            'unexpected_original_changes': unexpected, 'utc': datetime.now(UTC).isoformat()})
        assert not unexpected, unexpected
