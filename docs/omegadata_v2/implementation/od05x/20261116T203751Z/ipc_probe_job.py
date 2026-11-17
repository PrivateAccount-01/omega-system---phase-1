"""X06 native local-IPC positive control; no financial data or network packets."""
import ctypes
import errno
import json
from pathlib import Path

def run(config):
    lib = ctypes.CDLL(None, use_errno=True)
    pair = (ctypes.c_int * 2)()
    assert lib.socketpair(1, 1, 0, pair) == 0
    ctypes.set_errno(0)
    sent = lib.send(pair[0], b'NON_MARKET_CANARY', 16, 0)
    error = ctypes.get_errno()
    lib.close(pair[0])
    lib.close(pair[1])
    record = {'native_call': 'send on connected AF_UNIX socketpair', 'return': sent,
              'errno': error, 'expected': 16, 'financial_rows': 0,
              'external_network_packets': 0, 'python_hooks': False}
    with Path('/work/ipc-result.json').open('x') as stream:
        json.dump(record, stream, indent=2)
    return 0 if sent == 16 else 1
