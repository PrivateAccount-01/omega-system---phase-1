from pathlib import Path
S=Path('/home/parilrupani/omega-od06-final-20261118T075140Z/staged2/repo')
p=S/'src/omegadata/identity.py';v=p.read_text()
v=v.replace('from dataclasses import dataclass, replace','from dataclasses import dataclass, field, replace')
v=v.replace('from uuid import NAMESPACE_URL, uuid5','from uuid import NAMESPACE_URL, uuid5\n\nfrom omegadata.identity_authority import EvidenceAuthority')
v=v.replace("return self.classification == 'SOURCE_DOCUMENT' and self.authentication == 'VERIFIED'","return False  # Plain labels cannot establish trusted financial evidence.")
v=v.replace('or old.exchange != r.exchange or old.valid_from != r.valid_from','or old.listing_id != r.listing_id\n                or old.exchange != r.exchange or old.valid_from != r.valid_from')
v=v.replace('    financial_eligible: bool = False','    financial_eligible: bool = field(default=False, init=False)')
v=v.replace('    claims: tuple[IdentifierClaim, ...] = ()','    claims: tuple[IdentifierClaim, ...] = ()\n    authority: EvidenceAuthority | None = field(default=None, compare=False, repr=False)')
v=v.replace('        ii = {r.issuer_id for r in self.issuers}',"        if self.authority is not None and type(self.authority) is not EvidenceAuthority:\n            raise ValueError('TRUSTED_AUTHORITY_TYPE')\n        ii = {r.issuer_id for r in self.issuers}")
v=v.replace('if any(c.known_from is None or not c.evidence.eligible(evidence_policy) for c in candidates):',"if any(c.known_from is None or not (c.evidence.eligible(evidence_policy) if evidence_policy=='CANARY_ONLY'\n                   else self.authority is not None and self.authority.check_claim(c,known_at).allowed) for c in candidates):")
v=v.replace("        return Resolution('RESOLVED', ids, listing.listing_id, security.security_id,\n                          security.issuer_id, c.lifecycle, evidence_policy == 'STRICT')", "        result=Resolution('RESOLVED', ids, listing.listing_id, security.security_id,\n                          security.issuer_id, c.lifecycle)\n        object.__setattr__(result,'financial_eligible', evidence_policy=='STRICT')\n        return result")
v=v.replace('        text(self.event_id)',"        if type(self.affected_identity_ids) is not tuple:\n            raise ValueError('IMMUTABLE_EVENT_IDENTITIES')\n        text(self.event_id)")
p.write_text(v)
p=S/'src/omegadata/identity_adapters.py';v=p.read_text()
v=v.replace("    status: str = 'SOURCE_BACKED_UNVERIFIED'","    status: str = 'SOURCE_BACKED_UNVERIFIED'\n    supersedes_membership_id: str | None = None")
v=v.replace('    financial_eligible: bool = False','    financial_eligible: bool = field(default=False, init=False)\n    authoritative_coverage: bool = field(default=False, init=False)')
needle="    selected = tuple(sorted((c for c in claims if c.index_name == index_name"
v=v.replace(needle,"""    by_id={c.membership_id:c for c in claims}
    ends: dict[str,datetime]={}
    for claim in claims:
        if claim.supersedes_membership_id is not None:
            old=by_id.get(claim.supersedes_membership_id)
            if (old is None or old.membership_id in ends or old.known_from is None
                    or claim.known_from is None or claim.known_from<=old.known_from
                    or (old.index_name,old.exchange,old.valid_from,old.valid_to)!=(claim.index_name,claim.exchange,claim.valid_from,claim.valid_to)):
                raise ValueError('INVALID_MEMBERSHIP_SUPERSESSION')
            ends[old.membership_id]=claim.known_from
    selected = tuple(sorted((c for c in claims if c.index_name == index_name""")
v=v.replace('and (c.known_to is None or known_at < c.known_to)), key=lambda c: c.membership_id))','and (c.known_to is None or known_at < c.known_to)\n        and (c.membership_id not in ends or known_at<ends[c.membership_id])), key=lambda c: c.membership_id))')
v=v.replace("                          len(selected), 'COMPLETE' if complete else 'INCOMPLETE',\n                          bool(selected) and complete and evidence_policy == 'STRICT')","                          len(selected), 'COMPLETE' if complete else 'INCOMPLETE')")
p.write_text(v)
p=S/'src/omegadata/session_calendar.py';v=p.read_text()
v=v.replace('from dataclasses import dataclass, replace','from dataclasses import dataclass, field, replace')
v=v.replace('from omegadata.identity import Evidence, Policy, aware, intervals, query_time, text','from omegadata.identity import Evidence, Policy, aware, intervals, query_time, text\nfrom omegadata.identity_authority import EvidenceAuthority')
v=v.replace('    financial_eligible: bool = False','    financial_eligible: bool = field(default=False, init=False)')
v=v.replace('    claims: tuple[SessionClaim, ...] = ()\n\n    def __post_init__',"    claims: tuple[SessionClaim, ...] = ()\n    coverage: tuple[CoverageClaim, ...] = ()\n    authority: EvidenceAuthority | None = field(default=None,compare=False,repr=False)\n\n    def __post_init__")
v=v.replace('        revision_ends(self.claims)',"        if type(self.coverage) is not tuple or len({c.coverage_id for c in self.coverage})!=len(self.coverage):\n            raise ValueError('INVALID_COVERAGE_LEDGER')\n        if self.authority is not None and type(self.authority) is not EvidenceAuthority:\n            raise ValueError('TRUSTED_AUTHORITY_TYPE')\n        revision_ends(self.claims)")
v=v.replace('if c.known_from is None or not c.evidence.eligible(evidence_policy):',"if c.known_from is None or not (c.evidence.eligible(evidence_policy) if evidence_policy=='CANARY_ONLY'\n                else self.authority is not None and self.authority.check_claim(c,known_at).allowed):")
v=v.replace("        return SessionResolution(status, selected, evidence_policy == 'STRICT')", "        result=SessionResolution(status, selected)\n        object.__setattr__(result,'financial_eligible',evidence_policy=='STRICT')\n        return result")
insert='''
    def coverage_status(self,exchange: str,day: date,known_at: datetime,
                        evidence_policy: Policy='STRICT') -> str:
        query_time(known_at)
        selected=tuple(c for c in self.coverage if c.exchange==exchange and c.valid_from<=day<c.valid_to
            and c.known_from is not None and c.known_from<=known_at
            and (c.known_to is None or known_at<c.known_to))
        if not selected:return 'UNKNOWN'
        if len(selected)>1:return 'CONFLICTING'
        c=selected[0]
        eligible=c.evidence.eligible(evidence_policy) if evidence_policy=='CANARY_ONLY' else (
            self.authority is not None and self.authority.check_claim(c,known_at).allowed)
        return c.status if eligible else 'UNKNOWN'

    def next_session(self,exchange: str,day: date,known_at: datetime,
                     evidence_policy: Policy='STRICT',*,direction: int=1) -> SessionResolution:
        if direction not in {-1,1}:raise ValueError('SESSION_DIRECTION')
        for _ in range(3660):
            day+=timedelta(days=direction)
            if self.coverage_status(exchange,day,known_at,evidence_policy)!='COMPLETE':
                raise ValueError('CALENDAR_COVERAGE_REQUIRED')
            result=self.query(exchange,day,known_at,evidence_policy)
            if result.status in {'AUTHORITATIVE_SESSION','VERIFIED_SPECIAL_SESSION'}:return result
            if result.status!='KNOWN_CLOSURE':raise ValueError('SESSION_EVIDENCE_REQUIRED')
        raise ValueError('CALENDAR_RESOURCE_LIMIT')

    def previous_session(self,exchange: str,day: date,known_at: datetime,
                         evidence_policy: Policy='STRICT') -> SessionResolution:
        return self.next_session(exchange,day,known_at,evidence_policy,direction=-1)

'''
v=v.replace('    def add_business_days(',insert+'    def add_business_days(')
v=v.replace("        anchor = self.query(exchange, anchor_date, known_at, evidence_policy)","        if evidence_policy=='STRICT' and self.coverage_status(exchange,anchor_date,known_at,evidence_policy)!='COMPLETE':\n            raise ValueError('CALENDAR_COVERAGE_REQUIRED')\n        anchor = self.query(exchange, anchor_date, known_at, evidence_policy)")
v=v.replace('            session = self.query(exchange, current, known_at, evidence_policy)',"            if evidence_policy=='STRICT' and self.coverage_status(exchange,current,known_at,evidence_policy)!='COMPLETE':\n                raise ValueError('CALENDAR_COVERAGE_REQUIRED')\n            session = self.query(exchange, current, known_at, evidence_policy)")
coverage='''
@dataclass(frozen=True)
class CoverageClaim:
    coverage_id: str
    exchange: str
    valid_from: date
    valid_to: date
    known_from: datetime | None
    known_to: datetime | None
    evidence: Evidence
    calendar_version: str
    status: str

    def __post_init__(self) -> None:
        for value in (self.coverage_id,self.exchange,self.calendar_version):text(value)
        intervals(self.valid_from,self.valid_to,self.known_from,self.known_to)
        if self.status not in {'COMPLETE','INCOMPLETE','UNKNOWN'}:
            raise ValueError('COVERAGE_STATUS')

'''
v=v.replace('@dataclass(frozen=True)\nclass VerifiedCalendar:',coverage+'\n@dataclass(frozen=True)\nclass VerifiedCalendar:')
p.write_text(v)
