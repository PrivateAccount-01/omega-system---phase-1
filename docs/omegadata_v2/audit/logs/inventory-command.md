# Inventory and tracked-byte preservation command

RUN; 2026-11-14 UTC; configured Python; cwd repository root; exit 0.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; @'
import ast,json,pathlib,importlib.metadata as md,subprocess,hashlib,datetime
root=pathlib.Path.cwd()
modules=[]
for p in sorted(pathlib.Path('src/omegadata').rglob('*.py')):
    t=ast.parse(p.read_text(encoding='utf-8-sig'))
    modules.append({'file':p.as_posix(),'lines':len(p.read_text(encoding='utf-8-sig').splitlines()),'definitions':[{'name':n.name,'line':n.lineno} for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]})
packages=[]
for d in md.distributions():
    packages.append({'name':d.metadata['Name'],'version':d.version,'license_expression':d.metadata.get('License-Expression'),'license':str(d.metadata.get('License',''))[:250],'license_files':d.metadata.get_all('License-File',[])})
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'modules':modules,'installed_package_metadata':sorted(packages,key=lambda r:r['name'].lower())}
pathlib.Path('docs/omegadata_v2/audit/logs/module-and-package-inventory.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
before=json.loads(pathlib.Path('docs/omegadata_v2/audit/logs/tracked-hashes-before.json').read_text(encoding='utf-8-sig'))
deltas=[]
for row in before:
    p=root/row['path']
    h=hashlib.sha256(p.read_bytes()).hexdigest().upper() if p.is_file() else None
    if h!=row['sha256']: deltas.append({'path':row['path'],'before':row['sha256'],'after':h})
pathlib.Path('docs/omegadata_v2/audit/logs/preservation-check.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tracked_files_checked':len(before),'deltas':deltas},indent=2),encoding='utf-8')
print('Modules:',len(modules),'packages:',len(packages),'tracked files checked:',len(before),'deltas:',deltas)
'@ | & '.venv/Scripts/python.exe' -B -
```

Output: 46 modules; 68 installed packages; 11,357 tracked files checked; zero deltas.

