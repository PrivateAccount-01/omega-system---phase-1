from pathlib import Path
S=Path('/home/parilrupani/omega-od06-final-20261118T075140Z/staged2/repo')
p=S/'src/omegadata/identity_authority.py';v=p.read_text().replace('import json','import json\nimport re',1)
v=v.replace("or not source_record.get('artifact_sha256') or not source_record.get('publisher_identity')", "or not isinstance(source_record.get('artifact_sha256'),str)\n                or not re.fullmatch('[a-f0-9]{64}',source_record['artifact_sha256'])\n                or not source_record.get('publisher_identity')")
v=v.replace('t=datetime.fromisoformat(raw)',"if not isinstance(raw,str):return deny('EVIDENCE_TIME_UNKNOWN')\n                t=datetime.fromisoformat(raw)")
p.write_text(v)
p=S/'src/omegadata/identity_repository.py';v=p.read_text()
start=v.index('            # Only direct successors')
end=v.index('            ls=self._rows',start)
v=v[:start]+'''            # Load only histories for candidate listings. Preserve original records
            # for authority hashing; derived temporal closure stays inside resolver.
            relevant_listing_ids={c.listing_id for c in selected}
            reduced=self._rows(conn,claims,IdentifierClaim,select(claims).where(
                claims.c.listing.in_(relevant_listing_ids)).order_by(claims.c.id)) if relevant_listing_ids else ()
'''+v[end:]
v=v.replace("Index('od06_session_lookup'", "Index('od06_claim_listing_history',claims.c.listing,claims.c.known_from)\nIndex('od06_session_lookup'")
v=v.replace("            validate_events((*old,value))", "            duplicate=next((e for e in old if e.event_id==value.event_id),None)\n            if duplicate is not None:\n                if idempotent and canonical(duplicate)==canonical(value):return\n                raise ValueError('DUPLICATE_EVENT')\n            validate_events((*old,value))")
v=v.replace("            for kind,table,rows,key in [('issuer'", "            operations: list[tuple[str,Table,Any,str]]=[('issuer'")
v=v.replace("('listing',listings,listing_rows,'listing_id')]:", "('listing',listings,listing_rows,'listing_id')]\n            for kind,table,rows,key in operations:")
p.write_text(v)
