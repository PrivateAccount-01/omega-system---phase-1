import ast,hashlib,json
from pathlib import Path
from datetime import UTC,datetime
B=Path('/home/parilrupani/omega-od08-20261119T184624Z');p=B/'staged2/repo/tests/unit/test_od08_universe.py';tree=ast.parse(p.read_text());nodes=[]
groups=[f'{prefix}{i:02}' for prefix,n in [('U',10),('I',6),('C',5),('A',5),('L',5),('E',4),('R',2),('P',6),('S',4)] for i in range(1,n+1)]
for f in tree.body:
 if not isinstance(f,ast.FunctionDef) or not f.name.startswith('test_'):continue
 values=None
 for decorator in f.decorator_list:
  if isinstance(decorator,ast.Call) and isinstance(decorator.func,ast.Attribute) and decorator.func.attr=='parametrize':values=groups if isinstance(decorator.args[1],ast.Name) else ast.literal_eval(decorator.args[1])
 if values is None:nodes.append('tests/unit/test_od08_universe.py::'+f.name)
 else:nodes.extend('tests/unit/test_od08_universe.py::'+f.name+'['+v+']' for v in values)
assert len(nodes)==92
(B/'reviewed-new-tests.json').write_text(json.dumps(sorted(nodes),indent=2));(B/'new-test-classification-review.json').write_text(json.dumps({'utc':datetime.now(UTC).isoformat(),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'nodes':nodes,'classification':'A','reason':'Reviewed anonymous structural controls, explicit literal membership expectations, nonmarket scalar calculation fixtures, protected disposable SQLite and kernel canaries only','reviewer':'same coding agent; not independent human'},indent=2))
