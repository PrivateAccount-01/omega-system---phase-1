"""Read only explicit approved code/evidence identities; never Git or mixed-tree discovery."""
import hashlib,json,difflib,ast
from pathlib import Path
B=Path(__file__).resolve().parent;S=B/'staged/repo';P=Path('/home/parilrupani/omega-od08-20261119T184624Z');OLD=P/'staged2/repo'
D=P/'delivery/docs/omegadata_v2/implementation/od08/20261119T184624Z'
pins=json.loads((B/'upstream-pins.json').read_bytes())
new=['src/omegadata/universe/observation_binding.py','tests/unit/test_od08_dependencies.py']+['src/omegadata/reconciliation/'+n+'.py' for n in ('__init__','contracts','engine','metrics','tolerances','anomalies','reviews','repository','compatibility','dependencies')]+['scripts/od09_structural_experiments.py','tests/unit/test_od09_reconciliation.py']
allpins={};changes=[]
for name in list(pins)+new:
 p=S/name;st=p.lstat();assert not p.is_symlink() and st.st_nlink==1
 raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest();allpins[name]=sha
 if pins.get(name)!=sha:changes.append({'path':name,'before_sha256':pins.get(name),'after_sha256':sha,'bytes':len(raw),'stage':'A' if name.startswith('src/omegadata/universe/') or name=='tests/unit/test_od08_dependencies.py' else 'B'})
assert len(changes)==20 and len(allpins)==3852
stagea=json.loads((B/'stagea-source-inventory.json').read_bytes())
assert all(allpins[r['path']]==r['after_sha256'] for r in stagea)
assert all(hashlib.sha256((OLD/n).read_bytes()).hexdigest()==pin for n,pin in pins.items())
seal=json.loads((D/'evidence-sha256.json').read_bytes())
assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==r['sha256'] for n,r in seal['files'].items())
old_delivery=json.loads((D/'20_preservation_manifest.json').read_bytes())['combined_delivery']
base=Path('/home/parilrupani/omega-od05xr1-r1-afb1e01c18/output/repo')
before_checks=[]
for row in old_delivery:
 name=row['path'];p=base/name;before=row.get('before_sha256')
 if before is None:assert not p.exists(),name
 else:assert hashlib.sha256(p.read_bytes()).hexdigest()==before,name
 before_checks.append({'path':name,'expected_original_before_sha256':before,'verified':True})
combined={r['path']:{**r,'after_sha256':allpins[r['path']],'bytes':(S/r['path']).stat().st_size} for r in old_delivery}
for name in new:combined[name]={'path':name,'before_sha256':None,'after_sha256':allpins[name],'bytes':(S/name).stat().st_size}
assert len(combined)==51
source_dir=B/'source-delivery';source_dir.mkdir()
for name,row in combined.items():
 p=source_dir/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((S/name).read_bytes())
 body=''.join(difflib.unified_diff((base/name).read_text().splitlines(keepends=True) if row.get('before_sha256') is not None else [],(S/name).read_text().splitlines(keepends=True),fromfile='a/'+name if row.get('before_sha256') is not None else '/dev/null',tofile='b/'+name))
 row['patch_text']=body
(B/'implementation.patch').write_text(''.join(combined[n].pop('patch_text') for n in sorted(combined)))
for phase in ('A','B'):
 parts=[]
 for row in changes:
  if row['stage']!=phase:continue
  name=row['path'];before=(OLD/name).read_text().splitlines(keepends=True) if row['before_sha256'] is not None else []
  parts.extend(difflib.unified_diff(before,(S/name).read_text().splitlines(keepends=True),fromfile='a/'+name if before else '/dev/null',tofile='b/'+name))
 (B/('stage-'+phase.lower()+'.patch')).write_text(''.join(parts))
manifest={'reviewed_head':'38c6658a3587b93880fa6ab20e2caf841e7a47ac','snapshot_root':str(S),'source_manifest_digest':hashlib.sha256(json.dumps(allpins,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'snapshot_file_count':len(allpins),'before_checks':before_checks,'changes':changes,'combined_delivery':[combined[n] for n in sorted(combined)],'all_3838_upstream_snapshot_files_preserved_in_prior_workspace':True,'prior_sealed_evidence_files_preserved':len(seal['files']),'original_application_integrated':False,'original_dataset_bytes_read_hashed_copied':0,'source_policies_and_owner_roots_changed':False}
for n,v in [('preservation.json',manifest),('final-source-pins.json',allpins)]:
 with (B/n).open('x') as f:json.dump(v,f,indent=2)
files=['src/omegadata/track_b/'+n+'.py' for n in ('cross_source_validation','confidence','tolerance_policy','manual_review','review_policy','corporate_action_matching','discontinuity')]+['src/omegadata/db/models.py','src/omegadata/domain.py','scripts/build_cross_source_tolerance_report.py']
audit=[]
for name in files:
 raw=(S/name).read_bytes();tree=ast.parse(raw)
 audit.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'functions':[{'name':node.name,'line':node.lineno} for node in ast.walk(tree) if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))],'read_as_code_only':True,'executed_against_original_or_operational_data':False})
with (B/'legacy-source-audit.json').open('x') as f:json.dump(audit,f,indent=2)
print(json.dumps({'files_changed':len(changes),'combined_delivery':len(combined),'snapshot_files':len(allpins),'snapshot_digest':manifest['source_manifest_digest'],'before_hashes_verified':len(before_checks),'prior_seal_files_unchanged':len(seal['files'])}))
