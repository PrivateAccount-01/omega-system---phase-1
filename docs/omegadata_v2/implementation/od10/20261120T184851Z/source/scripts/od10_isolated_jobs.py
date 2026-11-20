"""Trusted OD10 experiment adapter; unchanged worker seccomp and namespace contract.

The template is a hash-pinned successful accepted-launcher command. Only fresh
/work output, exact policy input and one explicitly owned generated-canary mount
are substituted. No source discovery, original mount, subprocess from worker,
network grant, cleanup or production invocation is provided.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def start_worker(
    template: Path,
    template_sha256: str,
    policy_template: Path,
    output: Path,
    shared: Path,
    owned_root: Path,
    role: dict[str, Any],
) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    raw = template.read_bytes()
    if hashlib.sha256(raw).hexdigest() != template_sha256:
        raise ValueError("LAUNCH_TEMPLATE_PIN")
    if (
        output.exists()
        or not output.is_relative_to(owned_root)
        or not shared.is_relative_to(owned_root)
        or output == shared
    ):
        raise ValueError("EXPERIMENT_SCOPE")
    if not owned_root.is_absolute() or ".." in owned_root.parts:
        raise ValueError("EXPERIMENT_SCOPE")
    for p in (*shared.parents, shared, *output.parent.parents, output.parent):
        if p.is_symlink():
            raise ValueError("EXPERIMENT_LINK_ESCAPE")
    if (shared / "NON_MARKET_SHARED.json").read_text() != '{"class":"OD10_NON_MARKET_SHARED/v1"}':
        raise ValueError("EXPERIMENT_OWNERSHIP")
    if shared.stat().st_dev != owned_root.stat().st_dev:
        raise ValueError("EXPERIMENT_DEVICE")
    output.mkdir(mode=0o700)
    base = json.loads(raw)
    argv = base["argv"]
    config = json.loads(policy_template.read_bytes())
    if argv[0] != "/usr/bin/bwrap" or base["exit_code"] != 0:
        raise ValueError("ACCEPTED_TEMPLATE_REQUIRED")
    for flag in (
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "--clearenv",
        "--remount-ro",
    ):
        if flag not in argv:
            raise ValueError("BOUNDARY_FLAGS_REQUIRED")
    if argv[-2:] != ["/input/scripts/od05x_isolated_runner.py", "worker"]:
        raise ValueError("WORKER_ENTRYPOINT")
    if role.get("mode") not in {"initial", "attempt", "recover", "race", "reader"}:
        raise ValueError("EXPERIMENT_ROLE")
    config = {**config, "job": "od10proc", "od10_role": role}
    policy = output.parent / (output.name + "-policy.json")
    with policy.open("x") as f:
        json.dump(config, f, indent=2)
    args = list(argv)
    bind = args.index("--bind")
    if args[bind + 2] != "/work":
        raise ValueError("WORKSPACE_BIND_REQUIRED")
    args[bind + 1] = str(output)
    pos = args.index("/policy/config.json")
    if args[pos - 2] != "--ro-bind":
        raise ValueError("POLICY_BIND_REQUIRED")
    args[pos - 1] = str(policy)
    pos = args.index("--remount-ro")
    args[pos:pos] = ["--bind", str(shared), "/work/shared"]
    # Existing seccomp denies fork/exec/network inside worker. Only trusted host launcher starts it.
    process = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    )
    record = {
        "argv": args,
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "template_sha256": template_sha256,
        "global_launcher_pid": process.pid,
        "role": role,
        "shared_class": "OD10_NON_MARKET_SHARED/v1",
        "isolation_weakened": False,
        "original_mounts_added": False,
    }
    with (output.parent / (output.name + "-launch.json")).open("x") as f:
        json.dump(record, f, indent=2)
    return process, record
