from pathlib import Path
import hashlib,json
from datetime import datetime,UTC
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');p=B/'staged2/repo/tests/unit/test_od07_final.py'
with p.open('a') as f:f.write('''

@pytest.mark.parametrize("case", ["price-factor", "volume-factor", "factor-status", "calendar-link"])
def test_independent_factor_and_calendar_admission(case, tmp_path, monkeypatch):
    from omegadata.adjustments import admission
    from omegadata.adjustments.repository import AdjustmentRepository
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    out=run(pin)
    link=out.calculation.adjustment_factor_chain[0]
    if case=="price-factor":
        link=replace(link,factor=replace(link.factor,price_factor=Decimal(999)))
    elif case=="volume-factor":
        link=replace(link,factor=replace(link.factor,volume_factor=Decimal(999)))
    elif case=="factor-status":
        link=replace(link,factor=replace(link.factor,status="NOT_APPLICABLE"))
    else:
        link=replace(link,calendar_reference='["unrelated-session"]')
    bad=replace(out,calculation=replace(out.calculation,adjustment_factor_chain=(link,)))
    monkeypatch.setattr(admission,"calculate_bound_chain",lambda ignored:bad)
    db=AdjustmentRepository("sqlite:///:memory:",disposable_root=tmp_path)
    db.append_action(a)
    with pytest.raises(ValueError):
        db.pin_context(pin)
''')
raw=p.read_bytes();(B/'factor-review-source.py').write_bytes(raw)
(B/'factor-review-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'test_sha256':hashlib.sha256(raw).hexdigest(),'cases':['price-factor','volume-factor','factor-status','calendar-link'],'expected_baseline':'independent admission erroneously permits producer defect; no real data'},indent=2))
