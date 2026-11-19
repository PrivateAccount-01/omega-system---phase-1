from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
p=S/'src/omegadata/adjustments/repository.py';v=p.read_text().replace('    raw = body["raw"]','''    raw = body["raw"]
    expected_actions=sorted((action for action in body["actions"] if action["ex_date"] is None or raw["trade_date"]<action["ex_date"]<=body["valid_at"]),key=lambda action:(action["ex_date"] or raw["trade_date"],action["sequence"] or 0,action["action_id"]))
    if [link.action_revision_id for link in result.adjustment_factor_chain]!=[action["action_id"] for action in expected_actions]:raise ValueError("RESULT_CHAIN_ORDER_MISMATCH")''');p.write_text(v)
p=B/'format_code.py';v=p.read_text().replace("[['format'],", "[['format','--no-cache'],");p.write_text(v)
p=B/'run.py';v=p.read_text().replace('len(newnodes)==95','len(newnodes)==99');p.write_text(v)
p=B/'reviewed-new-tests.json';p.rename(B/'reviewed-new-tests-95-historical.json')
p=B/'new-test-classification-review.json';p.rename(B/'new-test-classification-95-historical.json')
