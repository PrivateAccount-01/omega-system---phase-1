"""Freeze final bytes, guarded corpus expectations and separate clean runtimes."""
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import control

sys.path.insert(0,str(control.ROOT/'tests/unit'))
import od05_oracle

copies={}
for name in ('win314','win311'):
    root=Path(tempfile.mkdtemp(prefix='omega-od05-final-'))/'repo'
    control.copy_sources(root)
    copies[name]=str(root)
control.save('final-copies.json',copies)
control.save('oracle-vectors.json',{'utc':datetime.now(UTC).isoformat(),
    'classification':'SYNTHETIC_TEST_ONLY','producer':'independent frozen literal oracle, no parser import',
    'legacy_raw_sha256':hashlib.sha256(od05_oracle.LEGACY).hexdigest(),
    'modern_raw_sha256':hashlib.sha256(od05_oracle.MODERN).hexdigest(),
    'legacy_semantic_sha256':od05_oracle.expected_digest('2019-12-31','legacy-illustrative'),
    'modern_semantic_sha256':od05_oracle.expected_digest('2026-04-10','udiff-illustrative'),
    'expected':od05_oracle.EXPECTED})
control.save('final-source-freeze.json',{'utc':datetime.now(UTC).isoformat(),
    'files':{p.relative_to(control.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [*control.ROOT.joinpath('src/omegadata/parsers').glob('*.py'),
    control.ROOT/'tests/unit/test_od05_era_parsing.py',control.ROOT/'tests/unit/od05_oracle.py']}})
print(json.dumps(copies))
