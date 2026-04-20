from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_CORPUS = REPO_ROOT / "tests/fixtures/official_source/adjustment_reference_corpus.json"
SYNTHETIC_CORPUS = REPO_ROOT / "tests/fixtures/synthetic_manual/adjustment_reference_hand_computed.json"
OUTPUT_PATH = REPO_ROOT / "artifacts/verification/corporate_action_corpus_coverage.json"

REQUIRED_TRANSFORMATIONAL_TYPES = (
    "SPLIT",
    "BONUS",
    "RIGHTS",
    "SPLIT_REVERSE",
    "DEMERGER_PARENT",
    "RIGHTS_RENOUNCE",
    "MERGER_TARGET",
)

STRICT_REQUIRED_OFFICIAL_CASE_LABELS = (
    "reverse_split",
    "demerger_parent_final_stage",
    "sequential_multi_action_chain",
    "correction_or_supersession",
    "later_delisted_post_action_case",
)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def main() -> None:
    official = _read_json(OFFICIAL_CORPUS)
    synthetic = _read_json(SYNTHETIC_CORPUS)

    official_cases = [item for item in official.get("cases", []) if isinstance(item, dict)]
    synthetic_cases = [item for item in synthetic.get("cases", []) if isinstance(item, dict)]

    official_types = {str(item.get("action_type", "")).strip() for item in official_cases}
    synthetic_types = {
        str(action.get("action_type", "")).strip()
        for case in synthetic_cases
        for action in case.get("actions", [])
        if isinstance(action, dict)
    }
    synthetic_labels = {str(case.get("label", "")).strip() for case in synthetic_cases}

    official_labels = {str(item.get("label", "")).strip() for item in official_cases}
    sequential_official_labels = sorted(label for label in official_labels if "SEQUENTIAL" in label.upper())

    strict_official_closure = {
        "reverse_split": "SPLIT_REVERSE" in official_types,
        "demerger_parent_final_stage": "DEMERGER_PARENT" in official_types,
        "sequential_multi_action_chain": len(sequential_official_labels) > 0,
        "correction_or_supersession": any("CORRECTION" in label.upper() or "SUPERSESSION" in label.upper() for label in official_labels),
        "later_delisted_post_action_case": any("DELIST" in label.upper() for label in official_labels),
    }

    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "official_corpus_path": _relative(OFFICIAL_CORPUS),
        "synthetic_corpus_path": _relative(SYNTHETIC_CORPUS),
        "official_case_count": int(official.get("case_count", len(official_cases))),
        "official_transformational_case_count": int(
            official.get("transformational_case_count", 0)
        ),
        "official_transformational_types_present": sorted(
            value for value in official_types if value in REQUIRED_TRANSFORMATIONAL_TYPES
        ),
        "synthetic_transformational_types_present": sorted(
            value for value in synthetic_types if value in REQUIRED_TRANSFORMATIONAL_TYPES
        ),
        "required_transformational_types": list(REQUIRED_TRANSFORMATIONAL_TYPES),
        "strict_required_official_case_labels": list(STRICT_REQUIRED_OFFICIAL_CASE_LABELS),
        "strict_required_official_case_closure": strict_official_closure,
        "strict_required_official_cases_complete": all(strict_official_closure.values()),
        "strict_required_official_cases_missing": [
            label for label, present in strict_official_closure.items() if not present
        ],
        "notes": (
            "This artifact makes the official-vs-synthetic coverage boundary explicit. "
            "Synthetic/manual coverage is useful for adjustment math, but only official-source-backed "
            "coverage closes the frozen transformational proof requirement."
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
