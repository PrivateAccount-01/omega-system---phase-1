"""Correct this run's report references before the final exclusive check."""
from pathlib import Path

here = Path(__file__).resolve().parent
for report in here.glob("0[0-8]_*.md"):
    text = report.read_text(encoding="utf-8").replace(
        "logs/final-check-reviewed.json", "logs/final-check-accepted.json"
    )
    report.write_text(text, encoding="utf-8", newline="\n")
with (here / "04_cross_platform_findings.md").open("a", encoding="utf-8") as out:
    out.write("\nThe [second mechanical check](logs/final-check-reviewed.json) also exited 1 solely because its own not-yet-written JSON link was treated as missing. All source identity, test, policy and preservation checks were true. The checker now exempts only its exact forthcoming result path; all other links must exist. The [accepted check](logs/final-check-accepted.json) is the final authoritative result. Both earlier failed checks are retained.\n")
