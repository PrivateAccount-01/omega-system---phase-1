from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');D=B/'staged2/repo/src/omegadata/universe'
p=D/'contracts.py';s=p.read_text().replace("    version:str='od08.membership/v1'", "    version:str='od08.membership/v1'\n    effective_at:datetime|None=None\n    removal_effective_at:datetime|None=None").replace("self.effective_convention not in {'SOURCE_DATE','UNKNOWN'}", "self.effective_convention not in {'SOURCE_DATE','EXPLICIT_TIMESTAMP','UNKNOWN'}").replace("        for stamp in (self.announcement_at,self.published_at,self.ingested_at):", "        for stamp in (self.announcement_at,self.published_at,self.ingested_at,self.effective_at,self.removal_effective_at):").replace("    valid_at:date\n    known_at", "    valid_at:date|datetime\n    known_at")
s=s.replace("raise ValueError('MEMBERSHIP_VERSION')", "raise ValueError('MEMBERSHIP_VERSION')\n        if self.effective_convention=='EXPLICIT_TIMESTAMP' and self.effective_at is None:raise ValueError('EXPLICIT_EFFECTIVE_TIME_REQUIRED')\n        if self.effective_at is not None and self.removal_effective_at is not None and self.effective_at>=self.removal_effective_at:raise ValueError('EFFECTIVE_TIME_INTERVAL')")
p.write_text(s)
p=D/'temporal.py';s=p.read_text().replace('from typing import Any','from typing import Any\nfrom zoneinfo import ZoneInfo')
a=s.index('def select_memberships(');z=s.index('\ndef get_membership_history',a)
s=s[:a]+'''def business_day(point:date|datetime)->date:
    if isinstance(point,datetime):
        query_time(point);return point.astimezone(ZoneInfo('Asia/Kolkata')).date()
    if type(point) is not date:raise ValueError('DATE_OR_AWARE_TIMESTAMP_REQUIRED')
    return point

def valid_member(r:c.MembershipRevision,point:date|datetime)->bool:
    day=business_day(point);claim=r.claim
    upper=claim.valid_to
    if claim.valid_from>day:return False
    if upper is not None and (day>upper or day==upper and r.removal_effective_at is None):return False
    if isinstance(point,datetime):
        if r.effective_at is not None and point<r.effective_at:return False
        if r.removal_effective_at is not None and point>=r.removal_effective_at:return False
    return True

def select_memberships(x:c.UniverseContext,day:date|datetime,cutoff:datetime)->tuple[c.MembershipRevision,...]:
    business_day(day)
    return tuple(r for r in visible_revisions(x,cutoff) if valid_member(r,day))
''' +s[z:]
s=s.replace("        if not authorized(r,x,cutoff):status='SOURCE_BLOCKED'", "        if any(v is not None and v>cutoff for v in (r.announcement_at,r.published_at)):status='BLOCKED_AVAILABILITY'\n        if not authorized(r,x,cutoff):status='SOURCE_BLOCKED'")
p.write_text(s)
p=D/'snapshots.py';s=p.read_text().replace('authorized,known,availability','authorized,known,availability,business_day').replace('def bindings(x:c.UniverseContext,day:date,','def bindings(x:c.UniverseContext,day:date|datetime,').replace('valid_at:date,known_at:datetime','valid_at:date|datetime,known_at:datetime')
s=s.replace('query_time(known_at);d=x.definition;p=eligibility_policy','query_time(known_at);d=x.definition;p=eligibility_policy;valid_point=valid_at;valid_at=business_day(valid_point)').replace("if source_snapshot_id!=x.source_snapshot_id or type(valid_at) is not date", "if source_snapshot_id!=x.source_snapshot_id").replace('selected=select_memberships(x,valid_at,known_at)','selected=select_memberships(x,valid_point,known_at)')
s=s.replace("r.effective_convention=='UNKNOWN'", "(r.effective_convention=='UNKNOWN' or r.effective_convention=='EXPLICIT_TIMESTAMP' and not isinstance(valid_point,datetime))")
s=s.replace('snapshot=c.UniverseSnapshot(d.universe_id,d.version,valid_at,known_at','snapshot=c.UniverseSnapshot(d.universe_id,d.version,valid_point,known_at').replace('canonical(bindings(x,valid_at,known_at,p,selected))','canonical(bindings(x,valid_point,known_at,p,selected))')
p.write_text(s)
p=D/'repository.py';s=p.read_text().replace('from omegadata.universe.temporal import validate_revisions','from omegadata.universe.temporal import validate_revisions,business_day')
s=s.replace("Column('known_to',String),*payload())", "Column('known_to',String),Column('effective_at',String),Column('removal_at',String),*payload())",1)
s=s.replace('def _rows(self,con:Connection,table:Table)->tuple[Any,...]:\n        rows=con.execute(select(table.c.payload,table.c.digest).order_by(table.c.id)).all()', "def _rows(self,con:Connection,table:Table,event_id:str|None=None)->tuple[Any,...]:\n        stmt=select(table.c.payload,table.c.digest).order_by(table.c.id)\n        if event_id is not None:stmt=stmt.where(table.c.event==event_id)\n        rows=con.execute(stmt).all()")
s=s.replace('for r in self._rows(con,members) if r.universe_id==value.universe_id','for r in self._rows(con,members,value.event_id) if r.universe_id==value.universe_id').replace('known_to=sqltime(value.claim.known_to))','known_to=sqltime(value.claim.known_to),effective_at=sqltime(value.effective_at),removal_at=sqltime(value.removal_effective_at))')
s=s.replace('day:date,cutoff:datetime','day:date|datetime,cutoff:datetime')
s=s.replace("child=members.alias('successor');k=sqltime(cutoff)", "child=members.alias('successor');k=sqltime(cutoff);point=day;day=business_day(point)")
s=s.replace('or_(members.c.valid_to.is_(None),members.c.valid_to>sqltime(day))','or_(members.c.valid_to.is_(None),members.c.valid_to>sqltime(day),(members.c.valid_to==sqltime(day)) & members.c.removal_at.is_not(None))')
s=s.replace('        return tuple(con.execute(stmt).scalars())', "        if isinstance(point,datetime):stmt=stmt.where(or_(members.c.effective_at.is_(None),members.c.effective_at<=sqltime(point)),or_(members.c.removal_at.is_(None),members.c.removal_at>sqltime(point)))\n        return tuple(con.execute(stmt).scalars())",1)
p.write_text(s)
