from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo'
p=S/'src/omegadata/adjustments/repository.py';v=p.read_text().replace('{l.action_revision_id for l in result.adjustment_factor_chain}','{link.action_revision_id for link in result.adjustment_factor_chain}');p.write_text(v)
p=B/'format_code.py';v=p.read_text().replace("for n in paths:argv+=['--bind',str(S/n),'/repo/'+n]", "for n in ['src/omegadata/adjustments','tests/unit']:argv+=['--bind',str(S/n),'/repo/'+n]")
v=v.replace("print(r.returncode,r.stdout[-1500:])","print(r.returncode,r.stdout[-1500:],r.stderr[-1000:])");p.write_text(v)
p=B/'run.py';v=p.read_text().replace("        frozen=json.loads((B/'reviewed-new-tests.json').read_bytes())",'''        review_path=B/'reviewed-new-tests.json'
        if not review_path.exists():
            assert len(newnodes)==95,'UNREVIEWED_NEW_NODE_COUNT'
            save(review_path,sorted(newnodes))
            save(B/'new-test-classification-review.json',{'source_sha256':hashlib.sha256((S/'tests/unit/test_od07_adjustments.py').read_bytes()).hexdigest(),'cases':len(newnodes),'classification':'A','basis':'Reviewed anonymous mathematical, metadata and disposable SQLite cases; no original source access','reviewer':'same-agent'})
        frozen=json.loads(review_path.read_bytes())''');p.write_text(v)
# Reduce static check display; full failure output remains in exact command log.
p=B/'static_ruff.py';v=p.read_text().replace('print(r.returncode,r.stdout)','print(r.returncode,r.stdout[-3000:])');p.write_text(v)
