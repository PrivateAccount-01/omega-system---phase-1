from pathlib import Path
B=Path('/home/parilrupani/omega-od07-20261119T171019Z');P=B/'staged2/repo/src/omegadata/adjustments'
p=P/'temporal.py';v=p.read_text();v=v.replace('from datetime import datetime','from datetime import datetime\nfrom dataclasses import dataclass, replace\nfrom omegadata.identity import Evidence\nfrom omegadata.session_calendar import VerifiedCalendar')
pos=v.index('\ndef eligibility(')
v=v[:pos]+'''
@dataclass(frozen=True)
class AuthorityClaim:
    evidence: Evidence
    payload: str
    source_evidence_version: str

def verified(value: object, evidence: Evidence, x: Context) -> bool:
    return x.authority is not None and x.authority.check_claim(AuthorityClaim(evidence,canonical(value),x.source_evidence_version),x.known_at).allowed

def raw_eligibility(raw: Raw, x: Context, *, execution: bool=False) -> tuple[str,str]:
    if raw.known_from is None or raw.known_from>x.known_at:return "BLOCKED_KNOWLEDGE","RAW_AVAILABILITY_UNKNOWN"
    if raw.evidence.permission!="PERMITTED":return "BLOCKED_EVIDENCE","RAW_RIGHTS_REFUSAL"
    mode="CANARY_ONLY" if x.mode=="NON_MARKET_MATH" else "STRICT"
    if not (raw.evidence.eligible(mode) if mode=="CANARY_ONLY" else verified(raw,raw.evidence,x)):return "BLOCKED_EVIDENCE","RAW_AUTHORITY_NOT_SUPPLIED"
    for day in (x.valid_at,raw.trade_date):
        result=x.identity_repository.resolve_listing(raw.exchange,raw.symbol,raw.series,day,x.known_at,mode)
        if result.state!="RESOLVED" or result.security_id!=raw.security_id or result.listing_id!=raw.listing_id or execution and result.lifecycle!="LISTED":return "BLOCKED_IDENTITY","IDENTITY_OR_EXECUTION_STATUS_UNRESOLVED"
    return "CALCULATED","RAW_ELIGIBILITY_CHECKED"
''' +v[pos:]
v=v.replace('if ref.known_from is None or ref.known_from>x.known_at:', 'if ref.known_from is not None:query_time(ref.known_from)\n        if ref.known_from is None or ref.known_from>x.known_at:')
v=v.replace('if x.authority is None or not x.authority.verify_identity_evidence(a.evidence.evidence_id,{}, {},"RESEARCH",x.known_at,digest(a)).allowed:', 'if not verified(a,a.evidence,x):')
v=v.replace('    identity=x.identity_repository.resolve_listing', '''    for ref in references(a):
        if ref.currency!=raw.currency:return "INVALID_PARAMETERS","REFERENCE_CURRENCY_MISMATCH",""
        if mode=="STRICT" and (ref.evidence is None or not verified(ref,ref.evidence,x)):return "BLOCKED_EVIDENCE","REFERENCE_AUTHORITY_UNKNOWN",""
    if isinstance(a.parameters,(Rights,Dividend)) and a.parameters.currency!=raw.currency:return "INVALID_PARAMETERS","ACTION_CURRENCY_MISMATCH",""
    identity=x.identity_repository.resolve_listing''')
v=v.replace('prior=x.calendar.previous_session(a.exchange,a.ex_date,x.known_at,mode)', '''pinned=VerifiedCalendar(tuple(c for c in x.calendar.claims if c.calendar_version==x.calendar_version),tuple(c for c in x.calendar.coverage if c.calendar_version==x.calendar_version),x.calendar.authority)
            prior=pinned.previous_session(a.exchange,a.ex_date,x.known_at,mode)''')
p.write_text(v)
p=P/'chains.py';v=p.read_text().replace('eligibility, select_revisions','eligibility, raw_eligibility, select_revisions')
v=v.replace('    inputs=canonical(', '    try:inputs=canonical(')
a=v.index('    def blocked(')
v=v[:a]+'    except (ValueError,TypeError):return Result("INVALID_PARAMETERS","NONFINITE_OR_INVALID_INPUT",raw.artifact_id,consumer_profile=policy.profile)\n'+v[a:]
v=v.replace('    try:selected=select_revisions', '''    status,reason=raw_eligibility(raw,x,execution=policy.profile=="EXECUTION")
    if status!="CALCULATED":return blocked(status,reason)
    try:selected=select_revisions''')
v=v.replace('    applicable=[', '''    if any(a.known_to is not None and a.known_to<=x.known_at and not any(b.supersedes_action_id==a.action_id and b.known_from is not None and b.known_from<=x.known_at for b in actions) for a in actions):return blocked("BLOCKED_KNOWLEDGE","EXPIRED_ACTION_WITHOUT_KNOWN_SUCCESSOR")
    applicable=[''')
v=v.replace('        for a in ordered:\n', '''        for a in ordered:
            if policy.profile=="EXECUTION" and a.action_type in {"SUSPENSION","DELISTING","DELISTING_VOLUNTARY","DELISTING_REGULATORY"}:return blocked("BLOCKED_IDENTITY","LIFECYCLE_EXECUTION_CONSTRAINT")
''')
p.write_text(v)
p=P/'repository.py';v=p.read_text();v=v.replace('            old=connection.scalar(select(results.c.payload)', '''            stored={a.action_id:a for a in self._all(connection)}
            for link in result.adjustment_factor_chain:
                if link.action_revision_id not in stored or c.canonical(stored[link.action_revision_id])!=link.input_parameters:raise ValueError('RESULT_ACTION_PAYLOAD_MISMATCH')
            old=connection.scalar(select(results.c.payload)''')
p.write_text(v)
