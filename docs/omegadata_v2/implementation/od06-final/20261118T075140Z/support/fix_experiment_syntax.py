from pathlib import Path
p=Path('/home/parilrupani/omega-od06-final-20261118T075140Z/staged2/repo/scripts/od06_database_experiments.py')
v=p.read_text()
old='''        with suppress(RuntimeError):
            db.append_identity_correction(correction)
            status = "COMMITTED"
        except ValueError:'''
new='''        try:
            db.append_identity_correction(correction)
            status = "COMMITTED"
        except ValueError:'''
assert old in v;v=v.replace(old,new);compile(v,str(p),'exec');p.write_text(v)
