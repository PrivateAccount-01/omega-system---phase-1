from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');D=B/'staged2/repo'
p=D/'src/omegadata/universe/snapshots.py';s=p.read_text();a=s.index('            if status == "INCLUDED" and p.require_adjustment:');z=s.index('            if status == "INCLUDED" and p.view == "LIQUIDITY":',a)
s=s[:a]+'''            if status == "INCLUDED" and p.require_adjustment and (
                not obs or any(
                    o.adjustment is None
                    or adjustment_eligible(o.adjustment,o.adjustment_pin,known_at,p.required_profile,p.required_basis).startswith("BLOCKED")
                    or o.adjustment_pin is not None and o.adjustment_pin.raw.raw.listing_id != listing
                    for o in obs
                )
            ):
                status = "BLOCKED_AVAILABILITY"
                reasons.append("BLOCKED_ADJUSTMENT_CONTEXT")
'''+s[z:];p.write_text(s)
p=D/'tests/unit/test_od08_universe.py';s=p.read_text().replace('import pytest','import pytest\nfrom sqlalchemy.exc import IntegrityError',1).replace('pytest.raises(Exception)','pytest.raises(IntegrityError)');p.write_text(s)
