"""Exact rational terms in Decimal, division only under local versioned precision.
Total return: gross single-security ex-close reinvestment, backward Q/(Q+D).
This is an explicit research policy, not an exchange/index certification.
"""

from decimal import Decimal, Inexact, InvalidOperation, localcontext

from omegadata.adjustments.contracts import (
    PRECISION,
    Bonus,
    Conversion,
    Demerger,
    Dividend,
    Factor,
    Lifecycle,
    Merger,
    Policy,
    Rights,
    Split,
    arithmetic_context,
    number,
)


def factor(kind: str, p: object, policy: Policy) -> Factor:
    try:
        with localcontext(arithmetic_context()) as context:
            context.prec = 20480
            n, d, vn, vd = Decimal(1), Decimal(1), Decimal(1), Decimal(1)
            if kind in {"SPLIT", "SPLIT_REVERSE"} and type(p) is Split:
                d = number(p.multiplier)
                vn = d
                if kind == "SPLIT_REVERSE" and d >= 1:
                    raise ValueError("REVERSE_SPLIT_MULTIPLIER")
            elif kind == "BONUS" and type(p) is Bonus:
                old = number(p.existing_shares)
                new = number(p.new_shares)
                n, d = old, old + new
                vn, vd = d, n
            elif kind in {"RIGHTS", "RIGHTS_RENOUNCE"} and type(p) is Rights:
                old, new = number(p.existing_shares), number(p.new_shares)
                issue = number(p.subscription_price, zero=True)
                if (
                    p.reference is None
                    or p.exercise_assumed is not True
                    or p.reference.currency != p.currency
                ):
                    raise ValueError("RIGHTS_REFERENCE_OR_EXERCISE")
                prior = number(p.reference.value)
                n, d = old * prior + new * issue, (old + new) * prior
            elif kind in {"DIVIDEND_CASH", "DIVIDEND_SPECIAL"} and type(p) is Dividend:
                amount = number(p.amount, zero=True)
                if policy.profile != "TOTAL_RETURN":
                    return Factor(
                        "NOT_APPLICABLE",
                        "CASH_DISTRIBUTION_SEPARATE_FROM_PRICE_RETURN",
                        Decimal(1),
                        Decimal(1),
                        Decimal(1),
                        Decimal(1),
                        Decimal(1),
                        Decimal(1),
                    )
                if (
                    p.convention != "EX_CLOSE_GROSS"
                    or p.reinvestment is None
                    or p.reinvestment.currency != p.currency
                ):
                    raise ValueError("DIVIDEND_REINVESTMENT_REQUIRED")
                n = number(p.reinvestment.value)
                d = n + amount
            elif type(p) is Lifecycle and kind in {
                "SUSPENSION",
                "REINSTATEMENT",
                "LISTING",
                "DELISTING",
                "DELISTING_VOLUNTARY",
                "DELISTING_REGULATORY",
            }:
                return Factor(
                    "NOT_APPLICABLE",
                    "LIFECYCLE_NOT_PRICE_FACTOR",
                    Decimal(1),
                    Decimal(1),
                    Decimal(1),
                    Decimal(1),
                    Decimal(1),
                    Decimal(1),
                )
            elif type(p) in {Merger, Demerger, Conversion}:
                return Factor(
                    "UNSUPPORTED_POLICY",
                    "MULTI_SECURITY_ALLOCATION_AND_CONTINUITY_REQUIRE_REVIEWED_METHOD",
                )
            else:
                return Factor("UNSUPPORTED_POLICY", "ACTION_OR_PARAMETER_CONTRACT_UNSUPPORTED")
            if policy.profile in {"RAW", "EXECUTION"}:
                n = d = vn = vd = Decimal(1)
            elif policy.profile == "VOLUME":
                n = d = Decimal(1)
            if policy.direction == "FORWARD":
                n, d, vn, vd = d, n, vd, vn
            context.traps[Inexact] = False
            context.prec = PRECISION
            return Factor("CALCULATED", "EXPLICIT_POLICY_MATH", n, d, n / d, vn, vd, vn / vd)
    except (ValueError, TypeError, InvalidOperation, ZeroDivisionError):
        return Factor("INVALID_PARAMETERS", "MISSING_INVALID_OR_UNSUPPORTED_NUMERICAL_INPUT")
