from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');S=B/'staged2/repo';P=S/'src/omegadata/adjustments';P.mkdir()
files={
'__init__.py': '''"""OD07 opt-in immutable adjustment engineering; no source acquisition or publication."""\n''',
'contracts.py': '''"""Versioned immutable inputs. NON_MARKET_MATH is permanently publication-ineligible."""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from omegadata.identity import Evidence, MemoryIdentityRepository, aware, query_time, text
from omegadata.identity_authority import EvidenceAuthority
from omegadata.session_calendar import VerifiedCalendar

VERSION = "od07.calc/v1"
PRECISION = 80

def normalized(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value,type): return normalized(asdict(value))
    if isinstance(value,Decimal):
        if not value.is_finite(): raise ValueError("NONFINITE_CANONICAL")
        return str(value)
    if isinstance(value,datetime):
        query_time(value);return value.astimezone(UTC).isoformat()
    if isinstance(value,date):return value.isoformat()
    if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [normalized(v) for v in value]
    return value

def canonical(value: Any) -> str:
    return json.dumps(normalized(value),sort_keys=True,separators=(",",":"),allow_nan=False)

def digest(value: Any) -> str:return hashlib.sha256(canonical(value).encode()).hexdigest()

def number(value: Any, *, zero: bool=False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value < 0 or (not zero and value==0):
        raise ValueError("INVALID_DECIMAL")
    if len(value.as_tuple().digits)>64 or abs(value.as_tuple().exponent)>64:
        raise ValueError("DECIMAL_RESOURCE_LIMIT")
    return value

@dataclass(frozen=True)
class Reference:
    value: Decimal
    session_date: date
    known_from: datetime | None
    artifact_id: str
    currency: str
    evidence: Evidence | None = None
    source_id: str | None = None

@dataclass(frozen=True)
class Split:
    multiplier: Decimal

@dataclass(frozen=True)
class Bonus:
    new_shares: Decimal
    existing_shares: Decimal

@dataclass(frozen=True)
class Rights:
    existing_shares: Decimal
    new_shares: Decimal
    subscription_price: Decimal | None
    reference: Reference | None
    currency: str
    exercise_assumed: bool | None

@dataclass(frozen=True)
class Dividend:
    amount: Decimal
    currency: str
    reinvestment: Reference | None
    convention: str | None

@dataclass(frozen=True)
class Merger:
    successor_security_id: str | None
    exchange_ratio: Decimal | None
    cash_component: Decimal | None

@dataclass(frozen=True)
class Demerger:
    successor_security_id: str | None
    entitlement_ratio: Decimal | None
    successor_value: Reference | None

@dataclass(frozen=True)
class Conversion:
    successor_security_id: str | None
    exchange_ratio: Decimal | None

@dataclass(frozen=True)
class Lifecycle:
    constraint: str = "NO_PRICE_FACTOR"

Parameters = Split | Bonus | Rights | Dividend | Merger | Demerger | Conversion | Lifecycle

@dataclass(frozen=True)
class Action:
    action_id: str
    action_type: str
    security_id: str
    listing_id: str | None
    exchange: str
    evidence: Evidence
    source_artifact_identity: str
    ex_date: date | None
    known_from: datetime | None
    known_to: datetime | None
    parameters: Parameters
    source_id: str
    announcement_at: datetime | None = None
    published_at: datetime | None = None
    effective_date: date | None = None
    record_date: date | None = None
    ingested_at: datetime | None = None
    parameter_known_from: datetime | None = None
    parameter_version: str = "od07.parameters/v1"
    action_revision: int = 1
    supersedes_action_id: str | None = None
    review_status: str = "UNVERIFIED"
    sequence: int | None = None
    version: str = "od07.action/v1"

    def __post_init__(self) -> None:
        for v in (self.action_id,self.action_type,self.security_id,self.exchange,self.source_id,self.source_artifact_identity):text(v)
        if self.listing_id is not None:text(self.listing_id)
        for t in (self.known_from,self.known_to,self.announcement_at,self.published_at,self.ingested_at,self.parameter_known_from):aware(t)
        for d in (self.ex_date,self.effective_date,self.record_date):
            if d is not None and type(d) is not date:raise ValueError("DATE_REQUIRED")
        if self.known_to is not None and (self.known_from is None or self.known_to<=self.known_from):raise ValueError("KNOWLEDGE_INTERVAL")
        if self.version!="od07.action/v1" or self.parameter_version!="od07.parameters/v1" or type(self.action_revision) is not int or self.action_revision<1:raise ValueError("ACTION_VERSION")
        if type(self.parameters) not in (Split,Bonus,Rights,Dividend,Merger,Demerger,Conversion,Lifecycle):raise ValueError("PARAMETER_TYPE")
        if self.sequence is not None and (type(self.sequence) is not int or self.sequence<0):raise ValueError("ACTION_SEQUENCE")
        if self.review_status not in {"UNVERIFIED","REVIEWED","REVOKED","CONFLICTING"}:raise ValueError("REVIEW_STATUS")

@dataclass(frozen=True)
class Raw:
    artifact_id: str
    security_id: str
    listing_id: str
    exchange: str
    symbol: str
    series: str
    trade_date: date
    known_from: datetime | None
    price: Decimal
    volume: Decimal
    currency: str
    evidence: Evidence
    original_price_basis: str = "RAW"
    def __post_init__(self) -> None:
        for v in (self.artifact_id,self.security_id,self.listing_id,self.exchange,self.symbol,self.series,self.currency):text(v)
        if type(self.trade_date) is not date or self.original_price_basis!="RAW":raise ValueError("RAW_BASIS_OR_DATE")
        aware(self.known_from);number(self.price);number(self.volume,zero=True)

@dataclass(frozen=True)
class Policy:
    profile: str
    direction: str = "BACKWARD"
    version: str = "od07.policy/v1"
    price_quantum: Decimal = Decimal("0.000001")
    volume_quantum: Decimal = Decimal("0.0001")
    def __post_init__(self) -> None:
        if self.profile not in {"RAW","EXECUTION","PRICE_RETURN","TOTAL_RETURN","VOLUME"} or self.direction not in {"BACKWARD","FORWARD"} or self.version!="od07.policy/v1":raise ValueError("UNSUPPORTED_POLICY")
        if self.price_quantum!=Decimal(".000001") or self.volume_quantum!=Decimal(".0001"):raise ValueError("ROUNDING_VERSION")

@dataclass(frozen=True)
class Context:
    valid_at: date
    known_at: datetime
    identity_version: str
    source_evidence_version: str
    calendar_version: str
    mode: str
    identity_repository: MemoryIdentityRepository
    calendar: VerifiedCalendar
    authority: EvidenceAuthority | None = field(default=None,compare=False,repr=False)
    def __post_init__(self) -> None:
        query_time(self.known_at)
        if type(self.valid_at) is not date or self.mode not in {"STRICT","NON_MARKET_MATH"}:raise ValueError("CONTEXT")
        if self.identity_version!="od06.identity/v1":raise ValueError("IDENTITY_VERSION")
        for v in (self.source_evidence_version,self.calendar_version):text(v)
        if type(self.identity_repository) is not MemoryIdentityRepository or type(self.calendar) is not VerifiedCalendar:raise ValueError("UPSTREAM_TYPE")
        if self.authority is not None and type(self.authority) is not EvidenceAuthority:raise ValueError("AUTHORITY_TYPE")

@dataclass(frozen=True)
class Factor:
    status: str
    reason: str
    numerator: Decimal | None = None
    denominator: Decimal | None = None
    price_factor: Decimal | None = None
    volume_numerator: Decimal | None = None
    volume_denominator: Decimal | None = None
    volume_factor: Decimal | None = None

@dataclass(frozen=True)
class Link:
    action_revision_id: str
    source_artifact_id: str
    identity_resolution_id: str
    calendar_reference: str
    raw_observation_reference: str
    calculation_version: str
    consumer_profile: str
    input_parameters: str
    factor: Factor
    rounding_policy: str
    knowledge_cutoff: datetime

@dataclass(frozen=True)
class Result:
    status: str
    reason: str
    original_raw_reference: str = ""
    original_price_basis: str = "RAW"
    consumer_profile: str = ""
    adjustment_factor_chain: tuple[Link,...] = ()
    cumulative_factor: Decimal | None = None
    cumulative_volume_factor: Decimal | None = None
    adjusted_price: Decimal | None = None
    adjusted_volume: Decimal | None = None
    inputs: str = ""
    publication_eligibility: bool = field(default=False,init=False)
    version: str = VERSION
    @property
    def canonical_json(self) -> str:return canonical(self)
    @property
    def output_digest(self) -> str:return hashlib.sha256(self.canonical_json.encode()).hexdigest()
''',
'factors.py': '''"""Exact rational terms in Decimal, division only under local versioned precision.
Total return: gross single-security ex-close reinvestment, backward Q/(Q+D).
This is an explicit research policy, not an exchange/index certification.
"""
from decimal import Decimal, InvalidOperation, localcontext
from omegadata.adjustments.contracts import Bonus, Conversion, Demerger, Dividend, Factor, Lifecycle, Merger, Policy, PRECISION, Rights, Split, number

def factor(kind: str, p: object, policy: Policy) -> Factor:
    try:
        with localcontext() as context:
            context.prec=20480
            n,d,vn,vd=Decimal(1),Decimal(1),Decimal(1),Decimal(1)
            if kind in {"SPLIT","SPLIT_REVERSE"} and type(p) is Split:
                d=number(p.multiplier);vn=d
            elif kind=="BONUS" and type(p) is Bonus:
                old=number(p.existing_shares);new=number(p.new_shares)
                n,d=old,old+new;vn,vd=d,n
            elif kind in {"RIGHTS","RIGHTS_RENOUNCE"} and type(p) is Rights:
                old,new=number(p.existing_shares),number(p.new_shares)
                issue=number(p.subscription_price,zero=True)
                if p.reference is None or p.exercise_assumed is not True or p.reference.currency!=p.currency:raise ValueError("RIGHTS_REFERENCE_OR_EXERCISE")
                prior=number(p.reference.value)
                n,d=old*prior+new*issue,(old+new)*prior
            elif kind in {"DIVIDEND_CASH","DIVIDEND_SPECIAL"} and type(p) is Dividend:
                amount=number(p.amount,zero=True)
                if policy.profile!="TOTAL_RETURN":return Factor("NOT_APPLICABLE","CASH_DISTRIBUTION_SEPARATE_FROM_PRICE_RETURN",Decimal(1),Decimal(1),Decimal(1),Decimal(1),Decimal(1),Decimal(1))
                if p.convention!="EX_CLOSE_GROSS" or p.reinvestment is None or p.reinvestment.currency!=p.currency:raise ValueError("DIVIDEND_REINVESTMENT_REQUIRED")
                n=number(p.reinvestment.value);d=n+amount
            elif type(p) is Lifecycle and kind in {"SUSPENSION","REINSTATEMENT","LISTING","DELISTING","DELISTING_VOLUNTARY","DELISTING_REGULATORY"}:
                return Factor("NOT_APPLICABLE","LIFECYCLE_NOT_PRICE_FACTOR",Decimal(1),Decimal(1),Decimal(1),Decimal(1),Decimal(1),Decimal(1))
            elif type(p) in {Merger,Demerger,Conversion}:return Factor("UNSUPPORTED_POLICY","MULTI_SECURITY_ALLOCATION_AND_CONTINUITY_REQUIRE_REVIEWED_METHOD")
            else:return Factor("UNSUPPORTED_POLICY","ACTION_OR_PARAMETER_CONTRACT_UNSUPPORTED")
            if policy.profile in {"RAW","EXECUTION"}:n=d=vn=vd=Decimal(1)
            elif policy.profile=="VOLUME":n=d=Decimal(1)
            if policy.direction=="FORWARD":n,d,vn,vd=d,n,vd,vn
            context.prec=PRECISION
            return Factor("CALCULATED","EXPLICIT_POLICY_MATH",n,d,n/d,vn,vd,vn/vd)
    except (ValueError,TypeError,InvalidOperation,ZeroDivisionError):return Factor("INVALID_PARAMETERS","MISSING_INVALID_OR_UNSUPPORTED_NUMERICAL_INPUT")
''',
 'temporal.py': '''"""Append-only revision selection and OD06 authority/identity/calendar integration."""
from __future__ import annotations
from datetime import datetime
from omegadata.adjustments.contracts import Action, Context, Raw, Reference, Rights, Dividend, Demerger, canonical, digest
from omegadata.identity import query_time

def select_revisions(actions: tuple[Action,...], known_at: datetime) -> tuple[Action,...]:
    query_time(known_at)
    if type(actions) is not tuple:raise ValueError("IMMUTABLE_ACTION_LEDGER")
    by_id={a.action_id:a for a in actions}
    if len(by_id)!=len(actions):raise ValueError("DUPLICATE_ACTION_ID")
    ends={}
    for a in actions:
        if a.supersedes_action_id is None:continue
        old=by_id.get(a.supersedes_action_id)
        if old is None or old.action_id in ends or a.known_from is None or old.known_from is None or a.known_from<=old.known_from or (old.security_id,old.listing_id,old.exchange,old.ex_date,old.action_type)!=(a.security_id,a.listing_id,a.exchange,a.ex_date,a.action_type) or a.action_revision!=old.action_revision+1 or old.known_to is not None and old.known_to<a.known_from:
            raise ValueError("INVALID_ACTION_SUPERSESSION")
        ends[old.action_id]=a.known_from
    return tuple(sorted((a for a in actions if (a.known_from is None or a.known_from<=known_at) and (a.known_to is None or known_at<a.known_to) and (a.action_id not in ends or known_at<ends[a.action_id])),key=lambda a:a.action_id))

def references(a: Action) -> tuple[Reference,...]:
    p=a.parameters
    ref=p.reference if isinstance(p,Rights) else p.reinvestment if isinstance(p,Dividend) else p.successor_value if isinstance(p,Demerger) else None
    return () if ref is None else (ref,)

def eligibility(a: Action, raw: Raw, x: Context) -> tuple[str,str,str]:
    for v in (raw.known_from,a.known_from):
        if v is None or v>x.known_at:return "BLOCKED_KNOWLEDGE","UNKNOWN_OR_FUTURE_AVAILABILITY",""
    for v in (a.announcement_at,a.published_at,a.parameter_known_from):
        if v is not None and v>x.known_at:return "BLOCKED_KNOWLEDGE","FUTURE_ACTION_PARAMETER",""
    for ref in references(a):
        if ref.known_from is None or ref.known_from>x.known_at:return "BLOCKED_KNOWLEDGE","REFERENCE_NOT_YET_KNOWN",""
        query_time(ref.known_from)
    if a.review_status in {"REVOKED","CONFLICTING"} or a.evidence.permission!="PERMITTED" or raw.evidence.permission!="PERMITTED":return "BLOCKED_EVIDENCE","REVIEW_OR_RIGHTS_REFUSAL",""
    if (a.security_id,a.exchange)!=(raw.security_id,raw.exchange) or a.listing_id is not None and a.listing_id!=raw.listing_id:return "BLOCKED_IDENTITY","WRONG_ACTION_IDENTITY",""
    mode="CANARY_ONLY" if x.mode=="NON_MARKET_MATH" else "STRICT"
    if mode=="CANARY_ONLY":
        if not a.evidence.eligible(mode) or not raw.evidence.eligible(mode):return "BLOCKED_EVIDENCE","MATH_ONLY_INPUT_REQUIRED",""
    else:
        # Plain labels cannot qualify; actual configured authority and canonical action binding required.
        if x.authority is None or not x.authority.verify_identity_evidence(a.evidence.evidence_id,{}, {},"RESEARCH",x.known_at,digest(a)).allowed:return "BLOCKED_EVIDENCE","AUTHENTIC_ACTION_AUTHORITY_NOT_SUPPLIED",""
    identity=x.identity_repository.resolve_listing(raw.exchange,raw.symbol,raw.series,x.valid_at,x.known_at,mode)
    historical=x.identity_repository.resolve_listing(raw.exchange,raw.symbol,raw.series,raw.trade_date,x.known_at,mode)
    if any(v.state!="RESOLVED" or v.security_id!=raw.security_id or v.listing_id!=raw.listing_id for v in (identity,historical)):return "BLOCKED_IDENTITY","IDENTITY_UNRESOLVED_OR_CONFLICTING",""
    if a.ex_date is None:return "BLOCKED_CALENDAR","EX_DATE_UNKNOWN",""
    session=x.calendar.query(a.exchange,a.ex_date,x.known_at,mode,calendar_version=x.calendar_version)
    if session.status not in {"AUTHORITATIVE_SESSION","VERIFIED_SPECIAL_SESSION"}:return "BLOCKED_CALENDAR","EX_SESSION_UNVERIFIED",""
    calendar_ref=canonical(tuple(c.claim_id for c in session.claims))
    if isinstance(a.parameters,Rights):
        try:
            prior=x.calendar.previous_session(a.exchange,a.ex_date,x.known_at,mode)
        except ValueError:return "BLOCKED_CALENDAR","PRIOR_SESSION_OR_COVERAGE_UNKNOWN",""
        ref=a.parameters.reference
        if ref is None or prior.claims[0].session_date!=ref.session_date or prior.claims[0].calendar_version!=x.calendar_version:return "BLOCKED_CALENDAR","PRIOR_VERIFIED_SESSION_MISMATCH",""
        calendar_ref=canonical((calendar_ref,prior.claims[0].claim_id))
    if isinstance(a.parameters,Dividend) and a.parameters.reinvestment is not None and a.parameters.reinvestment.session_date!=a.ex_date:return "BLOCKED_CALENDAR","REINVESTMENT_SESSION_MISMATCH",""
    return "CALCULATED",digest((identity,historical)),calendar_ref
''',
'chains.py': '''"""Deterministic immutable back/forward comparison chains; no ORM mutation."""
from decimal import Decimal, ROUND_HALF_UP, localcontext
from omegadata.adjustments.contracts import Action, Context, Link, Policy, PRECISION, Raw, Result, VERSION, canonical
from omegadata.adjustments.factors import factor
from omegadata.adjustments.temporal import eligibility, select_revisions

def calculate_chain(raw: Raw, actions: tuple[Action,...], policy: Policy, x: Context) -> Result:
    inputs=canonical({"raw":raw,"actions":tuple(sorted(actions,key=lambda a:a.action_id)),"policy":policy,"valid_at":x.valid_at,"known_at":x.known_at,"identity_version":x.identity_version,"source_evidence_version":x.source_evidence_version,"calendar_version":x.calendar_version,"mode":x.mode})
    def blocked(status: str, reason: str) -> Result:
        return Result(status,reason,raw.artifact_id,raw.original_price_basis,policy.profile,inputs=inputs)
    if len(actions)>128:return blocked("CONFLICTING_ACTIONS","ACTION_RESOURCE_LIMIT")
    if raw.trade_date>x.valid_at or raw.known_from is None or raw.known_from>x.known_at:return blocked("BLOCKED_KNOWLEDGE","RAW_NOT_AVAILABLE_AT_QUERY")
    try:selected=select_revisions(actions,x.known_at)
    except ValueError as e:return blocked("CONFLICTING_ACTIONS",str(e))
    # A directly requested future-only revision is a refusal, never silently accepted as complete.
    roots={a.action_id for a in actions if a.supersedes_action_id is None}
    if any(a.known_from is not None and a.known_from>x.known_at and a.action_id in roots for a in actions):return blocked("BLOCKED_KNOWLEDGE","REQUESTED_EVENT_NOT_YET_KNOWN")
    applicable=[a for a in selected if a.ex_date is None or raw.trade_date<a.ex_date<=x.valid_at]
    for a in applicable:
        peers=[b for b in applicable if b.ex_date==a.ex_date]
        if len(peers)>1 and (any(b.sequence is None for b in peers) or len({b.sequence for b in peers})!=len(peers)):return blocked("CONFLICTING_ACTIONS","SAME_DAY_ORDER_NOT_ESTABLISHED")
    ordered=sorted(applicable,key=lambda a:(a.ex_date or raw.trade_date,a.sequence or 0,a.action_id))
    links=[]
    with localcontext() as math:
        # Bounded 128 inputs * <=64 digits/exponents: exact multiplication before one division.
        math.prec=20480
        n=d=vn=vd=Decimal(1)
        for a in ordered:
            status,identity_ref,calendar_ref=eligibility(a,raw,x)
            if status!="CALCULATED":return blocked(status,identity_ref)
            f=factor(a.action_type,a.parameters,policy)
            if f.status not in {"CALCULATED","NOT_APPLICABLE"}:return blocked(f.status,f.reason)
            if None in (f.numerator,f.denominator,f.volume_numerator,f.volume_denominator):return blocked("INVALID_PARAMETERS","INCOMPLETE_FACTOR")
            assert f.numerator is not None and f.denominator is not None and f.volume_numerator is not None and f.volume_denominator is not None
            n*=f.numerator;d*=f.denominator;vn*=f.volume_numerator;vd*=f.volume_denominator
            links.append(Link(a.action_id,a.source_artifact_identity,identity_ref,calendar_ref,raw.artifact_id,VERSION,policy.profile,canonical(a),f,"decimal80-final-half-up/v1",x.known_at))
        math.prec=PRECISION
        cumulative=n/d;volume=vn/vd
        price=raw.price if policy.profile in {"RAW","EXECUTION","VOLUME"} else (raw.price*n/d).quantize(policy.price_quantum,rounding=ROUND_HALF_UP)
        quantity=raw.volume if policy.profile in {"RAW","EXECUTION"} else (raw.volume*vn/vd).quantize(policy.volume_quantum,rounding=ROUND_HALF_UP)
    return Result("CALCULATED","MATH_ONLY_NOT_AUTHENTIC_FINANCIAL_ACCEPTANCE" if x.mode=="NON_MARKET_MATH" else "PUBLICATION_REQUIRES_INDEPENDENT_RELEASE_GATE",raw.artifact_id,"RAW",policy.profile,tuple(links),cumulative,volume,price,quantity,inputs)
''',
'compatibility.py': '''"""Read-only opt-in legacy inspection, never implicit economic promotion."""
from dataclasses import dataclass
from typing import Any
from omegadata.adjustments.contracts import canonical

@dataclass(frozen=True)
class LegacyActionObservation:
    record_id: str
    action_type: str
    parameters: str
    known_from: None = None
    status: str = "BLOCKED_EVIDENCE"
    reason: str = "LEGACY_CONFIRMATION_NOT_AUTHENTIC_KNOWLEDGE_EVIDENCE"

def legacy_action(row: Any) -> LegacyActionObservation:
    return LegacyActionObservation(str(row.id),str(row.action_type),canonical(row.parameters or {}))
'''
}
for n,raw in files.items():(P/n).write_text(raw)
print('Implemented',len(files),'opt-in modules; legacy unchanged')
