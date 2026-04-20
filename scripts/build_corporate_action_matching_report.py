from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "tests/fixtures/official_source/corporate_action_matching_benchmark.json"
POLICY_PATH = REPO_ROOT / "config/corporate_action_matching_policy.json"
OUT_PATH = REPO_ROOT / "artifacts/verification/corporate_action_matching_report.json"

ECONOMIC_KEYS = {
    "bonus_ratio_numerator",
    "bonus_ratio_denominator",
    "rights_ratio_numerator",
    "rights_ratio_denominator",
    "issue_price",
    "old_face_value",
    "new_face_value",
    "dividend_per_share",
    "demerger_ratio",
    "swap_ratio",
    "cash_component",
    "spinoff_isin",
    "acquirer_isin",
}


@dataclass(frozen=True)
class MatchingPolicy:
    version: str
    pair_max_gap_days: int
    related_candidate_gap_days: int
    high_similarity_threshold: int
    ambiguous_similarity_threshold: int
    pair_min_score: int
    economic_overlap_bonus: int


@dataclass(frozen=True)
class ActionRow:
    isin: str
    action_type: str
    announcement_date: date | None
    ex_date: date | None
    record_date: date | None
    payload: dict[str, object]


def _parse_date(value: object) -> date | None:
    if value in {None, ""}:
        return None
    return date.fromisoformat(str(value))


def _row(raw: dict[str, object]) -> ActionRow:
    return ActionRow(
        isin=str(raw["isin"]),
        action_type=str(raw["action_type"]),
        announcement_date=_parse_date(raw.get("announcement_date")),
        ex_date=_parse_date(raw.get("ex_date")),
        record_date=_parse_date(raw.get("record_date")),
        payload=dict(raw.get("payload", {})),
    )


def _load_policy() -> MatchingPolicy:
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return MatchingPolicy(
        version=str(payload.get("version", "unknown")),
        pair_max_gap_days=int(payload.get("pair_max_gap_days", 30)),
        related_candidate_gap_days=int(payload.get("related_candidate_gap_days", 10)),
        high_similarity_threshold=int(payload.get("high_similarity_threshold", 60)),
        ambiguous_similarity_threshold=int(payload.get("ambiguous_similarity_threshold", 35)),
        pair_min_score=int(payload.get("pair_min_score", 1)),
        economic_overlap_bonus=int(payload.get("economic_overlap_bonus", 8)),
    )


def _event_date(row: ActionRow) -> date | None:
    return row.ex_date or row.record_date or row.announcement_date


def _numeric_close(left: object, right: object) -> bool:
    try:
        left_dec = Decimal(str(left))
        right_dec = Decimal(str(right))
    except Exception:
        return False
    if right_dec == 0:
        return left_dec == 0
    return abs((left_dec - right_dec) / right_dec) <= Decimal("0.01")


def _payload_score(policy: MatchingPolicy, left: ActionRow, right: ActionRow) -> int:
    left_payload = left.payload or {}
    right_payload = right.payload or {}
    shared = ECONOMIC_KEYS & set(left_payload) & set(right_payload)
    score = 0
    for key in shared:
        left_value = left_payload.get(key)
        right_value = right_payload.get(key)
        if left_value == right_value:
            score += 6
        elif _numeric_close(left_value, right_value):
            score += 4
        else:
            score -= 5
    if shared:
        score += policy.economic_overlap_bonus
    return score


def _economic_overlap_count(left: ActionRow, right: ActionRow) -> int:
    structural = 1 if left.isin == right.isin else 0
    return len(ECONOMIC_KEYS & set(left.payload or {}) & set(right.payload or {})) + structural


def _has_economic_signal(policy: MatchingPolicy, left: ActionRow, right: ActionRow) -> bool:
    return _economic_overlap_count(left, right) > 0 or _payload_score(policy, left, right) > 0


def _relatedness_score(policy: MatchingPolicy, left: ActionRow, right: ActionRow) -> int:
    left_date = _event_date(left)
    right_date = _event_date(right)
    if left_date is None or right_date is None:
        return -5_000
    gap_days = abs((left_date - right_date).days)
    if gap_days > policy.related_candidate_gap_days:
        return -2_000
    score = 50 - (gap_days * 4)
    if left.action_type == right.action_type:
        score += 35
    if left.ex_date and right.ex_date and left.ex_date == right.ex_date:
        score += 20
    if left.record_date and right.record_date and left.record_date == right.record_date:
        score += 10
    if left.announcement_date and right.announcement_date and left.announcement_date == right.announcement_date:
        score += 6
    score += _payload_score(policy, left, right)
    return score


def _pair_score(policy: MatchingPolicy, left: ActionRow, right: ActionRow) -> int:
    if left.action_type != right.action_type:
        return -10_000
    left_date = _event_date(left)
    right_date = _event_date(right)
    if left_date is None or right_date is None:
        return -5_000
    gap_days = abs((left_date - right_date).days)
    if gap_days > policy.pair_max_gap_days:
        return -2_000
    score = 100 - (gap_days * 5)
    if left.ex_date and right.ex_date and left.ex_date == right.ex_date:
        score += 30
    if left.record_date and right.record_date and left.record_date == right.record_date:
        score += 15
    if left.announcement_date and right.announcement_date and left.announcement_date == right.announcement_date:
        score += 10
    score += _payload_score(policy, left, right)
    return score


def main() -> None:
    policy = _load_policy()
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
        pair_score = _pair_score(policy, nse, bse)
        related_score = _relatedness_score(policy, nse, bse)
        if pair_score >= policy.pair_min_score:
            predicted = "match"
        elif (
            related_score >= policy.high_similarity_threshold
            and nse.action_type != bse.action_type
            and _has_economic_signal(policy, nse, bse)
        ):
            predicted = "type_mismatch"
        elif (
            related_score >= policy.ambiguous_similarity_threshold
            and _has_economic_signal(policy, nse, bse)
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
        "policy_version": policy.version,
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
