from pathlib import Path
import json,hashlib
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py';s=p.read_text().replace("e,'reference-a')","e,'reference-a',granularity='COMPLETE_CHANGE_HISTORY',ending_member_identities=('security-a',),ending_reference='end-reference')").replace("D,K,K,K,None,K,'control-source'","D,K,K,K,K,None,K,'control-source'").replace("assert len(out.included_member_ids)==1 and all(d.status=='CONFLICTING_MEMBERSHIP' for d in out.decisions)","assert len(out.member_identities)==1 and not out.included_member_ids and all(d.status=='CONFLICTING_MEMBERSHIP' for d in out.decisions)")
p.write_text(s);(B/'fixture-correction-source.py').write_text(s);(B/'fixture-corrections.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'sha256':hashlib.sha256(s.encode()).hexdigest(),'changes':['Explicit complete nonmarket interval history, not an oversized single snapshot','Fix new availability fixture positional known_from/known_to','Duplicate conflicting members must not be included; retain one underlying member identity'],'historical_tests_changed':False},indent=2))
p=B/'staged2/repo/src/omegadata/universe/repository.py';s=p.read_text().replace('from dataclasses import fields,replace','from dataclasses import fields,replace,is_dataclass').replace('from omegadata.adjustments.repository import encode,TYPES as OLD_TYPES','from omegadata.adjustments.repository import encode as encode_scalar,TYPES as OLD_TYPES')
s=s.replace('def decode(v:Any)->Any:', '''def encode(v:Any)->Any:
    if is_dataclass(v) and not isinstance(v,type):return {'type':type(v).__name__,'values':{f.name:encode(getattr(v,f.name)) for f in fields(v)}}
    if isinstance(v,(tuple,list)):return [encode(a) for a in v]
    if isinstance(v,dict):return {n:encode(a) for n,a in v.items()}
    return encode_scalar(v)

def decode(v:Any)->Any:''')
p.write_text(s)
