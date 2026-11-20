from pathlib import Path
D=Path('/home/parilrupani/omega-od08-20261119T184624Z/staged2/repo/src/omegadata/universe')
(D/'repository.py').write_text('''"""Additive, append-only SQLAlchemy store in explicitly owned disposable SQLite.
Reuse OD06 transaction/path conventions and OD07 typed payload encoding.
No operational DB migration, raw-source reads, cleanup, or same-process tamper claim.
"""
from __future__ import annotations
import json,hashlib
from dataclasses import fields,replace
from datetime import date,datetime
from decimal import Decimal
from pathlib import Path
from contextlib import contextmanager
from collections.abc import Iterator
from typing import Any,cast
from sqlalchemy import Column,String,ForeignKey,MetaData,Table,Index,create_engine,event,inspect,select,func,or_,exists
from sqlalchemy.engine import Connection,make_url
from sqlalchemy.pool import StaticPool
from omegadata.universe import contracts as c
from omegadata.universe.temporal import validate_revisions
from omegadata.universe.snapshots import get_universe_as_of
from omegadata.identity_authority import EvidenceAuthority
from omegadata.adjustments.repository import encode,TYPES as OLD_TYPES
from omegadata import identity as identity
from omegadata import session_calendar as cal
from omegadata.identity_adapters import MembershipClaim
from omegadata.adjustments import contracts as ac
from omegadata.adjustments import bound_contracts as bc

M=MetaData();schema=Table('od08_schema',M,Column('version',String,primary_key=True))
def payload()->list[Column[Any]]:return [Column('payload',String,nullable=False),Column('digest',String,nullable=False)]
definitions=Table('od08_definition',M,Column('id',String,primary_key=True),Column('universe',String,nullable=False),*payload())
members=Table('od08_membership',M,Column('id',String,primary_key=True),Column('definition',ForeignKey(definitions.c.id),nullable=False),Column('universe',String,nullable=False),Column('event',String,nullable=False),Column('parent',ForeignKey('od08_membership.id'),unique=True),Column('valid_from',String,nullable=False),Column('valid_to',String),Column('known_from',String),Column('known_to',String),*payload())
coverages=Table('od08_coverage',M,Column('id',String,primary_key=True),Column('definition',ForeignKey(definitions.c.id),nullable=False),*payload())
observations=Table('od08_availability',M,Column('id',String,primary_key=True),Column('definition',ForeignKey(definitions.c.id),nullable=False),*payload())
policies=Table('od08_policy',M,Column('id',String,primary_key=True),*payload())
contexts=Table('od08_context',M,Column('id',String,primary_key=True),Column('definition',ForeignKey(definitions.c.id),nullable=False),Column('policy',ForeignKey(policies.c.id),nullable=False),*payload())
snapshots=Table('od08_snapshot',M,Column('id',String,primary_key=True),Column('context',ForeignKey(contexts.c.id),nullable=False),*payload())
decisions=Table('od08_decision',M,Column('snapshot',ForeignKey(snapshots.c.id),primary_key=True),Column('revision',ForeignKey(members.c.id),primary_key=True),*payload())
Index('od08_membership_query',members.c.universe,members.c.valid_from,members.c.known_from)
Index('od08_membership_history',members.c.event,members.c.known_from)
TYPES:dict[str,Any]={**OLD_TYPES,**{v.__name__:v for v in [c.UniverseDefinition,c.MembershipRevision,c.CoverageTransition,c.UniverseCoverage,c.AvailabilityPolicy,c.AvailabilityObservation,c.LiquidityPolicy,c.EligibilityPolicy,c.UniverseContext,c.MemberDecision,c.UniverseSnapshot,c.RankingCandidate,identity.Issuer,identity.Security,identity.Listing,identity.IdentifierClaim,identity.MemoryIdentityRepository,cal.SessionClaim,cal.CoverageClaim,cal.VerifiedCalendar,MembershipClaim,ac.Raw,ac.Context,ac.Policy,ac.Result,ac.Link,ac.Factor,bc.RawObservation,bc.ParameterSet,bc.HistorySnapshot,bc.BasisPolicy,bc.ExecutionConstraints,bc.PinnedCalculation,bc.BoundResult]}}

def decode(v:Any)->Any:
    if isinstance(v,list):return tuple(decode(a) for a in v)
    if not isinstance(v,dict):return v
    if set(v)=={'date'}:return date.fromisoformat(v['date'])
    if set(v)=={'datetime'}:return datetime.fromisoformat(v['datetime'])
    if set(v)=={'decimal'}:return Decimal(v['decimal'])
    if set(v)=={'type','values'}:
        kind=TYPES[v['type']];allowed={f.name for f in fields(kind) if f.init}
        return kind(**{n:decode(a) for n,a in v['values'].items() if n in allowed})
    return {n:decode(a) for n,a in v.items()}

def pack(v:Any)->str:return ac.canonical(encode(v))
def unpack(v:str)->Any:return decode(json.loads(v))
def sqltime(v:date|datetime|None)->str|None:return str(ac.normalized(v)) if v is not None else None

class UniverseRepository:
    def __init__(self,url:str,*,disposable_root:Path,authority:EvidenceAuthority|None=None)->None:
        parsed=make_url(url)
        if parsed.drivername not in {'sqlite','sqlite+pysqlite'}:raise ValueError('DEVELOPMENT_SQLITE_ONLY')
        if parsed.database not in {None,'',':memory:'}:
            path=Path(str(parsed.database));root=disposable_root.resolve(strict=True)
            if not path.is_absolute() or '..' in path.parts or path.is_symlink() or not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in path.parents):raise ValueError('DISPOSABLE_DATABASE_REQUIRED')
        self.authority=authority
        self.engine=create_engine(url,poolclass=StaticPool if parsed.database in {None,'',':memory:'} else None,connect_args={'check_same_thread':False,'timeout':5})
        @event.listens_for(self.engine,'connect')
        def setup(dbapi:Any,record:Any)->None:dbapi.execute('PRAGMA foreign_keys=ON')
        existing=set(inspect(self.engine).get_table_names())
        if existing and existing!=set(M.tables):raise ValueError('OWNED_SCHEMA_REQUIRED')
        with self.engine.begin() as con:
            M.create_all(con)
            versions=con.execute(select(schema.c.version)).scalars().all()
            if versions and versions!=['od08.store/v1']:raise ValueError('SCHEMA_VERSION_UNSUPPORTED')
            if not versions:con.execute(schema.insert().values(version='od08.store/v1'))
            for table in M.tables.values():
                for op in ('UPDATE','DELETE'):
                    con.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS {table.name}_{op.lower()} BEFORE {op} ON {table.name} BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END")
    @contextmanager
    def transaction(self)->Iterator[Connection]:
        with self.engine.connect() as con:
            con.exec_driver_sql('BEGIN IMMEDIATE')
            try:yield con;con.commit()
            except BaseException:con.rollback();raise
    def close(self)->None:self.engine.dispose()
    def _put(self,con:Connection,table:Table,key:str,value:Any,**extra:Any)->None:
        body=pack(value);old=con.scalar(select(table.c.payload).where(table.c.id==key))
        if old is not None:
            if old!=body:raise ValueError('IMMUTABLE_RECORD_ID_REUSED')
            return
        con.execute(table.insert().values(id=key,payload=body,digest=hashlib.sha256(body.encode()).hexdigest(),**extra))
    def _rows(self,con:Connection,table:Table)->tuple[Any,...]:
        rows=con.execute(select(table.c.payload,table.c.digest).order_by(table.c.id)).all()
        for body,pin in rows:
            if hashlib.sha256(body.encode()).hexdigest()!=pin:raise ValueError('PERSISTED_PAYLOAD_CHANGED')
        return tuple(unpack(body) for body,pin in rows)
    def append_definition(self,value:c.UniverseDefinition)->str:
        key=ac.digest(value)
        with self.transaction() as con:self._put(con,definitions,key,value,universe=value.universe_id)
        return key
    def _definition_key(self,con:Connection,universe_id:str,key:str|None)->str:
        keys=con.execute(select(definitions.c.id).where(definitions.c.universe==universe_id)).scalars().all()
        if key is not None and key in keys:return key
        if key is None and len(keys)==1:return str(keys[0])
        raise ValueError('EXACT_DEFINITION_REQUIRED')
    def append_membership(self,value:c.MembershipRevision,definition_key:str|None=None)->None:
        with self.transaction() as con:
            key=self._definition_key(con,value.universe_id,definition_key)
            old=tuple(r for r in self._rows(con,members) if r.universe_id==value.universe_id)
            existing=next((r for r in old if r.revision_id==value.revision_id),None)
            if existing is None:validate_revisions((*old,value))
            self._put(con,members,value.revision_id,value,definition=key,universe=value.universe_id,event=value.event_id,parent=value.claim.supersedes_membership_id,valid_from=sqltime(value.claim.valid_from),valid_to=sqltime(value.claim.valid_to),known_from=sqltime(value.claim.known_from),known_to=sqltime(value.claim.known_to))
    def seed_context(self,x:c.UniverseContext,policy:c.EligibilityPolicy)->None:
        key=self.append_definition(x.definition)
        for r in sorted(x.memberships,key=lambda r:(r.revision_number,r.revision_id)):self.append_membership(r,key)
        with self.transaction() as con:
            self._put(con,policies,policy.policy_version,policy)
            for v in x.coverage:self._put(con,coverages,v.coverage_id,v,definition=key)
            for o in x.observations:self._put(con,observations,o.observation_id,o,definition=key)
    def _selected_sql(self,con:Connection,universe_id:str,day:date,cutoff:datetime)->tuple[str,...]:
        child=members.alias('successor');k=sqltime(cutoff)
        successor=exists(select(child.c.id).where(child.c.parent==members.c.id,child.c.known_from<=k))
        stmt=select(members.c.id).where(members.c.universe==universe_id,members.c.valid_from<=sqltime(day),or_(members.c.valid_to.is_(None),members.c.valid_to>sqltime(day)),or_(members.c.known_from.is_(None),members.c.known_from<=k),or_(members.c.known_to.is_(None),members.c.known_to>k),~successor).order_by(members.c.id)
        return tuple(con.execute(stmt).scalars())
    def pin_context(self,context_id:str,x:c.UniverseContext,day:date,cutoff:datetime,policy:c.EligibilityPolicy)->None:
        # Future-known inputs are not allowed to change an earlier pinned decision.
        kept=tuple(r for r in x.memberships if r.claim.known_from is None or r.claim.known_from<=cutoff)
        clean=replace(x,memberships=kept,coverage=tuple(v for v in x.coverage if v.known_from is None or v.known_from<=cutoff),observations=tuple(v for v in x.observations if v.known_from is None or v.known_from<=cutoff),authority=None,identity=replace(x.identity,authority=None),calendar=replace(x.calendar,authority=None))
        expected=get_universe_as_of(x,day,cutoff,policy,x.source_snapshot_id)
        envelope={'context':clean,'day':day,'cutoff':cutoff,'policy':policy,'expected':expected.canonical_json,'authority_digest':(x.authority or EvidenceAuthority.unconfigured()).snapshot_digest()}
        with self.transaction() as con:
            self._reconcile(con,x,day,cutoff,policy,expected)
            self._put(con,contexts,context_id,envelope,definition=ac.digest(x.definition),policy=policy.policy_version)
    def _reconcile(self,con:Connection,x:c.UniverseContext,day:date,cutoff:datetime,p:c.EligibilityPolicy,out:c.UniverseSnapshot)->None:
        if self._selected_sql(con,x.definition.universe_id,day,cutoff)!=out.selected_revision_ids:raise ValueError('INDEPENDENT_SQL_SELECTED_MEMBERS_MISMATCH')
        selected=set(out.selected_revision_ids)
        if len(out.decisions)!=len(selected) or {v.revision_id for v in out.decisions}!=selected or out.decision_digest!=ac.digest(out.decisions):raise ValueError('INDEPENDENT_DECISION_ACCOUNTING')
        allrows=self._rows(con,members);stored={r.revision_id:r for r in allrows if r.universe_id==x.definition.universe_id and (r.claim.known_from is None or r.claim.known_from<=cutoff)}
        supplied={r.revision_id:r for r in x.memberships if r.universe_id==x.definition.universe_id and (r.claim.known_from is None or r.claim.known_from<=cutoff)}
        if pack(stored)!=pack(supplied):raise ValueError('MEMBERSHIP_LEDGER_OMITTED_OR_CHANGED')
        if con.scalar(select(definitions.c.payload).where(definitions.c.id==ac.digest(x.definition)))!=pack(x.definition) or con.scalar(select(policies.c.payload).where(policies.c.id==p.policy_version))!=pack(p):raise ValueError('DEFINITION_OR_POLICY_NOT_PINNED')
        for table,items,idname in [(coverages,x.coverage,'coverage_id'),(observations,x.observations,'observation_id')]:
            for value in items:
                lower=getattr(value,'known_from')
                if lower is not None and lower>cutoff:continue
                if con.scalar(select(table.c.payload).where(table.c.id==getattr(value,idname)))!=pack(value):raise ValueError('UPSTREAM_EVIDENCE_NOT_PINNED')
        if out.financial_accepted or out.execution_accepted:raise ValueError('FINANCIAL_PROMOTION_NOT_AUTHORIZED')
        for d in out.decisions:
            row=stored[d.revision_id]
            if row.security_id is not None and d.security_id is not None and d.security_id!=row.security_id:raise ValueError('MEMBER_IDENTITY_CHANGED')
    def admit_snapshot(self,context_id:str,out:c.UniverseSnapshot)->None:
        with self.transaction() as con:
            envelope=con.scalar(select(contexts.c.payload).where(contexts.c.id==context_id))
            if envelope is None:raise ValueError('PINNED_CONTEXT_REQUIRED')
            data=unpack(envelope);x=data['context'];cutoff=data['cutoff'];day=data['day'];policy=data['policy']
            if out.canonical_json!=data['expected']:raise ValueError('SNAPSHOT_DOES_NOT_MATCH_PINNED_CONTEXT')
            self._reconcile(con,x,day,cutoff,policy,out)
            self._put(con,snapshots,out.universe_snapshot_id,out,context=context_id)
            for decision in out.decisions:
                body=pack(decision);old=con.scalar(select(decisions.c.payload).where(decisions.c.snapshot==out.universe_snapshot_id,decisions.c.revision==decision.revision_id))
                if old is None:con.execute(decisions.insert().values(snapshot=out.universe_snapshot_id,revision=decision.revision_id,payload=body,digest=ac.digest(decision)))
                elif old!=body:raise ValueError('IMMUTABLE_DECISION_CHANGED')
    def get_snapshot(self,snapshot_id:str)->str:
        with self.engine.connect() as con:
            row=con.execute(select(snapshots.c.payload,snapshots.c.digest).where(snapshots.c.id==snapshot_id)).first()
            if row is None:raise LookupError(snapshot_id)
            if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('SNAPSHOT_STORAGE_CHANGED')
            result=cast(c.UniverseSnapshot,unpack(row[0]))
            if result.universe_snapshot_id!=snapshot_id:raise ValueError('SNAPSHOT_DIGEST_CHANGED')
            return result.canonical_json
    def replay_context(self,context_id:str)->c.UniverseSnapshot:
        with self.engine.connect() as con:body=con.scalar(select(contexts.c.payload).where(contexts.c.id==context_id))
        if body is None:raise LookupError(context_id)
        data=unpack(body);x=data['context'];authority=self.authority or EvidenceAuthority.unconfigured()
        if authority.snapshot_digest()!=data['authority_digest']:raise ValueError('AUTHORITY_STATE_CHANGED')
        x=replace(x,authority=self.authority,identity=replace(x.identity,authority=self.authority),calendar=replace(x.calendar,authority=self.authority))
        result=get_universe_as_of(x,data['day'],data['cutoff'],data['policy'],x.source_snapshot_id)
        if result.canonical_json!=data['expected']:raise ValueError('REPLAY_NOT_REPRODUCIBLE')
        return result
    def query_plan(self,universe_id:str,day:date,cutoff:datetime)->tuple[str,...]:
        with self.engine.connect() as con:
            rows=con.exec_driver_sql('EXPLAIN QUERY PLAN SELECT id FROM od08_membership WHERE universe=? AND valid_from<=? AND (known_from IS NULL OR known_from<=?)',(universe_id,sqltime(day),sqltime(cutoff))).all()
        return tuple(str(r[-1]) for r in rows)
    def rollback_empty(self)->None:
        with self.transaction() as con:
            if any(con.scalar(select(func.count()).select_from(t)) for t in M.tables.values() if t is not schema):raise ValueError('NONEMPTY_ROLLBACK_REFUSED')
            M.drop_all(con)
''')
