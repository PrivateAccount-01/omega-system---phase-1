"""Move only this run's explicitly recorded disposable corpus; prove old path fails."""
import json,os,sys
from pathlib import Path
from datetime import UTC,datetime
root=Path(sys.argv[1]).resolve()
assert root.is_dir() and root.name.startswith('omega-od04-process-')
if os.name=='nt':
    import tempfile
    assert root.parent == Path(tempfile.gettempdir()).resolve()
else:
    assert root.parent == Path('/home/parilrupani')
target=root.with_name(root.name+'-moved-for-negative')
assert target.parent==root.parent and not target.exists()
# Validated exact absolute source/target; no recursive deletion or shell command.
root.rename(target)
print(json.dumps({'old':str(root),'moved':str(target),'utc':datetime.now(UTC).isoformat()}))
