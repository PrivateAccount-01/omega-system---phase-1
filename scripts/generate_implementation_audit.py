from __future__ import annotations

import json
from pathlib import Path

from omegadata.verification.audit import build_audit_summary


def main() -> None:
    summary = build_audit_summary()
    out_dir = Path("artifacts/verification")
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "implementation_audit.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote audit summary to {json_path}")


if __name__ == "__main__":
    main()
