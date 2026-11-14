"""Read-only final evidence/scope checks; no signing contents read."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime, UTC

root = Path.cwd()
run = Path(__file__).resolve().parent
docs = list(run.glob("*.md")) + [Path("docs/omegadata_v2/decisions/od01-source-policy-reuse.md")]
broken = []
for path in docs:
    prose = re.sub(r"```[^\n]*\n.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    for target in re.findall(r"\]\(([^)]+)\)", prose):
        if target.startswith(("https:", "http:", "#")):
            continue
        if not (path.parent / target.split("#")[0].strip("<>")).exists():
            broken.append({"file": str(path), "target": target})
authorized = {
    "scripts/generate_source_probe_report.py",
    "src/omegadata/pipelines/sequential_pipeline.py",
    "src/omegadata/track_a/download_manager.py",
    "tests/conftest.py",
    "tests/unit/test_operations_layer.py",
    "tests/unit/test_pipeline_and_api.py",
}
before = json.loads((run/"logs/preservation-before.json").read_text())
unexpected = []
checked = 0
for name, previous in before.items():
    if name in authorized:
        continue
    path = Path(name)
    checked += 1
    if not path.is_file():
        unexpected.append(name)
        continue
    stat = path.stat()
    if path.parts[:2] == ("artifacts", "gnupg"):
        unchanged = previous == {"length":stat.st_size, "mtime_ns":stat.st_mtime_ns}
    else:
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        unchanged = previous == {"length":stat.st_size, "sha256":digest}
    if not unchanged:
        unexpected.append(name)
status = subprocess.run(["git","status","--short"], capture_output=True, text=True)
diff = subprocess.run(["git","diff","--no-ext-diff"], capture_output=True, text=True)
(run/"logs/final-status.txt").write_text(status.stdout + status.stderr, encoding="utf-8")
(run/"logs/implementation-final.patch").write_text(diff.stdout, encoding="utf-8")
from omegadata.track_a.source_registry import SOURCE_REGISTRY
from omegadata.track_a.source_rights import load_policy_register
policy = load_policy_register()
default_ok = set(SOURCE_REGISTRY) == {p.source_key for p in policy.policies} and all(
    p.status.value == "PENDING_REVIEW" and not p.permitted_operations and not p.permitted_transports
    and p.approved_by is None and p.terms_sha256 is None for p in policy.policies
)
commands = ["baseline-offline-v3", "targeted-reviewed", "full-offline-reviewed",
            "ruff-reviewed", "mypy-reviewed", "pip-final"]
exits = {label: json.loads((run/"logs"/(label+".json")).read_text())["exit_code"] for label in commands}
required = ["design.md", "source-policy-schema.md", "implementation-diff.md",
            "test-matrix.md", "risk-and-rollback.md", "gatekeeper-verdict.md", "next-phase-request.md"]
missing = [name for name in required if not (run/name).is_file()]
result = {
    "evaluated_at":datetime.now(UTC).isoformat(),
    "branch":subprocess.check_output(["git","branch","--show-current"],text=True).strip(),
    "head_before":"d4b5a58f0c50dc348e0d4e1150a725cc6fab5674",
    "head_after":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
    "protected_original_records_checked":checked,
    "unexpected_original_changes":unexpected,
    "signing_check":"filename/size/mtime only; never opened signing material",
    "broken_document_links":broken,
    "missing_required_documents":missing,
    "registered_sources":len(SOURCE_REGISTRY),
    "policy_records":len(policy.policies),
    "approved_sources":sum(p.status.value=="APPROVED" for p in policy.policies),
    "defaults_exhaustive_pending":default_ok,
    "verification_exit_codes":exits,
}
result["passed"] = not (unexpected or broken or missing) and default_ok and not any(exits.values()) and result["head_before"] == result["head_after"]
(run/"logs/final-qa.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
raise SystemExit(0 if result["passed"] else 1)

