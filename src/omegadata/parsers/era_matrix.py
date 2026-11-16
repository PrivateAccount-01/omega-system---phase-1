"""Retain reference ambiguity; never dispatch production parsers by a guessed era."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from omegadata.parsers.reference_evidence import ReferenceError, ReferenceResult


@dataclass(frozen=True)
class EraCell:
    business_date: date
    state: str
    reference_ids: tuple[str, ...]
    supported: bool = False


def build_matrix(
    references: tuple[ReferenceResult, ...], dates: tuple[date, ...]
) -> tuple[EraCell, ...]:
    if (
        len(references) > 16
        or len(dates) > 64
        or len({r.evidence.reference_id for r in references}) != len(references)
    ):
        raise ReferenceError("MATRIX_BUDGET_OR_IDENTITY")
    cells = []
    for business_date in dates:
        if type(business_date) is not date:
            raise ReferenceError("DATE_INVALID")
        applicable = tuple(
            r
            for r in references
            if r.evidence.effective_from <= business_date.isoformat()
            and (
                r.evidence.effective_to is None
                or business_date.isoformat() <= r.evidence.effective_to
            )
        )
        state = "UNKNOWN"
        if applicable:
            state = "PENDING_REFERENCE"
        if len(applicable) > 1:
            state = "OVERLAP"
            claims: dict[tuple[str, str], set[str]] = {}
            for ref in applicable:
                declaration = ref.evidence.model_dump(
                    mode="json",
                    include={
                        "format_id",
                        "document_sha256",
                        "mime",
                        "semantics",
                        "effective_from",
                        "effective_to",
                        "announced_on",
                    },
                )
                claims.setdefault((ref.evidence.document_id, ref.evidence.version), set()).add(
                    json.dumps(declaration, sort_keys=True, separators=(",", ":"))
                )
            if any(len(formats) > 1 for formats in claims.values()):
                state = "CONFLICT"
        cells.append(
            EraCell(
                business_date, state, tuple(sorted(r.evidence.reference_id for r in applicable))
            )
        )
    return tuple(cells)
