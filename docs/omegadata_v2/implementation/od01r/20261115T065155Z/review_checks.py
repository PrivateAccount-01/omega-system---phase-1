"""Read-only final evidence checks. GnuPG content is never read."""
from __future__ import annotations
import ast
import hashlib
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
ALLOWED = {
    "OMEGADATA_AGENTS.md", "src/omegadata/track_a/source_rights.py",
    "src/omegadata/track_a/download_manager.py", "src/omegadata/track_a/orchestration.py",
    "scripts/generate_source_probe_report.py", "scripts/load_nse_fo_into_pipeline_db.py",
    "scripts/backfill_nse_equity_history.py", "scripts/probe_endpoints.py",
    "scripts/probe_bse_urls.py", "scripts/generate_source_probe_matrix.py",
}

def save(name, value):
    with (LOGS / name).open("x", encoding="utf-8") as out:
        json.dump(value, out, indent=2)

def symbol(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return symbol(node.value) + "." + node.attr
    return "?"

def inventory():
    calls = []
    class Visitor(ast.NodeVisitor):
        def __init__(self, path):
            self.path, self.scope = path, []
        def visit_FunctionDef(self, node):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_Call(self, node):
            name = symbol(node.func)
            if (name.startswith(("httpx.", "requests.", "subprocess.", "socket."))
                or name in {"urlopen", "client.get", "client.post"}
                or name.endswith((".download", ".ingest_raw_source", ".probe_source_candidates", ".fetch_bse_stockreach_graph"))):
                calls.append({"file": self.path.as_posix(), "line": node.lineno,
                              "function": ".".join(self.scope) or "module", "call": name})
            self.generic_visit(node)
    for folder in ("src", "scripts", "airflow"):
        for path in sorted(Path(folder).rglob("*.py")):
            Visitor(path).visit(ast.parse(path.read_text(encoding="utf-8-sig")))
    workflows = [{"file":p.as_posix(), "sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in Path(".github").rglob("*") if p.is_file()]
    save("source-entry-inventory.json", {"utc":datetime.now(UTC).isoformat(), "calls":calls,
         "workflow_files":workflows, "scope":"AST source/scripts/airflow; source access classification in 01_review_findings.md"})

def final():
    qa_name = "final-qa-reviewed.json"
    spec = importlib.util.spec_from_file_location("od01r_runner", HERE / "verification_runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    before = json.loads((LOGS / "preservation-before.json").read_text())
    after = runner.snapshot()
    unexpected = [p for p, state in before.items() if p not in ALLOWED and state != after.get(p)]
    changes = [p for p, state in before.items() if state != after.get(p)]
    required = ["00_baseline_identity.md", "01_review_findings.md", "02_contract_and_design.md",
                "03_test_matrix.md", "04_implementation_diff.md", "05_risks_rollback.md",
                "06_gatekeeper_verdict.md", "07_next_phase_request.md"]
    missing = [p for p in required if not (HERE / p).is_file()]
    broken = []
    for file in [*(HERE / p for p in required), Path("AGENTS.md"), Path("docs/omegadata_v2/decisions/od01r-policy-boundary.md")]:
        if not file.is_file():
            missing.append(str(file))
            continue
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            path = target.split("#")[0].strip("<>")
            resolved = (file.parent / path).resolve()
            planned = {LOGS / qa_name, LOGS / "implementation.patch"}
            if not resolved.exists() and resolved not in planned:
                broken.append({"file":str(file), "target":target})
    sys.path.insert(0, str(ROOT / "src"))
    from omegadata.track_a.source_rights import load_policy_register
    from omegadata.track_a.source_registry import SOURCE_REGISTRY
    register = load_policy_register()
    checks = {}
    for label in ("baseline-offline-v2", "targeted-reviewed", "full-reviewed", "collection-reviewed", "ruff-reviewed", "mypy-reviewed", "pip-reviewed"):
        checks[label] = json.loads((LOGS / (label + ".json")).read_text())["exit_code"]
    git = {}
    for label, args in {"head":["rev-parse","HEAD"], "branch":["branch","--show-current"],
                        "main":["rev-parse","main"], "status":["status","--short"],
                        "scope":["diff","--name-only"], "staged":["diff","--cached","--name-only"]}.items():
        result = subprocess.run(["git", *args], capture_output=True, text=True)
        git[label] = {"exit_code":result.returncode,"stdout":result.stdout,"stderr":result.stderr}
    patch = subprocess.run(["git", "diff", "--binary", "--", *sorted(ALLOWED)], capture_output=True)
    patch_path = LOGS / "implementation.patch"
    if patch_path.exists():
        if patch_path.read_bytes() != patch.stdout:
            raise RuntimeError("Production patch changed since first preservation check")
    else:
        with patch_path.open("xb") as out:
            out.write(patch.stdout)
    pending = len(register.policies) == len(SOURCE_REGISTRY) == 13 and all(
        p.status.value == "PENDING_REVIEW" and not p.permitted_operations and not p.allowed_hosts
        and not p.permitted_transports and p.approved_by is None for p in register.policies)
    passed = not unexpected and not missing and not broken and pending and all(code == 0 for code in checks.values())
    passed = passed and set(git["scope"]["stdout"].splitlines()) == ALLOWED and not git["staged"]["stdout"]
    passed = passed and git["head"]["stdout"].strip() == "3b5c0fffdd5ecd28a9318a51b43784d3ba133dcc"
    passed = passed and git["branch"]["stdout"].strip() == "feature/od01-source-rights"
    data = {"utc":datetime.now(UTC).isoformat(), "original_records_checked":len(before),
            "changes":changes,"unexpected_original_changes":unexpected,"missing_docs":missing,
            "broken_links":broken,"pending_sources":13 if pending else None,"checks":checks,
            "git":git,"passed":passed,"signing":"metadata only; no key contents opened"}
    save(qa_name, data)
    # Planned self-output links are now actual files; do not claim success if
    # creation or post-write existence fails.
    for file in [HERE / p for p in required]:
        for target in re.findall(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (file.parent / target.split("#")[0].strip("<>")).exists()
    print(json.dumps(data, indent=2))
    return 0 if passed else 1

if __name__ == "__main__":
    sys.dont_write_bytecode = True
    if sys.argv[1] == "inventory":
        inventory()
    else:
        raise SystemExit(final())
