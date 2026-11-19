from pathlib import Path
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo'
p=S/'src/omegadata/identity.py';v=p.read_text();at=v.index('\n\nEVENT_TYPES =')
v=v[:at]+'''

    def resolve_listing_id(self,listing_id: str,valid_at: date,known_at: datetime,evidence_policy: Policy="STRICT") -> Resolution:
        """OD07 dependency: stable-ID lookup after observation-date symbol resolution."""
        text(listing_id);query_time(known_at)
        if type(valid_at) is not date:raise ValueError("DATE_REQUIRED")
        ends=revision_ends(self.claims)
        selected=tuple(c for c in self.claims if c.listing_id==listing_id and c.valid_from<=valid_at and (c.valid_to is None or valid_at<c.valid_to) and (c.known_from is None or c.known_from<=known_at) and (c.known_to is None or known_at<c.known_to) and (c.claim_id not in ends or known_at<ends[c.claim_id]))
        keys={(c.exchange,c.symbol,c.series) for c in selected}
        if not keys:return Resolution("UNKNOWN",reason="STABLE_LISTING_COVERAGE_UNKNOWN")
        if len(keys)!=1:return Resolution("AMBIGUOUS",tuple(sorted(c.claim_id for c in selected)),reason="OVERLAPPING_STABLE_LISTING_CLAIMS")
        exchange,symbol,series=next(iter(keys))
        result=self.resolve_listing(exchange,symbol,series,valid_at,known_at,evidence_policy)
        if result.state=="RESOLVED" and result.listing_id!=listing_id:return Resolution("CONFLICTING",result.claim_ids)
        return result
'''+v[at:];p.write_text(v)
p=S/'src/omegadata/identity_authority.py';v=p.read_text()+'''

    def snapshot_digest(self) -> str:
        """OD07 dependency: exact bundle/root/policy identity, not a permission grant."""
        from omegadata.track_a.source_rights import load_policy_register
        try:policy=load_policy_register().model_dump(mode="json")
        except ValueError:policy={"status":"SOURCE_POLICY_UNAVAILABLE"}
        try:root=hashlib.sha256(OWNER_ROOT_PATH.read_bytes()).hexdigest()
        except OSError:root="ROOT_UNAVAILABLE"
        return hashlib.sha256(canonical({"bundle_sha256":hashlib.sha256(self.__raw).hexdigest(),"bundle_pin":self.__pin,"owner_root_sha256":root,"source_policy":policy}).encode()).hexdigest()
''';p.write_text(v)
p=S/'src/omegadata/adjustments/temporal.py';v=p.read_text().replace('for day in (x.valid_at, raw.trade_date):','for day in (raw.trade_date, x.valid_at):')
old='''        result = x.identity_repository.resolve_listing(
            raw.exchange, raw.symbol, raw.series, day, x.known_at, mode
        )'''
new='''        result = (x.identity_repository.resolve_listing(raw.exchange,raw.symbol,raw.series,day,x.known_at,mode) if day==raw.trade_date else x.identity_repository.resolve_listing_id(raw.listing_id,day,x.known_at,mode))'''
assert old in v;v=v.replace(old,new)
v=v.replace('''    identity = x.identity_repository.resolve_listing(
        raw.exchange, raw.symbol, raw.series, x.valid_at, x.known_at, mode
    )''','''    identity = x.identity_repository.resolve_listing_id(raw.listing_id,x.valid_at,x.known_at,mode)''');p.write_text(v)
# Type-only widening preserves v1 scalar references and source compatibility.
p=S/'src/omegadata/adjustments/contracts.py';v=p.read_text().replace('from typing import Any','from typing import TYPE_CHECKING, Any\n\nif TYPE_CHECKING:\n    from omegadata.adjustments.bound_contracts import ReferenceObservation')
v=v.replace('reference: Reference | None','reference: Reference | ReferenceObservation | None').replace('reinvestment: Reference | None','reinvestment: Reference | ReferenceObservation | None').replace('successor_value: Reference | None','successor_value: Reference | ReferenceObservation | None');p.write_text(v)
p=S/'src/omegadata/adjustments/temporal.py';v=p.read_text().replace('from datetime import datetime','from datetime import datetime\nfrom typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    from omegadata.adjustments.bound_contracts import ReferenceObservation').replace('tuple[Reference, ...]','tuple[Reference | ReferenceObservation, ...]');p.write_text(v)
