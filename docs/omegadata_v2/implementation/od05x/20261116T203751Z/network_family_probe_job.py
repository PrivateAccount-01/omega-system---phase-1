"""Frozen X06 deny-default native probe; no packets or peer connections."""
import ctypes
import errno
import json
from pathlib import Path

def run(config):
    lib = ctypes.CDLL(None, use_errno=True)
    rows = []
    ctypes.set_errno(0)
    fd = lib.socket(16, 3, 0)  # AF_NETLINK, SOCK_RAW; no bind/send/receive.
    error = ctypes.get_errno()
    rows.append({'probe': 'non_UNIX_socket_family', 'return': fd, 'errno': error,
                 'denied': fd == -1 and error == errno.EPERM})
    if fd >= 0: lib.close(fd)
    for name in ('bind', 'listen', 'accept4'):
        fd = lib.socket(1, 1, 0)
        assert fd >= 0
        address = ctypes.create_string_buffer(b'\x01\x00\x00OD05X_NON_MARKET_CANARY')
        ctypes.set_errno(0)
        if name == 'bind': value = lib.bind(fd, ctypes.byref(address), 27)
        elif name == 'listen': value = lib.listen(fd, 1)
        else: value = lib.accept4(fd, None, None, 0x800)
        error = ctypes.get_errno()
        rows.append({'probe': name, 'return': value, 'errno': error,
                     'denied': value == -1 and error == errno.EPERM})
        if name == 'accept4' and value >= 0: lib.close(value)
        lib.close(fd)
    with Path('/work/family-result.json').open('x') as stream:
        json.dump({'probes': rows, 'packets': 0, 'peer_connections': 0, 'financial_rows': 0,
                   'python_hook': False}, stream, indent=2)
    return 0 if all(r['denied'] for r in rows) else 1
