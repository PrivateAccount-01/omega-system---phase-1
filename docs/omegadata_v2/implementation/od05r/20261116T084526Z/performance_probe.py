"""Bounded synthetic envelope measurements, not source-capacity certification."""
import hashlib
import json
import sys
import time
import tracemalloc
from pathlib import Path

import pytest

sys.path.insert(0,str(Path.cwd()/'tests/unit'))
from od05r_reference_oracle import META, encode, expected_digest
from omegadata.parsers.reference_evidence import verify_reference


@pytest.mark.parametrize('size',[1024,16384,262144])
def test_bounded_verification(size):
    payload=b'%PDF-SYNTHETIC_TEST_ONLY\n'+b'x'*(size-25)
    meta=META|{'document_length':len(payload),'document_sha256':hashlib.sha256(payload).hexdigest()}
    metadata=encode(meta)
    tracemalloc.start()
    started=time.perf_counter()
    outputs=[verify_reference(metadata,{'document.pdf':payload}) for _ in range(16)]
    elapsed=time.perf_counter()-started
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(outputs)==16 and all(r.semantic_sha256==expected_digest(meta) for r in outputs)
    assert all(not r.official_eligible for r in outputs)
    print(json.dumps({'classification':'SYNTHETIC_TEST_ONLY','document_bytes':len(payload),
        'envelope_count':16,'elapsed_seconds':elapsed,'tracemalloc_peak_bytes':peak,
        'measurement':'Python allocations during verification only, not process RSS'}))
