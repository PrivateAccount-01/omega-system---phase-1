"""OD09 NON_MARKET_STRUCTURAL_CONTROL / PURE_MATHEMATICAL_TEST only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal,localcontext
import pytest
from test_od08_universe import setup_case,observation,D,K


def controls(**kw):
    from omegadata.reconciliation import contracts as c
    _,x,member,coverage,policy,_=setup_case()
    a=observation(x,observation_id='left',price_value=Decimal(2))
    b=replace(a,observation_id='right',artifact_identity='right-artifact',record_identity='right-row',price_value=Decimal(2))
    left=c.Observation(a,'security-a','CANARY-X','TOKEN','SERIES','publisher-a','parse-v1','schema-v1',1,'close',Decimal(2),'CONTROL_ONLY','root-a')
    right=c.Observation(b,'security-a','CANARY-X','TOKEN','SERIES','publisher-b','parse-v1','schema-v1',1,'close',Decimal(2),'CONTROL_ONLY','root-b')
    tolerance=c.TolerancePolicy('policy','v1',('control-source','control-source'),'SAME_VENUE','CONTROL_ONLY','close',('CANARY-X',),'ABSOLUTE',Decimal('0.1'),Decimal('0.2'),'CONTROL_UNIT','CONTROL_ONLY',K,D,None,'NON_MARKET_MATH_CONTROL')
    context=c.ComparisonContext('comparison',(left,),(right,),tolerance,x,D,K)
    return c,replace(context,**kw),left,right


GROUPS=[f'{p}{i:02}' for p,n in [('C',8),('M',4),('T',3),('N',5),('G',4),('R',6),('P',4),('S',3)] for i in range(1,n+1)]


@pytest.mark.parametrize('group',GROUPS)
def test_od09_acceptance(group,tmp_path):
    from omegadata.reconciliation.engine import reconcile_context,comparability,eligibility,match_candidates
    from omegadata.reconciliation.metrics import difference
    from omegadata.reconciliation.anomalies import structural_anomalies,discontinuity,persistent_discrepancy
    from omegadata.reconciliation.reviews import ReviewRevision,advance_review,ReprocessRequest,ReprocessCompletion,verify_completion
    from omegadata.reconciliation.repository import ReconciliationRepository
    from omegadata.adjustments.contracts import digest
    c,x,left,right=controls()
    if group=='C01':assert reconcile_context(x)[0].outcome=='PASS'
    elif group=='C02':assert reconcile_context(replace(x,right=(replace(right,security_id='other'),)))[0].outcome=='UNCOMPARABLE'
    elif group=='C03':
        other=replace(right,exchange='OTHER',availability=replace(right.availability,listing_id='other-listing'))
        assert comparability(left,other,x)[0]=='SAME_SECURITY_DIFFERENT_VENUE'
    elif group=='C04':assert reconcile_context(replace(x,right=(replace(right,availability=replace(right.availability,price_basis='OTHER')),)))[0].outcome=='UNCOMPARABLE'
    elif group=='C05':assert reconcile_context(replace(x,right=(replace(right,availability=replace(right.availability,session_date=D+timedelta(days=1))),)))[0].outcome=='UNCOMPARABLE'
    elif group=='C06':
        assert reconcile_context(replace(x,right=()))[0].comparability=='MISSING_COUNTERPART'
        assert reconcile_context(replace(x,right=(right,replace(right,availability=replace(right.availability,observation_id='duplicate')))))[0].comparability=='CONFLICTING_COUNTERPARTS'
    elif group=='C07':assert 'DEPENDENT_SOURCE_LINEAGE' in reconcile_context(replace(x,right=(replace(right,source_lineage_root='root-a'),)))[0].reason_codes
    elif group=='C08':assert reconcile_context(replace(x,right=(replace(right,availability=replace(right.availability,known_from=K+timedelta(seconds=1))),)))[0].outcome=='UNCOMPARABLE'
    elif group=='M01':assert difference(Decimal(3),Decimal(2),'REFERENCE_RELATIVE').exact_ratio==(1,2)
    elif group=='M02':assert difference(Decimal(1),Decimal(0),'REFERENCE_RELATIVE').status=='UNDEFINED_DENOMINATOR'
    elif group=='M03':
        for v,status in [('2.1','PASS'),('2.15','WARN'),('2.2','FAIL')]:
            r=replace(right,value=Decimal(v),availability=replace(right.availability,price_value=Decimal(v)))
            assert reconcile_context(replace(x,right=(r,)))[0].outcome==status
    elif group=='M04':
        values=[]
        for prec in (5,28,90):
            with localcontext() as ctx:ctx.prec=prec;values.append(difference(Decimal(1),Decimal(3),'REFERENCE_RELATIVE'))
        assert values[0]==values[1]==values[2]
    elif group=='T01':assert reconcile_context(x)[0].policy_digest==c.fingerprint(x.policy)
    elif group=='T02':assert reconcile_context(replace(x,policy=replace(x.policy,calibration_knowledge_cutoff=K+timedelta(days=1))))[0].outcome=='UNCOMPARABLE'
    elif group=='T03':assert not reconcile_context(x)[0].financial_eligibility
    elif group=='N01':assert structural_anomalies({'open':Decimal(2),'close':Decimal(2),'high':Decimal(1),'low':Decimal(0),'volume':Decimal(0)},ohlc_semantics='STANDARD')==('STRUCTURAL_INVALIDITY',)
    elif group=='N02':
        # No caller-asserted boolean can stand in for a bound corporate-action reference.
        assert discontinuity(left,right,x,Decimal('0.1'),None)=='NO_DISCONTINUITY'
    elif group=='N03':
        r=replace(right,value=Decimal(4),availability=replace(right.availability,price_value=Decimal(4)))
        assert discontinuity(left,r,x,Decimal('0.1'),None)=='UNEXPLAINED_DISCONTINUITY'
    elif group=='N04':assert comparability(left,replace(right,exchange='OTHER'),x)[0]=='SAME_SECURITY_DIFFERENT_VENUE'
    elif group=='N05':assert persistent_discrepancy((Decimal(1),Decimal(2),Decimal(3)),Decimal('0.5'),minimum_samples=3)=='PERSISTENT_DIRECTIONAL_DISCREPANCY'
    elif group in {'G01','G02','G03','G04'}:
        block={'G01':'SOURCE_RIGHTS_DENIED','G02':'UNKNOWN_IDENTITY','G03':'UNRESOLVED_CRITICAL_ANOMALY','G04':'UNCOMPARABLE'}[group]
        decision=eligibility(Decimal(1),'PASS',(block,),mode='CANARY_ONLY')
        assert not decision.financial_eligibility and not decision.publication_eligibility and not decision.execution_eligibility and block in decision.hard_block_reasons
    elif group.startswith('R'):
        review=ReviewRevision('rev-a','review','discrepancy','OPEN',K,'data-review',('source-a',),'review-v1',None,('listing-a',),'CRITICAL')
        if group=='R01':
            nxt=advance_review(review,'UNDER_REVIEW','rev-b',K+timedelta(seconds=1),'anonymous-reviewer','reason',(),mode='CANARY_ONLY')
            assert review.state=='OPEN' and nxt.previous_record_digest==c.fingerprint(review)
        elif group=='R02':
            with pytest.raises(ValueError):advance_review(review,'CLOSED','rev-b',K,'anonymous','reason',(),mode='CANARY_ONLY')
        elif group=='R03':
            review=replace(review,state='UNDER_REVIEW')
            with pytest.raises(ValueError):advance_review(review,'CORRECTION_PROPOSED','rev-b',K,'anonymous','reason',(),mode='CANARY_ONLY')
        elif group=='R04':
            review=replace(review,state='CORRECTION_PROPOSED')
            with pytest.raises(ValueError,match='AUTHORITY'):advance_review(review,'APPROVED','rev-b',K,'forged-reviewer','reason',('new-evidence',),mode='STRICT')
        else:
            req=ReprocessRequest('request','correction',('listing-a',),(D,),('raw-v2',),('adjusted-v2',),('universe-v2',),('result-v2',),(('policy','v1'),))
            actual=ReprocessCompletion('completion','request',c.fingerprint(req),'correction',('raw-v2',),('adjusted-v2',),('universe-v2',),('result-v2',),(('policy','v1'),),'COMPLETED_UNVERIFIED',('completion-evidence',))
            if group=='R05':assert req.request_digest==c.fingerprint(req)
            else:
                assert verify_completion(req,actual,mode='CANARY_ONLY')=='COMPLETED_UNVERIFIED'
                assert verify_completion(req,replace(actual,affected_reconciliation_results=()),mode='CANARY_ONLY')=='BLOCKED_DEPENDENCY'
    elif group.startswith('P'):
        url='sqlite:///:memory:' if group!='P03' else 'sqlite:///'+str(tmp_path/'reconciliation.sqlite')
        db=ReconciliationRepository(url,disposable_root=tmp_path)
        db.pin_comparison(x)
        results=reconcile_context(x)
        if group=='P01':
            db.admit_results(x.context_id,results);db.admit_results(x.context_id,results)
            with pytest.raises(ValueError):db.admit_results(x.context_id,(replace(results[0],outcome='FAIL'),))
        elif group=='P02':
            later=replace(x,context_id='later',known_at=K+timedelta(days=1));db.pin_comparison(later)
            assert db.replay(x.context_id)==results
        elif group=='P03':
            db.admit_results(x.context_id,results);db.close();db=ReconciliationRepository(url,disposable_root=tmp_path)
            assert db.replay(x.context_id)==results
            with pytest.raises(ValueError):db.rollback_empty()
        else:
            with pytest.raises(ValueError):db.pin_comparison(replace(x,known_at=K+timedelta(days=1)))
        db.close()
    elif group=='S01':assert not reconcile_context(x)[0].financial_eligibility
    elif group=='S02':
        import od05x_isolated_runner
        assert od05x_isolated_runner.assert_boundary()['verified']
    elif group=='S03':
        from omegadata.track_b.confidence import ConfidenceScorer
        assert ConfidenceScorer.THRESHOLDS


@pytest.mark.parametrize('metric,left,right,expected',[('ABSOLUTE','3','2',(1,1)),('SIGNED','2','3',(-1,1)),('REFERENCE_RELATIVE','1','3',(2,3)),('SYMMETRIC_RELATIVE','3','1',(1,1)),('RATIO_DIFFERENCE','3','2',(1,2)),('TICK','3','2',(4,1))])
def test_literal_metric_oracle(metric,left,right,expected):
    from omegadata.reconciliation.metrics import difference
    assert difference(Decimal(left),Decimal(right),metric,tick=Decimal('0.25')).exact_ratio==expected
