"""Reconcile executed evidence; never promotes missing OS isolation or source rights."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
PRIOR=ROOT/'docs/omegadata_v2/implementation/od05v/20261116T172401Z'
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    path=HERE/name
    if path.exists():
        old=load(path)
        assert {k:v for k,v in old.items() if k!='utc'}=={k:v for k,v in value.items() if k!='utc'}, 'Existing evidence differs; refusing overwrite'
        return
    with (HERE/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
def doc(name,text):
    with (HERE/name).open('x',encoding='utf-8') as stream:stream.write(text.rstrip()+'\n')

head=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
branch=subprocess.check_output(['git','branch','--show-current']).decode().strip()
assert head=='c8e7ff974e6c4a471a002d4807f268dc5d0044b1' and branch=='feature/od01-source-rights'
before=load(LOGS/'preservation-before.json')
owned={'src/omegadata/parsers/local_archive_presence.py','scripts/audit_local_archive_presence.py','tests/unit/test_od05v_local_presence.py','tests/unit/test_od05w_engineering.py'}
unexpected=[n for n,v in before.items() if sha(ROOT/n)!=v and n not in owned]
assert not unexpected
historical=load(PRIOR/'evidence-sha256.json')['files']
historical_changed=[n for n,v in historical.items() if sha(PRIOR/n)!=v['sha256'] or (PRIOR/n).stat().st_size!=v['bytes']]
assert not historical_changed
stats=load(LOGS/'original-payload-stat-preservation.json')
changed_stats=[]
for n,v in stats.items():
    info=(ROOT/n).lstat()
    if [info.st_size,info.st_mtime_ns,info.st_nlink,info.st_ino]!=v:changed_stats.append(n)
assert not changed_stats
# Read the historical metadata record, then only lstat original paths. No key,
# market, release or database content is opened or hashed here.
oldstats=load(PRIOR/'logs/preservation-before.json')['data_artifact_db_metadata']
oldstat_changed=[]
for n,v in oldstats.items():
    path=ROOT/n
    assert path.is_relative_to(ROOT) and '..' not in Path(n).parts
    info=path.lstat()
    if [info.st_size,info.st_mtime_ns]!=v:oldstat_changed.append(n)
preservation={'utc':datetime.now(UTC).isoformat(),'before_current_run_code_and_evidence_files':len(before),'unexpected_hash_changes':unexpected,'authorized_changed_paths':sorted(n for n in owned if n in before and sha(ROOT/n)!=before[n]),'historical_OD05V_sealed_files':len(historical),'historical_seal_changes':historical_changed,'fresh_before_after_archive_stat_records':len(stats),'fresh_stat_changes':changed_stats,'ARCH_to_RUN_data_artifact_database_metadata_records':len(oldstats),'ARCH_to_RUN_metadata_changes':oldstat_changed,'raw_payload_content_hashed':False,'signing_content_read_or_hashed':False,'byte_integrity_of_original_payloads':'NOT_MEASURED'}
assert not oldstat_changed
save('preservation.json',preservation)

matrix={};failures={};identities={};skips={};coverage={};inventories={}
checks=('collection','focused','A','full-diagnostic','ruff','mypy','pip','compile','environment')
for runtime in ('win314','win311','linux312'):
    prefix=runtime+'-r3-accepted-'
    rows={name:load(LOGS/(prefix+name+'.json')) for name in checks}
    initial_concurrent=None
    if runtime=='win314':
        initial_concurrent=rows['A']
        assert initial_concurrent['exit_code']==1
        assert [r['nodeid'] for r in initial_concurrent['test_reports'] if r['outcome']=='failed']==['tests/unit/test_od05v_local_presence.py::test_p01_p03_real_candidates[P03]']
        assert 'INPUT_CHANGED' in next(r['reason'] for r in initial_concurrent['test_reports'] if r['outcome']=='failed')
        rows['A']=load(LOGS/'win314-serialized-A.json')
    inventory=load(LOGS/(runtime+'-r3-test-inventory.json'))
    inventories[runtime]=inventory
    assert len(inventory)==775 and Counter(inventory.values())=={'A':767,'B':4,'C':4}
    assert {r['nodeid'] for r in rows['collection']['collected']}==set(inventory)
    assert len(rows['A']['collected'])==767
    assert {r['nodeid'] for r in rows['A']['collected']}=={n for n,c in inventory.items() if c=='A'}
    assert all(rows[n]['exit_code']==0 for n in checks if n!='full-diagnostic')
    assert rows['full-diagnostic']['exit_code']==1
    assert rows['focused']['counts']=={'passed':39}
    failed=[r for r in rows['full-diagnostic']['test_reports'] if r['outcome']=='failed']
    assert {r['nodeid'] for r in failed}=={n for n,c in inventory.items() if c=='B'}
    assert set(rows['full-diagnostic']['deselected'])=={n for n,c in inventory.items() if c=='C'}
    failures[runtime]=failed
    skips[runtime]=[r for r in rows['A']['test_reports'] if r['outcome']=='skipped']
    identities[runtime]={n:r['source_identity'] for n,r in rows.items()}
    reference=rows['focused']['source_identity']
    assert all(r['source_identity']==reference for r in rows.values())
    assert all(sha(ROOT/n)==v for n,v in reference.items())
    assert all(r['runner_sha256']==sha(HERE/'control.py') for r in rows.values())
    matrix[runtime]={n:{'exit_code':r['exit_code'],'counts':r['counts'],'elapsed_seconds':r['elapsed_seconds'],'start_utc':r['start_utc'],'end_utc':r['end_utc'],'command_log':'logs/'+prefix+n+'.json','stdout_stderr':'logs/'+prefix+n+'.txt'} for n,r in rows.items()}
    if initial_concurrent is not None:
        matrix[runtime]['A']['command_log']='logs/win314-serialized-A.json'
        matrix[runtime]['A']['stdout_stderr']='logs/win314-serialized-A.txt'
        matrix[runtime]['A_initial_concurrent']={'exit_code':1,'counts':initial_concurrent['counts'],'command_log':'logs/win314-r3-accepted-A.json','state':'FAIL_INPUT_CHANGED_NOT_REWRITTEN'}
    for scope in ('A','full-diagnostic'):
        measured=load(LOGS/('win314-serialized-A-coverage.json' if runtime=='win314' and scope=='A' else prefix+scope+'-coverage.json'))
        coverage[runtime+'-'+scope]={'totals':measured['totals'],'presence_module':next(v['summary'] for n,v in measured['files'].items() if n.replace('\\','/').endswith('parsers/local_archive_presence.py'))}
assert identities['win314']['focused']==identities['win311']['focused']==identities['linux312']['focused']
counterparts=[]
for runtime,records in skips.items():
    for item in records:
        others=[]
        for other in matrix:
            if other==runtime:continue
            reports=load(LOGS/('win314-serialized-A.json' if other=='win314' else other+'-r3-accepted-A.json'))['test_reports']
            if any(r['nodeid']==item['nodeid'] and r['outcome']=='passed' for r in reports):others.append(other)
        counterparts.append({'runtime':runtime,'nodeid':item['nodeid'],'reason':item['reason'],'passing_counterparts':others})
assert all(r['passing_counterparts'] for r in counterparts)
save('runtime-matrix.json',matrix);save('full-diagnostic-failures.json',failures)
save('runtime-source-identity.json',identities);save('skip-counterparts.json',counterparts)
save('coverage-summary.json',coverage);save('test-dependency-inventory.json',inventories)

commands=[]
for path in sorted(LOGS.glob('*.json')):
    body=load(path)
    if isinstance(body,dict) and 'argv' in body and 'exit_code' in body:
        commands.append({'log':path.relative_to(HERE).as_posix(),**{k:body[k] for k in ('argv','cwd','start_utc','end_utc','exit_code','counts','elapsed_seconds') if k in body}})
save('command-index.json',commands)
groups={f'W{i:02d}':[] for i in range(1,25)}
for report in load(LOGS/'win314-r3-accepted-focused.json')['test_reports']:
    group='W'+re.search(r'test_w(\d\d)',report['nodeid']).group(1)
    groups[group].append(report['nodeid'])
assert all(groups.values()) and sum(map(len,groups.values()))==39
save('W01-W24-results.json',{'groups':{g:{'nodes':nodes,'software_execution':'39 focused cases pass on all three runtimes','acceptance':'BLOCKED_OS_ISOLATION' if g=='W04' else 'EXECUTED_WITH_DOCUMENTED_SCOPE'} for g,nodes in groups.items()},'precode_initial':load(LOGS/'win314-precode-red.json')['counts'],'precode_expanded_count':load(LOGS/'win314-precode-count-red.json')['counts'],'later_negative_first':{'original_boundary':'win314-original-boundary-red.json','copy_root':'win314-copy-root-red.json','external_boundary':'win314-external-boundary-red.json'},'kernel_isolation':'NOT_ESTABLISHED; Python tests alone cannot close W04'})

original=load(LOGS/'original-stat.json')
post=load(LOGS/'original-v2-post.json')
score={'phase':'OD05W','scope':'LOCAL_META; no financial acceptance','manifest_candidates':3626,'seed':3596,'cache':30,'physical_regular_paths':3626,'filesystem_sizes_matching_manifest':3626,'hardlinked':2760,'single_link':866,'missing_payload_paths':0,'new_original_market_payload_bytes_read':0,'new_original_market_hashes_verified':0,'zip_structures_verified':0,'market_observations_inspected':0,'market_observations_independently_verified':0,'real_field_mismatches':None,'missing_sessions':None,'rejected_market_records':None,'financial_coverage':None,'financial_coverage_denominator':None,'synthetic_financial_acceptance_contribution':0,'publisher_origin':'PUBLISHER_ORIGIN_UNVERIFIED','source_rights':'13 PENDING_REVIEW; 0 APPROVED; unchanged policy hash in preservation/runtime identities','financial_data_verdict':'BLOCKED_REAL_DATA','historical_OD05V_incident':'ARCHIVE_OBSERVATION; not newly authenticated or approved'}
save('07_real_data_scorecard.json',score)
gate={'phase':'OD05W_SAFE_HARNESS_REMEDIATION_AND_ARCHIVE_PRESENCE_CORRECTION_ONLY','head':head,'branch':branch,'software_engineering_tests':'PASS_WITH_RECORDED_PLATFORM_SKIPS','safe_engineering_verdict':'BLOCKED','blocking_requirement':'W04 host-level filesystem/network/subprocess containment was not established. Exact allowlists and active Python audit hooks are useful tested controls, but are not an OS sandbox and cannot certify hostile native-call/child-process containment. No safety PASS is issued.','financial_data_verdict':'BLOCKED_REAL_DATA','focused_cases_per_runtime':39,'A_suite_cases_per_runtime':767,'B_cases':'4 BLOCKED_INPUT; actual full diagnostic retains 4 FAIL','C_cases':'4 BLOCKED_REAL_DATA; not run','linux_original_mount':'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED; 30-second limit unchanged','historical_incident_review':'PENDING_HUMAN_OWNER_REVIEW; NOT_SELF_APPROVED','new_original_market_payload_access':'No prohibited read observed; zero opened/copied by the reviewed code/metadata pipelines; not a kernel-level proof','preservation':'PASS for recorded code/evidence hashes and original metadata dimensions; no payload byte-integrity claim','commit_push_merge_release_OD06':'NOT_AUTHORIZED_NOT_PERFORMED'}
gate['software_engineering_tests']='FINAL_SCOPED_RUNS_PASS_WITH_RECORDED_SKIPS_AND_PRIOR_CANARY_REFUSAL'
gate['unexplained_canary_stat_refusal']={'initial':'win314-r3-accepted-A.json P03 INPUT_CHANGED, exit 1','initial_changed_fields':'UNKNOWN_NOT_CAPTURED','reprobe':'8 fresh cache observations passed without stat changes','final_scoped_recheck':'win314-serialized-A.json; actual result retained separately','security_checks_relaxed':False}
save('gatekeeper.json',gate)

doc('00_identity_and_preservation.md',f'''# OD-05W identity and preservation

Branch `{branch}`, reviewed/current HEAD `{head}`. No commit, push, merge, release or later phase. Entry commands and exact diffs are in [entry](logs/entry.json); the phase prompt, pre-existing environments and untracked signing paths were preserved.

Allowed patch: [presence library](../../../../../src/omegadata/parsers/local_archive_presence.py), [presence CLI](../../../../../scripts/audit_local_archive_presence.py), new [safe copy contract](../../../../../scripts/od05w_safe_harness.py), new [W tests](../../../../../tests/unit/test_od05w_engineering.py), and an explicit immutable-observation/native-canary harness contract in [existing presence tests](../../../../../tests/unit/test_od05v_local_presence.py). All other application, source-policy, financial expectation, routing, database and signing/release code is unchanged.

[Preservation](preservation.json): {len(before)} current-run code/evidence identities, {len(historical)} previous sealed evidence files, 3,626 fresh before/after archive stat records, and {len(oldstats)} historical-to-current data/artifact/database metadata comparisons. No unexpected hash/stat change. Historical-to-current is ARCH compared with RUN, not a new pre-run snapshot. Raw payload/key bytes were never hashed for this check. Size/mtime/inode/link preservation is not byte-integrity certification.

Installed runtime identities and packages are in each `*-r3-accepted-environment` log. Windows 3.14.3, Windows 3.11.15 and WSL/native Ubuntu 3.12.3 share one physical host. No independent hardware claim.
''')
doc('01_incident_root_cause_and_pre_guard_containment.md','''# Incident and containment status

Historical OD05V `control.py:53` called OD05R `control.py:32` `copy_sources`. Its lines 54–58 read OD02V `logs/fixture-allowlist.json`, then opened, SHA-checked and copied every selected path before guards. Exact source and call graph remain in the immutable historical files. [Original incident ledger](../../od05v/20261116T172401Z/logs/setup-deviation.json) contains all 39 path identities and recorded byte identities: 6,135,515 bytes. These remain ARCHIVE_OBSERVATION, not newly authorized or authenticated observations. Additional old disposable regression reads are unmeasured. No retained copies or affected original payloads were opened/rehash/copied to investigate this incident.

The new [copy contract](../../../../../scripts/od05w_safe_harness.py) takes an exact classified manifest and reviewed hashes, preflights the complete list, refuses glob/unknown/data-bearing/private/link/device paths, requires an active guard callback, creates only a fresh destination, compares source descriptor identities and source/destination hashes, and has no old-helper fallback. An injected unlisted payload cannot be selected by this contract. Guard activation precedes bootstrap and production copying; [copy manifests](logs/copy-manifest.json) and [production-contract copy](logs/accepted-copy-manifest.json) retain files/bytes and guard receipt. Source classifications are reviewed code/existing regression metadata/LOCAL_META, not extension-based financial approval. A single manual sync copied the already phase-authored Python test file during the pre-code count reproduction; it copied no data, but was not through the production copy API and is not evidence of universal copy-API enforcement.

New red/green probes exposed and corrected missing protection of the original repository, unprotected external/retained-copy locations (using only new harmless sentinels), and linked/private source roots. Original-root, external read, protected write, DNS/TCP, subprocess and old security contract denials execute. Guard exceptions retain both OSError and legacy RuntimeError compatibility. The Windows null device remains an explicit non-market runtime allowance. Exact runtime/package paths and a small public OS metadata/timezone set are permitted; arbitrary external reads are denied.

**Containment is incomplete at the OS layer.** Python audit hooks/callbacks are not a kernel sandbox; native calls and separately executed hostile processes have not been proven constrained by OS filesystem/egress/exec policies. The production copy receipt explicitly says NOT_ESTABLISHED. Therefore W04 acceptance and the safe-engineering Gatekeeper remain BLOCKED. A successful isolated Linux network-namespace capability probe does not prove a complete filesystem/exec sandbox and was not applied to certify the matrix. No retrospective exception acceptance was created. Accountable owner/legal incident review remains pending; old verdicts are unchanged.

No Git history rewrite, old-copy cleanup or data publication occurred. The repository is private per its user designation; public exposure was not newly verified through a network service and is UNKNOWN, not declared absent.
''')
doc('02_hardlink_presence_correction.md','''# Versioned physical presence

[Fresh baseline](logs/original-v1-baseline.json), [independent stat reconciliation](logs/original-stat.json), [v2 result/profile](logs/original-v2-post.json), and [actual guarded CLI calls](logs/original-cli-proof.json).

| Fact | v1 | v2 |
|---|---:|---:|
| Manifest candidates | 3626 | 3626 |
| Regular paths observed | 3626 | 3626 |
| Simplified present/size-match totals | 866 | 3626 |
| Hardlinked regular paths | 2760, HARDLINK_REFUSED | 2760, PRESENT_HARDLINK_SIZE_MATCHED |
| Missing paths | 0 | 0 |
| Eligible for content inspection | never granted | 0 |

Seed: 3596 present/matched, 2760 hardlinks, 836 single links. Cache: 30 present/matched, all single links. Each v2 row separates path existence, regular type, filesystem length match, link class, discovery state, rights eligibility and four false content/authenticity/financial verification fields. A hardlink size mismatch is SIZE_MISMATCH with HARDLINKED retained. Manifest identity and original claims remain; payload bytes are not read.

Library v1 remains the default for existing callers; opt-in `version=2` supplies the new report. CLI defaults to v2 and offers `--report-version 1`. Fresh seed CLI exits: v2 `0`, v1 `2`, `--payload-integrity` `2 / POLICY_PENDING`. Exit 0 means stat discovery/length agreement only. Integrity requests never report success without content verification. No RawArchive, source-rights, registry or acquisition semantics changed.

The 2020 legacy-name claim remains ERA_CONFLICT_2020_REFERENCE_PENDING; 2011 lineage is a repository claim; the July 2024 URL is a manifest claim. No historical schema or issuer-origin certification follows from stat agreement.
''')
doc('03_linux_runtime_optimization.md','''# Measured scan costs and legitimate corpus distinction

[Windows profile](logs/win314-scan-profile.json), [native Linux profile](logs/linux312-scan-profile.json), [fresh original WSL mount](logs/linux-original-mount-v2.json).

The v2 traversal enumerates each directory once, groups ancestor checks, uses fresh final-file lstat and revalidates directory identities. Windows DirEntry.stat does not supply the identity/link fields needed here; the first implementation failed 14 focused cases and was corrected to use Windows lstat. Linux can use non-following DirEntry stat. A trusted owner-controlled snapshot is required; hostile concurrent mount/ownership changes and race immunity are not certified.

Seed Python-operation counts: Windows v1 42,557 lstat / 388 scandir, v2 25,674 / 194. Native Linux v1 42,541 lstat, v2 15,513 lstat / 194 scandir (DirEntry.stat calls are not included in the Path.lstat counter). These are intercepted Python API counts, **not kernel syscall traces**. Actual stage vectors are retained; no OS-level syscall instrumentation was obtained. New report construction adds work: this measured native seed v2 was 3.87 s versus v1 3.61 s; Windows v2 9.41 s versus v1 8.26 s under concurrent host load. Do not claim every single scan became faster.

The useful repeated-work correction is explicit immutable observation reuse: five accesses run one scan and read 3596 metadata files once, with stat-based invalidation. Measured seed totals: native 4.81 s, Windows 17.40 s, versus five uncached full scans. Returned mappings are freshly decoded. Mutation tests use no cache; an observed metadata/inode/stat change invalidates the observation.

A concurrent Windows 3.14 A run refused cache P03 with INPUT_CHANGED. The differing stat fields were not captured, so its cause remains UNKNOWN; the refusal is not rewritten as a pass. Eight fresh cache snapshot reprobes found no changes and passed. The later unchanged full diagnostic passed P03, and a serialized A run supplies an additional explicit result. No identity check, expected count or time ceiling was weakened. The original failure remains an unresolved canary-filesystem limitation, separate from original archive preservation.

Portable OD05V path/claim tests now have an explicitly labelled native disposable NON_MARKET_CANARY contract: real pinned metadata plus sparse zero files, matching link layout. Their names/assertions remain, but they no longer pretend to be five independent full original mounted scans. Fresh Windows original-host inventory independently establishes the physical counts. No canary contributes a financial observation.

Fresh mounted seed v2 still reached BUDGET after about 30.1 s during enumeration (10,591 entries, zero metadata reads); cache completed in about 2.41 s. Status LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED remains. The 30-second ceiling was not increased. Native focused/security/regression checks pass separately; this does not turn the mounted scan into PASS.
''')
doc('04_regression_dependency_inventory.md','''# Exact dependency inventory

[Runtime-specific exact inventories](test-dependency-inventory.json), [full diagnostic failures](full-diagnostic-failures.json), [skip pairing](skip-counterparts.json).

Final collection: **775 = A 767 + B 4 + C 4** on every runtime. Classification is pinned to reviewed test source hashes, exact function identities/cardinalities and exact runtime node IDs; unknown identities/cardinalities fail closed. Three old acquisition parameter IDs embed compressed existing robustness-fixture bytes that differ with interpreter/zlib. The first Windows 3.11 A attempt correctly failed node selection (exit 4); the harness now freezes each runtime's exact IDs against the same unchanged source/function contract. No test assertion or synthetic financial fixture was rewritten to normalize IDs.

| Class | Status | Dependency |
|---|---|---|
| A: 767 | Executed engineering scope | Code/nonfinancial metadata and existing software robustness fixtures; zero real-market acceptance |
| B: official reference-corpus case | BLOCKED_INPUT; diagnostic FAIL | Missing original corporate-action .bin snapshot and original ZIP path identities |
| B: three seed backfill/PIT/autoflush cases | BLOCKED_INPUT; diagnostic FAIL | Missing permitted cached symbol-to-ISIN mapping inputs |
| C: 4 realdata-marked tests | BLOCKED_REAL_DATA, NOT_RUN | External/real source authority absent |

The four B names and economic assertions are unchanged. Each unchanged full `pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing` diagnostic actually executes and fails those four cases on all runtimes. B is not counted as passed or executed in A. C alone is deselected in the full diagnostic. No -k filter, added skip/xfail marker, invented snapshot or financial mapping was used.

The first Windows diagnostic additionally failed two legacy guard tests because they expected RuntimeError; guard denial initially used PermissionError. The dual-compatible exception fixes the harness, retaining the security assertions. The stricter external-read guard then refused the known non-market Linux system MIME map; the exact public OS configuration path was added, without general /etc access. A standalone API recheck still hit an existing module-level database environment override and was correctly denied a code-root database write; it is retained as FAIL, not financial/application remediation evidence. Full-suite disposable database initialization supplies its normal A context.

All early failures and preliminary matrices remain. Some preliminary matrices overlapped a later phase-owned test sync; they are not the frozen final acceptance matrix. Only the `*-r3-accepted-*` commands supply final totals and source identities.
''')
lines=['# Genuine negative-first chronology','','The [initial freeze](logs/negative-first-freeze.json) preceded application corrections. Initial run: 27 failed / 7 passed; count-regression expansion before code: 28 failed / 7 passed. Missing harness/v2 APIs are NEW_FEATURE_ABSENT, not legacy defects. W07 independently reproduces the old physical-count discrepancy.','',
'First green attempt: 21 pass / 14 fail from Windows DirEntry identity handling; next focused run 35 pass. Later adversarial tests were written and run before their corresponding corrections: original-boundary 1 fail, private/junction root 2 fail, external-boundary 1 fail. Benign source instructions/new non-market sentinels were used, never actual incident payloads. Existing guard-contract regressions supplied additional failing executable evidence. No retrospective alteration of OD04/OD05V chronology or owner decision.', '',
'Final: 39 focused cases execute successfully on each runtime. W04 OS-level acceptance remains BLOCKED despite Python-layer test success. W05 cross-device checks are implemented; a hostile mount-owner/race or live cross-volume mutation experiment was not certified. W15 reports Python operation counts, not kernel syscall tracing. These limitations cannot be self-approved away.','', '| Group | Executed final nodes |','|---|---|']
for g,nodes in groups.items():lines.append('| '+g+' | '+'; '.join('`'+n+'`' for n in nodes)+' |')
doc('05_negative_first_W01_W24.md','\n'.join(lines))
lines=['# Fresh final runtime execution','','All exact argv/cwd/interpreter/UTC/exit/stdout/stderr: [command index](command-index.json), [final matrix](runtime-matrix.json), [source identities](runtime-source-identity.json), [coverage](coverage-summary.json). Final runner/code hashes match across all three runtime matrices. Installed package inventories are in the environment logs.','', '| Runtime | Focused | A | Unchanged full diagnostic | Ruff / mypy / pip / compile |','|---|---|---|---|---|']
for runtime in matrix:
    row=matrix[runtime];lines.append(f"| {runtime} | {row['focused']['counts']} | {row['A']['counts']} | exit 1: {row['full-diagnostic']['counts']}; C 4 deselected | all exit 0 |")
lines+=['','Every OS/privilege skip has an actually passing exact-node counterpart, recorded separately; no skip becomes a pass. WSL PATH translation and SQLite cleanup warnings are retained. Linux is native filesystem code/canary storage on the same WSL host. Pip check verifies installed dependency consistency; it is not a fresh CVE/license audit. Security/source-rights regressions are part of A. The original-mount performance failure and missing OS-isolation backend remain explicit limitations.']
doc('06_cross_platform_execution.md','\n'.join(lines))
doc('08_security_risks_rollback.md','''# Remaining risks and rollback boundary

- P0 inherited signing custody/release eligibility risks remain unwaived; no signing material was read or altered and no release was certified.
- P1 W04 OS filesystem/egress/exec containment is not established. The working Python-layer allowlist/denials are tested but insufficient for a complete safety PASS against hostile native calls or separate processes. Guard receipts are not independent OS attestations.
- P1 OD05V original payload-copy incident remains pending accountable owner/legal review. No retrospective approval was generated. Historical paths/hashes are observations, not source-use grants.
- P1 publisher permissions, authenticity, exact historical 2020/2024 applicability, original-row reference comparison, completeness and PIT availability remain unverified. Financial gate BLOCKED_REAL_DATA.
- P2 original seed scanning through the WSL Windows mount still exceeds 30 seconds. Native portability is a distinct passing engineering scope. Python API call counts are not OS syscall traces.
- P2 one concurrent Windows canary snapshot refused INPUT_CHANGED; the changed stat dimensions were not captured. Eight reprobes and the later full diagnostic passed it without changing the check. The initial failure remains; no race/volatility cause was invented and no check was relaxed.
- P2 trusted-owner directory/copy assumptions exclude hostile concurrent ownership/mount swaps; identity checks detect observed mutations but do not certify race immunity. Cross-device checks lack an independently executed hostile mount experiment.

Rollback, only if subsequently requested, is review/revert of the five phase-owned application/test patch paths while preserving all evidence. No data/schema/routing migration occurred. Do not reset/clean/delete original or retained directories. Preserve failed setup attempts, preliminary matrices, final source seals and old Gatekeeper reports. No Git lifecycle, OD06, market acquisition or publication authorization follows this phase.

Reuse decision: extend existing ExpectedMetadata/path vocabulary/read_file/source-rights contracts, retain v1, use stdlib lstat/scandir/json/hashlib and current pytest tooling. No external library, paid dependency, provider call or new financial parser was needed. A robust OS backend remains work to be completed in a configured isolated environment; no imagined third-party sandbox was credited as deployed.
''')
doc('09_gatekeeper_verdict.md','''# OD-05W Gatekeeper: BLOCKED / BLOCKED_REAL_DATA

**Safe engineering verdict: BLOCKED.** The software corrections, 24-group/39-case focused suite, scoped A regressions and quality checks execute successfully on Windows 3.14/3.11 and native Linux 3.12, with recorded counterpart skips. That does not satisfy the full contract: W04 requires host-level filesystem, network and subprocess containment. Only Python-layer controls were installed/proven. A complete OS sandbox and actual kernel file/exec-denial evidence are absent; a network-namespace capability probe is not sufficient. W05 hostile cross-volume/mount mutation and W15 kernel syscall traces are not certified. No blanket containment PASS or process-exception acceptance is issued.

**Financial verdict: BLOCKED_REAL_DATA.** 3626 regular paths/length matches and 2760 hardlinks are fresh LOCAL_META observations. Zero new raw hashes, ZIP inspections or independently compared financial rows. Source rights remain pending, publisher origin unverified and the 2020 era conflict unresolved. Existing synthetic robustness tests contribute zero financial acceptance.

All final full diagnostics exit 1 with four genuine source-input failures; B remains BLOCKED_INPUT outside A and C remains NOT_RUN. The original-mounted Linux seed scan is separately PERFORMANCE_BLOCKED. One concurrent Windows A run additionally refused a canary INPUT_CHANGED snapshot; its unknown cause and later separate reprobe/serialized results are retained. No initial failure is erased. See [machine verdict](gatekeeper.json), [matrix](runtime-matrix.json), [failures](full-diagnostic-failures.json), [scorecard](07_real_data_scorecard.json), [preservation](preservation.json), and [chronology](05_negative_first_W01_W24.md).

STOP after OD05W. Nothing was committed, pushed, merged, signed, released or advanced to OD06. Earlier historical Gatekeeper decisions are unchanged.
''')
doc('10_one_next_owner_input.md','''# One accountable owner handoff

Review this OD05W dossier together with the immutable OD05V incident ledger, then supply an accountable incident disposition and an operator-approved OS-isolated runner configuration covering the original and retained archive paths, egress and child/native execution. This is required to finish W04 safely; no publisher-permission loop is needed to continue that engineering remediation. No acceptance is inferred, and the agent has not accepted the historical deviation.

Real-file byte/row validation remains separately rights/reference blocked. This handoff does not authorize market acquisition, policy promotion, release/signing, OD06, commit, push or merge. Any subsequent action requires the applicable explicit scope.
''')
save('evidence-sha256.json',{'scope':'Phase-owned code/metadata evidence only; excludes original market/signing content','files':{p.relative_to(HERE).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}})
print(json.dumps({'matrix':{r:{k:v['counts'] for k,v in rows.items() if k in {'focused','A','full-diagnostic'}} for r,rows in matrix.items()},'preservation':preservation,'verdict':gate},indent=2))
