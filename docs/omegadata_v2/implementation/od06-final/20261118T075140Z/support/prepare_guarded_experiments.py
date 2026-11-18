from pathlib import Path
B=Path('/home/parilrupani/omega-od06-final-20261118T075140Z');S=B/'staged2/repo'
p=S/'scripts/od06_database_experiments.py';v=p.read_text();v=v.replace('import sys','import sys\n\nfrom od06_experiment_contract import experiment_stage_accepted as experiment_stage_accepted',1);p.write_text(v)
p=B/'run.py';v=p.read_text().replace("'scripts/od06_database_experiments.py']","'scripts/od06_database_experiments.py','scripts/od06_experiment_contract.py']").replace("'test_final_semantic_refusals':2}","'test_final_semantic_refusals':2,'test_failed_experiment_stages':2}");p.write_text(v)
p=B/'fix_ruff.py';v=p.read_text().replace("'scripts/od06_database_experiments.py'","'scripts/od06_database_experiments.py','scripts/od06_experiment_contract.py'");p.write_text(v)
p=B/'format_code.py';v=p.read_text().replace("'scripts/od06_database_experiments.py'","'scripts/od06_database_experiments.py','scripts/od06_experiment_contract.py'");p.write_text(v)
p=B/'launch_shared_guarded.py';v=(B/'launch_shared.py').read_text().replace("ROOT=B/'shared-canary-database'","ROOT=B/'shared-canary-database-accepted'");p.write_text(v)
