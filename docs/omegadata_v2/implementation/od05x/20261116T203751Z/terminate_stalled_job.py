"""Terminate only the identified disposable, isolated stalled A worker."""
import json
import os
import signal
from datetime import UTC, datetime
from pathlib import Path
here = Path(__file__).parent
pid = 495
proc = Path('/proc') / str(pid)
argv = (proc / 'cmdline').read_bytes().split(b'\0')
assert b'/input/scripts/od05x_isolated_runner.py' in argv and b'worker' in argv
config = json.loads((proc / 'root/policy/config.json').read_bytes())
assert config['job'] == 'A' and 'feb3c3b6df4c' in config['outside_canary']
assert os.readlink(proc / 'ns/pid') != os.readlink('/proc/self/ns/pid')
record = {'utc': datetime.now(UTC).isoformat(), 'pid': pid, 'job': 'A-feb3c3b6df4c',
          'wchan': (proc / 'wchan').read_text(), 'signal': 'SIGTERM',
          'reason': 'Stalled isolated run; native local IPC send independently reproduced EPERM',
          'scope': 'Only this newly created disposable worker; no retained/original paths deleted'}
os.kill(pid, signal.SIGTERM)
with (here / 'logs/stalled-A-termination.json').open('x') as f: json.dump(record, f, indent=2)
print(json.dumps(record))
