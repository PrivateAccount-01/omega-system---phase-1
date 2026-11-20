from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/src/omegadata/universe/snapshots.py';s=p.read_text().replace('security_ids = sorted({v.security_id for v in selected_listings})','security_ids = sorted({v.security_id for v in selected_listings if v.security_id is not None})');p.write_text(s)
