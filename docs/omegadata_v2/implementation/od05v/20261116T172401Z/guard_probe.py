"""Fresh disposable guard-negative evidence, not production tests or source data."""
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest


def test_dns_guard():
    assert socket.getaddrinfo.__name__ == '<lambda>'
    with pytest.raises(RuntimeError, match='BLOCKED_DNS'):
        socket.getaddrinfo('example.invalid', 443)


def test_tcp_udp_guard():
    assert socket.socket.connect.__name__ == 'connection'
    with socket.socket() as stream:
        with pytest.raises(RuntimeError, match='BLOCKED_SOCKET'):
            stream.connect(('192.0.2.1', 443))
    assert socket.socket.sendto.__name__ == '<lambda>'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as datagram:
        with pytest.raises(RuntimeError, match='BLOCKED_UDP'):
            datagram.sendto(b'SYNTHETIC_TEST_ONLY', ('192.0.2.1', 53))


def test_process_guard():
    with pytest.raises(RuntimeError, match='BLOCKED_SUBPROCESS'):
        subprocess.run([sys.executable, '-c', 'raise SystemExit(99)'], check=False)


def test_disposable_copy_write_guard():
    target = Path(os.environ['OD02V_WORKTREE'])/'guard-negative-canary'
    with pytest.raises(RuntimeError, match='BLOCKED_PROTECTED_WRITE'):
        target.write_bytes(b'SYNTHETIC_TEST_ONLY')
    assert not target.exists()


def test_fictional_signing_read_guard():
    target = Path(os.environ['OD02V_WORKTREE'])/'gnupg'/'nonexistent-synthetic-key'
    with pytest.raises(RuntimeError, match='BLOCKED_SIGNING_READ'):
        target.read_bytes()


def test_fictional_credential_read_guard():
    target = Path(os.environ['OD02V_WORKTREE'])/'.env-od05v-nonexistent-canary'
    with pytest.raises(RuntimeError, match='BLOCKED_CREDENTIAL_READ'):
        target.read_bytes()


def test_original_market_payload_read_guard():
    target = Path(os.environ['OD05V_ORIGINAL'])/'data'/'nonexistent-od05v-canary.zip'
    with pytest.raises(RuntimeError, match='BLOCKED_ORIGINAL_MARKET_PAYLOAD_READ'):
        target.read_bytes()
