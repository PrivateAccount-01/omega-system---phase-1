"""Pure calibration over supplied pinned samples; never loads or authenticates data."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from typing import cast

from omegadata.adjustments.contracts import number
from omegadata.identity import query_time
from omegadata.reconciliation.contracts import TolerancePolicy, fingerprint


@dataclass(frozen=True)
class CalibrationSample:
    sample_id: str
    lineage_pair: tuple[str, str]
    discrepancy: Decimal | None
    known_from: datetime | None
    period: str
    liquidity_bucket: str
    expected_anomaly: bool | None = None
    independent: bool = False
    evidence_class: str = "NON_MARKET_MATH_CONTROL"


@dataclass(frozen=True)
class CalibrationResult:
    status: str
    sample_digest: str
    training_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    rejected_ids: tuple[str, ...]
    warning_threshold: Decimal | None
    failure_threshold: Decimal | None
    false_positive_count: int
    false_negative_count: int
    unlabeled_count: int
    authenticity: str = "BLOCKED_CALIBRATION"
    methodology: str = "nearest-rank-p90-p99/no-outlier-deletion/v1"


def calibrate(
    samples: tuple[CalibrationSample, ...],
    cutoff: datetime,
    *,
    minimum_samples: int,
    liquidity_bucket: str,
) -> CalibrationResult:
    query_time(cutoff)
    if type(samples) is not tuple or len(samples) > 10000 or not 2 <= minimum_samples <= 10000:
        raise ValueError("CALIBRATION_BUDGET")
    if len({s.sample_id for s in samples}) != len(samples):
        raise ValueError("DUPLICATE_CALIBRATION_SAMPLE")
    accepted = []
    rejected = []
    pairs = set()
    for s in samples:
        if s.known_from is not None:
            query_time(s.known_from)
        if s.discrepancy is not None:
            number(s.discrepancy, zero=True)
        if (
            s.discrepancy is None
            or s.known_from is None
            or s.known_from > cutoff
            or s.liquidity_bucket != liquidity_bucket
            or not s.independent
            or s.lineage_pair[0] == s.lineage_pair[1]
            or s.period not in {"TRAIN", "VALIDATION"}
        ):
            rejected.append(s.sample_id)
            continue
        key = (s.lineage_pair, s.period)
        if key in pairs:
            raise ValueError("DEPENDENT_DUPLICATE_CALIBRATION_PAIR")
        pairs.add(key)
        accepted.append(s)
    train = sorted(
        (s for s in accepted if s.period == "TRAIN"), key=lambda s: (s.discrepancy, s.sample_id)
    )
    validation = tuple(s for s in accepted if s.period == "VALIDATION")

    def result(
        status: str,
        w: Decimal | None = None,
        f: Decimal | None = None,
        fp: int = 0,
        fn: int = 0,
        unknown: int = 0,
    ) -> CalibrationResult:
        return CalibrationResult(
            status,
            fingerprint(samples),
            tuple(s.sample_id for s in train),
            tuple(s.sample_id for s in validation),
            tuple(sorted(rejected)),
            w,
            f,
            fp,
            fn,
            unknown,
        )

    if len(train) < minimum_samples or not validation:
        return result("BLOCKED_SAMPLE_ADEQUACY")

    def quantile(n: int, d: int) -> Decimal:
        index = max(0, (len(train) * n + d - 1) // d - 1)
        return cast(Decimal, train[index].discrepancy)

    warning, failure = quantile(9, 10), quantile(99, 100)
    fp = fn = unknown = 0
    for s in validation:
        if s.expected_anomaly is None:
            unknown += 1
            continue
        predicted = Fraction(cast(Decimal, s.discrepancy)) > Fraction(warning)
        fp += int(predicted and not s.expected_anomaly)
        fn += int(not predicted and s.expected_anomaly)
    return result("PROVISIONAL_ALGORITHM_RESULT", warning, failure, fp, fn, unknown)


def select_policy(
    policies: tuple[TolerancePolicy, ...], valid_at: date, known_at: datetime
) -> TolerancePolicy:
    eligible = tuple(
        p
        for p in policies
        if p.effective_from <= valid_at
        and (p.effective_to is None or valid_at < p.effective_to)
        and p.known_from <= known_at
        and (p.known_to is None or known_at < p.known_to)
        and (p.calibration_knowledge_cutoff is None or p.calibration_knowledge_cutoff <= known_at)
    )
    if len(eligible) != 1:
        raise ValueError("EXACT_TOLERANCE_POLICY_REQUIRED")
    return eligible[0]
