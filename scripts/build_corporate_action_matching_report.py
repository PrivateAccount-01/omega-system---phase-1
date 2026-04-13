from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

from omegadata.domain import CorporateActionType
from omegadata.track_b.corporate_action_matching import CorporateActionMatcher

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests/fixtures/official_source/corporate_action_matching_benchmark.json"
OUT_PATH = REPO_ROOT / "artifacts/verification/corporate_action_matching_report.json"


def _row(raw: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        id=0,
        isin=str(raw["isin"]),
        action_type=CorporateActionType(str(raw["action_type"])),
        announcement_date=None if raw.get("announcement_date") is None else date.fromisoformat(str(raw["announcement_date"])),
        ex_date=None if raw.get("ex_date") is None else date.fromisoformat(str(raw["ex_date"])),
        record_date=None if raw.get("record_date") is None else date.fromisoformat(str(raw["record_date"])),
        payload=dict(raw.get("payload", {})),
    )


def main() -> None:
    matcher = CorporateActionMatcher()
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    results = []
    correct = 0
    positives = 0
    predicted_positive = 0
    true_positive = 0

    for case in cases:
        nse = _row(case["nse"])
        bse = _row(case["bse"])
        pair_score = matcher.score_pair(nse, bse)
        related_score = matcher.relatedness_score(nse, bse)
        if pair_score >= matcher.policy.pair_min_score:
            predicted = "match"
        elif (
            related_score >= matcher.policy.high_similarity_threshold
            and nse.action_type != bse.action_type
            and matcher.has_economic_signal(nse, bse)
        ):
            predicted = "type_mismatch"
        elif (
            related_score >= matcher.policy.ambiguous_similarity_threshold
            and matcher.has_economic_signal(nse, bse)
        ):
            predicted = "ambiguous"
        else:
            predicted = "no_match"

        expected = str(case["expected"])
        if expected in {"match", "type_mismatch"}:
            positives += 1
        if predicted in {"match", "type_mismatch"}:
            predicted_positive += 1
        if predicted == expected:
            correct += 1
        if expected in {"match", "type_mismatch"} and predicted == expected:
            true_positive += 1
        results.append(
            {
                "label": case["label"],
                "expected": expected,
                "predicted": predicted,
                "pair_score": pair_score,
                "related_score": related_score,
                "snapshot_paths": case["snapshot_paths"],
            }
        )

    precision = 0.0 if predicted_positive == 0 else true_positive / predicted_positive
    recall = 0.0 if positives == 0 else true_positive / positives
    artifact = {
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "ok",
        "policy_version": matcher.policy.version,
        "fixture_version": payload.get("version", "unknown"),
        "metrics": {
            "accuracy": 0.0 if not results else correct / len(results),
            "precision": precision,
            "recall": recall,
            "benchmark_passed": precision >= 0.75 and recall >= 0.75,
            "case_count": len(results),
        },
        "results": results,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
