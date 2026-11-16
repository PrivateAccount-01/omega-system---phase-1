"""Native Linux copy of code and authorized regression/manifest metadata only."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

source=Path(sys.argv[1])
assert not (source/'data').exists(), 'No market-data directory may enter this copy'
target=Path(tempfile.mkdtemp(prefix='omega-od05v-',dir='/home/parilrupani'))/'repo'
shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__','.mypy_cache','.ruff_cache'))
here=Path(__file__).resolve().parent
with (here/'logs/linux-location.json').open('x',encoding='utf-8') as f:
    json.dump({'root':str(target),'python':sys.executable,'version':sys.version,
               'original_archive_stat_root':'/mnt/e/omega system - phase 1','market_payloads_copied':0},f,indent=2)
print(target)
