"""Exact fresh commands on one authorized installed runtime; no data setup."""
import json
import hashlib
import os
import subprocess
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
label,root=sys.argv[1:3]
contract=json.loads((Path(root)/'od05w_inputs/test-contract.json').read_text())
commands=[
 ('collection','pytest',['--collect-only','-q']),
 ('focused','pytest',['-q','tests/unit/test_od05w_engineering.py']),
 ('A','pytest',['@A','-q','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
 ('full-diagnostic','pytest',['-q','-m','not realdata','--cov=omegadata','--cov-branch','--cov-report=term-missing']),
 ('ruff','ruff',['check','--no-cache','src/omegadata','scripts','tests']),
 ('mypy','mypy',['src/omegadata']),
 ('pip','pip',['check']),
 ('compile','compileall',['-q','src/omegadata','scripts']),
 ('environment','environment',[]),
]
results=[]
for name,module,args in commands:
    argv=[sys.executable,'-B',str(here/'control.py'),'run',label+'-accepted-'+name,root,module,*args]
    r=subprocess.run(argv)
    results.append({'argv':argv,'exit_code':r.returncode})
    if name=='collection':
        assert r.returncode==0
        collected=json.loads((here/'logs'/(label+'-accepted-collection.json')).read_text())['collected']
        actual={};inventory={}
        for row in collected:
            base=row['nodeid'].split('[',1)[0]
            if base not in contract['functions']:raise RuntimeError('UNCLASSIFIED_TEST')
            actual[base]=actual.get(base,0)+1
            category=contract['functions'][base]['class']
            assert (category=='C')==row['realdata']
            inventory[row['nodeid']]=category
        assert actual=={n:v['count'] for n,v in contract['functions'].items()}
        assert all(hashlib.sha256((Path(root)/n).read_bytes()).hexdigest()==v for n,v in contract['source_hashes'].items())
        # Exact runtime node IDs are frozen, including version-specific zlib byte
        # repr IDs. The economic assertions and original test files stay intact.
        name=label+'-test-inventory.json'
        with (here/'logs'/name).open('x') as stream:json.dump(inventory,stream,indent=2)
        (Path(root)/'od05w_inputs'/name).write_text(json.dumps(inventory))
        os.environ['OD05W_INVENTORY']=name
print(json.dumps(results,indent=2))
