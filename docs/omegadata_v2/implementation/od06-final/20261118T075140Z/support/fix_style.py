from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
p=S/'scripts/od06_database_experiments.py';v=p.read_text().replace('import json','import json\nfrom contextlib import suppress',1)
v=v.replace('lambda: db.append_identity_claim(claim)','lambda claim=claim: db.append_identity_claim(claim)')
v=v.replace('lambda: db.append_identity_correction(child)','lambda child=child: db.append_identity_correction(child)')
v=v.replace('        try:\n            db.append_identity_correction(', '        with suppress(RuntimeError):\n            db.append_identity_correction(').replace('        except RuntimeError:\n            pass\n        assert before', '        assert before')
p.write_text(v)
p=S/'src/omegadata/identity_repository.py';v=p.read_text().replace('{l.security_id for l in ls}','{listing.security_id for listing in ls}')
old='''                if (a.valid_to is None or b.valid_from < a.valid_to) and (
                    b.valid_to is None or a.valid_from < b.valid_to
                ):
                    if (
                        a.known_from is None
                        or b.known_from is None
                        or ((ae is None or b.known_from < ae) and (be is None or a.known_from < be))
                    ):
                        issues.append("OVERLAPPING_CLAIMS:" + a.claim_id + ":" + b.claim_id)'''
new='''                if ((a.valid_to is None or b.valid_from < a.valid_to)
                    and (b.valid_to is None or a.valid_from < b.valid_to)
                    and (a.known_from is None or b.known_from is None
                         or ((ae is None or b.known_from < ae) and (be is None or a.known_from < be)))):
                    issues.append("OVERLAPPING_CLAIMS:" + a.claim_id + ":" + b.claim_id)'''
assert old in v;v=v.replace(old,new);p.write_text(v)
p=S/'tests/unit/test_od06_foundation.py';v=p.read_text().replace('import pytest','import pytest\nfrom sqlalchemy.exc import IntegrityError',1).replace('pytest.raises(Exception)','pytest.raises(IntegrityError)')
start=v.index('        kwargs = dict(');end=v.index('        if case == "missing":',start)
v=v[:start]+'''        kwargs = {
            'evidence_id':e.evidence_id,
            'source_record':{'source_key':'CANARY'},
            'reviewer_attestation':{'review_reference':'forged'},
            'consumer_purpose':'RESEARCH',
            'as_of_knowledge':K,
            'claim_sha256':claim_digest(c),
        }
'''+v[end:];p.write_text(v)
