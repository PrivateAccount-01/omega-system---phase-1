"""Evidence-backed, non-approving OD05X reconciliation. No original byte reads."""
import hashlib
import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
HERE = Path(__file__).parent
LOGS = HERE / 'logs'
OLD = ROOT / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'
HEAD = 'f7ebc463980fd5c1c80961c3e5ecece4e337911a'
PHASE_FILES = ['scripts/od05x_isolated_runner.py', 'scripts/od05x_worker_jobs.py',
               'tests/unit/test_od05x_isolation.py', 'tests/unit/test_od05x_native_extensions.py']

def load(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value):
    with (HERE / name).open('x', encoding='utf-8') as f: json.dump(value, f, indent=2)
def doc(name, value):
    with (HERE / name).open('x', encoding='utf-8') as f: f.write(value.strip() + '\n')
def git(*args): return subprocess.check_output(['git', *args], text=True).strip()

assert git('rev-parse', 'HEAD') == HEAD
assert git('branch', '--show-current') == 'feature/od01-source-rights'
assert not git('diff', '--name-only') and not git('diff', '--cached', '--name-only')
current = {n: sha(ROOT / n) for n in PHASE_FILES}
commands = [load(p) | {'command_log': p.relative_to(HERE).as_posix()}
            for p in LOGS.glob('*-command.json')]

def accepted(job):
    candidates = []
    for row in commands:
        if row.get('job') != job or not row.get('worker_result'):
            continue
        argv = row['argv']
        manifest = Path(argv[argv.index('--manifest') + 1])
        # Linux paths are translated only to read this phase's own manifest.
        name = manifest.name
        pins = {r['path']: r['sha256'] for r in load(LOGS / name)['files']}
        if all(pins.get(n) == h for n, h in current.items()): candidates.append(row)
    assert candidates, 'NO_FINAL_SOURCE_RESULT_' + job
    return max(candidates, key=lambda r: r['start_utc'])

jobs = {n: accepted(n) for n in ('collection', 'focused', 'presence', 'W', 'A',
                                'diagnostic', 'mypy', 'pip', 'compile', 'environment', 'profile')}
for name, row in jobs.items():
    assert row['worker_result']['exit_code'] == (1 if name == 'diagnostic' else 0), name
inventory = load(HERE / 'inputs/runtime-inventory.json')
assert Counter(inventory.values()) == {'A': 800, 'B': 4, 'C': 4}
assert set(inventory) == {r['nodeid'] for r in jobs['collection']['worker_result']['collected']}
assert jobs['A']['worker_result']['counts'] == {'passed': 795, 'skipped': 5}
assert jobs['diagnostic']['worker_result']['counts'] == {'passed': 795, 'failed': 4, 'skipped': 5}
assert jobs['focused']['worker_result']['counts'] == {'passed': 33}
assert {r['nodeid'] for r in jobs['A']['worker_result']['collected']} == {n for n, c in inventory.items() if c == 'A'}
b = {n for n, c in inventory.items() if c == 'B'}
c = {n for n, kind in inventory.items() if kind == 'C'}
failed = [r for r in jobs['diagnostic']['worker_result']['reports'] if r['outcome'] == 'failed']
assert {r['nodeid'] for r in failed} == b
assert set(jobs['diagnostic']['worker_result']['deselected']) == c
win = load(LOGS / 'final-windows-quality.json')
assert all(r['source_pins'] == current for r in win)
assert all(r['exit_code'] == (2 if r['kind'] == 'refused-runner' else 0) for r in win)
assert load(LOGS / 'linux-static-ruff-final.json')['exit_code'] == 0

before = load(LOGS / 'read-and-preservation-before.json')
changed_code = [n for n, h in before['code_and_metadata_before'].items() if sha(ROOT / n) != h]
changed_old = [n for n, r in before['entire_prior_dossier'].items() if sha(OLD / n) != r['sha256']]
stats = load(HERE / 'inputs/original-independent-stat.json')
stat_changes = []
for n, row in stats['rows'].items():
    s = (ROOT / n).lstat()
    if [s.st_size, s.st_mtime_ns, s.st_ino, s.st_nlink] != [row[k] for k in ('size', 'mtime_ns', 'ino', 'nlink')]:
        stat_changes.append(n)
arch_path = ROOT / 'docs/omegadata_v2/implementation/od05v/20261116T172401Z/logs/preservation-before.json'
arch = load(arch_path)['data_artifact_db_metadata']
arch_changed_count = 0
for n, expected in arch.items():
    s = (ROOT / n).lstat()
    arch_changed_count += [s.st_size, s.st_mtime_ns] != expected
assert not changed_code and not changed_old and not stat_changes and not arch_changed_count
preservation = {'utc': datetime.now(UTC).isoformat(), 'current_HEAD': HEAD, 'new_source_pins': current,
    'existing_code_metadata_files_verified': len(before['code_and_metadata_before']), 'existing_code_changes': changed_code,
    'prior_dossier_files_verified': len(before['entire_prior_dossier']), 'prior_dossier_changes': changed_old,
    'prior_sealed_files_verified': before['sealed_files_verified'], 'fresh_before_after_original_stat_records': len(stats['rows']),
    'fresh_stat_changes': stat_changes, 'ARCH_to_RUN_data_artifact_db_metadata_records': len(arch),
    'ARCH_to_RUN_metadata_changed_count': arch_changed_count, 'original_payload_byte_integrity': 'NOT_MEASURED',
    'original_payload_or_signing_content_read_or_hashed': False,
    'pre_existing_environment_and_private_untracked_items': 'PRESERVED_EXCLUDED; private paths redacted'}
save('11_preservation_and_source_hashes.json', preservation)

matrix = {'linux312': {name: {'exit_code': row['worker_result']['exit_code'],
    'counts': row['worker_result']['counts'], 'command_log': row['command_log'],
    'start_utc': row['start_utc'], 'elapsed_seconds': row['elapsed_seconds']}
    for name, row in jobs.items()},
    'Windows_static_checks': win, 'Windows_pytest': {'win314': 'NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED',
                                                  'win311': 'NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED'},
    'linux_ruff': load(LOGS / 'linux-static-ruff-final.json'),
    'static_tool_caveat': 'Windows static tools and Linux Rust Ruff are separate static jobs; they are not full child-execution containment certifications'}
save('10_cross_platform_runtime_matrix.json', matrix)
save('09_test_dependency_reconciliation.json', {'collection': 808, 'counts': dict(Counter(inventory.values())),
     'nodes': inventory, 'source_contract': 'inputs/review-v2.json', 'original_B_unchanged': sorted(b),
     'C_NOT_RUN': sorted(c), 'diagnostic_failures': failed,
     'skip_records': [r for r in jobs['A']['worker_result']['reports'] if r['outcome'] == 'skipped'],
     'fresh_Windows_skip_counterparts': 'BLOCKED; archived OD05W counterparts retained, not fresh proof',
     'archived_counterpart_reference': '../../od05w/20261116T183719Z/skip-counterparts.json'})

profile_prefix = Path(jobs['profile']['command_log']).name.removesuffix('-command.json')
native_profile = load(LOGS / (profile_prefix + '-native-profile.json'))
identity_probe = load(LOGS / (profile_prefix + '-identity-diagnostics.json'))
assert identity_probe['scan_count'] == 1 and identity_probe['events'][-1]['reason'] == 'INPUT_CHANGED'
assert identity_probe['events'][-1]['changes']
save('08_linux_performance_profile.json', {'native_canary': native_profile,
     'Windows_original_host': load(LOGS / 'original-windows-profile.json'),
     'WSL_original_mount': load(LOGS / 'linux-original-mount-profile.json'),
     'ScanLimits_max_seconds': 30, 'corpora_are_distinct': True,
     'metadata_reuse': '3 OS-proved bounded canonical staging batches; pin-verified native source only; fresh destination per job'})
capabilities = {'Windows': load(LOGS / 'windows-capabilities.json'),
     'API_exports_and_packages': load(LOGS / 'host-api-capabilities.json'),
     'Linux_proof': jobs['profile']['worker_result']['boundary'],
     'Windows_required_boundary': 'OS_ISOLATION_CAPABILITY_BLOCKED',
     'Linux_runtime_trust': 'Installed interpreter/packages and read-only public /usr support; trusted initialization precedes seccomp, untrusted jobs and staging follow it',
     'Landlock': 'RESEARCHED_NOT_DEPLOYED; exact bounded mounts used instead'}
save('02_host_isolation_capabilities.json', capabilities)
manifest_path = Path(jobs['A']['argv'][jobs['A']['argv'].index('--manifest') + 1]).name
manifest = load(LOGS / manifest_path)
receipt_prefix = Path(jobs['A']['command_log']).name.removesuffix('-command.json')
receipt = load(LOGS / (receipt_prefix + '-copy-receipt.json'))
assert receipt['file_count'] == manifest['file_count'] == 3801
assert {r['path']: r['sha256'] for r in receipt['files']} == {r['path']: r['sha256'] for r in manifest['files']}
save('04_copy_manifest_and_preflight.json', {'manifest': 'logs/' + manifest_path,
     'receipt': 'logs/' + receipt_prefix + '-copy-receipt.json', 'files': receipt['files'],
     'file_count': receipt['file_count'], 'input_bytes': receipt['bytes'], 'payload_files': 0,
     'canonical_entrypoint': 'stage', 'bootstrap_fallback': False,
     'derived_canaries': 'Separately generated sparse non-market filesystem fixtures and copied reviewed metadata; not original payloads',
     'bounded_staging_sources': 'inputs/validated-native-source-chunks.json'})
probe = load(LOGS / (profile_prefix + '-native-probes.json'))
assert len(probe['probes']) == 8 and all(p['denied'] for p in probe['probes'])
assert probe['local_ipc_control']['bytes'] == 16
save('05_native_denial_probes.json', {'Linux': probe, 'Windows': 'NOT_RUN_NO_APPROVED_OS_BOUNDARY',
     'native_read_refusal': 'ENOENT: independently created outside canary not mounted; does not claim Windows ACL denial',
     'native_write_refusal': 'EROFS', 'process_and_Internet_refusal': 'EPERM from seccomp',
     'local_IPC_exception': 'Connected AF_UNIX socketpair send only; no Internet sockets or connect calls enabled',
     'pre_correction_IPC_failure': 'logs/ipc-f90083e876-command.json',
     'post_correction_IPC_success': 'logs/ipc-324a921505-command.json'})

coverage = {}
for job in ('A', 'diagnostic'):
    prefix = Path(jobs[job]['command_log']).name.removesuffix('-command.json')
    coverage[job] = load(LOGS / (prefix + '-coverage.json'))['totals']
save('coverage-summary.json', {'results': coverage, 'scope': 'omegadata package only; new script bootstrap coverage not instrumented; no financial-accuracy metric'})
score = {'original_manifest_candidates': 3626, 'original_regular_paths': 3626, 'size_matches': 3626,
    'hardlinked_paths': 2760, 'single_link_paths': 866, 'missing_candidate_paths': 0,
    'market_payload_bytes_read': 0, 'market_payload_hashes_verified': 0,
    'market_rows_inspected': 0, 'market_rows_independently_verified': 0,
    'financial_mismatches': None, 'missing_market_sessions': None, 'financial_coverage': None,
    'financial_rejected_records': None, 'synthetic_financial_acceptance_contribution': 0,
    'source_rights': 'UNCHANGED_PENDING', 'publisher_origin': 'UNVERIFIED',
    'financial_verdict': 'BLOCKED_REAL_DATA'}
save('real-data-scorecard.json', score)
gate = {'phase': 'OD05X_HOST_ISOLATION_AND_ENGINEERING_GATE_CLOSURE_ONLY', 'branch': 'feature/od01-source-rights',
    'HEAD': HEAD, 'software_regression': 'BLOCKED_REQUIRED_WINDOWS_RUNS_NOT_EXECUTED',
    'Linux_scoped_engineering': 'PASS_795_PASS_5_PLATFORM_SKIPS',
    'host_containment': 'BLOCKED_REQUIRED_WINDOWS_BOUNDARY_NOT_ESTABLISHED',
    'Linux_native_controls': 'EIGHT_NATIVE_DENIALS_AND_LOCAL_IPC_CONTROL_EXECUTED',
    'safe_engineering': 'BLOCKED', 'financial': 'BLOCKED_REAL_DATA',
    'full_diagnostic_exit': 1, 'full_diagnostic_failed_B_cases': 4, 'C': '4_NOT_RUN',
    'historical_Windows_identity_cause': 'INPUT_CHANGED_ROOT_CAUSE_UNKNOWN',
    'Linux_original_mount': 'LINUX_ORIGINAL_MOUNT_FULL_SCAN_PERFORMANCE_BLOCKED',
    'OD05V_incident': 'PENDING_HUMAN_OWNER_REVIEW_NOT_SELF_APPROVED',
    'preservation': 'PASS_RECORDED_HASHES_AND_METADATA_DIMENSIONS_NO_RAW_BYTE_CLAIM',
    'next_required_owner_action': 'Provide an operator-approved Windows OS-isolated runner configuration/environment for Python 3.14 and 3.11, with filesystem, native child and network denial proofs; rerun only OD05X',
    'commit_push_merge_release_OD06': 'NOT_PERFORMED_NOT_AUTHORIZED',
    'review_independence': 'Same-agent engineering review; kernel probes and separate metadata observations are independent mechanisms, not independent human approval'}
save('14_gatekeeper.json', gate)

doc('03a_bounded_staging_and_local_IPC_addendum.md', '''# Final runner addendum

The initial 3,799-per-file mount command exceeded bubblewrap's 9,000-argument limit and failed before staging. A Landlock alternative was researched but not deployed. The accepted runner retains exact mounts: three bounded manifests stage all 3,626 metadata files through the same OS-proved `stage()` API. Receipt-pinned, data-free native input trees are then explicitly mounted read-only; their exact file sets and all hashes are rechecked. Every execution destination remains fresh. Code and updated test contracts remain exact current-source mounts. No broad original repository, archive, incident-copy or credential directory is mounted.

The initial blanket sendto restriction also blocked connected Unix socketpair IPC. A frozen native canary failed with EPERM before correction and sent 16 bytes afterward. Only destination-less local IPC is permitted; Internet socket creation, every connect, addressed sendto, fork and exec remain kernel-denied. A positive IPC control now runs before staging. The stalled A worker was identified by its disposable policy and PID namespace and terminated with SIGTERM; exit 143 remains recorded, with no completed pytest totals fabricated.

Two completed diagnostic harness failures were fixed without changing original tests: permit the exact reviewed launcher source for introspection, and retain the legacy BLOCKED refusal message. A further focused legacy failure demonstrated that the kernel denies Internet creation before that old test's connect-time refusal context. An explicit Python refusal object now uses only an AF_UNIX descriptor and refuses network operations. It never creates or simulates a functioning Internet transport. The independent native probes still require real kernel EPERM. Existing tests and financial assertions remain unchanged.

The coordinator adds a declared 600-second job timeout after the unbounded stalled attempt. This is a new execution bound, not a scanner-budget increase; scanner max_seconds remains 30. Static Rust Ruff runs as a separate read-only source/network-namespace job, without a child-denial certification. Windows static checks similarly do not substitute for missing OS-isolated pytest runs.
''')
doc('06_negative_first_X01_X18.md', '''# Genuine negative-first record

[Initial frozen tests](logs/negative-first-freeze.json): 26 actual missing-module failures before implementation (NEW_FEATURE_ABSENT). [Three stronger integration cases](logs/integration-test-freeze.json) then failed on the absent reconciliation API in [their actual run](logs/integration-negative-first.json). The current isolation test source matches that expanded freeze.

[Four extensions](logs/native-extension-freeze.json) were frozen before correction. [Their baseline](logs/focused-fb4e3144640c-command.json) executed 29 passing / 4 failing cases: three absent direct-native probe kinds and one missing new-test source-hash enforcement. The fixes subsequently produced 33 passing cases. [The separate native IPC canary](logs/ipc-negative-first-freeze.json) failed before its syscall-rule correction and passed afterward. No unsafe original-market/credential probe was used to obtain a failure.

X01 missing sandbox and X02 false capability reports refuse; X03 native outside read, X04 protected write, X05 fork/exec and X06 socket/connect/DNS-send denials execute on Linux. X07 verifies the sole staging path and actual receipts; X08 exact names/classes/counts/pins; X09 symlink/hardlink/destination ancestor refusal; X10 both mutation windows; X11 fresh destination/no overwrite; X12 canary identity diagnostics; X13 threaded invalidation; X14 corpus distinction; X15 exact collection/source contracts including new-source pin refusal; X16 unchanged B/C blocks; X17 independent fresh inventory/preservation; X18 separate Gatekeeper axes all execute in the 33-case focused suite.

These are Linux execution results. Required Windows groups remain BLOCKED/NOT_RUN except actual fail-closed launcher preflight. No Windows junction/native-containment PASS or historical negative-first compliance is inferred. Initial feature absences, launcher refusals, IPC defect, terminated A, six-failure diagnostic and focused legacy failure remain in logs.
''')
doc('07_filesystem_identity_investigation.md', f'''# Filesystem identity investigation

The historical Windows event remains **INPUT_CHANGED_ROOT_CAUSE_UNKNOWN**. Its differing fields were never captured. Current Windows serialized/stress tests are NOT_RUN because the required approved OS boundary is absent. Later Linux success cannot explain that historical failure.

The additive canary-only wrapper captures dev, inode, mode, size, mtime_ns, link count, directory identity, generation, process, thread and invocation. Original paths and contents are not instrumented. [Fresh native diagnostics](logs/{profile_prefix}-identity-diagnostics.json) record 100 serial accesses, 8 threaded readers, one underlying scan, and deterministic mutation refusal. The changed metadata size/mtime are explicit. These demonstrate known-mutation invalidation only; they do not identify the cause of the old Windows event. No check or cache invalidation was disabled.
''')
doc('12_incident_containment_status.md', '''# Incident status

Historical OD-05V: 39 files / 6,135,515 recorded bytes remain PENDING_HUMAN_OWNER_REVIEW and NOT_SELF_APPROVED. The ledger and all prior evidence remain byte-identical. No affected original or retained copy was opened, rehashed, copied or deleted in this phase. No retrospective approval is created.

The Linux accepted path stages reviewed code/metadata only after namespace, read-only-mount, seccomp and direct-native controls execute. Windows refuses before manifest reads or destination creation. Original payload bindings/copies are zero in the reviewed manifests. This is scoped engineering evidence, not proof against a malicious host administrator or authorization of the historical operation. Signing, source-policy, production-routing, release and database contents remain unchanged.
''')
doc('13_security_risks_and_rollback.md', '''# Remaining risks and rollback

- P1: required Windows filesystem/egress/native-child containment and regression matrix remain blocked. AppContainer/restricted-token/job/mitigation APIs exist, but no configured boundary is demonstrated. Windows Sandbox is absent; no privileged software or host-wide policy is installed.
- P1: historical incident disposition and financial-source permissions/authenticity remain unapproved. No new approval is inferred. Existing signing/release custody risks are not waived.
- P2: historical Windows INPUT_CHANGED cause remains unknown. Linux canary diagnostics are not Windows reproduction evidence.
- P2: original mounted WSL seed enumeration still exceeds the unchanged 30-second budget. Native corpus and Windows-host metadata performance are distinct.
- P2: trusted launcher, installed runtime/public system support and trusted-owner source trees remain assumptions. Host administrator/kernel compromise, hostile host mount swaps, hardware power-loss durability and complete executable/supply-chain certification are outside these tests. New script bootstrap coverage was not measured by package coverage.

The implementation is additive. A future requested rollback can remove/revert only the four new script/test paths after review, retaining this dossier. No cleanup, data rollback, signing action, release or branch operation was performed. Old controllers stay historical and are not a fallback. Static tool PASS does not certify the blocked Windows or child-execution requirements.
''')
doc('15_final_phase_report.md', f'''# OD-05X — BLOCKED / BLOCKED_REAL_DATA

Branch `feature/od01-source-rights`; HEAD `{HEAD}`. Four new source/test paths and this fresh dossier are uncommitted. Existing tracked files are unchanged; pre-existing environment/private untracked files remain excluded and preserved.

Added [trusted launcher](../../../../../scripts/od05x_isolated_runner.py), [worker](../../../../../scripts/od05x_worker_jobs.py), [X01–X18 tests](../../../../../tests/unit/test_od05x_isolation.py) and [native/hash extensions](../../../../../tests/unit/test_od05x_native_extensions.py). The accepted path uses one staging API, exact reviewed manifests, bounded OS-proved metadata batches, fresh destinations, source/descriptor/hash checks, native denial probes and content-addressed receipts. No historical bootstrap fallback remains. See the [architecture addendum](03a_bounded_staging_and_local_IPC_addendum.md).

Fresh Linux 3.12: focused X 33 passed; OD05V 40 passed/1 platform skip; OD05W 39 passed; collection 808 = A800+B4+C4. A: **795 passed/5 skipped, exit 0**. Unchanged full non-realdata diagnostic: **795 passed/4 failed/5 skipped, exit 1**, with exactly B failed and C4 deselected. All failures, the earlier exit-143 stalled A and six-failure diagnostic are retained. [Matrix](10_cross_platform_runtime_matrix.json), [dependency reconciliation](09_test_dependency_reconciliation.json), [negative-first chronology](06_negative_first_X01_X18.md), [coverage](coverage-summary.json).

Windows 3.14/3.11 launchers actually refused with exit 2 before manifest reads/copying. Their collection/focused/A/diagnostic/stress runs are **NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED**. Fresh Windows Ruff/mypy/pip/compilation checks exit 0. Linux mypy/pip/compilation exit 0 inside the restricted worker. Linux Rust Ruff exits 0 in a separately scoped static namespace job. Static outcomes do not replace missing full-boundary verification. Archived Windows counterpart skips are not fresh proof.

Actual native Linux errno results: unmounted canary read ENOENT(2), read-only source write EROFS(30), fork/exec/Internet socket/connect/addressed send EPERM(1). Probes precede Python hooks and staging. Local Unix IPC is explicitly allowed and independently controlled; no Internet transport is enabled. Windows native denial probes remain unexecuted. [Native evidence](05_native_denial_probes.json), [capabilities](02_host_isolation_capabilities.json).

Fresh original-host inventory independently reconciles 3,626 paths and size matches (seed3596/cache30; hardlinks2760/single866). Payload inspection remains ineligible. Original WSL seed scanning remains PERFORMANCE_BLOCKED at 30 seconds. Native profiling and known-mutation diagnostics are separate. Historical Windows cause remains UNKNOWN. [Profiles](08_linux_performance_profile.json), [identity investigation](07_filesystem_identity_investigation.md).

Preservation: {len(before['code_and_metadata_before'])} existing code/metadata identities; 361 prior dossier files including 358 sealed files; 3,626 fresh before/after payload stat identities; {len(arch)} archived-to-current data/artifact/database metadata observations — no changes. These are recorded hashes/stat dimensions, not new original-payload byte-integrity verification. The historical 39-file incident remains pending human review, never self-approved. [Preservation](11_preservation_and_source_hashes.json), [incident status](12_incident_containment_status.md).

**Software regression: BLOCKED for required Windows runs. Host containment: BLOCKED for required Windows controls. Overall safe engineering: BLOCKED. Financial: BLOCKED_REAL_DATA** — zero original payload bytes/hashes or independently verified financial rows; existing robustness fixtures contribute zero financial acceptance. [Gatekeeper](14_gatekeeper.json), [real-data scorecard](real-data-scorecard.json), [risks](13_security_risks_and_rollback.md).

**One next owner action:** provide an operator-approved Windows OS-isolated runner environment/configuration for Python 3.14 and 3.11, covering filesystem access, native child execution and network denial, then rerun only OD05X. This is an engineering environment requirement, not a new publisher-permission request.

STOP after OD-05X. No commit, push, merge, release, signing, production routing change, real acquisition or OD-06.
''')
save('command-index.json', [{'log': r['command_log'], **{k: r[k] for k in ('argv', 'start_utc', 'end_utc', 'elapsed_seconds', 'exit_code') if k in r}} for r in commands])
save('evidence-sha256.json', {'scope': 'Phase-owned source/evidence/metadata only; no original market/key content',
    'excluded': ['evidence-sha256.json', 'postseal-validation.json'],
    'files': {p.relative_to(HERE).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
              for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}})
seal = load(HERE / 'evidence-sha256.json')
assert all(sha(HERE / n) == row['sha256'] and (HERE / n).stat().st_size == row['bytes'] for n, row in seal['files'].items())
save('postseal-validation.json', {'utc': datetime.now(UTC).isoformat(), 'files_verified': len(seal['files']),
     'all_match': True, 'seal_sha256': sha(HERE / 'evidence-sha256.json'),
     'original_payload_or_signing_content_hashed': False})
print(json.dumps({'Gatekeeper': gate, 'files_sealed': len(seal['files']),
                  'coverage': coverage, 'preservation': preservation}, indent=2))
