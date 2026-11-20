"""Independent admission against immutable persisted context, not result.inputs.
Trusted internal development interface; not protection from arbitrary same-process code.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omegadata.adjustments.repository import AdjustmentRepository

from sqlalchemy import select

from omegadata.adjustments import bound_contracts as b
from omegadata.adjustments import contracts as c
from omegadata.adjustments.bound_chain import calculate_bound_chain, validate_history


def pin_context(repository: AdjustmentRepository, pin: b.PinnedCalculation) -> str:
    from omegadata.adjustments.repository import contexts

    selected = validate_history(pin)
    outcome = calculate_bound_chain(pin)
    if outcome.status != "CALCULATED":
        raise ValueError("CALCULATION_CONTEXT_NOT_ACCEPTABLE:" + outcome.calculation.reason)
    inputs = reconciliation_inputs(pin, selected)
    payload = c.canonical(
        {
            "reconciliation_inputs": inputs,
            "context_bindings": json.loads(outcome.context_bindings),
            "expected_result": json.loads(outcome.canonical_json),
            "verification_class": outcome.verification_class,
        }
    )
    with repository.transaction() as connection:
        stored = repository._all(connection)
        expected = {a.action_id: c.canonical(a) for a in selected}
        # Reconcile declared complete history against the independently persisted scoped ledger.
        from omegadata.adjustments.temporal import select_revisions

        scoped = tuple(
            a
            for a in stored
            if a.security_id == pin.history.security_id
            and (a.listing_id is None or a.listing_id == pin.history.listing_id)
            and a.source_id in pin.history.source_scope
            and (a.ex_date is None or pin.history.valid_from <= a.ex_date < pin.history.valid_to)
        )
        actual = {
            a.action_id: c.canonical(a) for a in select_revisions(scoped, pin.context.known_at)
        }
        if actual != expected:
            raise ValueError("PERSISTED_ACTION_HISTORY_INCOMPLETE_OR_CHANGED")
        independent_reconcile(outcome, inputs, {a.action_id: a for a in stored})
        old = connection.scalar(select(contexts.c.payload).where(contexts.c.id == pin.snapshot_id))
        if old is not None:
            if old != payload:
                raise ValueError("IMMUTABLE_CONTEXT_ID_REUSED")
            return pin.snapshot_id
        connection.execute(
            contexts.insert().values(
                id=pin.snapshot_id, payload=payload, digest=c.digest(json.loads(payload))
            )
        )
    return pin.snapshot_id


def append_bound_result(
    repository: AdjustmentRepository,
    result: b.BoundResult,
    context_id: str,
    expected_result_id: str | None = None,
) -> None:
    from omegadata.adjustments.repository import contexts, links, result_context, results

    if (
        type(result) is not b.BoundResult
        or result.status != "CALCULATED"
        or result.publication_eligibility
    ):
        raise ValueError("BOUND_RESULT_ADMISSION")
    if expected_result_id is not None and expected_result_id != result.output_digest:
        raise ValueError("RESULT_DIGEST_IDENTITY_CHANGED")
    with repository.transaction() as connection:
        row = (
            connection.execute(select(contexts).where(contexts.c.id == context_id))
            .mappings()
            .first()
        )
        if row is None or c.digest(json.loads(row["payload"])) != row["digest"]:
            raise ValueError("PINNED_CONTEXT_MISSING_OR_CHANGED")
        pinned = json.loads(row["payload"])
        if c.canonical(pinned["expected_result"]) != result.canonical_json:
            raise ValueError("RESULT_DOES_NOT_RECONCILE_WITH_PERSISTED_CONTEXT")
        # Recheck immutable referenced action bytes independently of result.inputs.
        stored = {a.action_id: a for a in repository._all(connection)}
        independent_reconcile(result, pinned["reconciliation_inputs"], stored)
        for link in result.calculation.adjustment_factor_chain:
            a = stored.get(link.action_revision_id)
            if a is None or c.canonical(a) != link.input_parameters:
                raise ValueError("PERSISTED_ACTION_PROVENANCE_CHANGED")
        old = connection.scalar(
            select(results.c.payload).where(results.c.id == result.output_digest)
        )
        if old is not None:
            if old != result.canonical_json:
                raise ValueError("RESULT_ID_REUSED")
            linked = connection.scalar(
                select(result_context.c.context_id).where(
                    result_context.c.result_id == result.output_digest
                )
            )
            if linked != context_id:
                raise ValueError("RESULT_CONTEXT_MISMATCH")
            return
        connection.execute(
            results.insert().values(
                id=result.output_digest, payload=result.canonical_json, digest=result.output_digest
            )
        )
        for link in result.calculation.adjustment_factor_chain:
            connection.execute(
                links.insert().values(
                    result_id=result.output_digest, action_id=link.action_revision_id
                )
            )
        connection.execute(
            result_context.insert().values(result_id=result.output_digest, context_id=context_id)
        )


def reconciliation_inputs(
    pin: b.PinnedCalculation, selected: tuple[c.Action, ...]
) -> dict[str, Any]:
    """Build from the input pin and actual upstream state, never calculator output."""
    from omegadata.adjustments.bound_chain import (
        active_window,
        execution_state,
        identity_state,
        snapshot_bindings,
    )

    state, past, current = identity_state(pin)
    calendar, tradability, execution, allowed = execution_state(pin, past)
    actions = active_window(selected, pin.raw, pin.policy)
    from omegadata.adjustments.bound_chain import mode
    from omegadata.session_calendar import VerifiedCalendar

    x = pin.context
    calendar_snapshot = VerifiedCalendar(
        tuple(v for v in x.calendar.claims if v.calendar_version == x.calendar_version),
        tuple(v for v in x.calendar.coverage if v.calendar_version == x.calendar_version),
        x.calendar.authority,
    )
    calendar_links = {}
    for action in actions:
        if action.ex_date is None:
            raise ValueError("INDEPENDENT_EX_DATE_UNKNOWN")
        session = calendar_snapshot.query(
            action.exchange,
            action.ex_date,
            x.known_at,
            mode(x),
            calendar_version=x.calendar_version,
        )
        refs = [v.claim_id for v in session.claims]
        if isinstance(action.parameters, c.Rights):
            prior = calendar_snapshot.previous_session(
                action.exchange, action.ex_date, x.known_at, mode(x)
            )
            refs.append(prior.claims[0].claim_id)
        calendar_links[action.action_id] = c.canonical(refs)
    return {
        "raw": c.normalized(pin.raw),
        "policy": c.normalized(pin.policy),
        "actions": tuple(a.action_id for a in actions),
        "calendar_links": calendar_links,
        "bindings": c.normalized(snapshot_bindings(pin, selected, (past, current))),
        "identity_status": state,
        "calendar_status": calendar,
        "tradability_status": tradability,
        "execution_status": execution,
        "execution_allowed": allowed,
        "mode": pin.context.mode,
    }


def independent_reconcile(
    result: b.BoundResult, inputs: dict[str, Any], stored: dict[str, c.Action]
) -> None:
    """Fraction oracle and precise lineage checks independent of factor/chains output."""
    from decimal import ROUND_HALF_UP, Decimal, Inexact, localcontext
    from fractions import Fraction

    inner = result.calculation
    raw = inputs["raw"]
    policy = inputs["policy"]
    bindings = inputs["bindings"]
    if (
        c.canonical(bindings) != result.context_bindings
        or inner.consumer_profile != policy["profile"]
        or inner.original_raw_reference != raw["observation_id"]
        or inner.original_price_basis != "RAW"
        or inner.version != b.BOUND_VERSION
    ):
        raise ValueError("INDEPENDENT_CONTEXT_MISMATCH")
    if (
        result.identity_status,
        result.calendar_status,
        result.tradability_status,
        result.execution_status,
        result.execution_eligibility,
    ) != (
        inputs["identity_status"],
        inputs["calendar_status"],
        inputs["tradability_status"],
        inputs["execution_status"],
        inputs["execution_allowed"],
    ):
        raise ValueError("INDEPENDENT_EXECUTION_STATUS_MISMATCH")
    if (
        result.publication_eligibility
        or inputs["mode"] != "STRICT"
        and result.execution_eligibility
    ):
        raise ValueError("NON_MARKET_FINANCIAL_PROMOTION")
    identities = list(inputs["actions"])
    if [link.action_revision_id for link in inner.adjustment_factor_chain] != identities:
        raise ValueError("INDEPENDENT_REQUIRED_ACTION_SET")
    actions = [stored[n] for n in identities]
    expected_inputs = c.canonical(
        {"bindings": bindings, "raw": raw, "selected_actions": actions, "policy": policy}
    )
    if inner.inputs != expected_inputs:
        raise ValueError("INDEPENDENT_RAW_OR_POLICY_INPUTS")
    fp = fv = Fraction(1)
    for a, link in zip(actions, inner.adjustment_factor_chain, strict=True):
        if (
            link.source_artifact_id != a.source_artifact_identity
            or link.input_parameters != c.canonical(a)
            or c.normalized(link.knowledge_cutoff) != bindings["knowledge_cutoff"]
            or link.raw_observation_reference != raw["observation_id"]
            or link.identity_resolution_id != bindings["identity_resolution_digest"]
            or link.calculation_version != b.BOUND_VERSION
            or link.consumer_profile != policy["profile"]
            or link.calendar_reference != inputs["calendar_links"][a.action_id]
            or link.rounding_policy != bindings["rounding_policy_version"]
        ):
            raise ValueError("INDEPENDENT_ACTION_LINEAGE")
        params = a.parameters
        n = d = vn = vd = Fraction(1)
        expected_status = "CALCULATED"
        if a.action_type in {"SPLIT", "SPLIT_REVERSE"} and isinstance(params, c.Split):
            d = Fraction(params.multiplier)
            vn = d
        elif a.action_type == "BONUS" and isinstance(params, c.Bonus):
            n = Fraction(params.existing_shares)
            d = n + Fraction(params.new_shares)
            vn, vd = d, n
        elif a.action_type in {"RIGHTS", "RIGHTS_RENOUNCE"} and isinstance(params, c.Rights):
            if params.reference is None or params.subscription_price is None:
                raise ValueError("ORACLE_REFERENCE_MISSING")
            old, new, prior, issue = map(
                Fraction,
                (
                    params.existing_shares,
                    params.new_shares,
                    params.reference.value,
                    params.subscription_price,
                ),
            )
            n, d = old * prior + new * issue, (old + new) * prior
        elif a.action_type in {"DIVIDEND_CASH", "DIVIDEND_SPECIAL"} and isinstance(
            params, c.Dividend
        ):
            if policy["profile"] == "TOTAL_RETURN":
                if params.reinvestment is None:
                    raise ValueError("ORACLE_REINVESTMENT_MISSING")
                n = Fraction(params.reinvestment.value)
                d = n + Fraction(params.amount)
            else:
                expected_status = "NOT_APPLICABLE"
        elif isinstance(params, c.Lifecycle):
            expected_status = "NOT_APPLICABLE"
        else:
            raise ValueError("ORACLE_UNSUPPORTED_ECONOMICS")
        if policy["profile"] in {"RAW", "EXECUTION"}:
            n = d = vn = vd = Fraction(1)
        elif policy["profile"] == "VOLUME":
            n = d = Fraction(1)
        if policy["adjustment_basis"] in {"FORWARD_ADJUSTED", "INVERSE_FACTOR_COMPARISON"}:
            n, d, vn, vd = d, n, vd, vn
        f = link.factor
        if (
            f.numerator is None
            or f.denominator is None
            or f.volume_numerator is None
            or f.volume_denominator is None
            or Fraction(f.numerator) / Fraction(f.denominator) != n / d
            or Fraction(f.volume_numerator) / Fraction(f.volume_denominator) != vn / vd
        ):
            raise ValueError("INDEPENDENT_FACTOR_MISMATCH")
        with localcontext(c.arithmetic_context()) as factor_context:
            factor_context.prec = c.PRECISION
            factor_context.traps[Inexact] = False
            price_ratio = n / d
            volume_ratio = vn / vd
            if (
                f.status != expected_status
                or f.price_factor
                != Decimal(price_ratio.numerator) / Decimal(price_ratio.denominator)
                or f.volume_factor
                != Decimal(volume_ratio.numerator) / Decimal(volume_ratio.denominator)
            ):
                raise ValueError("INDEPENDENT_DISPLAYED_FACTOR_OR_STATUS")
        fp *= n / d
        fv *= vn / vd
    with localcontext(c.arithmetic_context()) as math:
        math.prec = c.PRECISION
        math.traps[Inexact] = False

        def decimal(value: Fraction) -> Decimal:
            return Decimal(value.numerator) / Decimal(value.denominator)

        price = Decimal(raw["raw"]["price"])
        volume = Decimal(raw["raw"]["volume"])
        expected_price = (
            price
            if policy["profile"] in {"RAW", "EXECUTION", "VOLUME"}
            else decimal(Fraction(price) * fp).quantize(Decimal(".000001"), rounding=ROUND_HALF_UP)
        )
        expected_volume = (
            volume
            if policy["profile"] in {"RAW", "EXECUTION"}
            else decimal(Fraction(volume) * fv).quantize(Decimal(".0001"), rounding=ROUND_HALF_UP)
        )
        if (
            inner.cumulative_factor,
            inner.cumulative_volume_factor,
            inner.adjusted_price,
            inner.adjusted_volume,
        ) != (decimal(fp), decimal(fv), expected_price, expected_volume):
            raise ValueError("INDEPENDENT_NUMERICAL_RECONCILIATION")
