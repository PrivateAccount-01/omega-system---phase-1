"""Read-only OD-02 preservation, diff, syntax and report checks; never open keys."""
from __future__ import annotations

import ast
import difflib
import hashlib
import importlib.metadata
import importlib.util
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).resolve().parent
LOGS = HERE / "logs"
EXISTING = {
    "src/omegadata/track_a/download_manager.py",
    "scripts/generate_source_probe_report.py",
    "scripts/load_nse_fo_into_pipeline_db.py",
    "tests/conftest.py", "tests/unit/test_od01_source_rights.py",
    "tests/unit/test_od01r_rights_hardening.py",
}
NEW = {"src/omegadata/track_a/acquisition.py", "config/acquisition_limits.v1.json",
       "tests/unit/test_od02_acquisition.py"}
DOCS = ["00_preflight.md", "01_repo_selection.md", "02_design_and_adrs.md",
        "03_red_green_test_matrix.md", "04_implementation_diff.md", "05_security_failure_analysis.md",
        "06_evidence_and_coverage.md", "07_remaining_defects.md", "08_gatekeeper_verdict.md",
        "09_next_phase_request.md"]


def save(name, value):
    with (LOGS / name).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.PIPE).decode()


def baseline_texts():
    """Apply the reviewed OD-01R text patch in memory only. No Git writes."""
    lines = Path("docs/omegadata_v2/implementation/od01r/20261115T065155Z/logs/implementation.patch").read_text().splitlines()
    result, index = {}, 0
    while index < len(lines):
        if not lines[index].startswith("diff --git "):
            index += 1
            continue
        path = lines[index].split(" b/", 1)[1]
        original = git("show", "HEAD:" + path).splitlines()
        output, cursor = [], 0
        index += 1
        while index < len(lines) and not lines[index].startswith("diff --git "):
            header = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", lines[index])
            if header is None:
                index += 1
                continue
            start = int(header[1]) - 1
            output.extend(original[cursor:start])
            cursor = start
            index += 1
            while index < len(lines) and not lines[index].startswith(("@@", "diff --git ")):
                line = lines[index]
                if line.startswith((" ", "-")):
                    assert original[cursor] == line[1:], (path, cursor)
                    cursor += 1
                if line.startswith((" ", "+")):
                    output.append(line[1:])
                index += 1
        output.extend(original[cursor:])
        result[path] = "\n".join(output) + "\n"
    return result


def inventory():
    parsed, calls = [], []
    for folder in ("src", "scripts", "tests", "airflow"):
        for path in sorted(Path(folder).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path), feature_version=(3, 11))
            parsed.append(path.as_posix())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = ast.unparse(node.func)
                    if any(token in name for token in ("httpx.", "urlopen", "subprocess.", "client.get", "client.stream", "offline_runner", "adapter(")):
                        calls.append({"file":path.as_posix(), "line":node.lineno, "call":name})
    packages = {}
    for name in ("httpx", "httpcore", "anyio", "h11", "idna", "certifi", "pydantic", "omegadata"):
        dist = importlib.metadata.distribution(name)
        packages[name] = {"version":dist.version, "license":dist.metadata.get("License-Expression") or dist.metadata.get("License"),
                          "requires":dist.requires or []}
    save("parse-and-component-inventory-v2.json", {"utc":datetime.now(UTC).isoformat(),
         "python311_syntax_parse_only":parsed, "network_boundary_calls":calls, "installed_metadata":packages,
         "limitation":"Syntax parse is not Python 3.11 dependency/runtime verification. No upstream advisories queried."})
    before = baseline_texts()
    patch = []
    for path in sorted(EXISTING | NEW):
        actual = Path(path).read_text(encoding="utf-8")
        if path in NEW:
            old = ""
        elif path == "tests/unit/test_od01r_rights_hardening.py":
            old = actual.replace(', offline_runner=fake_run)', ')').replace(
                '        if revoke_after_bootstrap and command[-1] == "https://www.nseindia.com/":',
                '        elif revoke_after_bootstrap:')
            baseline = json.loads((LOGS/"preservation-before.json").read_text())[path]["sha256"]
            assert hashlib.sha256(old.encode()).hexdigest() == baseline
        else:
            old = before.get(path)
            if old is None:
                old = git("show", "HEAD:" + path)
        patch.extend(difflib.unified_diff(old.splitlines(keepends=True),actual.splitlines(keepends=True),
            fromfile="a/"+path if old else "/dev/null",tofile="b/"+path))
    with (LOGS/"od02-only.patch").open("x",encoding="utf-8",newline="\n") as handle:
        handle.writelines(patch)
    print(json.dumps({"parsed_files":len(parsed), "network_calls_inventoried":len(calls), "od02_paths":sorted(EXISTING | NEW)}))


def final():
    spec = importlib.util.spec_from_file_location("od02_runner",HERE/"verification_runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    before=json.loads((LOGS/"preservation-before.json").read_text())
    after=runner.snapshot()
    changes=[p for p,v in before.items() if v != after.get(p)]
    unexpected=[p for p in changes if p not in EXISTING]
    missing=[p for p in DOCS if not (HERE/p).is_file()]
    adr=Path("docs/omegadata_v2/decisions/od02-direct-acquisition-reuse.md")
    broken=[]
    for file in [*(HERE/p for p in DOCS),adr]:
        if not file.is_file():
            missing.append(str(file))
            continue
        for target in re.findall(r"\]\(([^)]+)\)",file.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            resolved=(file.parent/target.split("#")[0].strip("<>")).resolve()
            if not resolved.exists() and resolved != (LOGS/"final-qa.json").resolve():
                broken.append({"file":str(file),"target":target})
    sys.path.insert(0,str(ROOT/"src"))
    from omegadata.track_a.source_rights import load_policy_register
    register=load_policy_register()
    pending=len(register.policies)==13 and all(p.status.value=="PENDING_REVIEW" and not p.permitted_operations and not p.allowed_hosts and not p.permitted_transports and p.approved_by is None for p in register.policies)
    checks={label:json.loads((LOGS/(label+".json")).read_text())["exit_code"] for label in
        ("baseline","targeted-final","final-reviewed","collection-final","lint-reviewed","type-final","pip-final")}
    platforms={label:json.loads((LOGS/(label+".json")).read_text())["exit_code"] for label in ("py311-targeted","linux-targeted")}
    identity={"head":git("rev-parse","HEAD").strip(),"branch":git("branch","--show-current").strip(),
              "main":git("rev-parse","main").strip(),"staged":git("diff","--cached","--name-only").splitlines()}
    correct_identity=identity=={"head":"3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc","branch":"feature/od01-source-rights",
        "main":"d4b5a58f0c50dc348e0d4e1150a725cc6fab5674","staged":[]}
    integrity=not unexpected and not missing and not broken and pending and correct_identity and all(v==0 for v in checks.values())
    data={"utc":datetime.now(UTC).isoformat(),"original_records_checked":len(before),
        "authorized_existing_changes":changes,"new_implementation_paths":sorted(NEW),
        "unexpected_original_changes":unexpected,"missing_docs":missing,"broken_links":broken,
        "pending_sources":13 if pending else None,"approved_sources":0 if pending else None,
        "checks":checks,"blocked_platform_exits":platforms,"git":identity,"integrity_checks_passed":integrity,
        "gatekeeper":"BLOCKED","blocked_dimensions":["3 inherited Windows file-symlink cases require privilege", "Windows Python 3.11 and Linux Python 3.12 missing pytest/dependencies"],
        "independent_source_review":"SOURCE_REFERENCE_PENDING; no live financial certification",
        "signing":"metadata only; no key content opened", "phase_stop":"OD-02 only; no commit/push/release/later phase"}
    save("final-qa.json",data)
    print(json.dumps(data,indent=2))
    return 0 if integrity else 1


if __name__ == "__main__":
    sys.dont_write_bytecode=True
    if sys.argv[1]=="inventory":
        inventory()
    else:
        raise SystemExit(final())
