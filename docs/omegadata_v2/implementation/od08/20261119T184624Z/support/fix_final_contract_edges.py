from pathlib import Path
D=Path('/home/parilrupani/omega-od08-20261119T184624Z/staged2/repo/src/omegadata/universe')
p=D/'repository.py';s=p.read_text();s=s.replace('def encode(v: Any) -> Any:\n','def encode(v: Any) -> Any:\n    if type(v) is EvidenceAuthority:\n        return {"authority_snapshot_digest":v.snapshot_digest()}\n',1)
s=s.replace('def decode(v: Any) -> Any:', 'def decode(v: Any,authority:EvidenceAuthority|None=None) -> Any:')
s=s.replace('return tuple(decode(a) for a in v)','return tuple(decode(a,authority) for a in v)').replace('n: decode(a) for n, a in v["values"].items()', 'n: decode(a,authority) for n, a in v["values"].items()').replace('return {n: decode(a) for n, a in v.items()}','return {n: decode(a,authority) for n, a in v.items()}')
s=s.replace('    if set(v) == {"date"}:', '''    if set(v)=={"authority_snapshot_digest"}:
        candidate=authority or EvidenceAuthority.unconfigured()
        if candidate.snapshot_digest()!=v['authority_snapshot_digest']:raise ValueError('EXACT_AUTHORITY_OBJECT_REQUIRED')
        return candidate
    if set(v) == {"date"}:''')
s=s.replace('def unpack(v: str) -> Any:\n    return decode(json.loads(v))','def unpack(v: str,authority:EvidenceAuthority|None=None) -> Any:\n    return decode(json.loads(v),authority)')
s=s.replace('unpack(body) for body, pin in rows','unpack(body,self.authority) for body, pin in rows').replace('data = unpack(envelope)','data = unpack(envelope,self.authority)').replace('data = unpack(body)','data = unpack(body,self.authority)')
p.write_text(s)
p=D/'contracts.py';s=p.read_text();start=s.index('class UniverseDefinition');i=s.index('    def __post_init__(self) -> None:',start)+len('    def __post_init__(self) -> None:');s=s[:i]+"\n        if type(self.source_scope) is not tuple or type(self.exchange_scope) is not tuple:raise ValueError('IMMUTABLE_DEFINITION_SCOPE_REQUIRED')"+s[i:]
start=s.index('class UniverseCoverage');i=s.index('    def __post_init__(self) -> None:',start)+len('    def __post_init__(self) -> None:');s=s[:i]+"\n        if any(type(v) is not tuple for v in (self.expected_member_identities,self.transitions,self.ending_member_identities)):raise ValueError('IMMUTABLE_COVERAGE_REQUIRED')"+s[i:]
p.write_text(s)
