"""Additional X05/X06/X15 proofs, frozen before their API corrections."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize("kind", ["execve", "tcp_connect", "dns_sendto"])
def test_x05_x06_direct_native_calls(kind):
    h = importlib.import_module("od05x_isolated_runner")
    h.assert_boundary()
    result = h.native_probe(kind)
    assert result["denied"] is True
    assert result["native_return"] == -1 and result["errno"] == 1
    assert result["python_hook"] is False


def test_x15_new_test_source_pin_is_enforced(monkeypatch):
    h = importlib.import_module("od05x_isolated_runner")
    original = Path.read_bytes

    def changed(path):
        if path == Path("/work/repo/tests/unit/test_od05x_isolation.py"):
            return b"# NON_MARKET_CANARY changed test source\n"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", changed)
    with pytest.raises((AssertionError, ValueError)):
        h.reconcile_reviewed_inputs(Path("/work/repo"))
