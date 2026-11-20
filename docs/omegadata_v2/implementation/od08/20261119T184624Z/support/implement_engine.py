from pathlib import Path
D=Path('/home/parilrupani/omega-od08-20261119T184624Z/staged2/repo/src/omegadata/universe')
(D/'eligibility.py').write_text('''"""Versioned consumer policies; membership is never silently filtered."""
from __future__ import annotations
from datetime import date,datetime,timedelta
from decimal import Decimal,localcontext
from typing import Any
from omegadata.adjustments.contracts import arithmetic_context,canonical
from omegadata.adjustments.bound_contracts import BoundResult,PinnedCalculation,BOUND_VERSION
from omegadata.adjustments.bound_chain import calculate_bound_chain
from omegadata.universe import contracts as c
from omegadata.universe.temporal import availability

def adjustment_eligible(result:BoundResult,pin:PinnedCalculation|None,cutoff:datetime,profile:str,basis:str)->str:
    if pin is None or result.version!=BOUND_VERSION or result.status!='CALCULATED' or result.calculation.consumer_profile!=profile or result.adjustment_basis!=basis or pin.context.known_at>cutoff:return 'BLOCKED_ADJUSTMENT_CONTEXT'
    rebuilt=calculate_bound_chain(pin)
    if rebuilt.canonical_json!=result.canonical_json or pin.raw.observation_id!=result.calculation.original_raw_reference:return 'BLOCKED_ADJUSTMENT_CONTEXT'
    return 'ELIGIBLE_NON_MARKET' if pin.context.mode=='NON_MARKET_MATH' else 'ELIGIBLE_SOURCE_BACKED'

def liquidity(member:c.MembershipRevision,x:c.UniverseContext,observations:tuple[c.AvailabilityObservation,...],day:date,cutoff:datetime,p:c.LiquidityPolicy)->tuple[str,dict[str,Any]]:
    needed=[];current=day;calendar=x.calendar;diagnostics:dict[str,Any]={}
    for _ in range(3660):
        if calendar.coverage_status(member.claim.exchange,current,cutoff,x.mode)!='COMPLETE':return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'CALENDAR_COVERAGE_UNKNOWN','date':current.isoformat()}
        session=calendar.query(member.claim.exchange,current,cutoff,x.mode,calendar_version=x.calendar_version)
        if session.status in {'AUTHORITATIVE_SESSION','VERIFIED_SPECIAL_SESSION'}:
            close=session.claims[0].closes_at
            if close is None:return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'SESSION_COMPLETION_UNKNOWN'}
            if close<=cutoff:needed.append(current)
        elif session.status!='KNOWN_CLOSURE':return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'SESSION_UNKNOWN'}
        if len(needed)==p.lookback_sessions:break
        current-=timedelta(days=1)
    if len(needed)!=p.lookback_sessions:return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'WINDOW_BUDGET'}
    usable=[];missing=[]
    for d in needed:
        rows=[o for o in observations if o.session_date==d]
        if len(rows)>1:return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'DUPLICATE_SESSION'}
        if not rows:missing.append(d);continue
        o=rows[0]
        if o.listing_id!=member.listing_id or (o.currency,o.price_unit,o.price_basis,o.volume_basis)!=(p.currency,p.price_unit,p.price_basis,p.volume_basis) or o.volume is None or o.turnover is None or availability(o,cutoff,c.AvailabilityPolicy(),x)!='AVAILABLE':return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'OBSERVATION_IDENTITY_UNITS_AVAILABILITY_OR_MISSING_VALUE'}
        if p.volume_basis!='RAW' and (o.adjustment is None or adjustment_eligible(o.adjustment,o.adjustment_pin,cutoff,'VOLUME',o.adjustment.adjustment_basis).startswith('BLOCKED')):return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'VOLUME_ADJUSTMENT_CONTEXT_REQUIRED'}
        usable.append(o)
    with localcontext(arithmetic_context()) as math:
        math.prec=80
        ratio=Decimal(len(usable))/Decimal(len(needed))
        if len(usable)<p.minimum_completed_sessions or ratio<p.minimum_observation_coverage:return 'BLOCKED_LIQUIDITY_COVERAGE',{'reason':'INSUFFICIENT_OBSERVATIONS','expected':len(needed),'actual':len(usable),'missing':missing}
        volumes=[o.volume for o in usable if o.volume is not None];turnovers=sorted(o.turnover for o in usable if o.turnover is not None)
        average=sum(volumes,Decimal(0))/Decimal(len(volumes));n=len(turnovers);median=turnovers[n//2] if n%2 else (turnovers[n//2-1]+turnovers[n//2])/Decimal(2)
    diagnostics.update(window=needed,missing=missing,coverage=ratio,average_volume=average,median_turnover=median)
    return ('ELIGIBLE' if average>=p.minimum_average_volume and median>=p.minimum_median_turnover else 'EXCLUDED_BY_POLICY'),diagnostics

def reconstruct(rows:tuple[c.RankingCandidate,...],top_n:int,cutoff:datetime,x:c.UniverseContext)->tuple[str,tuple[str,...],tuple[tuple[str,str],...]]:
    if not 1<=top_n<=10000 or len(rows)>10000:raise ValueError('RANKING_BUDGET')
    if len({r.member_identity for r in rows})!=len(rows):raise ValueError('DUPLICATE_RANKING_MEMBER')
    accepted=[];excluded=[]
    for r in rows:
        if type(r.metric) is not Decimal or not r.metric.is_finite() or r.metric<0:raise ValueError('RANKING_NUMBER')
        if availability(r.observation,cutoff,c.AvailabilityPolicy(),x)!='AVAILABLE':excluded.append((r.member_identity,'BLOCKED_AVAILABILITY'));continue
        resolution=x.identity.resolve_listing_id(r.observation.listing_id,r.observation.session_date,cutoff,x.mode)
        expected=resolution.security_id if x.definition.identity_granularity=='SECURITY' else resolution.listing_id
        if resolution.state!='RESOLVED' or expected!=r.member_identity:excluded.append((r.member_identity,'UNRESOLVED_IDENTITY'));continue
        accepted.append(r)
    ordered=sorted(accepted,key=lambda r:(-r.metric,r.member_identity))
    return 'RECONSTRUCTED_PROVISIONAL',tuple(r.member_identity for r in ordered[:top_n]),tuple(sorted(excluded+[(r.member_identity,'BELOW_RANK_CUTOFF') for r in ordered[top_n:]]))
''')
(D/'snapshots.py').write_text('''"""Deterministic OD08 query and bounded replay using pinned domain inputs."""
from __future__ import annotations
from dataclasses import replace
from datetime import date,datetime
from collections import Counter
from typing import Any
from omegadata.identity import query_time
from omegadata.identity_authority import EvidenceAuthority
from omegadata.adjustments.contracts import canonical,digest
from omegadata.universe import contracts as c
from omegadata.universe.temporal import select_memberships,visible_revisions,coverage_reconcile,authorized,known,availability
from omegadata.universe.eligibility import liquidity,adjustment_eligible

def bindings(x:c.UniverseContext,day:date,cutoff:datetime,p:c.EligibilityPolicy,selected:tuple[c.MembershipRevision,...])->dict[str,Any]:
    visible=tuple(r for r in x.memberships if r.universe_id==x.definition.universe_id and (r.claim.known_from is None or r.claim.known_from<=cutoff))
    listing_ids={r.listing_id for r in selected if r.listing_id is not None}
    claims=tuple(v for v in x.identity.claims if (v.known_from is None or v.known_from<=cutoff) and (v.listing_id in listing_ids or any((v.exchange,v.symbol,v.series)==(r.claim.exchange,r.claim.symbol,r.claim.series) for r in selected)))
    listing_ids.update(v.listing_id for v in claims)
    listings=tuple(v for v in x.identity.listings if v.listing_id in listing_ids)
    security_ids={v.security_id for v in listings};securities=tuple(v for v in x.identity.securities if v.security_id in security_ids);issuer_ids={v.issuer_id for v in securities}
    identity={'claims':claims,'listings':listings,'securities':securities,'issuers':tuple(v for v in x.identity.issuers if v.issuer_id in issuer_ids)}
    calendar={'claims':tuple(v for v in x.calendar.claims if v.exchange in x.definition.exchange_scope and (v.known_from is None or v.known_from<=cutoff) and (x.calendar_version is None or v.calendar_version==x.calendar_version)), 'coverage':tuple(v for v in x.calendar.coverage if v.exchange in x.definition.exchange_scope and (v.known_from is None or v.known_from<=cutoff) and (x.calendar_version is None or v.calendar_version==x.calendar_version))}
    observations=tuple(o for o in x.observations if o.listing_id in listing_ids and (o.known_from is None or o.known_from<=cutoff) and p.view!='MEMBERSHIP')
    refs=tuple({'observation_id':o.observation_id,'raw_observation_digest':digest(o.adjustment_pin.raw) if o.adjustment_pin else None,'adjustment_context_id':o.adjustment_pin.snapshot_id if o.adjustment_pin else None,'adjustment_result_digest':o.adjustment.output_digest,'bindings':o.adjustment.context_bindings} for o in observations if o.adjustment is not None)
    return {'universe_definition':digest(x.definition),'membership_ledger_digest':digest(tuple(sorted(visible,key=lambda r:r.revision_id))),'coverage_evidence_digest':digest(tuple(sorted((v for v in x.coverage if v.known_from is None or v.known_from<=cutoff),key=lambda v:v.coverage_id))),'identity_snapshot_digest':digest(identity),'calendar_snapshot_digest':digest(calendar),'source_authority_digest':(x.authority or EvidenceAuthority.unconfigured()).snapshot_digest(),'observation_digest':digest(tuple(replace(o,adjustment_pin=None) for o in observations)),'adjustment_context_references':refs,'policy':p,'known_at':cutoff,'valid_at':day,'source_snapshot_id':x.source_snapshot_id,'version':x.version}

def get_universe_as_of(x:c.UniverseContext,valid_at:date,known_at:datetime,eligibility_policy:c.EligibilityPolicy,source_snapshot_id:str)->c.UniverseSnapshot:
    query_time(known_at);d=x.definition;p=eligibility_policy
    if source_snapshot_id!=x.source_snapshot_id or type(valid_at) is not date:raise ValueError('EXACT_SOURCE_PIN_REQUIRED')
    if not d.valid_from<=valid_at or d.valid_to is not None and valid_at>=d.valid_to or d.known_from is None or not known(d.known_from,d.known_to,known_at):raise ValueError('DEFINITION_NOT_AVAILABLE')
    selected=select_memberships(x,valid_at,known_at)
    resolutions={}
    identities=[];unresolved=[]
    for r in selected:
        # Resolve as reported when the source claim became applicable, then follow stable IDs.
        origin=x.identity.resolve_listing(r.claim.exchange,r.claim.symbol,r.claim.series,r.claim.valid_from,known_at,x.mode)
        current=x.identity.resolve_listing_id(origin.listing_id,valid_at,known_at,x.mode) if origin.listing_id is not None else origin
        if origin.state!='RESOLVED' or current.state!='RESOLVED' or origin.security_id!=current.security_id or (r.security_id is not None and r.security_id!=origin.security_id) or (r.listing_id is not None and r.listing_id!=origin.listing_id):
            unresolved.append(r.revision_id);resolutions[r.revision_id]=None;continue
        resolutions[r.revision_id]=current
        if r.event_type!='CANCEL':identities.append(current.security_id if d.identity_granularity=='SECURITY' else current.listing_id)
    actual=tuple(v for v in identities if v is not None);counts=Counter(actual)
    state,reconciliation=coverage_reconcile(x,valid_at,known_at,actual,tuple(unresolved))
    decisions=[]
    complete=state in {'COMPLETE_VERIFIED','COMPLETE_FOR_DECLARED_NON_MARKET_SCOPE'}
    for r in selected:
        resolution=resolutions[r.revision_id];security=resolution.security_id if resolution else None;listing=resolution.listing_id if resolution else None
        ident=security if d.identity_granularity=='SECURITY' else listing
        status='INCLUDED';reasons=[];research='NOT_REQUESTED';liq='NOT_REQUESTED';tradability=resolution.lifecycle if resolution else 'UNKNOWN';execution=False
        if r.event_type=='CANCEL':status='EXCLUDED_BY_POLICY';reasons.append('CANCELLED')
        elif r.claim.exchange not in d.exchange_scope or r.source_id not in d.source_scope or not authorized(d,x,known_at) or not authorized(r,x,known_at):status='BLOCKED_SOURCE_RIGHTS'
        elif r.claim.known_from is None or r.effective_convention=='UNKNOWN' or any(v is not None and v>known_at for v in (r.published_at,r.announcement_at)):status='BLOCKED_AVAILABILITY'
        elif r.claim.status=='CONFLICTING' or ident is not None and counts[ident]>1:status='CONFLICTING_MEMBERSHIP'
        elif resolution is None:status='UNRESOLVED_IDENTITY'
        elif r.claim.status in {'RECONSTRUCTED_PROVISIONAL','UNKNOWN'} or d.universe_type=='PROVISIONAL_RECONSTRUCTION':status='PROVISIONAL_ONLY'
        elif not complete:status='BLOCKED_REFERENCE_COVERAGE'
        elif p.view!='MEMBERSHIP':
            obs=tuple(o for o in x.observations if o.listing_id==listing and o.session_date<=valid_at and (o.known_from is None or o.known_from<=known_at))
            if p.require_observations and (not obs or any(availability(o,known_at,p.availability_policy,x)!='AVAILABLE' for o in obs)):status='BLOCKED_AVAILABILITY';research=status
            else:research='ELIGIBLE_NON_MARKET' if x.mode=='CANARY_ONLY' else 'ELIGIBLE_SOURCE_BACKED'
            if status=='INCLUDED' and p.require_adjustment:
                if not obs or any(o.adjustment is None or adjustment_eligible(o.adjustment,o.adjustment_pin,known_at,p.required_profile,p.required_basis).startswith('BLOCKED') or o.adjustment_pin is not None and o.adjustment_pin.raw.raw.listing_id!=listing for o in obs):status='BLOCKED_AVAILABILITY';reasons.append('BLOCKED_ADJUSTMENT_CONTEXT')
            if status=='INCLUDED' and p.view=='LIQUIDITY':
                if p.liquidity_policy is None:status=liq='BLOCKED_LIQUIDITY_COVERAGE'
                else:
                    liq,detail=liquidity(replace(r,listing_id=listing),x,obs,valid_at,known_at,p.liquidity_policy)
                    reasons.append(canonical(detail))
                    if liq!='ELIGIBLE':status=liq
            if status=='INCLUDED' and p.view=='EXECUTION':
                eligible=[o for o in obs if o.adjustment is not None and o.adjustment_pin is not None and o.session_date==valid_at and availability(o,known_at,p.availability_policy,x)=='AVAILABLE' and adjustment_eligible(o.adjustment,o.adjustment_pin,known_at,'EXECUTION','RAW_UNADJUSTED')=='ELIGIBLE_SOURCE_BACKED' and o.adjustment.execution_eligibility and o.adjustment_pin.raw.raw.listing_id==listing]
                execution=bool(eligible) and x.mode=='STRICT'
                if not execution:status='BLOCKED_TRADABILITY'
        reasons.append(status)
        decisions.append(c.MemberDecision(r.revision_id,security,listing,status,tuple(reasons),r.evidence.evidence_id,digest(resolution),r.claim.status,research,liq,tradability or 'UNKNOWN',execution))
    rows=tuple(decisions)
    if len(rows)!=len(selected) or len({r.revision_id for r in rows})!=len(rows):raise ValueError('ACCOUNTING_INVARIANT')
    included=tuple(sorted({(v.security_id if d.identity_granularity=='SECURITY' else v.listing_id) for v in rows if v.status=='INCLUDED'}- {None}))
    snapshot=c.UniverseSnapshot(d.universe_id,d.version,valid_at,known_at,x.source_snapshot_id,tuple(v.revision_id for v in selected),rows,tuple(sorted(set(actual))),included,state,canonical(reconciliation),canonical(bindings(x,valid_at,known_at,p,selected)),digest(rows),p.policy_version,p.availability_policy.policy_version,p.liquidity_policy.policy_version if p.liquidity_policy else None)
    # Publication remains blocked until separate authentic corpus and release gates pass.
    return snapshot

def get_eligible_members(snapshot:c.UniverseSnapshot)->tuple[c.MemberDecision,...]:return tuple(v for v in snapshot.decisions if v.status=='INCLUDED')

def explain_member_decision(snapshot:c.UniverseSnapshot,revision_id:str)->c.MemberDecision:
    return next(v for v in snapshot.decisions if v.revision_id==revision_id)

def compare_universe_snapshots(old:c.UniverseSnapshot,new:c.UniverseSnapshot)->dict[str,Any]:
    if old.universe_id!=new.universe_id:raise ValueError('SNAPSHOT_SCOPE_MISMATCH')
    a={v.revision_id:v for v in old.decisions};b={v.revision_id:v for v in new.decisions}
    return {'added':sorted(set(b)-set(a)),'removed':sorted(set(a)-set(b)),'changed':sorted(n for n in set(a)&set(b) if a[n]!=b[n]),'old':old.snapshot_digest,'new':new.snapshot_digest}

def replay_universe_decisions(x:c.UniverseContext,steps:tuple[tuple[date,datetime],...],policy:c.EligibilityPolicy,*,max_steps:int=366)->tuple[c.UniverseSnapshot,...]:
    if type(steps) is not tuple or not 0<max_steps<=3660 or len(steps)>max_steps:raise ValueError('REPLAY_BUDGET')
    if steps and (max(v[0] for v in steps)-min(v[0] for v in steps)).days>3660:raise ValueError('REPLAY_DATE_BUDGET')
    return tuple(get_universe_as_of(x,d,k,policy,x.source_snapshot_id) for d,k in steps)
''')
(D/'compatibility.py').write_text('''"""OD08 read-only integration with the existing strict/legacy inventory contracts."""
from datetime import date
from sqlalchemy.orm import Session
from omegadata.identity_adapters import LegacyMembershipObservation,legacy_universe_inventory,source_backfill
from omegadata.universe.contracts import UniverseContext,MemberDecision
from omegadata.universe.temporal import get_membership_history

def legacy_inventory(session:Session,universe_id:str,valid_at:date)->tuple[LegacyMembershipObservation,...]:
    return legacy_universe_inventory(session,universe_id,valid_at)

def source_dependent_backfill()->None:
    from pathlib import Path
    source_backfill(Path('UNUSED_NO_SOURCE_TRAVERSAL'))

def membership_history(context:UniverseContext,event_id:str)->tuple[str,...]:
    return tuple(r.revision_id for r in get_membership_history(context,event_id))
''')
