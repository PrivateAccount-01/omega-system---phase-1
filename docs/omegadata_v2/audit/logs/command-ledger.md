# OD-00 command ledger and reproduction recipes

Repository: PrivateAccount-01/omega-system---phase-1, main,
09631ae5cdca7d35172724a68d70847183b914df.
CWD: E:/omega system - phase 1.
Shell: Windows PowerShell 5.1.26100.9818.
Run ID: OD-00-20261114-1107Z. Evidence: RUN/TEST; evaluated 2026-11-14 UTC.
Owner: Test engineer / Historian.

## Identity and discovery

Executed read-only orientation commands; exit 0 for git identity/status/remote and the master-file reads.
Initial Get-Content AGENTS.md exited 1 because absent. Initial rg glob inventories had
exit 1 where no matching optional file/directory existed; not a test failure.
Some combined read invocations returned their final command's exit status; do not use
those as individual-file existence proof. Missing files are explicitly recorded.

```powershell
Get-Content -LiteralPath 'AGENTS.md' -Raw
Get-Content -LiteralPath 'docs/verification/OMEGADATA_CODEX_MASTER_PROMPT.md' -Raw
Get-Location
git rev-parse --show-toplevel
git status --short
git branch --show-current
git rev-parse HEAD
git remote -v
rg --files -g '*AGENTS.md' -g 'pyproject.toml' -g '*MASTER_PROMPT*' -g '.vscode/tasks.json'
Get-Content -Encoding UTF8 -LiteralPath 'OMEGADATA_AGENTS.md' -Raw
Get-Item -LiteralPath 'E:/AGENTS.md','E:/omega system - phase 1/AGENTS.md' -ErrorAction SilentlyContinue
rg --files --hidden -g AGENTS.md -g '!**/.git/**' -g '!**/.venv*/**'
rg --files src/omegadata tests scripts config .github
rg --files --hidden -g '*PLANS.md' -g '*GOALS.md' -g '*PROMPTS.md' -g '*conftest*' -g '*lock*' -g '!**/.git/**' -g '!**/.venv*/**'
git diff -- src/omegadata/track_a/warehouse.py scripts/build_release_bundle.py
```

The master was reread completely with UTF-8 Select-Object chunks:
-First 240, -Skip 240 -First 240, -Skip 480 -First 240, -Skip 720.
README, both Track plans, environment example, fixture README, pyproject, workflow,
tests/conftest, live integration test and core source were inspected using Get-Content
and line-targeted rg. The [component search](component-search.md) preserves a further
exact command batch and output. Large tool excerpts were sometimes truncated; the
complete master was obtained in bounded chunks.

Git emitted permission warnings for the user-global ignore file; no configuration was
changed. Git still resolved root, origin, status, branch and HEAD. Working-tree diff
also emitted existing LF/CRLF conversion warnings; no checkout or renormalization ran.

## Preservation capture

Created only fresh audit/logs and plan directories after checking audit did not exist.
Saved git status and diff statistics; hashed all tracked files before tests.
The PowerShell hash loop used Get-FileHash -Algorithm SHA256 per git ls-files entry.
It completed with exit 0, 11,357 records. Host metadata is in [host.json](host.json).
The elapsed hash capture finished at 11:10:27Z; it ran concurrently with independent
checks, but all hashing began before baseline execution. No command intentionally
modified tracked files. A later full comparison found no deltas.

## Environment

Python environment tools selected the existing interpreter; no installs.
The following native commands were executed and their output retained in
[environment.txt](environment.txt), 11:07:34.3730768Z–11:07:42.8775416Z.
pip check exit 0.

```powershell
& '.venv/Scripts/python.exe' --version
& '.venv/Scripts/python.exe' -m pip --version
& '.venv/Scripts/python.exe' -m pip list --format=json
& '.venv/Scripts/python.exe' -m pip check
```

## Test collection

Exact test command, 11:08:06.3694892Z–11:08:14.2315000Z, exit 0.
[Output](pytest-collection.txt).

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='src'
$env:OMEGA_DB_URL='sqlite:///:memory:'
& '.venv/Scripts/python.exe' -B -m pytest --collect-only -q -m 'not realdata' -p no:cacheprovider
```

## Failed invocations retained

1. At 11:08:16Z an initial -B -c inline invocation of the guard/pytest code failed
with SyntaxError because PowerShell 5.1 native argument handling stripped double quotes
inside the single-quoted command argument. Exit 1 before test execution.
[Unmodified error output](pytest-offline.txt) includes the actual Python input as received.
No application failure is attributed to this.

2. The retry used a PowerShell here-string piped to -B -, with the same environment
and temporary output settings as the final recipe below, but replaced connect,
connect_ex and create_connection with a deny function and did not allow socketpair
construction. That exact difference blocked asyncio on Windows, not source access.
11:08:39.6741730Z–11:09:09.6554522Z, exit 1:
98 passed / 13 failed / 4 deselected / 2 warnings.
[Full failure output](pytest-offline-retry.txt).
Every failed case raised the audit guard RuntimeError; no repository test changed.

## Final full selected offline suite

Exact corrected recipe below.
11:10:34.4499650Z–11:10:57.7738542Z; exit 0;
111 passed / 4 deselected in 21.21s.
[Unmodified output](pytest-offline-final.txt).
Temporary root printed by the command is preserved there. No secrets were set in
environment overrides. Existing settings elsewhere remained process-local only.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='src'
@'
import os, tempfile, pathlib, socket, threading, pytest
root=pathlib.Path(tempfile.mkdtemp(prefix='od00-offline-'))
os.environ['OMEGA_DB_URL']='sqlite:///'+str(root/'default.sqlite')
keys={'PARQUET_ROOT':'parquet','RAW_ROOT':'raw','SEED_RAW_ROOT':'seed','REPORT_ROOT':'reports','REPROCESS_ROOT':'reprocess','RELEASE_ROOT':'releases','RELEASE_GPG_HOME':'gnupg'}
os.environ.update({'OMEGA_'+k:str(root/v) for k,v in keys.items()})
os.environ['OMEGA_VERIFICATION_DB_URL']='sqlite:///'+str(root/'verification.sqlite')
original_connect=socket.socket.connect
original_pair=socket.socketpair
local=threading.local()
def connect(self,address):
    if getattr(local,'creating_pair',False):
        return original_connect(self,address)
    raise RuntimeError('OD-00 external and service sockets denied: '+str(address))
def socketpair(*args,**kwargs):
    local.creating_pair=True
    try: return original_pair(*args,**kwargs)
    finally: local.creating_pair=False
def deny(*args,**kwargs):
    raise RuntimeError('OD-00 socket network access denied')
socket.socket.connect=connect
socket.socket.connect_ex=deny
socket.create_connection=deny
socket.socketpair=socketpair
print('Socket egress denied; Windows internal socketpair allowed only during construction. Temp:',root)
raise SystemExit(pytest.main(['-q','-m','not realdata','-p','no:cacheprovider','--basetemp',str(root/'pytest')]))
'@ | & '.venv/Scripts/python.exe' -B -
```

## Static baseline checks

```powershell
& '.venv/Scripts/python.exe' -B -m ruff check --no-cache src/omegadata tests scripts
& '.venv/Scripts/python.exe' -B -m mypy --cache-dir "$env:TEMP/od00-mypy-20261114" src/omegadata
$env:PYTHONPYCACHEPREFIX="$env:TEMP/od00-pycache-20261114"
& '.venv/Scripts/python.exe' -m compileall -q src/omegadata scripts
```

Ruff 11:08:51.3432074Z–11:08:54.4892801Z exit 0, [output](ruff.txt).
Mypy 11:08:54.5455346Z–11:09:21.2380803Z exit 0, [output](mypy.txt).
Compileall 11:10:46.0331919Z–11:10:48.0560189Z exit 0, [output](compileall.txt).
All caches redirected/disabled as recorded. No fix flags ran.

## Security and side-effect inventory

```powershell
rg -n 'TODO|FIXME|HACK|pass$|NotImplementedError|except Exception' src/omegadata scripts
rg -n 'part-00000.parquet|known_from|published_at|effective_date|fetched_at|seed_cache|reset-sqlite-db' src scripts config tests
rg -n -l 'PRIVATE KEY|BEGIN RSA|BEGIN OPENSSH|api[_-]?key|password|secret|token' src scripts config .github .env.example .gitignore
git ls-files artifacts/gnupg
```

Outputs: [exceptions](exception-and-placeholder-search.txt),
[temporal/write leads](temporal-and-side-effect-search.txt),
[secret-candidate paths only](security-candidate-paths.txt),
[tracked GnuPG paths](tracked-gnupg-paths.txt).
These searches returned matching paths; no private-key body was printed.
No exhaustive Git history or current advisory scan was performed.

## Disposable financial/storage experiments

Exact Python input run via a PowerShell here-string into the configured interpreter:
`& '.venv/Scripts/python.exe' -B -`.
11:12:07.4644804Z–11:12:09.2635735Z; exit 0.
[Output](disposable-integrity-experiments.txt).
All market values are synthetic; SQLite is in-memory and Parquet is newly temporary.

```python
from datetime import date
from decimal import Decimal
from pathlib import Path
import tempfile,hashlib,json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from omegadata.config import settings
from omegadata.db.base import Base
from omegadata.db.models import InstrumentMaster,PriceRecord,ConfirmedCorporateAction
from omegadata.domain import Exchange,InstrumentType,CorporateActionType,ConfidenceLevel
from omegadata.track_b.universe_manager import PointInTimeUniverseManager
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine
from omegadata.track_a.download_manager import DownloadManager
from omegadata.track_a.storage import ParquetStorage
import pandas as pd
r={}
engine=create_engine('sqlite:///:memory:'); Base.metadata.create_all(engine)
with Session(engine) as s:
    s.add(InstrumentMaster(isin='INE009A01021',instrument_type=InstrumentType.EQUITY,primary_exchange=Exchange.NSE,company_name='OD00 synthetic',listed_date=date(2010,1,1),active=True)); s.flush()
    m=PointInTimeUniverseManager(); m.add_membership(s,'INE009A01021','AUDIT',added_date=date(2026,1,1),effective_date=date(2019,1,1),source='SYN_OD00'); s.flush()
    rows=m.get_universe(s,'AUDIT',date(2020,1,1)); r['pit_late_added_membership']={'decision_date':'2020-01-01','added_date':'2026-01-01','effective_date':'2019-01-01','observed_count':len(rows),'expected_strict':0}
a=ConfirmedCorporateAction(action_type=CorporateActionType.RIGHTS,isin='INE009A01021',ex_date=date(2026,4,6),parameters={'rights_ratio_denominator':'4','rights_ratio_numerator':'1','issue_price':'50'},confidence=ConfidenceLevel.HIGH,source_preference=Exchange.NSE)
p=PriceRecord(trade_date=date(2026,4,3),close_price=Decimal('100'))
r['rights_monday']={'ex_date':'2026-04-06','prior_available_session':'2026-04-03','actual_factor':str(PriceAdjustmentEngine()._compute_factor(a,{p.trade_date:p})),'independent_expected_factor':str(((Decimal(4)*100+50)/5)/100),'evidence':'SYN; scheduling logic example, not claim Friday was an exchange session'}
try:
    DownloadManager._validate_payload('NSE_EQUITY_BHAVCOPY',b'<html>Access denied</html>',as_of=date(2026,4,6)); r['nse_equity_html_validation']='ACCEPTED (no error)'
except Exception as e: r['nse_equity_html_validation']=repr(e)
settings.parquet_root=tempfile.mkdtemp(prefix='od00-storage-'); store=ParquetStorage(); first=store.store_daily('audit_synthetic',date(2020,1,1),pd.DataFrame({'close':[100]})); before=hashlib.sha256(first.path.read_bytes()).hexdigest(); second=store.store_daily('audit_synthetic',date(2020,1,1),pd.DataFrame({'close':[101]})); after=hashlib.sha256(first.path.read_bytes()).hexdigest(); r['parquet_same_day']={'same_path':first.path==second.path,'original_hash':before,'current_hash':after,'first_bytes_preserved':before==after,'scope':'new disposable temp directory only'}
print(json.dumps(r,indent=2))
```

## Read-only archived evidence / database inspection

Executed Python stdin inspection, exit 0, evaluated 11:11:19.151894Z.
Full result: [read-only-evidence-checks.json](read-only-evidence-checks.json).
Procedure: json.loads on manifests and reports; SHA-256 over each referenced dataset;
UTC subtraction of generated_at against policy limits; SQLite connection using
`p.resolve().as_uri()+'?mode=ro'`, uri=True and PRAGMA query_only=ON.
Queries: sqlite_master table names; SELECT count(*) on price_record,
universe_membership, confirmed_corporate_action, release_record, manual_review_queue;
SELECT raw_source,count(*) FROM price_record GROUP BY raw_source;
SELECT release_id,ready_state,warehouse_sync_status FROM release_record.
Both connections were closed. No ORM startup, schema reconciliation, signature helper
or generator was invoked. Full runtime readiness was not reevaluated.

The separate catalog command iterated artifacts/verification/*.json, parsed UTF-8-sig,
recorded SHA-256 and existing generated_at/run_id/code_commit/source/mode/checks/summary
fields, and retained absent fields as absent. Output:
[artifact-catalog.json](artifact-catalog.json). Exit 0; no old artifact was regenerated.

## Module/dependency inventory and preservation

AST parsed each src/omegadata/**/*.py without importing application startup.
importlib.metadata supplied installed version/license fields (not legal clearance).
Full input command is in [inventory-command.md](inventory-command.md).
Exit 0: 46 modules, 68 installed packages, 11,357 tracked hashes compared, zero deltas.
[Output](module-and-package-inventory.json), [preservation check](preservation-check.json).

## Final document verification and encoding follow-up

Final verification used Python stdin with the configured interpreter to iterate all
new Markdown prose links (excluding fenced captured command output), resolve targets
relative to each document, and recompute the tracked-file snapshot hashes. The first
checker exited 1 because it incorrectly treated historical links inside fenced rg
output as navigation. Its result is retained. The second exited 1 because it checked
the newly added encoding-followup link before writing that target later in the same
command. The target now exists. No report/source claim was weakened to hide a failure.
The third check, 2026-11-14T11:28:02.496592Z, exited 0: 9 audit reports, 3 plan reports,
zero broken prose links and zero byte deltas across 11,357 tracked files.
[Final output](final-document-and-preservation-check-v3.json). The Problems tool also
reported no errors for the new documentation directory.

The original API stress JSON decoding issue was resolved read-only as UTF-16. The
follow-up recorded its current hash, absent timestamp/commit/run metadata and archived
results in [encoding-followup.json](encoding-followup.json). It is not a newly executed
stress test. Both the initial catalog exception and final interpretation were kept.

## Limitations / next action

Logs from native PowerShell redirection may be UTF-16; JSON files generated by Python
are UTF-8. Retain original outputs and decode accordingly. This ledger preserves full
baseline recipes and command-level evidence; it is not a shell-session recording of
every exploratory source read. No external acquisition, dependency install, package
publish, service startup, reset flag, release generator, broker action or Git mutation
was executed. Future acceptance commands in the implementation plan have not run.

