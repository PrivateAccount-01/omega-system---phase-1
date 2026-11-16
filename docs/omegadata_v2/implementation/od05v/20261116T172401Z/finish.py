"""Build factual evidence summaries from actual completed command records."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
def read(name):return json.loads((LOGS/name).read_text(encoding='utf-8-sig'))
def save(name,body):
    with (HERE/name).open('x',encoding='utf-8') as f:json.dump(body,f,indent=2)
def note(name,text):
    with (HERE/name).open('x',encoding='utf-8') as f:f.write(text)

matrix={};commands=[];skips={};failures={};groups={}
for label in ('win314-safe','win311-safe','linux312-safe'):
    result=read(label+'-matrix.json');focused=read(label+'-focused.json');full=read(label+'-full.json')
    matrix[label]={'commands':result,'python':full['python'],'platform':full['platform'],
        'focused':focused.get('call_counts'), 'full':full.get('call_counts'),'deselected':len(full.get('deselected',[]))}
    failures[label]=[r for r in full.get('test_reports',[]) if r['outcome']=='failed']
    skips[label]=[r['nodeid'] for r in full.get('test_reports',[]) if r['outcome']=='skipped']
    groups[label]={}
    for row in focused.get('test_reports',[]):
        match=re.search(r'test_p(\d+)',row['nodeid'])
        if not match:continue
        ids=['P'+match[1]]
        if 'test_p01_p03_real_candidates' in row['nodeid']:
            ids=[re.search(r'\[(P\d+)\]',row['nodeid'])[1]]
        for key in ids:groups[label].setdefault(key,[]).append({'nodeid':row['nodeid'],'outcome':row['outcome']})
    for key in result:
        row=read(label+'-'+key+'.json')
        commands.append({k:row.get(k) for k in ('command','cwd','start_utc','end_utc','elapsed_seconds','exit_code','output')})
save('runtime-matrix.json',matrix);save('command-index.json',commands);save('P01-P18-results.json',groups)
save('full-regression-failures.json',failures)
peers={}
for runtime, nodes in skips.items():
    for node in nodes:
        peers[runtime+':'+node]=[label for label in matrix if label!=runtime and any(r['nodeid']==node and r['outcome']=='passed' for r in read(label+'-full.json').get('test_reports',[]))]
save('skip-counterparts.json',peers)
scan=read('original-presence-scan.json')['groups'];rows=[r for g in scan.values() for r in g['rows']]
score={
    'scope':'Stat-level discovery; financial acceptance not established',
    'candidate_manifests_enumerated':len(rows),
    'payload_paths_existing':sum(g['counts']['payload_path_exists'] for g in scan.values()),
    'regular_payload_paths':sum(g['counts']['regular_file'] for g in scan.values()),
    'singly_linked_size_matching':sum(g['counts']['size_matches_manifest'] for g in scan.values()),
    'hardlink_refused':sum(g['counts']['hardlink_refused'] for g in scan.values()),
    'filesystem_length_matches_manifest_including_refused_hardlinks':sum(r['filesystem_bytes'] is not None and r['filesystem_bytes']==r['claimed_bytes'] for r in rows),
    'missing':sum(g['counts']['missing_payload'] for g in scan.values()),
    'wrong_type':sum(g['counts']['wrong_type'] for g in scan.values()),
    'same_date_observations_within_roots':sum(g['same_date_observations'] for g in scan.values()),
    'same_date_observations_across_roots':len(rows)-len({r['date'] for r in rows}),
    'duplicate_candidates_within_roots':sum(g['duplicate_candidate'] for g in scan.values()),
    'scanner_payload_bytes_read':0,
    'initial_setup_deviation':{'raw_files_read_hashed_copied':39,'raw_bytes_read_for_copy':6135515,
         'additional_disposable_regression_reads':'NOT_MEASURED','financial_acceptance_credit':0},
    'authorized_payload_hash_comparisons':None,'authorized_zip_structure_checks':None,
    'new_presence_tool_financial_rows_parsed':0,'independently_verified_financial_rows':0,
    'legacy_attempt_financial_rows_inspected':'NOT_MEASURED_NOT_CREDITED',
    'publisher_origin':'PUBLISHER_ORIGIN_UNVERIFIED','permitted_use':'UNRESOLVED',
    'real_field_mismatches':None,'real_coverage_denominator':None,'PIT':'UNKNOWN',
    'synthetic_financial_acceptance_contribution':0,
    'six_prior_official_reference_groups':['BLOCKED_REFERENCE']*6,
    'Q01_Q12':['NOT_EXECUTED_RIGHTS_PENDING']*12}
save('real-data-scorecard.json',score)
samples=[r for r in rows if r['date'] in ('2011-06-22','2020-01-02','2024-07-23')]
save('sample-and-quarantine-matrix.json',{'first_three':samples,'groups':{label:g['quarantine_groups'] for label,g in scan.items()}})
new_fail=any(any(r['outcome']=='failed' for r in read(label+'-focused.json').get('test_reports',[])) for label in matrix)
gate={'phase':'OD05V_LOCAL_ARCHIVE_DISCOVERY_AND_RIGHTS_GATED_REAL_DATA_DIAGNOSTICS_ONLY',
      'head':'0d43a43a7df2a997b394269d6a9ebf1e64a00de1','branch':'feature/od01-source-rights',
      'file_presence_verdict':'OD05V_FILE_PRESENCE_BLOCKED' if new_fail else 'OD05V_FILE_PRESENCE_TECHNICAL_PASS',
      'overall_verdict':'BLOCKED','full_regression':'See actual failures and rights-restricted inputs; no blanket PASS',
      'windows_presence_tests':'P01-P18 execute successfully with one OS symlink privilege skip per Windows runtime',
      'linux_presence_tests':'Five BUDGET failures on the mounted original seed tree; native security/canary tests reported separately',
      'payload_integrity':'PAYLOAD_INTEGRITY_NOT_RUN_RIGHTS_PENDING',
      'financial_rows':'REAL_ROW_VALIDATION_NOT_RUN_RIGHTS_PENDING',
      'publisher_origin':'PUBLISHER_ORIGIN_UNVERIFIED','financial_correctness':'FINANCIAL_CORRECTNESS_NOT_PROVEN',
      'setup_deviation':'NOT_SELF_APPROVED; requires owner review; see logs/setup-deviation.json',
      'independence':'Same-agent procedural review and separately implemented stat oracle; not human financial review',
      'production_release':'NOT_AUTHORIZED','OD06':'NOT_AUTHORIZED',
      'next_owner_action':'Provide applicable exact-file private inspection permission and nominate the bounded file/operations; separately review the recorded setup deviation. No price transcription required before permitted review.'}
save('gatekeeper.json',gate)
coverage={}
for label in matrix:
    path=LOGS/(label+'-full-coverage.json')
    if path.exists():
        data=read(path.name)
        coverage[label]={'global_percent':data['totals']['percent_covered'],
           'new_module':[{'path':p,'summary':v['summary']} for p,v in data['files'].items() if p.endswith('local_archive_presence.py')],
           'caveat':'Coverage from a failing input-restricted full run; not acceptance or a financial metric'}
save('coverage-summary.json',coverage)
identities=read('accepted-source-freeze.json');mismatches=[]
for label in matrix:
    for name in read(label+'-matrix.json'):
        actual=read(label+'-'+name+'-inputs.json')
        for path,sha in identities.items():
            if actual.get(path)!=sha:mismatches.append({'runtime':label,'command':name,'file':path})
save('runtime-source-identity.json',{'expected':identities,'mismatches':mismatches})
assert not mismatches
table='\n'.join('| '+label+' | '+str(v['focused'])+' | '+str(v['full'])+' | '+str(v['deselected'])+' |' for label,v in matrix.items())
note('04_runtime_and_gatekeeper.md',f'''# OD-05V: separate technical and financial decisions

Reviewed branch `feature/od01-source-rights`, HEAD `0d43a43a7df2a997b394269d6a9ebf1e64a00de1`.

File-presence result: **{gate['file_presence_verdict']}**. Overall result: **BLOCKED**, including the setup-scope deviation (not self-approved) and incomplete unrestricted regression acceptance. Financial correctness is not proven. No OD06 or release authorization.

| Runtime | Focused calls | Full calls | Live tests deselected |
|---|---|---|---|
{table}

[Exact commands and exits](command-index.json), [matrix](runtime-matrix.json), [full failures](full-regression-failures.json), [skip counterparts](skip-counterparts.json), [P01-P18](P01-P18-results.json), [scorecard](real-data-scorecard.json), [Gatekeeper](gatekeeper.json). Exit 1 is a failure; blocked input access is not relabeled PASS or hidden with deselection. Only four pre-existing realdata-marked tests are excluded from the full commands.

Windows 3.14/3.11 and native Ubuntu Python 3.12 code/test storage share one physical host. Original file-presence checks on Linux use the mounted original Windows archive; filesystem trap tests use disposable native Linux storage. No remote hardware/CI/power-loss guarantee. Ruff, strict mypy, pip consistency, compilation, environment and guard results are individually recorded. Pip check is not a CVE/licensing audit. Existing synthetic suites contribute zero financial acceptance.

Initial `*-final` commands were interrupted after the copy-scope discovery and are not accepted matrices. `*-safe` records use copies with no data directory, strengthened raw-read guards and unchanged legacy tests. All initial logs remain. Preservation checks stat originals without rereading payload or signing bytes; see [preservation](logs/preservation-after.json).
''')
print(json.dumps({'matrix':matrix,'scorecard':score,'gate':gate},indent=2))
