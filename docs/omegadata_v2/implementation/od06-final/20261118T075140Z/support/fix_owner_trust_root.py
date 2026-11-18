from pathlib import Path
import hashlib,json
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
root=S/'config/identity_authority_roots.v1.json';assert not root.exists()
raw=(json.dumps({'schema_version':'od06.owner-authority-roots/v1','roots':[]},sort_keys=True,indent=2)+'\n').encode()
root.write_bytes(raw);pin=hashlib.sha256(raw).hexdigest()
p=S/'src/omegadata/identity_authority.py';v=p.read_text()
location=v.index('\n\ndef canonical')
v=v[:location]+f'''\n\n# No owner-authenticated source-reference anchors have been supplied. This fixed,
# reviewed register is independent of a caller-supplied evidence bundle digest.
OWNER_ROOT_PATH=Path(__file__).resolve().parents[2]/'config/identity_authority_roots.v1.json'
OWNER_ROOT_SHA256='{pin}'
'''+v[location:]
method='''
    def _owner_root_approved(self,known_at: datetime) -> bool:
        try:
            if OWNER_ROOT_PATH.is_symlink():return False
            with OWNER_ROOT_PATH.open('rb') as stream:raw=stream.read(65537)
            if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=OWNER_ROOT_SHA256:return False
            body=json.loads(raw)
            if set(body)!={'schema_version','roots'} or body['schema_version']!='od06.owner-authority-roots/v1':return False
            for root in body['roots']:
                if root.get('anchor_sha256')!=self.__pin:continue
                when=datetime.fromisoformat(root['owner_recorded_at'])
                if (when.tzinfo is not None and when.utcoffset() is not None and when<=known_at
                    and root.get('owner_record_identity') and root.get('independent_reviewer_identity')
                    and not root.get('revoked') and not root.get('superseded')):return True
        except (OSError,ValueError,TypeError,KeyError):return False
        return False

'''
v=v.replace('    def verify_identity_evidence(',method+'    def verify_identity_evidence(')
needle='''        return AuthorityDecision(
            decision.allowed,'''
assert needle in v
v=v.replace(needle,'''        if not self._owner_root_approved(as_of_knowledge):
            return deny('OWNER_REVIEWED_AUTHORITY_ROOT_NOT_SUPPLIED')
        return AuthorityDecision(
            decision.allowed,''')
p.write_text(v)
p=B/'run.py';v=p.read_text().replace("'scripts/od06_experiment_contract.py']","'scripts/od06_experiment_contract.py','config/identity_authority_roots.v1.json']").replace("'test_failed_experiment_stages':2}","'test_failed_experiment_stages':2,'test_unreviewed_anchor_never_grants_financial_eligibility':1}")
v=v.replace("'class':'LOCAL_META' if n.endswith('.json') else 'CODE'", "'class':'STATIC_CONFIG' if n=='config/identity_authority_roots.v1.json' else 'LOCAL_META' if n.endswith('.json') else 'CODE'")
p.write_text(v)
