from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
v=(B/'fix_ruff.py').read_text()
v=v.replace("[R+'/bin/ruff','check','--no-cache','--fix',", "[R+'/bin/ruff','format',")
v=v.replace("'fix-ruff-'","'format-ruff-'")
(B/'format_code.py').write_text(v)
