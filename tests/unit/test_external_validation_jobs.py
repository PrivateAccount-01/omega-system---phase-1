from __future__ import annotations

from datetime import date
from decimal import Decimal

from omegadata.track_b.cross_source_validation import CrossSourceValidator


def test_monthly_flow_consistency_warn_band(db_session) -> None:
    outcome = CrossSourceValidator().validate_monthly_flow_consistency(
        db_session,
        data_date=date(2026, 3, 31),
        nse_net_flow=Decimal("107"),
        rbi_net_flow=Decimal("100"),
    )
    assert outcome.result.value == "WARN"


def test_secondary_source_validations_fail_when_outside_tolerance(db_session) -> None:
    validator = CrossSourceValidator()
    iv = validator.validate_implied_volatility_spot_check(
        db_session,
        isin="INE009A01021",
        data_date=date(2026, 3, 31),
        omega_iv=Decimal("0.30"),
        reference_iv=Decimal("0.20"),
    )
    adjusted = validator.validate_secondary_adjusted_price(
        db_session,
        isin="INE009A01021",
        data_date=date(2026, 3, 31),
        omegadata_adjusted_price=Decimal("125"),
        secondary_adjusted_price=Decimal("100"),
    )
    assert iv.result.value == "FAIL"
    assert adjusted.result.value == "FAIL"
