"""Reporting only after STOP: reads this phase's logs, never Git or original data.

The failed finalize.py is retained as incident evidence and MUST NOT be rerun.
No additional test, original-source verification or isolation attempt occurs here.
"""
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(p):
    return json.loads(p.read_bytes())

def save(n,v):
    with (HERE/n).open('x',encoding='utf-8') as f:
        json.dump(v,f,indent=2)

def md(n,v):
    with (HERE/n).open('x',encoding='utf-8') as f:
        f.write(v+'\n')

records=[]
for p in (HERE/'logs').glob('*-command.json'):
    row=load(p)
    row['log']=p.relative_to(HERE).as_posix()
    records.append(row)
latest={}
for r in sorted(records,key=lambda r:r['end_utc']):
    latest[r['job']]=r
inventory=load(HERE/'inputs/runtime-inventory.json')
counts=dict(Counter(inventory.values()))
matrix={n:{'command_log':r['log'],'exit_code':r['exit_code'],
           'counts':r['worker_result'].get('counts',{}),
           'python':r['worker_result']['python'],'argv':r['argv'],
           'start_utc':r['start_utc'],'end_utc':r['end_utc'],
           'elapsed_seconds':r['elapsed_seconds'],'manifest_sha256':r['manifest_sha256']}
        for n,r in latest.items()}
save('11_linux312_regression_execution.json',{'jobs':matrix,'inventory_counts':counts,
     'scope':'Executed before finalization incident; not a safety clearance for that incident',
     'all_attempts_preserved':len(records)})
save('08_exact_regression_inventory.json',{'Linux312':inventory,'counts':counts,
     'source_pin_log':latest['collection']['log'].replace('-command.json','-inventory-source-pins.json'),
     'Windows314':'NOT_COLLECTED_OS_CAPABILITY_BLOCKED','Windows311':'NOT_COLLECTED_OS_CAPABILITY_BLOCKED',
     'B':{n:'BLOCKED_INPUT; actual FAIL in full diagnostic' for n,c in inventory.items() if c=='B'},
     'C':{n:'NOT_RUN_BLOCKED_REAL_DATA' for n,c in inventory.items() if c=='C'},
     'classification':'Unknown functions/cardinalities refused; 40 R1 nonfinancial nodes explicitly reviewed, including seven blocked native requirements'})
save('04_trusted_input_manifest.json',{'latest_A_manifest':latest['A']['log'].replace('-command.json','-manifest.json'),
     'manifest_sha256':latest['A']['manifest_sha256'],'receipts':latest['A']['receipts'],
     'copy_path':'Unchanged Linux stage() only, after actual namespace/seccomp/native checks',
     'Windows_copy_path':'NONE; admission always refuses before input reads/output creation',
     'source_reuse':'Previous canonical data-free receipt-pinned input trees; every file set/hash checked',
     'new_worker_extension':'worker_extension.py delegates old jobs unchanged; exact code/metadata mounts',
     'unsafe_later_finalizer':'Separate trusted-controller audit failure, NOT a worker/bootstrap fallback; see incident log'})
probes=['host_read','protected_write','traversal','junction','hardlink_reparse','child_process',
        'job_breakaway','TCP','DNS','named_pipe','inherited_handles','host_drives','retained_incident']
save('05_native_windows_denial_probes.json',{'status':'OS_CAPABILITY_BLOCKED','executed':0,
     'probes':{n:{'status':'NOT_RUN_OS_CAPABILITY_BLOCKED','native_return':None,'win32_error':None} for n in probes},
     'capability_queries_are_not_denial_proof':True,'reason':'No approved Windows VM/restricted worker'})
coverage={}
for n in ['r1','A','diagnostic']:
    p=HERE/latest[n]['log'].replace('-command.json','-coverage.json')
    coverage[n]={'totals':load(p)['totals'],'log':p.relative_to(HERE).as_posix()}
save('12_cross_platform_coverage.json',{'Linux312':coverage,'Windows314':'NOT_RUN_OS_CAPABILITY_BLOCKED',
     'Windows311':'NOT_RUN_OS_CAPABILITY_BLOCKED',
     'skips':[r for r in latest['A']['worker_result']['reports'] if r['outcome']=='skipped'],
     'skip_reconciliation':'5 unchanged Windows-specific nodes (counterparts ARCH only), plus 7 explicitly blocked new Windows-native cases; none counted as PASS',
     'financial_accuracy_contribution':0,'scope':'A/diagnostic cover omegadata; R1 covers safe adapter contracts, not absent Windows OS controls'})
before=load(HERE/'logs/original-stat-before.json')
after=load(HERE/'logs/original-stat-after.json')
old=load(HERE/'logs/prior-evidence-read-and-verified.json')
save('13_preservation_and_hashes.json',{'recorded_before_incident':True,
     'prior_evidence_read_at_preflight':{k:{'files':len(v['files']),'sealed_verified':v['sealed_verified']} for k,v in old.items()},
     'code_baseline':'inputs/code-preservation-before.json',
     'original_stat_counts':after['counts'],'RUN_to_RUN_stat_changes':after['run_stat_changes'],
     'ARCH_to_RUN_stat_changes':after['historical_stat_changes'],
     'original_payload_stat_records':len(after['rows']),
     'stat_observation_interval':[before['utc'],after['utc']],
     'raw_byte_integrity':'NOT_VERIFIED; lstat is not content integrity',
     'finalizer_completed_preservation_assertions_before_failure':'finalize.py reached subsequent git diff assertion, then terminated; no finalizer PASS',
     'post_incident_original_verification':'NOT_RUN_AFTER_STOP',
     'original_payload_reads_or_hashes_during_unscoped_Git':'UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED',
     'incident_copy_access':'No deliberate access; unrestricted Git exposure cannot be independently excluded',
     'source_policy_signing_release_application_modifications':'None performed by authored R1 changes',
     'new_source_pins_from_final_A_manifest':'See 04_trusted_input_manifest.json and linked exact manifest; no additional original-source reads after STOP'})
windows={n:load(HERE/'logs'/f'windows{n}-final2-quality.json') for n in ['314','311']}
ruff=sorted((load(p) for p in (HERE/'logs').glob('linux-static-ruff-*.json')),key=lambda r:r['end_utc'])[-1]
save('18_final_quality_and_command_reconciliation.json',{'Windows':windows,'Linux_static_Ruff':ruff,
     'initial_Windows_reports':['09_windows314_execution.json','10_windows311_execution.json'],
     'initial_failure_preservation':'Those two mandatory reports retain first Ruff C408 failures; final2 logs above are the final static results',
     'quality_corrections':['Ruff C408 dict literal in new test','Strict adapter mypy object-input annotation','Ruff I001 phase worker import order'],
     'finalization_failure':{'argv':['Linux312 python','-B','finalize.py'],
          'controller_exit_code':1,'child_command':['git','diff','--name-only'],
          'child_signal':'SIGKILL (9)','output':'CalledProcessError at finalize.py line81; no finalizer success',
          'incident':'logs/finalization-git-safety-incident.json'},
     'no_further_verification_after_incident':True})
gate={'phase':'OD05X_WINDOWS_ISOLATION_AND_CROSS_PLATFORM_CLOSURE_ONLY',
     'branch':'feature/od01-source-rights','reviewed_HEAD':'e139cd168fb026c77a27bd4b1a87f8a9b180a1ec',
     'utc':datetime.now(UTC).isoformat(),'G1':'PASS_SCOPED_TEST_RESULTS_BEFORE_INCIDENT_ONLY',
     'G2':'BLOCKED_WINDOWS314_WINDOWS311_ISOLATED_EXECUTION_ABSENT',
     'G3':'BLOCKED_WINDOWS_BOUNDARY_ABSENT_AND_NEW_TRUSTED_CONTROLLER_INCIDENT',
     'G4':'BLOCKED_REAL_DATA','safe_engineering':'BLOCKED','financial_data_verdict':'BLOCKED_REAL_DATA',
     'Windows_backend':'Safe admission/validation contracts only; native VM/worker NOT_IMPLEMENTED',
     'historical_OD05V_incident':'PENDING_HUMAN_OWNER_REVIEW',
     'new_R1_incident':'PENDING_HUMAN_OWNER_REVIEW; unscoped WSL Git may read/hash tracked payloads; extent UNKNOWN',
     'payload_access_whole_phase':'UNKNOWN_NOT_INDEPENDENTLY_EXCLUDED; no zero-read certification',
     'financial_rows_independently_verified':0,'Windows_INPUT_CHANGED':'INPUT_CHANGED_ROOT_CAUSE_UNKNOWN',
     'original_WSL_performance':'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED; not rerun',
     'Linux_A':latest['A']['worker_result']['counts'],'full_diagnostic_exit_code':latest['diagnostic']['exit_code'],
     'full_diagnostic':latest['diagnostic']['worker_result']['counts'],'C_executed':0,
     'test_evidence':'11_linux312_regression_execution.json','incident':'logs/finalization-git-safety-incident.json',
     'next_required_action':'Owner review/disposition of new R1 Git-audit incident before resuming this phase; Windows VM/worker remains separately required',
     'commit_push_merge_release_sign_OD06':'NOT_PERFORMED',
     'review_independence':'Same-agent review; no self-approval or independent human clearance claimed'}
save('16_gatekeeper.json',gate)
md('00_identity_and_branch_provenance.md','''# OD-05X-R1 identity

Entry branch `feature/od01-source-rights`, HEAD `e139cd168fb026c77a27bd4b1a87f8a9b180a1ec`, matched reviewed commit. Prior X evidence correctly names its precommit f7ebc46; it was not rewritten. Root instructions, full engineering master, OD05W prompt, requested implementation/tests and complete W/X dossiers were read; structured files inspected programmatically and358W/384X sealed hashes verified. [Read/preservation record](logs/prior-evidence-read-and-verified.json).

Two additive source/test files and this dossier were authored; no existing tracked application/test file was edited. Pre-existing environments/signing items were excluded. No commit/push/merge/release/signing/OD06. Actual UTC run identity is November17 (November18 Asia/Kolkata), not backdated. Finalization stopped for a new Git-audit safety incident; see [incident](logs/finalization-git-safety-incident.json).''')
md('01_previous_OD05X_baseline.md','''# Historical baseline versus fresh execution

Prior795+5A,795+4+5diagnostic and all other prior test totals remain ARCH. Fresh Linux results reproduce X33,V40+1,W39 and add40 explicitly classified R1 cases. Linux source, seccomp, stage and original worker remain unchanged. The new trusted-controller finalization incident is separate from passing worker tests and cannot be cleared by them. All previous evidence remains preserved.''')
md('03_windows_isolation_architecture.md','''# Capability decision and implemented safe contracts

Windows11 Home Single Language build26300; no Sandbox executable, discovered VM command, Hyper-V module/service or supplied approved VM configuration. Current token is not AppContainer; effective process is unelevated; repository volume is NTFS. HypervisorPresent true and CPU flags false do not establish firmware availability or an approved Windows guest. API exports are not configured/proven enforcement. Native elevation query error24 is retained; the independent principal query reports unelevated. Inventory is limited to management surfaces, not arbitrary private VM-directory searches. [Assessment](02_windows_capability_assessment.json), [privileges/filesystem](logs/windows-privilege-and-filesystem.json).

[Microsoft requirements](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview) exclude Home. [VM configuration](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file), [child policy](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute) and [job limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information) were evaluated. No feature, privileged package, host ACL, profile, job, network policy or reboot was configured.

The new Windows contract module implements exact reviewed-manifest comparison, Windows lexical path/device/ADS/alias refusal, identity-value comparison, destination admission, closed classification and mandatory fail-closed launch. A JSON verified claim cannot unlock it. It contains no copier/fallback. This is **not a functioning Windows isolation backend**. Native handle-safe traversal, VM/worker enforcement, child/network/pipe/inherited-handle policy and actual Windows attack/race probes remain unimplemented/unverified.

Linux reuses unchanged namespaces/read-only mounts/seccomp/native12probes/localIPC/canonical stage. A new exact-mounted phase worker extension delegates old jobs and adds safe tests/coverage/type checks. Receipt-pinned data-free source trees are validated completely; each execution destination is fresh. No financial inputs were deliberately staged. No new dependency/production CI was installed. An operator-provisioned offline Windows VM with pinned read-only code/metadata bundle, restricted worker and controlled export is an unapproved design only.

The later trusted reporting controller nevertheless issued an unscoped WSL Git audit outside that worker. It was terminated and is a new unresolved incident. Do not confuse worker containment with trusted-controller safety. No overall no-read certificate is issued.''')
red=next(r for r in records if r['job']=='r1' and r['exit_code']==1)
freeze=load(HERE/'logs/negative-first-freeze.json')
lines=[]
for n in range(1,21):
    blocked=n in {3,4,5,6,15,18,20}
    initial='OS_CAPABILITY_BLOCKED' if blocked else ('PASS_EXISTING_CONTRACT' if n==17 else 'NEW_FEATURE_ABSENT')
    final='BLOCKED_NATIVE_NOT_RUN' if blocked else ('PASS_SAFE_MODEL; WINDOWS_NATIVE_NOT_VERIFIED' if n in {9,10,11,12,13,14,16} else 'PASS_SAFE_CONTRACT_ONLY')
    lines.append(f'| WIN{n:02} | {initial} | {final} |')
md('06_negative_first_WIN01_WIN20.md',f'''# Negative-first chronology and acceptance limits

[Freeze](logs/negative-first-freeze.json): SHA `{freeze['sha256']}`, before adapter existed. [Red]({red['log']}):32failed/1passed/7skipped,exit1. Missing API is NEW_FEATURE_ABSENT. No native Windows attack was issued. WIN17 already passed an old contract. [Final]({latest['r1']['log']}):33passed/7blocked-skipped,exit0 in Linux OS boundary. Every command has exact source hashes/runtime/UTC. One equivalent C408 dict-literal style edit changed test SHA after red; [old/new pins](logs/test-source-style-correction.json) preserve that distinction. Assertions and case counts were unchanged.

| Group | Actual initial condition | Final limited result |
|---|---|---|
{chr(10).join(lines)}

WIN09/10/12/13 compare provided identity values, not actual native Windows handles/races. WIN11 tests lexical rules on Linux. WIN16 has actual Linux collection only. Windows native/provenance acceptance is blocked. The40test cases do not mean20completed Windows groups. Ruff C408, wrapper I001 and strict adapter type error were recorded before correction; final quality checks pass. [Quality lineage](18_final_quality_and_command_reconciliation.json). A later Git-audit incident blocks global engineering regardless of these test results.''')
md('07_windows_file_identity_investigation.md','''# Windows identity remains unresolved

`INPUT_CHANGED_ROOT_CAUSE_UNKNOWN`. No Windows serial/concurrent replacement, truncation, timestamp or directory-renaming investigation ran because approved isolation is absent. New FileIdentity is a comparison contract only, not a native handle reader. Fresh Linux profile records100serial reads/eightthreads, one underlying scan and known-mutation refusal; its command/events are linked in the Linux matrix. Linux results do not explain the historical Windows event. Original identity/invalidation checks were not relaxed.''')
md('14_historical_incident_status.md','''# Historical and current incident dispositions

Historical OD05V39files/6,135,515recorded bytes remain PENDING_HUMAN_OWNER_REVIEW, never self-approved. Existing ledger/evidence was preserved. No deliberate incident-copy read/hash/copy/delete occurred.

**New R1 incident:** reporting finalizer invoked `git diff --name-only` across the original working tree under WSL. Tracked market files exist; cross-platform stat differences can cause Git to read/hash payloads. Git PID503 was paused with SIGSTOP and then killed with SIGKILL; finalizer exited1. Native counters/maps/FD metadata were captured while paused. Counters are not a complete lifetime syscall trace and cannot prove zero payload access. No payload content was returned to the tools, but actual payload read/hash extent is UNKNOWN. Do not infer no access from missing output or current mappings. [Incident record](logs/finalization-git-safety-incident.json), [termination](18_final_quality_and_command_reconciliation.json).

All further tests/source verification stopped. Only existing-log reporting and evidence sealing followed. No original/retained data was deleted, rehashed or copied for investigation. Both incident dispositions require human review; no retrospective approval was generated.''')
md('15_security_risks_and_rollback.md','''# Risks and safe stop

- P1: new trusted-controller Git audit could read/hash tracked restricted payloads; extent unknown. No complete zero-read claim. Owner disposition required before resuming.
- P1: Windows VM/restricted-worker/native proofs absent. Windows test matrix remains NOT_RUN, despite successful static checks.
- P1: historical OD05V incident, signing custody, source rights/authenticity and production eligibility remain unapproved.
- P2: historical Windows INPUT_CHANGED unknown; original mounted Linux seed performance blocked at unchanged30seconds. No benchmark/identity requirement weakened.
- P2: trusted controller/runtime/public system files remain outside a hostile-host guarantee; passing worker tests did not make unscoped controller Git safe.

Failed finalize.py is forensic evidence and MUST NOT be rerun. Do not clean/reset/delete original data, retained copies or evidence. No new branch/commit/push/release occurred. Any later rollback should address only the two additive R1 code/test files after review and preserve this dossier. Source data, source policies, production assertions and Linux backend were not edited.''')
md('17_final_review.md','''# OD-05X-R1 — BLOCKED, stopped on new audit incident

Branch `feature/od01-source-rights`; reviewed/entry HEAD `e139cd168fb026c77a27bd4b1a87f8a9b180a1ec`. Added [Windows admission/contracts](../../../../../scripts/od05xr1_windows_backend.py), [40 safe/blocked contract cases](../../../../../tests/unit/test_od05xr1_windows_contract.py) and this dossier. Existing Linux/application/test files were not edited. No commit/push/merge/sign/release/OD06.

Windows isolation could not be established: Home edition, Sandbox absent, no approved VM/worker supplied. Only safe validation/refusal code was implemented; a native Windows backend is **not implemented or accepted**. Windows3.14/3.11 CLI refuses with exit2 before input reads/output creation. Static Ruff/mypy/pip/compilation pass; Windows collection/A/diagnostic/native/stress are NOT_RUN. [Final Windows/static lineage](18_final_quality_and_command_reconciliation.json), [capabilities](02_windows_capability_assessment.json).

| Fresh Linux scope | Actual result |
|---|---|
| Collection |848=A840+B4+C4|
| New R1 cases |33passed/7explicit native blocks-skips,exit0|
| Existing X / V / W |33passed /40passed+1skip /39passed,exit0|
| A engineering |828passed/12skipped,exit0|
| Full unchanged non-realdata diagnostic |828passed/4failed/12skipped/C4deselected,**exit1**|
| Ruff/mypy/pip/compilation/new strict adapter type |final exit0|

The12A skips comprise five unchanged Windows-specific nodes and seven new blocked native requirements. No skip is a pass. Full diagnostic fails exactly the four originalB cases; their assertions remain unchanged. C4remain unexecuted. Linux12native denials and positive privateIPC precede canonical stage in each worker; no bootstrap fallback exists. [Exact matrix](11_linux312_regression_execution.json), [inventory](08_exact_regression_inventory.json), [negative-first](06_negative_first_WIN01_WIN20.md), [coverage](12_cross_platform_coverage.json).

**New stop-triggering incident:** final reporting issued an unscoped WSL `git diff --name-only`, which can rehash tracked market files across OS stat differences. It was paused/terminated; finalizer exited1. No payload content appeared in tool output, but available counters are insufficient to exclude original payload reads/hashes. Whole-phase access is **UNKNOWN**, not zero. All further verification stopped. [Incident and containment](14_historical_incident_status.md). This error is not approved or erased by passing tests.

Before that incident, fresh stat observations reconciled3626present/size-matched paths:seed3596/cache30,hardlinks2760/single866; fresh-before/after and historical stat comparisons had no changes. They do not establish raw-byte integrity, permission, authenticity or financial truth. Prior361W/386X dossiers and permitted code identities passed preservation checks before the unsafe Git step. No post-incident original verification ran. Windows INPUT_CHANGED remains UNKNOWN and original WSL performance remains separately blocked.

**G1:** scoped Linux tests pass before incident. **G2:** Windows execution BLOCKED. **G3:** global containment BLOCKED, including new controller incident. **G4:** BLOCKED_REAL_DATA; independently verified financial rows0. Overall safe engineering **BLOCKED**. Historical OD05V and new R1 incidents remain pending human owner review. [Machine Gatekeeper](16_gatekeeper.json).

**One immediate next owner action:** review and disposition the new R1 Git-audit incident before resuming this phase. A separately approved isolated Windows VM/worker remains necessary for eventual engineering closure. No source-permission loop, paid service or later phase is requested.

STOP after OD-05X-R1. No commit or push.''')
save('real-data-scorecard.json',{'metadata_candidates_observed_before_incident':3626,
     'financial_rows_parsed_by_authorized_verification':0,'financial_rows_independently_verified':0,
     'uncontrolled_Git_payload_read_hash_extent':'UNKNOWN','financial_mismatches':None,
     'missing_sessions':None,'coverage':None,'raw_sha_verified':False,'zip_structure_verified':False,
     'publisher_origin_verified':False,'row_financial_verified':False,'source_rights':'UNCHANGED',
     'financial_data_verdict':'BLOCKED_REAL_DATA','synthetic_financial_contribution':0})
save('command-index.json',[{k:r[k] for k in ['job','log','argv','start_utc','end_utc','elapsed_seconds','exit_code']} for r in records])
md('DO_NOT_RERUN_FAILED_FINALIZER.md','''# Do not rerun finalize.py

This file is retained as historical incident evidence. Its unscoped WSL Git diff can trigger content reads of tracked financial archives and caused the phase to stop. It did not successfully generate a PASS report. Only close_after_incident.py reads existing phase evidence to report the stop. No test or original-file verification was resumed.''')
print(json.dumps({'gate':'BLOCKED','incident':'PENDING_HUMAN_OWNER_REVIEW','matrix':{n:matrix[n]['counts'] for n in ['r1','focused','presence','W','A','diagnostic']},'financial_rows_verified':0}))
