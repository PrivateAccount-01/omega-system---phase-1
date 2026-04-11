from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from omegadata.db.models import CorporateActionStaging

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
class MatchedCorporateActionPair:
    nse: CorporateActionStaging
    bse: CorporateActionStaging
    score: int


class CorporateActionMatcher:
    @staticmethod
    def event_date(row: CorporateActionStaging) -> date | None:
        return row.ex_date or row.record_date or row.announcement_date

    @staticmethod
    def _numeric_close(left: object, right: object) -> bool:
        try:
            left_dec = Decimal(str(left))
            right_dec = Decimal(str(right))
        except Exception:
            return False
        if right_dec == 0:
            return left_dec == 0
        return abs((left_dec - right_dec) / right_dec) <= Decimal("0.01")

    def _payload_score(self, left: CorporateActionStaging, right: CorporateActionStaging) -> int:
        left_payload = left.payload or {}
        right_payload = right.payload or {}
        shared = ECONOMIC_KEYS & set(left_payload) & set(right_payload)
        score = 0
        for key in shared:
            left_value = left_payload.get(key)
            right_value = right_payload.get(key)
            if left_value == right_value:
                score += 6
            elif self._numeric_close(left_value, right_value):
                score += 4
            else:
                score -= 5
        return score

    def score_pair(self, left: CorporateActionStaging, right: CorporateActionStaging) -> int:
        if left.action_type != right.action_type:
            return -10_000
        left_date = self.event_date(left)
        right_date = self.event_date(right)
        if left_date is None or right_date is None:
            return -5_000
        gap_days = abs((left_date - right_date).days)
        if gap_days > 30:
            return -2_000
        score = 100 - (gap_days * 5)
        if left.ex_date and right.ex_date and left.ex_date == right.ex_date:
            score += 30
        if left.record_date and right.record_date and left.record_date == right.record_date:
            score += 15
        if left.announcement_date and right.announcement_date and left.announcement_date == right.announcement_date:
            score += 10
        score += self._payload_score(left, right)
        return score

    def match_pairs(
        self,
        nse_rows: list[CorporateActionStaging],
        bse_rows: list[CorporateActionStaging],
    ) -> tuple[list[MatchedCorporateActionPair], list[CorporateActionStaging], list[CorporateActionStaging]]:
        candidates: list[MatchedCorporateActionPair] = []
        for nse in nse_rows:
            for bse in bse_rows:
                score = self.score_pair(nse, bse)
                if score > 0:
                    candidates.append(MatchedCorporateActionPair(nse=nse, bse=bse, score=score))
        candidates.sort(key=lambda pair: pair.score, reverse=True)

        matched_nse_ids: set[int] = set()
        matched_bse_ids: set[int] = set()
        pairs: list[MatchedCorporateActionPair] = []
        for candidate in candidates:
            if candidate.nse.id in matched_nse_ids or candidate.bse.id in matched_bse_ids:
                continue
            pairs.append(candidate)
            matched_nse_ids.add(candidate.nse.id)
            matched_bse_ids.add(candidate.bse.id)

        unmatched_nse = [row for row in nse_rows if row.id not in matched_nse_ids]
        unmatched_bse = [row for row in bse_rows if row.id not in matched_bse_ids]
        return pairs, unmatched_nse, unmatched_bse
