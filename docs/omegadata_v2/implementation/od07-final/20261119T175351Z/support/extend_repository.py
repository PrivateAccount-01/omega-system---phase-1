from pathlib import Path
B=Path('/home/parilrupani/omega-od07-final-20261119T175351Z');S=B/'staged2/repo'
p=S/'src/omegadata/adjustments/repository.py';v=p.read_text()
a=v.index('\nTYPES =')
v=v[:a]+'''
contexts=Table("od07_calculation_context",M,Column("id",String,primary_key=True),Column("payload",String,nullable=False),Column("digest",String,nullable=False))
result_context=Table("od07_result_context",M,Column("result_id",ForeignKey("od07_result.id"),primary_key=True),Column("context_id",ForeignKey("od07_calculation_context.id"),nullable=False))
LEGACY_TABLES={"od07_schema","od07_action","od07_result","od07_result_action"}
'''+v[a:]
v=v.replace('    raise ValueError("PERSISTED_TYPE_INVALID")','    raise ValueError("PERSISTED_TYPE_INVALID")')
a=v.index('\ndef encode(')
v=v[:a]+'''\nfrom omegadata.adjustments.bound_contracts import ReferenceObservation
TYPES["ReferenceObservation"]=ReferenceObservation
'''+v[a:]
v=v.replace('if tables and tables != set(M.tables):','if tables and tables not in (LEGACY_TABLES,set(M.tables)):')
a=v.index('            old = connection.scalar(select(version.c.version))');z=v.index('            for table in M.tables:',a)
v=v[:a]+'''            old=set(connection.scalars(select(version.c.version)).all())
            if old-{"od07.store/v1","od07.store/v2"}:raise ValueError("STORE_VERSION")
            if not old:connection.execute(version.insert().values(version="od07.store/v1"))
            if "od07.store/v2" not in old:connection.execute(version.insert().values(version="od07.store/v2"))
'''+v[z:]
v=v.replace('                or connection.scalar(select(results.c.id).limit(1)) is not None','                or connection.scalar(select(results.c.id).limit(1)) is not None\n                or connection.scalar(select(contexts.c.id).limit(1)) is not None')
a=v.index('    def close(self) -> None:')
v=v[:a]+'''
    def pin_context(self,pin) -> str:
        from omegadata.adjustments.admission import pin_context
        return pin_context(self,pin)

    def append_bound_result(self,result,context_id: str,*,expected_result_id: str | None=None) -> None:
        from omegadata.adjustments.admission import append_bound_result
        append_bound_result(self,result,context_id,expected_result_id)

'''+v[a:];p.write_text(v)
# Allow source-formatting mutations only in the exact current phase set.
p=B/'format_code.py';v=p.read_text();a=v.index('paths=');z=v.index('\nargv=',a)
paths=['src/omegadata/identity.py','src/omegadata/identity_authority.py','src/omegadata/adjustments/contracts.py','src/omegadata/adjustments/temporal.py','src/omegadata/adjustments/repository.py','src/omegadata/adjustments/bound_contracts.py','src/omegadata/adjustments/bound_chain.py','src/omegadata/adjustments/admission.py','tests/unit/test_od07_final.py']
v=v[:a]+'paths='+repr(paths)+v[z:]
v=v.replace("['src/omegadata/adjustments','tests/unit']", "['src/omegadata','tests/unit']")
p.write_text(v)
