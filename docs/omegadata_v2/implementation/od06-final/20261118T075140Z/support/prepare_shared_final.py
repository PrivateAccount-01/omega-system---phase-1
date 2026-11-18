from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z')
v=(B/'launch_shared.py').read_text().replace("ROOT=B/'shared-canary-database'","ROOT=B/'shared-canary-database-final'")
(B/'launch_shared_final.py').write_text(v)
v=(B/'shared_experiments.py').read_text().replace("B/'shared-canary-database'","B/'shared-canary-database-final'").replace("launch_shared.py","launch_shared_final.py").replace('run_shared.py','run_shared_final.py')
(B/'shared_experiments_final.py').write_text(v)
