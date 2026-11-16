"""Freeze OD05R input identity, reconcile OD05 and create disposable copies."""
import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import control

old=control.ROOT/'docs/omegadata_v2/implementation/od05_impl/20261115T201333Z'
manifest=json.loads((old/'logs/evidence-sha256.json').read_text())
for name,sha in manifest.items():
    assert (old/name).resolve().is_relative_to(old.resolve())
    assert hashlib.sha256((old/name).read_bytes()).hexdigest()==sha,name
source=json.loads((old/'logs/final-source-freeze.json').read_text())['files']
assert all(hashlib.sha256((control.ROOT/p).read_bytes()).hexdigest()==sha for p,sha in source.items())
if len(sys.argv)==1:
    control.save('od05-evidence-reconciliation.json',{'utc':datetime.now(UTC).isoformat(),
        'evidence_files_verified':len(manifest),'source_test_files_verified':len(source),
        'original_authorizations_unchanged':True,'archived_not_fresh_runtime_results':True})
copies={}
for name in ('win314','win311'):
    root=Path(tempfile.mkdtemp(prefix='omega-od05r-final-'))/'repo'
    control.copy_sources(root)
    copies[name]=str(root)
control.save('reviewed-copies.json' if len(sys.argv)>1 else 'final-copies.json',copies)
paths=[control.ROOT/'src/omegadata/parsers/reference_evidence.py',control.ROOT/'src/omegadata/parsers/era_matrix.py',
    control.ROOT/'tests/unit/test_od05r_reference_evidence.py',control.ROOT/'tests/unit/od05r_reference_oracle.py']
control.save('reviewed-source-freeze.json' if len(sys.argv)>1 else 'final-source-freeze.json',{'utc':datetime.now(UTC).isoformat(),
    'files':{p.relative_to(control.ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
sys.path.insert(0,str(control.ROOT/'tests/unit'))
import od05r_reference_oracle as oracle
control.save('reviewed-oracle-vectors.json' if len(sys.argv)>1 else 'independent-oracle-vectors.json',{'producer':'stdlib-only pre-code literal oracle, no production import',
    'document_sha256':hashlib.sha256(oracle.DOCUMENT).hexdigest(),
    'sample_sha256':hashlib.sha256(oracle.SAMPLE).hexdigest(),
    'semantic_sha256':oracle.expected_digest(oracle.META),'metadata':oracle.META,
    'expected_references':1,'expected_documents':1,'expected_samples':0})
print(json.dumps(copies))
