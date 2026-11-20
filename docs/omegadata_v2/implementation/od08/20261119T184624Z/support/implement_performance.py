from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');S=B/'staged2/repo'
(S/'scripts/od08_structural_experiments.py').write_text('''"""Bounded NON_MARKET bookkeeping benchmark; no market observations or replay."""
from __future__ import annotations
import json,sys,time,statistics,tracemalloc
from dataclasses import replace
from datetime import UTC,datetime,timedelta
from pathlib import Path
from typing import Any

def run(config:dict[str,Any])->int:
    import od05x_isolated_runner as boundary
    boundary.assert_boundary()
    from test_od08_universe import setup_case,D,K
    from omegadata.identity import Issuer,Security,Listing,MemoryIdentityRepository
    from omegadata.universe.snapshots import get_universe_as_of,replay_universe_decisions
    from omegadata.universe.repository import UniverseRepository
    from omegadata.universe.temporal import get_membership_history
    c,x,member,cov,policy,query=setup_case()
    count=200
    securities=tuple(Security('control-security-'+str(i),'issuer-a') for i in range(count))
    listings=tuple(Listing('control-listing-'+str(i),securities[i].security_id,'CANARY-X') for i in range(count))
    claims=tuple(replace(x.identity.claims[0],claim_id='identity-'+str(i),listing_id=listings[i].listing_id,symbol='TOKEN-'+str(i)) for i in range(count))
    identity=MemoryIdentityRepository((Issuer('issuer-a'),),securities,listings,claims)
    members=tuple(replace(member,claim=replace(member.claim,membership_id='membership-'+str(i),symbol=claims[i].symbol),event_id='event-'+str(i),security_id=securities[i].security_id,listing_id=listings[i].listing_id) for i in range(count))
    expected=tuple(sorted(s.security_id for s in securities))
    x=replace(x,identity=identity,memberships=members,coverage=(replace(cov,expected_member_identities=expected,ending_member_identities=expected),))
    root=Path('/work/job');root.mkdir();start=datetime.now(UTC).isoformat();tracemalloc.start();samples=[]
    for _ in range(3):
        tick=time.perf_counter();out=get_universe_as_of(x,D,K,policy,x.source_snapshot_id);samples.append(time.perf_counter()-tick);assert out.included_member_ids==expected
    dbpath=root/'bookkeeping.sqlite';url='sqlite:///'+str(dbpath);db=UniverseRepository(url,disposable_root=root)
    tick=time.perf_counter();db.seed_context(x,policy);insert=time.perf_counter()-tick
    tick=time.perf_counter();db.pin_context('pin',x,D,K,policy);db.admit_snapshot('pin',out);admission=time.perf_counter()-tick
    tick=time.perf_counter();history=get_membership_history(x,members[0].event_id);history_time=time.perf_counter()-tick;assert len(history)==1
    correction=replace(members[0],claim=replace(members[0].claim,membership_id='correction',known_from=K+timedelta(days=1),supersedes_membership_id=members[0].revision_id),revision_number=2)
    tick=time.perf_counter();db.append_membership(correction);append=time.perf_counter()-tick
    changed=replace(x,memberships=(*members,correction));assert get_universe_as_of(changed,D,K,policy,x.source_snapshot_id).snapshot_digest==out.snapshot_digest
    plan=db.query_plan(x.definition.universe_id,D,K);db.close()
    tick=time.perf_counter();db=UniverseRepository(url,disposable_root=root);assert db.replay_context('pin').snapshot_digest==out.snapshot_digest;restart=time.perf_counter()-tick
    tick=time.perf_counter();replay=replay_universe_decisions(x,((D,K),(D,K+timedelta(seconds=1))),policy,max_steps=2);replay_seconds=time.perf_counter()-tick;assert len(replay)==2
    rollback_start=time.perf_counter()
    try:
        with db.transaction():raise RuntimeError('CONTROLLED_ROLLBACK')
    except RuntimeError:pass
    rollback=time.perf_counter()-rollback_start
    peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop();db.close()
    result={'job':config['job'],'exit_code':0,'counts':{},'python':sys.version,'interpreter':sys.executable,'start_utc':start,'end_utc':datetime.now(UTC).isoformat(),'stdout_stderr':'NON_MARKET_STRUCTURAL_CONTROL only; no exchange-scale throughput claim','boundary':boundary.assert_boundary(),'members':count,'revisions':count+1,'query_samples_seconds':samples,'query_median_seconds':statistics.median(samples),'seed_insert_seconds':insert,'snapshot_admission_seconds':admission,'membership_history_seconds':history_time,'correction_append_seconds':append,'restart_replay_seconds':restart,'two_step_replay_seconds':replay_seconds,'rollback_seconds':rollback,'peak_tracemalloc_bytes':peak,'snapshot_bytes':len(out.canonical_json.encode()),'query_plan':plan,'candidate_upper_bound':count,'deterministic_digest':out.snapshot_digest}
    (root/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return 0
''')
p=B/'final_worker.py';s=p.read_text().replace("    if job=='foundationperf':", "    if job=='od08perf':\n        import od08_structural_experiments\n        return od08_structural_experiments.run(config)\n    if job=='foundationperf':");p.write_text(s)
p=B/'run.py';s=p.read_text().replace("(B/'logs').mkdir", "NEW += ['scripts/od08_structural_experiments.py']\n(B/'logs').mkdir");p.write_text(s)
