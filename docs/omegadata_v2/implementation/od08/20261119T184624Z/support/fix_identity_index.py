from pathlib import Path
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');D=B/'staged2/repo/src/omegadata/universe';p=D/'snapshots.py';s=p.read_text().replace('from omegadata.identity import Resolution, query_time','from omegadata.identity import Resolution, query_time, MemoryIdentityRepository, IdentifierClaim')
s=s.replace('    listing_ids = {r.listing_id for r in selected if r.listing_id is not None}','    reported_keys={(r.claim.exchange,r.claim.symbol,r.claim.series) for r in selected}\n    listing_ids = {r.listing_id for r in selected if r.listing_id is not None}',1)
a=s.index('            or any(');z=s.index('\n        )',a)
s=s[:a]+'            or (v.exchange,v.symbol,v.series) in reported_keys'+s[z:]
point=s.index('\ndef get_universe_as_of(')
helper='''
def identity_views(x:c.UniverseContext,selected:tuple[c.MembershipRevision,...])->dict[str,MemoryIdentityRepository]:
    """Index once, then reuse the existing resolver on complete listing lineages."""
    claims_by_listing:dict[str,list[IdentifierClaim]]={}
    reported:dict[tuple[str,str,str],set[str]]={}
    for claim in x.identity.claims:
        claims_by_listing.setdefault(claim.listing_id,[]).append(claim)
        reported.setdefault((claim.exchange,claim.symbol,claim.series),set()).add(claim.listing_id)
    listings={v.listing_id:v for v in x.identity.listings}
    securities={v.security_id:v for v in x.identity.securities}
    issuers={v.issuer_id:v for v in x.identity.issuers}
    cache:dict[tuple[str,...],MemoryIdentityRepository]={}
    views={}
    for member in selected:
        ids=set(reported.get((member.claim.exchange,member.claim.symbol,member.claim.series),set()))
        if member.listing_id in listings:ids.add(str(member.listing_id))
        key=tuple(sorted(ids))
        if key not in cache:
            selected_listings=tuple(listings[n] for n in key)
            security_ids=sorted({v.security_id for v in selected_listings})
            selected_securities=tuple(securities[n] for n in security_ids)
            issuer_ids=sorted({v.issuer_id for v in selected_securities if v.issuer_id is not None})
            cache[key]=MemoryIdentityRepository(tuple(issuers[n] for n in issuer_ids),selected_securities,selected_listings,tuple(sorted((v for n in key for v in claims_by_listing.get(n,[])),key=lambda v:v.claim_id)),authority=x.identity.authority)
        views[member.revision_id]=cache[key]
    return views

'''
s=s[:point]+helper+s[point:]
s=s.replace('    resolutions: dict[str, Resolution | None] = {}','    views=identity_views(x,selected)\n    resolutions: dict[str, Resolution | None] = {}').replace('        origin = x.identity.resolve_listing(', '        origin = views[r.revision_id].resolve_listing(').replace('            x.identity.resolve_listing_id(', '            views[r.revision_id].resolve_listing_id(')
p.write_text(s)
p=D/'repository.py';s=p.read_text().replace('        for table, items, idname in [\n            (coverages, x.coverage, "coverage_id"),\n            (observations, x.observations, "observation_id"),\n        ]:', '        inputs_to_check:list[tuple[Table,tuple[Any,...],str]]=[(coverages,x.coverage,"coverage_id"),(observations,x.observations,"observation_id")]\n        for table,items,idname in inputs_to_check:');p.write_text(s)
