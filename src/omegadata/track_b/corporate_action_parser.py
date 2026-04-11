from __future__ import annotations

import re
from decimal import Decimal

from omegadata.domain import CorporateActionType


class CorporateActionParser:
    _RATIO_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)")
    _DIVIDEND_PATTERN = re.compile(
        r"\bdividend\b[^0-9]*(?:rs|re)\.?\s*([0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )
    _FACE_VALUE_PATTERN = re.compile(
        r"\bfrom\s+r(?:s|e)\.?\s*([0-9]+(?:\.[0-9]+)?)"
        r".*?\bto\s+r(?:s|e)\.?\s*([0-9]+(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )

    @staticmethod
    def to_decimal(value: str | int | float | None) -> Decimal | None:
        if value in (None, ""):
            return None
        text = str(value).replace(",", "").strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except Exception:
            return None

    @staticmethod
    def map_action_type(text: str) -> CorporateActionType:
        value = text.upper()
        if "BONUS" in value:
            return CorporateActionType.BONUS
        if "BUY BACK" in value or "BUYBACK" in value:
            return CorporateActionType.BUYBACK_OPEN_MARKET
        if "SPLIT" in value and "REVERSE" in value:
            return CorporateActionType.SPLIT_REVERSE
        if "SPLIT" in value:
            return CorporateActionType.SPLIT
        if "RIGHT" in value:
            return CorporateActionType.RIGHTS
        if "DEMERGER" in value:
            return CorporateActionType.DEMERGER_PARENT
        if "MERGER" in value or "AMALGAMATION" in value:
            return CorporateActionType.MERGER_TARGET
        if "DIVIDEND" in value and "SPECIAL" in value:
            return CorporateActionType.DIVIDEND_SPECIAL
        if "DIVIDEND" in value or "INTEREST PAYMENT" in value:
            return CorporateActionType.DIVIDEND_CASH
        return CorporateActionType.UNCLASSIFIED

    def enrich_payload_from_subject(
        self,
        *,
        payload: dict[str, object],
        action_type: CorporateActionType,
        purpose: str,
    ) -> None:
        if not purpose.strip():
            return

        ratio_match = self._RATIO_PATTERN.search(purpose)
        if ratio_match:
            left = self.to_decimal(ratio_match.group(1))
            right = self.to_decimal(ratio_match.group(2))
            if left is not None and right is not None:
                if action_type == CorporateActionType.BONUS:
                    payload.setdefault("bonus_ratio_numerator", str(left))
                    payload.setdefault("bonus_ratio_denominator", str(right))
                if action_type in {CorporateActionType.RIGHTS, CorporateActionType.RIGHTS_RENOUNCE}:
                    payload.setdefault("rights_ratio_numerator", str(left))
                    payload.setdefault("rights_ratio_denominator", str(right))

        if action_type in {CorporateActionType.DIVIDEND_CASH, CorporateActionType.DIVIDEND_SPECIAL}:
            dividend_match = self._DIVIDEND_PATTERN.search(purpose)
            if dividend_match is not None:
                amount = self.to_decimal(dividend_match.group(1))
                if amount is not None:
                    payload.setdefault("dividend_per_share", str(amount))

        if action_type in {CorporateActionType.SPLIT, CorporateActionType.SPLIT_REVERSE}:
            fv_match = self._FACE_VALUE_PATTERN.search(purpose)
            if fv_match is not None:
                old_face_value = self.to_decimal(fv_match.group(1))
                new_face_value = self.to_decimal(fv_match.group(2))
                if old_face_value is not None and new_face_value is not None:
                    payload.setdefault("old_face_value", str(old_face_value))
                    payload.setdefault("new_face_value", str(new_face_value))
