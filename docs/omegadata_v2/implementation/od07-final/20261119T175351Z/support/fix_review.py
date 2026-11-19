from pathlib import Path
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo'
p=S/'src/omegadata/adjustments/admission.py';v=p.read_text()
v=v.replace("    payload=c.canonical({'context_bindings'", "    inputs=reconciliation_inputs(pin,selected)\n    payload=c.canonical({'reconciliation_inputs':inputs,'context_bindings'")
v=v.replace("        old=connection.scalar(select(contexts.c.payload)", "        independent_reconcile(outcome,inputs,{a.action_id:a for a in stored})\n        old=connection.scalar(select(contexts.c.payload)")
v=v.replace("        for link in result.calculation.adjustment_factor_chain:\n            a=", "        independent_reconcile(result,pinned['reconciliation_inputs'],stored)\n        for link in result.calculation.adjustment_factor_chain:\n            a=")
v=v.replace('    from datetime import date\n','');p.write_text(v)
p=S/'src/omegadata/adjustments/bound_chain.py';v=p.read_text().replace("        selected=validate_history(pin)","        if p.basis_date>x.valid_at or r.raw.trade_date>x.valid_at:refuse('BLOCKED_KNOWLEDGE','OBSERVATION_OR_BASIS_AFTER_VALID_HORIZON')\n        selected=validate_history(pin)")
v=v.replace("for stamp in (a.announcement_at,a.published_at):", "for stamp in (a.announcement_at,a.published_at,a.parameter_known_from):")
v=v.replace("terms.restrictions_status!='CLEAR'", "terms.restrictions_status!='CLEAR' or terms.quantity_convention!='WHOLE_UNITS' or not terms.settlement_policy")
p.write_text(v)
p=S/'tests/unit/test_od07_final.py';v=p.read_text();old="other=replace(a,action_id='b',ex_date=D+timedelta(days=1),parameters=c.Bonus(Decimal(1),Decimal(2)))";assert old in v
v=v.replace(old,"other=replace(a,action_id='b',action_type='BONUS',ex_date=D+timedelta(days=1),parameters=c.Bonus(Decimal(1),Decimal(2)))");p.write_text(v)
