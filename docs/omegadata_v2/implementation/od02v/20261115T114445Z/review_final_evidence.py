"""Amend only this fresh report set; preserve failed command records."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
for report in sorted(HERE.glob("0[0-8]_*.md")):
    body = report.read_text(encoding="utf-8")
    body = body.replace("logs/final-check.json", "logs/final-check-reviewed.json")
    for gate in ("collection", "targeted", "full"):
        body = body.replace("logs/win314-" + gate, "logs/win314-reviewed-" + gate)
    report.write_text(body, encoding="utf-8", newline="\n")

note = """

## Final evidence-check correction

The retained [first mechanical check](logs/final-check.json) exited 1. It
identified a patch link checked before the patch had been created, and two
Windows 3.14 overlay hashes equal to the empty-file hash. Those hashes were
captured during a concurrent copy operation; the original Windows 3.14 matrix
therefore does not establish exact tested-source identity. No empty-file test
result is accepted as an identity proof. The sequential `win314-reviewed`
collection, targeted and complete regression commands replace that matrix as
authoritative evidence and record fresh source hashes. The first check and
all earlier command logs remain unchanged. The already-created patch is now
byte-compared with the current source diff, and the [reviewed final check](logs/final-check-reviewed.json)
must pass before the Gatekeeper verdict is valid. No application or test
changes were made for this evidence correction.
"""
for name in ("03_runtime_test_matrix.md", "04_cross_platform_findings.md", "07_gatekeeper_verdict.md"):
    with (HERE / name).open("a", encoding="utf-8", newline="\n") as output:
        output.write(note)
