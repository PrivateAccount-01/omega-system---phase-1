from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv/Scripts/python.exe"


def _run(mode: str) -> dict[str, object]:
    subprocess.run(
        [
            str(PYTHON),
            "scripts/generate_source_probe_report.py",
            "--profile-mode",
            mode,
            "--workflow",
            "diagnostic",
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    report = json.loads((REPO_ROOT / "artifacts/verification/source_probe_report.json").read_text(encoding="utf-8"))
    target = REPO_ROOT / f"artifacts/verification/source_probe_report_{mode}.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    deterministic = _run("deterministic")
    full = _run("full")
    comparison = {
        "generated_at": deterministic["generated_at"],
        "deterministic_primary_validated": deterministic["summary"]["bse_primary_validated"],
        "full_primary_validated": full["summary"]["bse_primary_validated"],
        "deterministic_healthy_fallback_count": deterministic["summary"]["healthy_fallback_count"],
        "full_healthy_fallback_count": full["summary"]["healthy_fallback_count"],
    }
    out_path = REPO_ROOT / "artifacts/verification/source_probe_profile_comparison.json"
    out_path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
