from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');D=B/'staged2/repo/src/omegadata/universe'
p=D/'contracts.py';s=p.read_text().replace('Evidence,MemoryIdentityRepository,intervals,text,query_time','Evidence,MemoryIdentityRepository,Policy,intervals,text,query_time').replace("mode:str='STRICT'\n    calendar_version", "mode:Policy='STRICT'\n    calendar_version")
s=s.replace('for v in (self.announcement_at,self.published_at,self.ingested_at):\n            if v is not None:query_time(v)','for stamp in (self.announcement_at,self.published_at,self.ingested_at):\n            if stamp is not None:query_time(stamp)').replace('for v in (self.economic_effective_time,self.observed_at,self.published_at,self.ingested_at,self.interval_completed_at):\n            if v is not None:query_time(v)','for stamp in (self.economic_effective_time,self.observed_at,self.published_at,self.ingested_at,self.interval_completed_at):\n            if stamp is not None:query_time(stamp)').replace('for v in (self.volume,self.turnover):\n            if v is not None and (type(v) is not Decimal or not v.is_finite() or v<0)', 'for number in (self.volume,self.turnover):\n            if number is not None and (type(number) is not Decimal or not number.is_finite() or number<0)');p.write_text(s)
p=D/'snapshots.py';s=p.read_text().replace('from omegadata.identity import query_time','from omegadata.identity import query_time,Resolution').replace('    resolutions={}\n','    resolutions:dict[str,Resolution|None]={}\n').replace("    observations=tuple(o for o in x.observations if o.listing_id in listing_ids and (o.known_from is None or o.known_from<=cutoff) and p.view!='MEMBERSHIP')", "    observations=tuple(sorted((o for o in x.observations if o.listing_id in listing_ids and (o.known_from is None or o.known_from<=cutoff) and p.view!='MEMBERSHIP'),key=lambda o:o.observation_id))")
s=s.replace("included=tuple(sorted({(v.security_id if d.identity_granularity=='SECURITY' else v.listing_id) for v in rows if v.status=='INCLUDED'}- {None}))", "included=tuple(sorted({str(v.security_id if d.identity_granularity=='SECURITY' else v.listing_id) for v in rows if v.status=='INCLUDED' and (v.security_id if d.identity_granularity=='SECURITY' else v.listing_id) is not None}))")
s=s.replace("if type(steps) is not tuple or not 0<max_steps", "if type(steps) is not tuple or type(max_steps) is not int or not 0<max_steps");p.write_text(s)
p=D/'repository.py';s=p.read_text();needle="        for table,items,idname in [(coverages,x.coverage,'coverage_id'),(observations,x.observations,'observation_id')]:"
s=s.replace(needle,"""        persisted_coverage={v.coverage_id:v for v in self._rows(con,coverages) if v.universe_id==x.definition.universe_id and (v.known_from is None or v.known_from<=cutoff)}
        supplied_coverage={v.coverage_id:v for v in x.coverage if v.universe_id==x.definition.universe_id and (v.known_from is None or v.known_from<=cutoff)}
        if pack(persisted_coverage)!=pack(supplied_coverage):raise ValueError('COVERAGE_LEDGER_OMITTED_OR_CHANGED')
"""+needle)
s=s.replace("            envelope=con.scalar(select(contexts.c.payload).where(contexts.c.id==context_id))\n            if envelope is None:raise ValueError('PINNED_CONTEXT_REQUIRED')", "            envelope=self._context_payload(con,context_id)")
s=s.replace("        with self.engine.connect() as con:body=con.scalar(select(contexts.c.payload).where(contexts.c.id==context_id))\n        if body is None:raise LookupError(context_id)", "        with self.engine.connect() as con:body=self._context_payload(con,context_id)")
s=s.replace('    def admit_snapshot(self,context_id:str,out:c.UniverseSnapshot)->None:', '''    def _context_payload(self,con:Connection,context_id:str)->str:
        row=con.execute(select(contexts.c.payload,contexts.c.digest).where(contexts.c.id==context_id)).first()
        if row is None:raise ValueError('PINNED_CONTEXT_REQUIRED')
        if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('CONTEXT_STORAGE_CHANGED')
        return str(row[0])
    def admit_snapshot(self,context_id:str,out:c.UniverseSnapshot)->None:''')
p.write_text(s)
