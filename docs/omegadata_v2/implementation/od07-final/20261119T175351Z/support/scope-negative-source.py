"""OD07 final: PURE_MATHEMATICAL_TEST / NON_MARKET_STRUCTURAL_CONTROL only."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import pytest
from test_od07_adjustments import system, D, K


def setup_bound(actions=None, *, raw=None, context=None, basis=None, parameters=None, history_state='COMPLETE_FOR_DECLARED_SCOPE'):
    from omegadata.adjustments import bound_contracts as b
    from omegadata.adjustments.bound_chain import calculate_bound_chain, pin_calculation
    c,x,a,r=system()
    x=x if context is None else context
    raw=b.RawObservation(r,'raw-observation','raw-record',1,'PER_TEST_UNIT','math-source') if raw is None else raw
    actions=(a,) if actions is None else actions
    basis=b.BasisPolicy('PRICE_RETURN','BACKWARD_ADJUSTED',x.valid_at) if basis is None else basis
    h=b.HistorySnapshot.create('history','s','l',('math-source',),D-timedelta(days=10),D+timedelta(days=15),x.known_at,actions,history_state,a.evidence,'ev-v1',basis.version)
    params=tuple(b.ParameterSet.for_action(item,K,item.evidence) for item in actions) if parameters is None else parameters
    pin=pin_calculation('context',raw,h,basis,x,params)
    return b,c,x,a,raw,h,basis,params,pin,calculate_bound_chain


def reference(a, *, kind='RAW_CLOSE',day=None):
    from omegadata.adjustments import bound_contracts as b
    from omegadata.adjustments.contracts import Reference
    day=D-timedelta(days=3) if day is None else day
    value=Reference(Decimal(100),day,K+timedelta(days=5),'reference-artifact','MATH_UNIT',a.evidence,'math-source')
    return b.ReferenceObservation(value,'reference-observation','source-record',1,'s','l','MATH','TOKEN','TEST','PER_TEST_UNIT','RAW_UNADJUSTED',kind,observed_at=K,published_at=None)


def rights_case(**kw):
    c,x,a,r=system()
    ref=reference(a)
    ref=replace(ref,**kw)
    a=replace(a,action_type='RIGHTS',parameters=c.Rights(Decimal(4),Decimal(1),Decimal(50),ref,'MATH_UNIT',True))
    return setup_bound((a,))


def calculate(parts):
    b,c,x,a,raw,h,policy,params,pin,run=parts
    return run(pin)


GROUPS=['R01','R02','R03','R04','R05','R06','I01','I02','I03','I04','H01','H02','H03','H04','P01','P02','P03','P04','E01','E02','E03','K01','K02','K03','D01','D02','D03','D04']
@pytest.mark.parametrize('group',GROUPS)
def test_targeted_contract(group,tmp_path):
    parts=setup_bound();b,c,x,a,raw,h,p,params,pin,run=parts
    if group.startswith('R'):
        change={'R01':{'security_id':'wrong'},'R02':{'listing_id':'wrong'},'R03':{'exchange':'OTHER'},'R04':{'price_basis':'BACKWARD_ADJUSTED'},'R05':{'observation_id':''},'R06':{}}[group]
        out=calculate(rights_case(**change))
        assert out.status==('CALCULATED' if group=='R06' else 'BLOCKED_IDENTITY' if group in {'R01','R02','R03'} else 'BLOCKED_EVIDENCE')
        if group=='R06':assert out.adjusted_price==Decimal(108)
    elif group=='I01':
        old=x.identity_repository.claims[0]
        renamed=replace(old,claim_id='renamed',valid_from=D-timedelta(days=1),symbol='NEW',series='OTHER')
        repo=replace(x.identity_repository,claims=(replace(old,valid_to=renamed.valid_from),renamed))
        out=calculate(setup_bound(context=replace(x,identity_repository=repo)))
        assert out.status=='CALCULATED' and out.identity_status=='SAME_LISTING_CONTINUITY'
    elif group=='I02':
        from omegadata.identity import Security, Listing
        old=x.identity_repository.claims[0]
        future=replace(old,claim_id='reuse',valid_from=D,symbol='TOKEN',listing_id='other-listing')
        renamed=replace(old,claim_id='rename',valid_from=D,symbol='NEW')
        repo=replace(x.identity_repository,securities=(*x.identity_repository.securities,Security('other-security','i')),listings=(*x.identity_repository.listings,Listing('other-listing','other-security','MATH')),claims=(replace(old,valid_to=D),renamed,future))
        assert calculate(setup_bound(context=replace(x,identity_repository=repo))).status=='CALCULATED'
        wrong=replace(raw,raw=replace(raw.raw,security_id='other-security',listing_id='other-listing'))
        assert calculate(setup_bound(raw=wrong,context=replace(x,identity_repository=repo))).status=='BLOCKED_IDENTITY'
    elif group=='I03':
        claim=replace(x.identity_repository.claims[0],lifecycle='DELISTED')
        out=calculate(setup_bound(context=replace(x,identity_repository=replace(x.identity_repository,claims=(claim,)))))
        assert out.status=='CALCULATED' and out.identity_status=='HISTORICALLY_VALID_BUT_NOT_TRADABLE'
    elif group=='I04':
        claim=x.identity_repository.claims[0]
        repo=replace(x.identity_repository,claims=(replace(claim,valid_to=D),))
        assert calculate(setup_bound(context=replace(x,identity_repository=repo))).status=='BLOCKED_IDENTITY'
    elif group=='H01':
        assert calculate(parts).status=='CALCULATED'
        assert calculate(setup_bound(history_state='PARTIAL')).status=='BLOCKED_EVIDENCE'
    elif group=='H02':
        assert calculate(setup_bound((),history_state='UNKNOWN')).status=='BLOCKED_EVIDENCE'
        empty=calculate(setup_bound(()))
        assert empty.status=='CALCULATED' and not empty.publication_eligibility
    elif group=='H03':
        altered=replace(h,action_revision_ids=('a','missing'))
        assert run(replace(pin,history=altered)).status=='CONFLICTING_ACTIONS'
    elif group=='H04':
        other=replace(a,action_id='b',sequence=2)
        parts=setup_bound((replace(a,sequence=1),other))
        pin=parts[8]
        bad=replace(pin.history,economic_event_ids=(('a','same-event'),('b','same-event')))
        assert run(replace(pin,history=bad)).status=='CONFLICTING_ACTIONS'
    elif group in {'P01','P02','P03','P04'}:
        from omegadata.adjustments.repository import AdjustmentRepository
        db=AdjustmentRepository('sqlite:///:memory:',disposable_root=tmp_path);db.append_action(a)
        db.pin_context(pin);out=run(pin)
        if group=='P01':
            db.append_bound_result(out,'context');assert db.get_result(out.output_digest)==out.canonical_json
        else:
            field={'P02':'raw_observation_digest','P03':'knowledge_cutoff','P04':'identity_snapshot_digest'}[group]
            import json
            bindings=json.loads(out.context_bindings);bindings[field]='tampered'
            bad=replace(out,context_bindings=c.canonical(bindings))
            with pytest.raises(ValueError):db.append_bound_result(bad,'context')
    elif group=='E01':
        exec_policy=b.BasisPolicy('EXECUTION','RAW_UNADJUSTED',raw.raw.trade_date)
        out=calculate(setup_bound((),basis=exec_policy))
        assert out.status=='CALCULATED' and out.raw_price_basis_preserved
        assert not out.execution_eligibility and not out.publication_eligibility
    elif group=='E02':
        claim=replace(x.identity_repository.claims[0],lifecycle='SUSPENDED')
        repo=replace(x.identity_repository,claims=(claim,))
        out=calculate(setup_bound((),context=replace(x,identity_repository=repo),basis=b.BasisPolicy('EXECUTION','RAW_UNADJUSTED',raw.raw.trade_date)))
        assert out.status=='CALCULATED' and out.tradability_status=='SUSPENDED'
        assert not out.execution_eligibility
    elif group=='E03':
        out=calculate(setup_bound((),basis=b.BasisPolicy('EXECUTION','RAW_UNADJUSTED',raw.raw.trade_date)))
        assert out.execution_status.startswith('BLOCKED')
    elif group=='K01':
        assert calculate(setup_bound(parameters=())).status=='BLOCKED_KNOWLEDGE'
    elif group=='K02':
        future=replace(params[0],known_from=x.known_at+timedelta(seconds=1))
        assert calculate(setup_bound(parameters=(future,))).status=='BLOCKED_KNOWLEDGE'
        boundary=replace(future,known_from=x.known_at)
        assert calculate(setup_bound(parameters=(boundary,))).status=='CALCULATED'
    elif group=='K03':
        corrected=replace(a,action_id='b',action_revision=2,supersedes_action_id='a',known_from=x.known_at+timedelta(days=1),parameters=c.Split(Decimal(4)))
        early=calculate(parts)
        later_ledger=calculate(setup_bound((a,corrected)))
        assert early.output_digest==later_ledger.output_digest
    elif group=='D01':
        pre=calculate(parts);assert pre.adjusted_price==Decimal(60)
        on=replace(raw,raw=replace(raw.raw,trade_date=D,price=Decimal(60)))
        assert calculate(setup_bound(raw=on)).adjusted_price==Decimal(60)
    elif group=='D02':
        policy=b.BasisPolicy('PRICE_RETURN','FORWARD_ADJUSTED',D-timedelta(days=1))
        on=replace(raw,raw=replace(raw.raw,trade_date=D,price=Decimal(60)))
        assert calculate(setup_bound(raw=on,basis=policy)).adjusted_price==Decimal(120)
        assert calculate(setup_bound(basis=policy)).adjusted_price==Decimal(120)
    elif group=='D03':
        inverse=b.BasisPolicy('PRICE_RETURN','INVERSE_FACTOR_COMPARISON',x.valid_at)
        assert calculate(setup_bound(basis=inverse)).adjusted_price==Decimal(240)
        assert calculate(setup_bound(basis=inverse)).adjustment_basis=='INVERSE_FACTOR_COMPARISON'
    elif group=='D04':
        other=replace(a,action_id='b',ex_date=D+timedelta(days=1),parameters=c.Bonus(Decimal(1),Decimal(2)))
        assert calculate(setup_bound((a,other))).adjusted_price==Decimal(40)
        post=replace(raw,raw=replace(raw.raw,trade_date=D+timedelta(days=1),price=Decimal(40)))
        assert calculate(setup_bound((a,other),raw=post,basis=b.BasisPolicy('PRICE_RETURN','FORWARD_ADJUSTED',D-timedelta(days=1)))).adjusted_price==Decimal(120)

ADMISSION=['omitted-action','fabricated-empty','wrong-raw','wrong-profile','changed-revision','source-artifact','knowledge-cutoff','missing-calendar','identity-snapshot','incorrect-factor','incomplete-math','duplicate-event','reused-digest']
@pytest.mark.parametrize('case',ADMISSION)
def test_admission_negative(case,tmp_path):
    from omegadata.adjustments.repository import AdjustmentRepository
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    db=AdjustmentRepository('sqlite:///:memory:',disposable_root=tmp_path);db.append_action(a)
    if case in {'omitted-action','incomplete-math'}:
        db.append_action(replace(a,action_id='b',ex_date=D+timedelta(days=1)))
        with pytest.raises(ValueError):db.pin_context(pin)
        return
    if case=='fabricated-empty':
        with pytest.raises(ValueError):db.pin_context(setup_bound(())[8])
        return
    if case=='duplicate-event':
        other=replace(a,action_id='b',sequence=2)
        bits=setup_bound((replace(a,sequence=1),other));bad=replace(bits[8],history=replace(bits[5],economic_event_ids=(('a','same'),('b','same'))))
        with pytest.raises(ValueError):db.pin_context(bad)
        return
    db.pin_context(pin);out=run(pin);inner=out.calculation
    if case=='wrong-raw':bad=replace(out,calculation=replace(inner,original_raw_reference='other'))
    elif case=='wrong-profile':bad=replace(out,calculation=replace(inner,consumer_profile='VOLUME'))
    elif case in {'changed-revision','source-artifact','knowledge-cutoff','incorrect-factor'}:
        link=inner.adjustment_factor_chain[0]
        if case=='changed-revision':link=replace(link,input_parameters='{}')
        elif case=='source-artifact':link=replace(link,source_artifact_id='other')
        elif case=='knowledge-cutoff':link=replace(link,knowledge_cutoff=K)
        else:link=replace(link,factor=replace(link.factor,price_factor=Decimal(9)))
        bad=replace(out,calculation=replace(inner,adjustment_factor_chain=(link,)))
    elif case in {'missing-calendar','identity-snapshot'}:
        import json
        value=json.loads(out.context_bindings)
        if case=='missing-calendar':value.pop('calendar_snapshot_digest')
        else:value['identity_snapshot_digest']='forged'
        bad=replace(out,context_bindings=c.canonical(value))
    elif case=='reused-digest':
        db.append_bound_result(out,'context');bad=replace(out,calculation=replace(inner,reason='changed'))
        with pytest.raises(ValueError):db.append_bound_result(bad,'context',expected_result_id=out.output_digest)
        assert db.get_result(out.output_digest)==out.canonical_json
        return
    with pytest.raises(ValueError):db.append_bound_result(bad,'context')


@pytest.mark.parametrize('case',['unbound-reference','wrong-type','wrong-unit','expired-reference','future-reference','unknown-parameter-time','revoked-parameter','incomplete-parameter','zero-issue','corrected-terms','wrong-venue-symbol','ambiguous-identity','reopen-context','legacy-migration','rollback-context','strict-no-promotion'])
def test_required_boundaries(case,tmp_path):
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    if case=='unbound-reference':
        a=replace(a,action_type='RIGHTS',parameters=c.Rights(Decimal(4),Decimal(1),Decimal(50),c.Reference(Decimal(100),D-timedelta(days=3),K,'ref','MATH_UNIT'),'MATH_UNIT',True))
        assert calculate(setup_bound((a,))).status=='BLOCKED_IDENTITY'
    elif case in {'wrong-type','wrong-unit','expired-reference','future-reference'}:
        kw={'wrong-type':{'observation_type':'RAW_OPEN'},'wrong-unit':{'price_unit':'OTHER'},'expired-reference':{'known_to':K+timedelta(days=10)},'future-reference':{'published_at':x.known_at+timedelta(seconds=1)}}[case]
        assert calculate(rights_case(**kw)).status in {'BLOCKED_EVIDENCE','BLOCKED_KNOWLEDGE'}
    elif case=='unknown-parameter-time':assert calculate(setup_bound(parameters=(replace(params[0],known_from=None),))).status=='BLOCKED_KNOWLEDGE'
    elif case=='revoked-parameter':
        e=replace(a.evidence,permission='DENIED')
        assert calculate(setup_bound(parameters=(replace(params[0],evidence=e),))).status=='BLOCKED_EVIDENCE'
    elif case=='incomplete-parameter':assert calculate(setup_bound(parameters=(replace(params[0],parameters_digest='other'),))).status=='BLOCKED_KNOWLEDGE'
    elif case=='zero-issue':
        ref=reference(a)
        a=replace(a,action_type='RIGHTS',parameters=c.Rights(Decimal(4),Decimal(1),Decimal(0),ref,'MATH_UNIT',True))
        assert calculate(setup_bound((a,))).adjusted_price==Decimal(96)
    elif case=='corrected-terms':
        a=replace(a,action_type='RIGHTS',parameters=c.Rights(Decimal(4),Decimal(1),Decimal(50),reference(a),'MATH_UNIT',True))
        future=replace(a,action_id='b',action_revision=2,supersedes_action_id='a',known_from=x.known_at+timedelta(days=1),parameters=replace(a.parameters,subscription_price=Decimal(80)))
        assert calculate(setup_bound((a,future))).adjusted_price==Decimal(108)
    elif case=='wrong-venue-symbol':
        r=replace(raw,raw=replace(raw.raw,exchange='OTHER'))
        assert calculate(setup_bound(raw=r)).status=='BLOCKED_IDENTITY'
    elif case=='ambiguous-identity':
        old=x.identity_repository.claims[0];repo=replace(x.identity_repository,claims=(old,replace(old,claim_id='duplicate')))
        assert calculate(setup_bound(context=replace(x,identity_repository=repo))).status=='BLOCKED_IDENTITY'
    elif case=='strict-no-promotion':
        out=calculate(setup_bound(context=replace(x,mode='STRICT')))
        assert out.status=='BLOCKED_EVIDENCE' and not out.execution_eligibility and not out.publication_eligibility
    else:
        from omegadata.adjustments.repository import AdjustmentRepository
        url='sqlite:///'+str(tmp_path/'bound.sqlite')
        if case=='legacy-migration':
            from omegadata.adjustments.repository import M,version
            from sqlalchemy import create_engine
            engine=create_engine(url)
            with engine.begin() as connection:
                M.create_all(connection,tables=[M.tables[n] for n in ['od07_schema','od07_action','od07_result','od07_result_action']])
                connection.execute(version.insert().values(version='od07.store/v1'))
            engine.dispose()
        db=AdjustmentRepository(url,disposable_root=tmp_path);db.append_action(a)
        db.pin_context(pin);out=run(pin);db.append_bound_result(out,'context')
        if case=='rollback-context':
            with pytest.raises(ValueError):db.pin_context(replace(pin,raw=replace(raw,observation_id='different')))
            assert db.get_result(out.output_digest)==out.canonical_json
        db.close();db=AdjustmentRepository(url,disposable_root=tmp_path)
        assert db.get_result(out.output_digest)==out.canonical_json


@pytest.mark.parametrize('multiplier,day,price,basis,want',[
 ('2',-2,'120','BACKWARD_ADJUSTED','60'),('2',0,'60','BACKWARD_ADJUSTED','60'),('2',1,'60','BACKWARD_ADJUSTED','60'),
 ('2',-2,'120','FORWARD_ADJUSTED','120'),('2',0,'60','FORWARD_ADJUSTED','120'),('2',1,'60','FORWARD_ADJUSTED','120'),
 ('0.5',-2,'120','BACKWARD_ADJUSTED','240'),('0.5',0,'240','FORWARD_ADJUSTED','120'),('0.5',1,'240','FORWARD_ADJUSTED','120')])
def test_independent_basis_vectors(multiplier,day,price,basis,want):
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    a=replace(a,parameters=c.Split(Decimal(multiplier)))
    raw=replace(raw,raw=replace(raw.raw,trade_date=D+timedelta(days=day),price=Decimal(price)))
    policy=b.BasisPolicy('PRICE_RETURN',basis,x.valid_at if basis=='BACKWARD_ADJUSTED' else D-timedelta(days=1))
    assert calculate(setup_bound((a,),raw=raw,basis=policy)).adjusted_price==Decimal(want)


def test_legacy_rename_reproduction():
    from omegadata.adjustments.chains import calculate_chain
    c,x,a,r=system();claim=x.identity_repository.claims[0]
    renamed=replace(claim,claim_id='rename',symbol='NEW',valid_from=D-timedelta(days=1))
    repo=replace(x.identity_repository,claims=(replace(claim,valid_to=renamed.valid_from),renamed))
    assert calculate_chain(r,(a,),c.Policy('PRICE_RETURN'),replace(x,identity_repository=repo)).status=='CALCULATED'

@pytest.mark.parametrize('case',['independent-oracle','independent-lineage','valid-session-missing-lot','closed-session','delisted-execution','canary-execution-promotion','future-identity','unreviewed-merger','undefined-forward-rights','schema-version'])
def test_semantic_review(case,tmp_path,monkeypatch):
    from omegadata.adjustments.repository import AdjustmentRepository
    from omegadata.session_calendar import SessionClaim
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    if case in {'independent-oracle','independent-lineage'}:
        from omegadata.adjustments import admission
        out=run(pin)
        if case=='independent-oracle':bad=replace(out,calculation=replace(out.calculation,adjusted_price=Decimal(999)))
        else:
            link=replace(out.calculation.adjustment_factor_chain[0],source_artifact_id='wrong')
            bad=replace(out,calculation=replace(out.calculation,adjustment_factor_chain=(link,)))
        monkeypatch.setattr(admission,'calculate_bound_chain',lambda ignored:bad)
        db=AdjustmentRepository('sqlite:///:memory:',disposable_root=tmp_path);db.append_action(a)
        with pytest.raises(ValueError):db.pin_context(pin)
    elif case in {'valid-session-missing-lot','closed-session','delisted-execution','canary-execution-promotion'}:
        session=SessionClaim('raw-session','MATH',raw.raw.trade_date,'CLOSED' if case=='closed-session' else 'REGULAR','Asia/Kolkata','cal-v1',a.evidence,K,None)
        calendar=replace(x.calendar,claims=(*x.calendar.claims,session))
        if case=='delisted-execution':
            claim=replace(x.identity_repository.claims[0],lifecycle='DELISTED')
            x=replace(x,identity_repository=replace(x.identity_repository,claims=(claim,)))
        parts=setup_bound((),context=replace(x,calendar=calendar),basis=b.BasisPolicy('EXECUTION','RAW_UNADJUSTED',raw.raw.trade_date))
        pin=parts[8]
        if case=='canary-execution-promotion':
            terms=b.ExecutionConstraints('s','l','MATH',raw.raw.trade_date,K,a.evidence,10,'20','WHOLE_UNITS','CANARY_ONLY','CLEAR')
            pin=replace(pin,execution_constraints=terms)
        out=run(pin)
        assert out.status=='CALCULATED' and not out.execution_eligibility
        expected={'valid-session-missing-lot':'BLOCKED_LOT_OR_SETTLEMENT_UNKNOWN','closed-session':'BLOCKED_CALENDAR','delisted-execution':'BLOCKED_LIFECYCLE','canary-execution-promotion':'BLOCKED_NON_MARKET_CONTROL'}[case]
        assert out.execution_status==expected
    elif case=='future-identity':
        old=x.identity_repository.claims[0]
        correction=replace(old,claim_id='future',symbol='FUTURE',known_from=x.known_at+timedelta(days=1),supersedes_claim_id=old.claim_id)
        changed=replace(x,identity_repository=replace(x.identity_repository,claims=(old,correction)))
        assert calculate(setup_bound(context=changed)).output_digest==run(pin).output_digest
    elif case=='unreviewed-merger':
        from omegadata.identity import Listing,Security
        old=x.identity_repository.claims[0]
        new_listing=Listing('successor-listing','successor-security','MATH')
        successor=replace(old,claim_id='successor',listing_id='successor-listing',valid_from=D)
        repo=replace(x.identity_repository,securities=(*x.identity_repository.securities,Security('successor-security','i')),listings=(*x.identity_repository.listings,new_listing),claims=(replace(old,valid_to=D),successor))
        assert calculate(setup_bound(context=replace(x,identity_repository=repo))).status=='BLOCKED_IDENTITY'
    elif case=='undefined-forward-rights':
        bits=rights_case();raw=replace(bits[4],raw=replace(bits[4].raw,trade_date=D,price=Decimal(90)))
        assert calculate(setup_bound(bits[5].actions,raw=raw,basis=b.BasisPolicy('PRICE_RETURN','FORWARD_ADJUSTED',D-timedelta(days=1)))).status=='UNSUPPORTED_POLICY'
    elif case=='schema-version':
        from sqlalchemy import create_engine
        from omegadata.adjustments.repository import M,version
        url='sqlite:///'+str(tmp_path/'unknown.sqlite');engine=create_engine(url)
        with engine.begin() as connection:
            M.create_all(connection);connection.execute(version.insert().values(version='unrecognized'))
        engine.dispose()
        with pytest.raises(ValueError):AdjustmentRepository(url,disposable_root=tmp_path)

@pytest.mark.parametrize('case',['parameter-time-contradiction','unknown-quantity-convention','future-basis'])
def test_explicit_temporal_and_execution_scope(case):
    b,c,x,a,raw,h,p,params,pin,run=setup_bound()
    if case=='parameter-time-contradiction':
        a=replace(a,parameter_known_from=x.known_at+timedelta(days=1))
        assert calculate(setup_bound((a,))).status=='BLOCKED_KNOWLEDGE'
    elif case=='future-basis':
        assert calculate(setup_bound(basis=replace(p,basis_date=x.valid_at+timedelta(days=1)))).status=='BLOCKED_KNOWLEDGE'
    else:
        from omegadata.session_calendar import SessionClaim
        session=SessionClaim('raw','MATH',raw.raw.trade_date,'REGULAR','Asia/Kolkata','cal-v1',a.evidence,K,None)
        x=replace(x,calendar=replace(x.calendar,claims=(*x.calendar.claims,session)))
        terms=b.ExecutionConstraints('s','l','MATH',raw.raw.trade_date,K,a.evidence,10,'20','UNREVIEWED_CONVENTION','CANARY_ONLY','CLEAR')
        bits=setup_bound((),context=x,basis=b.BasisPolicy('EXECUTION','RAW_UNADJUSTED',raw.raw.trade_date))
        assert run(replace(bits[8],execution_constraints=terms)).execution_status=='BLOCKED_EXECUTION_CONSTRAINTS'
