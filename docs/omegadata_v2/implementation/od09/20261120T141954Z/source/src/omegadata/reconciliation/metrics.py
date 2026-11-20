"""Exact rational metrics and version-pinned Decimal display; no ambient context."""

from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from fractions import Fraction

from omegadata.adjustments.contracts import number
from omegadata.reconciliation.contracts import MetricResult


def difference(
    left: Decimal, right: Decimal, metric: str, *, tick: Decimal | None = None
) -> MetricResult:
    try:
        number(left, zero=True)
        number(right, zero=True)
        a, b = Fraction(left), Fraction(right)
        signed = a - b
        absolute = abs(signed)
        if metric == "ABSOLUTE":
            value = absolute
        elif metric == "SIGNED":
            value = signed
        elif metric in {"REFERENCE_RELATIVE", "RATIO_DIFFERENCE"}:
            if not b:
                return MetricResult(metric, "UNDEFINED_DENOMINATOR", None, None)
            value = absolute / abs(b)
        elif metric == "SYMMETRIC_RELATIVE":
            if not abs(a) + abs(b):
                return MetricResult(metric, "UNDEFINED_DENOMINATOR", None, None)
            value = 2 * absolute / (abs(a) + abs(b))
        elif metric == "TICK":
            if tick is None:
                return MetricResult(metric, "TICK_UNSPECIFIED", None, None)
            number(tick)
            value = absolute / Fraction(tick)
        else:
            return MetricResult(metric, "UNSUPPORTED_METRIC", None, None)
        with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999, Emax=999)):
            display = Decimal(value.numerator) / Decimal(value.denominator)
        return MetricResult(metric, "DEFINED", (value.numerator, value.denominator), display)
    except (ValueError, ArithmeticError, TypeError):
        return MetricResult(metric, "INVALID_OR_RESOURCE_LIMIT", None, None)
