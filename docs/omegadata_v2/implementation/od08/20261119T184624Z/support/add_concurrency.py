from pathlib import Path
from datetime import UTC,datetime
import hashlib,json
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py';s=p.read_text().replace('listing_id=l.listing_id','listing_id=listing.listing_id').replace('for i, l in enumerate(listings)','for i, listing in enumerate(listings)');p.write_text(s)
with p.open('a') as f:f.write('''

def test_two_connection_competing_corrections(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from omegadata.universe.repository import UniverseRepository
    c,x,m,cov,p,run=setup_case();url='sqlite:///'+str(tmp_path/'competing.sqlite')
    first=UniverseRepository(url,disposable_root=tmp_path);first.seed_context(x,p)
    second=UniverseRepository(url,disposable_root=tmp_path);barrier=Barrier(2)
    def attempt(repository,name):
        child=replace(m,claim=replace(m.claim,membership_id=name,known_from=K+timedelta(days=1),supersedes_membership_id='m-a'),revision_number=2)
        barrier.wait(timeout=5)
        try:repository.append_membership(child);return 'COMMITTED'
        except (ValueError,IntegrityError):return 'REFUSED'
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(attempt,first,'candidate-a');b=pool.submit(attempt,second,'candidate-b');assert sorted((a.result(),b.result()))==['COMMITTED','REFUSED']
    first.close();second.close()
''')
s=p.read_bytes();(B/'concurrency-regression-source.py').write_bytes(s);(B/'concurrency-regression-freeze.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(s).hexdigest(),'cases':88,'classification':'Regression of already implemented BEGIN IMMEDIATE/unique-parent constraints; no fabricated red result'},indent=2))
