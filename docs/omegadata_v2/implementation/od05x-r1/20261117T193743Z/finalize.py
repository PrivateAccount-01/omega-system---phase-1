"""Generate append-only R1 dossier from actual command records; no data access."""
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
OLD=ROOT/'docs/omegadata_v2/implementation/od05x/20261116T203751Z'
W=ROOT/'docs/omegadata_v2/implementation/od05w/20261116T183719Z'

def load(p):
    return json.loads(p.read_bytes())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2)

def md(name,body):
    with (HERE/name).open('x',encoding='utf-8') as f:
        f.write(body+'\n')

commands=[]
for p in (HERE/'logs').glob('*-command.json'):
    r=load(p)
    r['_log']=p.relative_to(HERE).as_posix()
    commands.append(r)
latest={}
for r in sorted(commands,key=lambda x:x['end_utc']):
    latest[r['job']]=r
required=['r1','r1type','collection','focused','presence','W','A','diagnostic','mypy','pip','compile','environment','profile']
assert set(required)<=set(latest)
for name in required:
    assert latest[name]['exit_code']==(1 if name=='diagnostic' else 0),(name,latest[name]['exit_code'])
inventory=load(HERE/'inputs/runtime-inventory.json')
counts=dict(Counter(inventory.values()))
assert counts=={'C':4,'A':840,'B':4}
worker=lambda name:latest[name]['worker_result']
assert worker('A')['counts']=={'passed':828,'skipped':12}
assert worker('diagnostic')['counts']=={'passed':828,'failed':4,'skipped':12}
B={n for n,c in inventory.items() if c=='B'}
failed={r['nodeid'] for r in worker('diagnostic')['reports'] if r['outcome']=='failed'}
assert failed==B
assert set(worker('diagnostic')['deselected'])=={n for n,c in inventory.items() if c=='C'}
red=[r for r in commands if r['job']=='r1' and r['exit_code']==1]
assert len(red)==1 and red[0]['worker_result']['counts']=={'failed':32,'skipped':7,'passed':1}
freeze=load(HERE/'logs/negative-first-freeze.json')
assert freeze['implementation_exists'] is False
source_paths=['scripts/od05xr1_windows_backend.py','tests/unit/test_od05xr1_windows_contract.py']
source_pins={n:sha(ROOT/n) for n in source_paths}
# Final A and diagnostic must carry exactly the current phase source pins.
for name in ['r1','collection','A','diagnostic']:
    manifest=load(Path(latest[name]['argv'][latest[name]['argv'].index('--manifest')+1]).resolve())
    pinmap={r['path']:r['sha256'] for r in manifest['files']}
    assert all(pinmap[n]==v for n,v in source_pins.items()),name
old=load(HERE/'logs/prior-evidence-read-and-verified.json')
prior_changes=[]
verified={}
for label,folder in [('OD05W',W),('OD05X',OLD)]:
    for n,pin in old[label]['files'].items():
        if sha(folder/n)!=pin['sha256']:
            prior_changes.append(label+'/'+n)
    verified[label]=len(old[label]['files'])
assert not prior_changes
baseline=load(HERE/'inputs/code-preservation-before.json')
old_final=load(OLD/'17_gatekeeper_final.json')['final_source_pins']
baseline.update(old_final)
assert all(sha(ROOT/n)==v for n,v in baseline.items())
before=load(HERE/'logs/original-stat-before.json')
after=load(HERE/'logs/original-stat-after.json')
assert not after['run_stat_changes'] and not after['historical_stat_changes']
assert before['rows']==after['rows']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
assert head=='e139cd168fb026c77a27bd4b1a87f8a9b180a1ec' and branch=='feature/od01-source-rights'
assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
windows={label:load(HERE/'logs'/('windows314-final2-quality.json' if label=='win314' else 'windows311-final2-quality.json')) for label in ['win314','win311']}
for r in windows.values():
    assert all(o['exit_code']==(2 if o['operation']=='refusal' else 0) for o in r['operations'])
ruff=max((load(p) for p in (HERE/'logs').glob('linux-static-ruff-*.json')),key=lambda r:r['end_utc'])
assert ruff['exit_code']==0
matrix={n:{'log':latest[n]['_log'],'exit_code':latest[n]['exit_code'],
           'counts':worker(n).get('counts',{}),'python':worker(n)['python'],
           'start_utc':latest[n]['start_utc'],'end_utc':latest[n]['end_utc'],
           'elapsed_seconds':latest[n]['elapsed_seconds'],'manifest_sha256':latest[n]['manifest_sha256']}
        for n in required}
save('11_linux312_regression_execution.json',{'jobs':matrix,'A_B_C':counts,'full_diagnostic_failed_nodes':sorted(failed),
     'native_probe_logs':[r['_log'].replace('-command.json','-native-probes.json') for r in latest.values()],
     'original_mount_scan':'NOT_RERUN; LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED retained',
     'all_attempts_retained':len(commands),'static_ruff':ruff})
save('08_exact_regression_inventory.json',{'Linux312':{'counts':counts,'node_inventory':inventory,
     'source_pin_log':latest['collection']['_log'].replace('-command.json','-inventory-source-pins.json')},
     'Windows314':'NOT_COLLECTED_OS_CAPABILITY_BLOCKED','Windows311':'NOT_COLLECTED_OS_CAPABILITY_BLOCKED',
     'B':{n:'BLOCKED_INPUT; executed and FAIL in diagnostic, never counted in A' for n in sorted(B)},
     'C':{n:'NOT_RUN_BLOCKED_REAL_DATA' for n,c in inventory.items() if c=='C'},
     'classification':'Exact old source/function cardinalities plus 40 explicitly reviewed nonfinancial R1 contract nodes; unknown test fails closed'})
manifest_path=Path(latest['A']['argv'][latest['A']['argv'].index('--manifest')+1])
save('04_trusted_input_manifest.json',{'schema_version':'od05xr1.reviewed-manifest-index/v1',
     'final_A_manifest':manifest_path.relative_to(HERE).as_posix(),'sha256':sha(manifest_path),
     'file_count':load(manifest_path)['file_count'],'entry_contract':'od05x.inputs/v1',
     'canonical_copy':'Unchanged Linux stage() after 12 native probes; no Windows copy path exists',
     'worker_extension':'worker_extension.py delegates all original jobs to unchanged od05x_base_worker_jobs.py',
     'prior_source_chunks':'Receipt-pinned prior canonical code/metadata trees only; full file set/hash revalidated; never an execution workspace fallback',
     'Windows_staged_files':0,'original_market_payload_files_copied':0,
     'source_changes':source_pins,'all_manifest_relationships':[{k:r[k] for k in ['job','_log','manifest_sha256','receipts']} for r in commands],
     'review_independence':'Same-agent engineering review; not independent human authorization of a VM or financial inputs'})
probe_names=['host_root_read','protected_write','traversal','junction_escape','hardlink_reparse',
             'CreateProcess','job_breakaway','TCP','DNS','named_pipe','inherited_handles',
             'unmapped_host_drive','retained_incident_directory']
save('05_native_windows_denial_probes.json',{'status':'OS_CAPABILITY_BLOCKED','native_probes_executed':0,
     'probes':{n:{'status':'NOT_RUN_OS_CAPABILITY_BLOCKED','native_return':None,'win32_error':None} for n in probe_names},
     'reason':'No operator-approved isolated Windows VM and restricted worker; no attack issued on unrestricted host',
     'native_API_read_only_token_queries':'02_windows_capability_assessment.json; not denial evidence',
     'Windows_VM_not_implemented':True,'Windows_no_input_refusal':{n:r['operations'][0] for n,r in windows.items()}})
coverage={}
for job in ['r1','A','diagnostic']:
    covpath=HERE/latest[job]['_log'].replace('-command.json','-coverage.json')
    cov=load(covpath)
    coverage[job]={'totals':cov['totals'],'log':covpath.relative_to(HERE).as_posix()}
save('12_cross_platform_coverage.json',{'Linux312':coverage,'Windows314':'NOT_RUN_OS_CAPABILITY_BLOCKED',
     'Windows311':'NOT_RUN_OS_CAPABILITY_BLOCKED',
     'A_skips':[r for r in worker('A')['reports'] if r['outcome']=='skipped'],
     'existing_skip_reconciliation':'5 prior Windows-specific nodes unchanged; previous counterpart evidence ARCH only, no fresh Windows counterpart claimed',
     'new_blocks':'7 explicit Windows OS-capability cases; these are blocked acceptance requirements, not passed tests',
     'financial_accuracy_contribution':0,'scope':'A/diagnostic measure omegadata; r1 measures new adapter contract only, not unimplemented Windows native controls'})
preservation={'utc':datetime.now(UTC).isoformat(),'existing_code_metadata_verified':len(baseline),
     'existing_source_pins':baseline,'changes':[], 'prior_dossiers_verified':verified,'prior_changes':prior_changes,
     'original_payload_stat_records_verified':len(after['rows']),'original_stat_counts':after['counts'],
     'RUN_to_RUN_stat_changes':after['run_stat_changes'],'ARCH_to_RUN_stat_changes':after['historical_stat_changes'],
     'original_payload_byte_integrity':'NOT_MEASURED; lstat dimensions do not certify content',
     'incident_copies_opened_hashed_copied_deleted':0,'source_policy_changes':0,
     'signing_content_opened_hashed_or_changed':False,'new_source_pins':source_pins,
     'preexisting_untracked_environment_and_signing_items':'Preserved and excluded; contents not inspected'}
save('13_preservation_and_hashes.json',preservation)
gate={'phase':'OD05X_WINDOWS_ISOLATION_AND_CROSS_PLATFORM_CLOSURE_ONLY','branch':branch,'HEAD':head,
     'utc':datetime.now(UTC).isoformat(),'G1':'PASS_SCOPED_NO_LINUX_REGRESSION',
     'G2':'BLOCKED_WINDOWS314_WINDOWS311_ISOLATED_TEST_EXECUTION_NOT_AVAILABLE',
     'G3':'BLOCKED_WINDOWS_VM_AND_WORKER_NATIVE_DENIAL_PROOF_NOT_AVAILABLE',
     'Linux_containment':'PASS_SCOPED_12_NATIVE_DENIALS_AND_POSITIVE_PRIVATE_IPC',
     'G4':'BLOCKED_REAL_DATA','safe_engineering':'BLOCKED','financial_data_verdict':'BLOCKED_REAL_DATA',
     'financial_rows_independently_verified':0,'historical_incident':'PENDING_HUMAN_OWNER_REVIEW',
     'historical_Windows_identity_cause':'INPUT_CHANGED_ROOT_CAUSE_UNKNOWN',
     'original_WSL_scan':'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED',
     'Windows_backend':'FAIL_CLOSED_ADMISSION_AND_VALIDATION_ONLY; NATIVE_VM_WORKER_NOT_IMPLEMENTED',
     'no_bootstrap_copy_bypass':'Windows never copies; Linux unchanged canonical stage exclusively',
     'full_diagnostic_exit_code':1,'B_failures':sorted(B),'C_executed':0,
     'new_contract_tests':worker('r1')['counts'],'Linux_A':worker('A')['counts'],
     'preservation':'PASS_CODE_EVIDENCE_AND_STAT_DIMENSIONS; NO_RAW_CONTENT_CLAIM',
     'changed_source_pins':source_pins,'evidence':'11_linux312_regression_execution.json',
     'next_owner_action':'Provide an operator-approved isolated Windows VM/worker environment with offline Python3.14/3.11, reviewed data-free input/evidence channels and enforceable native file/process/network restrictions; authorize only completion of this engineering phase',
     'commit_push_merge_release_sign_OD06':'NOT_PERFORMED_NOT_AUTHORIZED',
     'review_independence':'Same agent; actual kernel probes and frozen hash comparisons are separate mechanisms, not independent human approval'}
save('16_gatekeeper.json',gate)
md('00_identity_and_branch_provenance.md',f'''# OD-05X-R1 identity and scope

Branch `{branch}`; reviewed/current HEAD `{head}`. It matches. The OD-05X dossier truthfully names its precommit `f7ebc463980fd5c1c80961c3e5ecece4e337911a`; commit e139cd1 subsequently added those sealed files. Historical evidence is unchanged. No reset, merge, commit or push occurred in R1.

Read root instructions, controlling engineering master, OD05W prompt, requested source/tests and all 361 W/386 X evidence files; structured evidence inspected programmatically and all 358 W/384 final X sealed identities verified. [Read record](logs/prior-evidence-read-and-verified.json). No retained incident directory or original payload was read. Code changes are two additive source/test files plus this dossier.

UTC directory identity comes from actual host clock, November 17 UTC (November 18 in Asia/Kolkata). Commands carry their own actual UTC times; nothing is backdated. Pre-existing untracked environments/signing items remain untouched. No later phase, source-policy, financial-data, production, release or signing changes are authorized.''')
md('01_previous_OD05X_baseline.md','''# Prior baseline remains historical

The prior 33 X,40+1 V,39 W,795+5 A and795+4+5 diagnostic outcomes are ARCH until reproduced. Final R1 command logs reproduce the old focused scopes and add40 classified R1 nodes. The immutable Linux implementation is reused unchanged. [Fresh matrix](11_linux312_regression_execution.json), [preservation](13_preservation_and_hashes.json).

No old failure was erased. The 39-file/6,135,515-byte incident is NOT_SELF_APPROVED. Original WSL seed performance is still blocked at30seconds; no expensive mounted scan was repeated to obtain green evidence.''')
md('03_windows_isolation_architecture.md','''# Windows capability decision and safe additive implementation

The host reports Windows11 Home Single Language, build26300, no Sandbox executable, no discovered Hyper-V module/service or existing VM command, and a non-AppContainer current token. No approved VM configuration was supplied. HypervisorPresent is true; CPU virtualization fields are false in this environment. Those fields do not prove firmware virtualization is disabled. VM inventory is limited to installed management surfaces, not arbitrary private-directory searches. Native API exports are supported capabilities only. Current execution is unelevated. [Assessment](02_windows_capability_assessment.json), [privilege/filesystem](logs/windows-privilege-and-filesystem.json).

[Microsoft Sandbox requirements](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview) exclude Home. [Sandbox configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file), [child process policy](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute), and [job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) were evaluated. Starting a VM does not prove guest file/child/egress restrictions. No privileged software, feature enablement, reboot, ACL/profile/job or global policy modification was performed.

Implemented [Windows contract module](../../../../../scripts/od05xr1_windows_backend.py): exact separately reviewed manifest comparison; Windows lexical ADS/drive/UNC/DOS-device/trailing-alias refusal; file-ID/volume/link/reparse/type comparison; fresh-destination admission; closed test reconciliation; permanently blocked financial/incident gates; executable refusal before reading any input or creating output. This is useful offline contract implementation, **not a Windows OS isolation backend**. Native handle acquisition, safe parent-handle traversal, actual guest controls, named-pipe/handle filtering and native-denial probes remain unimplemented/unverified. A supplied JSON `verified` flag cannot unlock it. There is no Windows copy path or historical fallback.

The accepted Linux launcher/stage/seccomp and production worker files are byte-identical to reviewed HEAD. A new exact-mounted phase worker extension delegates all old jobs unchanged and runs only the new nonfinancial tests/coverage/type check. Every test workspace is freshly created after actual Linux namespace/seccomp/native proof. Input trees reused as read-only sources are prior receipt-pinned data-free canonical copies, whose complete file sets/hashes are revalidated before each coordinator invocation. No original repository/archive/incident/private root is exposed to workers. Installed runtime/public system files remain an explicit trusted boundary.

No external dependency adopted. Reuse stdlib and existing approved Linux APIs; defer a functioning Windows VM/AppContainer/restricted-token/ACL/job/mitigation combination until operator-approved resources exist. No hosted CI configuration was changed. A possible offline CI design is an operator-provisioned network-disabled Windows VM, pinned read-only data-free bundle, guest restricted worker and native proof before canonical staging, controlled evidence export, then both Windows runtimes. This is an unapproved design, not an implemented workflow.''')
table=[]
native={3,4,5,6,15,18,20}
partial={9,10,11,12,13,14,16}
for n in range(1,21):
    initial='OS_CAPABILITY_BLOCKED' if n in native else ('PASS_EXISTING_CONTRACT' if n==17 else 'NEW_FEATURE_ABSENT')
    outcome='OS_CAPABILITY_BLOCKED / NOT_RUN' if n in native else ('PASS_SAFE_CONTRACT; WINDOWS_NATIVE_ACCEPTANCE_BLOCKED' if n in partial else 'PASS_SAFE_CONTRACT')
    table.append(f'| WIN{n:02} | {initial} | {outcome} |')
md('06_negative_first_WIN01_WIN20.md',f'''# Genuine negative-first chronology

[Freeze](logs/negative-first-freeze.json) pins test SHA `{freeze['sha256']}` before the adapter existed. [Actual red]({red[0]['_log']}):32failed,1passed,7skipped,exit1; absent module failures are NEW_FEATURE_ABSENT, never reproduced kernel defects. The seven native Windows cases were not attempted on the unrestricted host. WIN17 already preserved an existing Linux contract and passed red.

[Final green]({latest['r1']['_log']}):33passed,7blocked/skipped,exit0 inside Linux3.12 bwrap/seccomp, with current test SHA `{source_pins[source_paths[1]]}`. The test source changed once after red: Ruff C408 rewrote dict keyword construction into an equivalent literal, with assertions/case counts unchanged. [Exact old/new source hashes and rationale](logs/test-source-style-correction.json). No negative-first identity is falsely claimed identical after that style edit.

Two quality failures also remain: Windows Ruff C408, Linux static wrapper import-order I001, and the dedicated strict adapter mypy argument annotation error were captured before their respective minimal corrections. Final static/type outputs pass. These are code/tooling issues, not native isolation fixes. Each per-command manifest freezes all exact source hashes.

| Group | Initial classification | Final bounded result |
|---|---|---|
{chr(10).join(table)}

WIN09/10/12/13 compare identity values only; they do not execute Windows junction, cross-volume or native handle races. WIN11 lexical tests run on Linux; real Windows alias behavior is not certified. WIN16 reconciles actual Linux nodes; Windows collection remains absent. WIN18 root cause remains UNKNOWN. WIN20 preservation is verified separately, but Windows native evidence remains missing. The40-case file covers safe contracts and explicit blocked placeholders, not20 completed Windows acceptance groups. No unsafe payload was executed to manufacture red evidence.''')
profile_path=HERE/latest['profile']['_log'].replace('-command.json','-identity-diagnostics.json')
md('07_windows_file_identity_investigation.md',f'''# Windows identity investigation remains blocked

`INPUT_CHANGED_ROOT_CAUSE_UNKNOWN`. No approved Windows host boundary exists, so Windows serial/concurrent replacement, truncation, timestamp mutation and directory-rename experiments were NOT_RUN. The historical failure did not capture changed fields. No green Linux run explains it.

The new Windows FileIdentity is a pure comparison contract, not a native handle reader or Windows diagnosis. It preserves volume/file-ID/link/type/size/mtime refusal semantics without weakening the current observer. Fresh Linux canary diagnostics remain separate: [events]({profile_path.relative_to(HERE).as_posix()}) record100serial/eightthreaded accesses, one scan and deliberate mutation refusal. No sensitive original paths/contents were instrumented.''')
md('14_historical_incident_status.md','''# Historical incident remains pending human review

OD05V:39files/6,135,515recorded bytes; `PENDING_HUMAN_OWNER_REVIEW`, not self-approved. Its ledger and historical dossiers remain byte-identical. No original/retained incident payload was opened, hashed, copied, deleted or approved. No source financial gate was promoted. Worker inputs are reviewed code/non-market metadata only. Windows refuses before input reads or staging; Linux retains canonical OS-proved staging. Preservation hashes concern permitted code/evidence and payload stat dimensions, never new raw-byte integrity.''')
md('15_security_risks_and_rollback.md','''# Risks, limitations and rollback

- P1: Windows VM/restricted-worker implementation and native file/process/network/IPC/handle proofs are absent. Required Windows A/diagnostic/identity investigations are NOT_RUN. Global safe engineering remains BLOCKED.
- P1: historical incident disposition remains pending human review; signing custody/source permissions/authenticity/release eligibility are not waived.
- P2: Windows historical INPUT_CHANGED cause remains unknown. Pure identity comparisons are not actual native handle-race evidence.
- P2: original-mounted Linux seed performance remains blocked at unchanged30seconds. Native sparse-canary and stat-presence results do not prove financial content or comparable mounted performance.
- P2: trusted host/launcher/installed interpreter/runtime/public OS files remain assumptions; hostile administrators/kernel compromise and hardware durability are not certified. New adapter coverage measures safe contracts only.

No running Windows backend is deployed. A later requested rollback may remove only the two R1 source/test additions after review while retaining this evidence; no original code, data, database, policy, CI, signing or release change needs reverting. Never clean/reset or delete retained incident directories. All failed commands and earlier evidence remain preserved. Review is same-agent, not independently authenticated owner approval.''')
md('17_final_review.md',f'''# OD-05X-R1 — BLOCKED / BLOCKED_REAL_DATA

Branch `{branch}`; HEAD `{head}`. No commit/push/merge/sign/release/OD06. Two additive code/test paths and this dossier are uncommitted; existing tracked code/test files remain unchanged.

Implemented executable fail-closed Windows admission plus exact manifest, Windows lexical path, identity-comparison, destination and classification contracts. Preserved the complete Linux backend. A functioning Windows VM/restricted-worker backend could not be established: Home edition, no Sandbox executable/approved existing VM configuration, no configured native worker policy. Native API availability and a hypervisor are not isolation proof. No privileged host changes were attempted. No Windows/bootstrap copy path was introduced.

| Fresh runtime/scope | Actual result |
|---|---|
| Linux3.12 collection |848=A840+B4+C4|
| New40R1 contract cases |33passed,7explicit OS-capability blocks/skips; exit0|
| Existing X |33passed; exit0|
| Existing V |40passed,1skip; exit0|
| Existing W |39passed; exit0|
| Linux A |828passed,12skipped; exit0|
| Unchanged full non-realdata diagnostic |828passed,4failed,12skipped,C4deselected; **exit1**|
| Linux mypy/package consistency/compilation/new strict adapter type check |exit0|
| Linux Ruff |exit0, separately scoped read-only/network namespace static tool|
| Windows3.14/3.11 |launcher exit2 before input read; static Ruff/mypy/pip/compile exit0; collection/A/diagnostic/native/stress NOT_RUN|

The12Linux skips are five unchanged Windows-specific nodes plus seven new explicitly blocked Windows-native requirements. No skip counts as a pass, no fresh Windows counterpart is invented. Exact classifications/source pins, outputs, times, coverage and B failure reasons are in [matrix](11_linux312_regression_execution.json), [inventory](08_exact_regression_inventory.json), [coverage](12_cross_platform_coverage.json). The diagnostic fails exactly the original fourB nodes; their assertions remain unchanged. All fourC remain unexecuted. Red baseline32failed/1passed/7blocked predates implementation; [group chronology](06_negative_first_WIN01_WIN20.md) explains safe contracts versus blocked native acceptance. Early Ruff/type failures are preserved.

Every Linux worker re-proved12native denials and positive local IPC before canonical staging. New source uses no old bootstrap helper. The same-agent review and independent kernel/hash mechanisms do not constitute independent human approval. Windows INPUT_CHANGED remains UNKNOWN; required Windows mutation experiments are blocked.

Fresh stat-only count:3626present/size-matched,seed3596/cache30,hardlinks2760/single866,0missing. Historical-to-current and fresh before/after stat comparisons show no changes; no raw content identity is claimed. Original WSL mounted performance remains separately blocked, not rerun. Existing source identities and all361W/386X evidence files remain unchanged. See [preservation](13_preservation_and_hashes.json). Zero original market payload bytes were opened/hashed/copied; zero financial rows independently verified. Existing robustness fixtures contribute zero financial acceptance. Historical39-file incident remains pending human owner review.

**G1 Linux: PASS within scoped engineering contract. G2 Windows: BLOCKED. G3 cross-platform containment: BLOCKED (Linux native proof reproduced; Windows absent). G4 financial: BLOCKED_REAL_DATA. Overall safe engineering: BLOCKED.** [Machine Gatekeeper](16_gatekeeper.json). This is a partial executable contract delivery with honest capability blocking, not completed Windows isolation.

**One next owner action:** provide an operator-approved isolated Windows VM/worker environment with offline Python3.14/3.11, reviewed data-free input/evidence channels and enforceable native file/process/network controls, then authorize completion of this same engineering phase. No publisher-permission loop or paid service is requested. Historical incident disposition remains an independent pending requirement, not approved by that environment action.

STOP after OD-05X-R1. No OD06, commit or push.''')
save('real-data-scorecard.json',{'metadata_candidates':3626,'financial_observations_inspected':0,
     'financial_observations_independently_verified':0,'financial_mismatches':None,'missing_sessions':None,
     'rejected_financial_records':None,'financial_coverage':None,'source_rights':'UNCHANGED_PENDING_REVIEW',
     'publisher_origin_verified':False,'raw_sha_verified':False,'zip_structure_verified':False,
     'row_financial_verified':False,'financial_data_verdict':'BLOCKED_REAL_DATA','synthetic_financial_contribution':0})
save('command-index.json',[{k:r[k] for k in ['job','_log','argv','start_utc','end_utc','elapsed_seconds','exit_code']} for r in commands])
print(json.dumps({'gate':gate,'coverage':coverage,'prior_dossiers_verified':verified}))
