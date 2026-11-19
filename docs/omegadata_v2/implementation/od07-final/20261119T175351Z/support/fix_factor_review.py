from pathlib import Path
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');p=B/'staged2/repo/src/omegadata/adjustments/admission.py';s=p.read_text();needle='    actions = active_window(selected, pin.raw, pin.policy)\n    return {'
s=s.replace(needle,'''    actions = active_window(selected, pin.raw, pin.policy)
    from omegadata.session_calendar import VerifiedCalendar
    from omegadata.adjustments.bound_chain import mode
    x=pin.context
    calendar_snapshot=VerifiedCalendar(
        tuple(v for v in x.calendar.claims if v.calendar_version==x.calendar_version),
        tuple(v for v in x.calendar.coverage if v.calendar_version==x.calendar_version),
        x.calendar.authority,
    )
    calendar_links={}
    for action in actions:
        if action.ex_date is None:
            raise ValueError("INDEPENDENT_EX_DATE_UNKNOWN")
        session=calendar_snapshot.query(action.exchange,action.ex_date,x.known_at,mode(x),calendar_version=x.calendar_version)
        refs=[v.claim_id for v in session.claims]
        if isinstance(action.parameters,c.Rights):
            prior=calendar_snapshot.previous_session(action.exchange,action.ex_date,x.known_at,mode(x))
            refs.append(prior.claims[0].claim_id)
        calendar_links[action.action_id]=c.canonical(refs)
    return {''').replace('        "actions": tuple(a.action_id for a in actions),','        "actions": tuple(a.action_id for a in actions),\n        "calendar_links": calendar_links,')
s=s.replace('            or not link.calendar_reference','            or link.calendar_reference != inputs["calendar_links"][a.action_id]\n            or link.rounding_policy != bindings["rounding_policy_version"]')
s=s.replace('        n = d = vn = vd = Fraction(1)','        n = d = vn = vd = Fraction(1)\n        expected_status="CALCULATED"',1)
s=s.replace('        elif isinstance(params, c.Lifecycle):\n            pass','            else:\n                expected_status="NOT_APPLICABLE"\n        elif isinstance(params, c.Lifecycle):\n            expected_status="NOT_APPLICABLE"')
needle='        fp *= n / d\n        fv *= vn / vd'
s=s.replace(needle,'''        with localcontext(c.arithmetic_context()) as factor_context:
            factor_context.prec=c.PRECISION
            factor_context.traps[Inexact]=False
            price_ratio=n/d
            volume_ratio=vn/vd
            if (
                f.status!=expected_status
                or f.price_factor!=Decimal(price_ratio.numerator)/Decimal(price_ratio.denominator)
                or f.volume_factor!=Decimal(volume_ratio.numerator)/Decimal(volume_ratio.denominator)
            ):
                raise ValueError("INDEPENDENT_DISPLAYED_FACTOR_OR_STATUS")
        fp *= n / d
        fv *= vn / vd''')
p.write_text(s)
# Archive the earlier reviewed80node inventory instead of overwriting evidence.
for n in ['reviewed-new-tests.json','new-test-classification-review.json']:
 old=B/n;old.rename(B/(old.stem+'-80-historical'+old.suffix))
p=B/'run.py';s=p.read_text().replace('assert len(newnodes)==80','assert len(newnodes)==84');p.write_text(s)
