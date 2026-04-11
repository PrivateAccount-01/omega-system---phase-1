from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from omegadata.db.models import ConfirmedCorporateAction, PriceRecord
from omegadata.domain import ConfidenceLevel, CorporateActionType, Exchange
from omegadata.track_b.adjustment_engine import PriceAdjustmentEngine

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "adjustment_reference_corpus.json"
PROJECT_ROOT = FIXTURE_PATH.parents[2]


def _price(
    db_session,
    *,
    isin: str,
    trade_date: date,
    close: str,
    exchange: Exchange = Exchange.NSE,
    volume: str = "100",
) -> None:
    close_dec = Decimal(close)
    existing = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.isin == isin)
        .where(PriceRecord.exchange == exchange)
        .where(PriceRecord.trade_date == trade_date)
    )
    if existing is None:
        db_session.add(
            PriceRecord(
                isin=isin,
                exchange=exchange,
                trade_date=trade_date,
                open_price=close_dec,
                high_price=close_dec,
                low_price=close_dec,
                close_price=close_dec,
                volume=Decimal(volume),
                raw_source="nse_bhavcopy" if exchange == Exchange.NSE else "bse_stockreach_graph",
                confidence_score=Decimal("1.00"),
            )
        )
        return
    existing.open_price = close_dec
    existing.high_price = close_dec
    existing.low_price = close_dec
    existing.close_price = close_dec
    existing.volume = Decimal(volume)


def _action(
    *,
    isin: str,
    action_type: CorporateActionType,
    ex_date: date,
    parameters: dict[str, object],
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
) -> ConfirmedCorporateAction:
    return ConfirmedCorporateAction(
        isin=isin,
        action_type=action_type,
        confidence=confidence,
        announcement_date=ex_date,
        ex_date=ex_date,
        record_date=ex_date,
        parameters=parameters,
        source_preference=Exchange.NSE,
        superseded=False,
    )


def test_reference_corpus_official_nse_source_pack_cases(db_session) -> None:
    corpus = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert corpus["case_count"] == len(corpus["cases"])
    assert corpus["case_count"] >= 10

    for case in corpus["cases"]:
        assert case["label"]
        assert (PROJECT_ROOT / case["snapshot_path"]).exists()
        for path in case["price_paths"]:
            assert (PROJECT_ROOT / path).exists()
        for row in case["prices"]:
            _price(
                db_session,
                isin=case["isin"],
                trade_date=date.fromisoformat(row["trade_date"]),
                close=row["close"],
                volume=row["volume"],
            )
        db_session.add(
            _action(
                isin=case["isin"],
                action_type=CorporateActionType(case["action_type"]),
                ex_date=date.fromisoformat(case["ex_date"]),
                parameters=dict(case["parameters"]),
            )
        )

    db_session.flush()

    engine = PriceAdjustmentEngine()
    for case in corpus["cases"]:
        engine.recompute_adjusted_series(db_session, case["isin"])
        for assertion in case["assertions"]:
            row = db_session.scalar(
                select(PriceRecord)
                .where(PriceRecord.isin == case["isin"])
                .where(PriceRecord.trade_date == date.fromisoformat(assertion["trade_date"]))
            )
            assert row is not None
            assert Decimal(str(row.adjusted_close_price)) == Decimal(assertion["expected_adjusted_close"])
            assert Decimal(str(row.adjusted_volume)) == Decimal(assertion["expected_adjusted_volume"])
            assert Decimal(str(row.cumulative_price_factor)) == Decimal(
                assertion["expected_cumulative_price_factor"]
            )
            assert Decimal(str(row.cumulative_volume_factor)) == Decimal(
                assertion["expected_cumulative_volume_factor"]
            )

    bonus_pre_row = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.isin == "INE219Y01018")
        .where(PriceRecord.trade_date == date(2026, 4, 7))
    )
    assert bonus_pre_row is not None
    assert bonus_pre_row.adjustment_chain[0]["action_type"] == "BONUS"
    assert bonus_pre_row.adjustment_chain[0]["ca_confidence"] == "HIGH"


def test_reference_corpus_multiple_action_chain_and_demerger_finalization(db_session) -> None:
    _price(db_session, isin="CASEMULTI01", trade_date=date(2026, 4, 1), close="1000")
    _price(db_session, isin="CASEMULTI01", trade_date=date(2026, 4, 2), close="500")
    _price(db_session, isin="CASEMULTI01", trade_date=date(2026, 4, 3), close="250")
    db_session.add_all(
        [
            _action(
                isin="CASEMULTI01",
                action_type=CorporateActionType.BONUS,
                ex_date=date(2026, 4, 2),
                parameters={"bonus_ratio_numerator": "1", "bonus_ratio_denominator": "1"},
            ),
            _action(
                isin="CASEMULTI01",
                action_type=CorporateActionType.SPLIT,
                ex_date=date(2026, 4, 3),
                parameters={"old_face_value": "10", "new_face_value": "5"},
            ),
        ]
    )

    _price(db_session, isin="CASEDEMFNL1", trade_date=date(2026, 4, 1), close="100")
    _price(db_session, isin="CASEDEMFNL1", trade_date=date(2026, 4, 2), close="70")
    _price(
        db_session,
        isin="CASESPINFNL1",
        trade_date=date(2026, 4, 2),
        close="30",
    )
    db_session.add(
        _action(
            isin="CASEDEMFNL1",
            action_type=CorporateActionType.DEMERGER_PARENT,
            ex_date=date(2026, 4, 2),
            parameters={
                "spinoff_isin": "CASESPINFNL1",
                "parent_value_pre_demerger": "100",
                "spinoff_value": "20",
            },
            confidence=ConfidenceLevel.MEDIUM,
        )
    )

    engine = PriceAdjustmentEngine()
    engine.recompute_adjusted_series(db_session, "CASEMULTI01")
    engine.recompute_adjusted_series(db_session, "CASEDEMFNL1")

    multi_row = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.isin == "CASEMULTI01")
        .where(PriceRecord.trade_date == date(2026, 4, 1))
    )
    demerger_row = db_session.scalar(
        select(PriceRecord)
        .where(PriceRecord.isin == "CASEDEMFNL1")
        .where(PriceRecord.trade_date == date(2026, 4, 1))
    )
    assert multi_row is not None
    assert demerger_row is not None
    assert Decimal(str(multi_row.adjusted_close_price)) == Decimal("250.000000")
    assert Decimal(str(demerger_row.adjusted_close_price)) == Decimal("70.000000")
    assert demerger_row.adjustment_chain[0]["demerger_adjustment_stage"] == "FINAL"
