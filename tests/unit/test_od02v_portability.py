"""SYNTHETIC_TEST_ONLY portability/security proofs; no external endpoints."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

from omegadata.track_a import download_manager as dm
from omegadata.track_a.acquisition import safe_url
from omegadata.track_a.download_manager import DownloadError, DownloadManager

KEY = "NSE_EQUITY_BHAVCOPY"
DAY = date(2024, 1, 2)


def test_v00_real_file_symlink_capability(tmp_path):
    target = tmp_path / "synthetic-target.txt"
    target.write_text("SYNTHETIC_TEST_ONLY")
    link = tmp_path / "synthetic-link.txt"
    link_to(link, target)
    assert link.is_symlink() and link.readlink() == target
    assert link.read_text() == "SYNTHETIC_TEST_ONLY"


def test_v01_guard_denies_dns_tcp_udp_children_and_protected_writes():
    assert os.environ.get("OD02V_DISPOSABLE_ROOT"), "Run only using OD-02V isolated runner"
    protected = Path(os.environ["OD02V_WORKTREE"]) / "must-not-create-od02v.bin"
    with pytest.raises(RuntimeError, match="BLOCKED"):
        socket.getaddrinfo("example.invalid", 443)
    with socket.socket() as client, pytest.raises(RuntimeError, match="BLOCKED"):
        client.connect(("192.0.2.1", 443))
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client,
        pytest.raises(RuntimeError, match="BLOCKED"),
    ):
        client.sendto(b"SYNTHETIC_TEST_ONLY", ("192.0.2.1", 9))
    with pytest.raises(RuntimeError, match="BLOCKED"):
        subprocess.run([sys.executable, "-c", "raise SystemExit(99)"])
    with pytest.raises(RuntimeError, match="BLOCKED"):
        protected.write_bytes(b"SYNTHETIC_TEST_ONLY")
    with pytest.raises(RuntimeError, match="BLOCKED"):
        sqlite3.connect(str(protected))
    assert not protected.exists()
    if os.name != "nt":
        directory = os.open(protected.parent, os.O_RDONLY)
        try:
            with pytest.raises(RuntimeError, match="BLOCKED"):
                os.unlink(protected.name, dir_fd=directory)
            with pytest.raises(RuntimeError, match="BLOCKED"):
                os.open(protected.name, os.O_WRONLY | os.O_CREAT, dir_fd=directory)
        finally:
            os.close(directory)
    left, right = socket.socketpair()
    try:
        left.send(b"x")
        assert right.recv(1) == b"x"
    finally:
        left.close()
        right.close()


def make_cache(tmp_path, provider, seed=False):
    manager = DownloadManager(policy_provider=provider)
    manager.raw_root, manager.seed_raw_root = tmp_path / "raw", tmp_path / "seed"
    root = manager.seed_raw_root if seed else manager.raw_root
    folder = root / KEY.lower() / "year=2024/month=01"
    folder.mkdir(parents=True)
    payload = b"SYNTHETIC_TEST_ONLY harmless cache"
    artifact = folder / "20240102__safe.bin"
    artifact.write_bytes(payload)
    pointer = folder / "20240102.latest.json"
    body = {
        "source_key": KEY,
        "as_of": DAY.isoformat(),
        "artifact_path": str(artifact),
        "checksum": hashlib.sha256(payload).hexdigest(),
        "bytes_downloaded": len(payload),
    }
    pointer.write_text(json.dumps(body))
    return manager, root, folder, pointer, artifact, body


def link_to(link, target, directory=False):
    try:
        if directory and sys.platform == "win32":
            import _winapi

            _winapi.CreateJunction(str(target), str(link))
        else:
            link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        pytest.skip(f"Actual symlink capability unavailable: {exc}")


@pytest.mark.parametrize("seed", [False, True])
def test_v02_real_directory_link_partition_confined(
    tmp_path, synthetic_source_policy_provider, monkeypatch, seed
):
    manager, root, folder, pointer, artifact, body = make_cache(
        tmp_path, synthetic_source_policy_provider, seed
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / artifact.name).write_bytes(b"SYNTHETIC_TEST_ONLY harmless cache")
    link = folder / "redirected"
    link_to(link, outside, True)
    body["artifact_path"] = str(link / artifact.name)
    pointer.write_text(json.dumps(body))
    reads = Mock(side_effect=AssertionError("No bytes outside cache partition"))
    monkeypatch.setattr(Path, "read_bytes", reads)
    assert manager._load_cached_artifact_from_root(root, KEY, DAY) is None
    reads.assert_not_called()


@pytest.mark.parametrize("kind", ["broken", "loop", "retarget"])
@pytest.mark.parametrize("seed", [False, True])
def test_v03_file_links_changed_at_lookup_refuse(
    tmp_path, synthetic_source_policy_provider, monkeypatch, kind, seed
):
    manager, root, folder, pointer, artifact, body = make_cache(
        tmp_path, synthetic_source_policy_provider, seed
    )
    pointer.unlink()
    if kind == "broken":
        link_to(pointer, folder / "absent.json")
    elif kind == "loop":
        link_to(pointer, folder / "loop.json")
        link_to(folder / "loop.json", pointer)
    else:
        inside = folder / "safe.json"
        inside.write_text(json.dumps(body))
        link_to(pointer, inside)
        assert manager._load_cached_artifact_from_root(root, KEY, DAY) is not None
        outside = tmp_path / "outside-synthetic.json"
        outside.write_text(json.dumps(body))
        pointer.unlink()
        link_to(pointer, outside)
    # Swap occurs before the API boundary. This does not claim a hostile
    # concurrent mutation during a filesystem syscall has been contained.
    reads = Mock(side_effect=AssertionError("Must refuse before payload read"))
    monkeypatch.setattr(Path, "read_bytes", reads)
    assert manager._load_cached_artifact_from_root(root, KEY, DAY) is None
    reads.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "/api/token/SYNTHETIC_SECRET/data",
        "/api/api_key/SYNTHETIC_SECRET",
        "/api/access_token/SYNTHETIC_SECRET",
        "/api/password=SYNTHETIC_SECRET/data",
        "/api/%74oken/SYNTHETIC_SECRET",
    ],
)
def test_v04_credential_shaped_path_redacted(path):
    value = safe_url(
        "https://user:SYNTHETIC_SECRET@example.invalid"
        + path
        + "?token=SYNTHETIC_SECRET#SYNTHETIC_SECRET"
    )
    assert "SYNTHETIC_SECRET" not in value
    assert value.startswith("https://example.invalid/")


def test_v04_legacy_cache_url_is_redacted(tmp_path, synthetic_source_policy_provider):
    manager, root, folder, pointer, artifact, body = make_cache(
        tmp_path, synthetic_source_policy_provider
    )
    body["used_url"] = "https://example.invalid/api/token/SYNTHETIC_SECRET?token=SYNTHETIC_SECRET"
    pointer.write_text(json.dumps(body))
    cached = manager._load_cached_artifact_from_root(root, KEY, DAY)
    assert cached is not None and "SYNTHETIC_SECRET" not in cached.used_url


def test_v04_structured_error_context_redacts_path(
    tmp_path, synthetic_source_policy_provider, monkeypatch
):
    manager = DownloadManager(policy_provider=synthetic_source_policy_provider)
    manager.raw_root = tmp_path / "raw"
    real_client = httpx.Client
    monkeypatch.setattr(
        dm.httpx,
        "Client",
        lambda **kw: real_client(
            transport=httpx.MockTransport(lambda _: httpx.Response(429)), **kw
        ),
    )
    monkeypatch.setattr(
        manager,
        "_candidate_urls",
        lambda *_: ["https://example.invalid/token/SYNTHETIC_SECRET/file"],
    )
    with pytest.raises(DownloadError) as exc:
        manager.download(KEY, DAY, use_cache=False)
    assert "SYNTHETIC_SECRET" not in json.dumps(exc.value.context)
    assert exc.value.context["actual_attempts"] == 1 and not manager.raw_root.exists()
