"""Append the final source revision; never edit the first seal or its reports."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
root = Path.cwd()
here = Path(__file__).parent
logs = here / 'logs'
def load(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n, body):
    with (here / n).open('x', encoding='utf-8') as f: json.dump(body, f, indent=2)
def doc(n, body):
    with (here / n).open('x', encoding='utf-8') as f: f.write(body.strip() + '\n')

initial = load(here / 'evidence-sha256.json')
assert all(sha(here / n) == v['sha256'] for n, v in initial['files'].items())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == 'f7ebc463980fd5c1c80961c3e5ecece4e337911a'
assert not subprocess.check_output(['git', 'diff', '--name-only'], text=True).strip()
paths = list(load(here / '11_preservation_and_source_hashes.json')['new_source_pins'])
pins = {n: sha(root / n) for n in paths}
all_commands = [load(p) | {'log': p.relative_to(here).as_posix()}
                for p in logs.glob('*-command.json')]
def accepted(job):
    candidates = []
    for r in all_commands:
        if r.get('job') != job or not r.get('worker_result'): continue
        argv = r['argv']
        manifest = load(logs / Path(argv[argv.index('--manifest') + 1]).name)
        source_pins = {row['path']: row['sha256'] for row in manifest['files']}
        if all(source_pins.get(n) == v for n, v in pins.items()): candidates.append(r)
    assert candidates, job
    return max(candidates, key=lambda r: r['start_utc'])
jobs = {n: accepted(n) for n in ('collection', 'focused', 'presence', 'W', 'A', 'diagnostic',
                                'mypy', 'pip', 'compile', 'environment', 'profile')}
for n, row in jobs.items(): assert row['worker_result']['exit_code'] == (1 if n == 'diagnostic' else 0)
assert jobs['A']['worker_result']['counts'] == {'passed': 795, 'skipped': 5}
assert jobs['focused']['worker_result']['counts'] == {'passed': 33}
assert jobs['diagnostic']['worker_result']['counts'] == {'passed': 795, 'failed': 4, 'skipped': 5}
inventory = load(here / 'inputs/runtime-inventory.json')
failed = [r for r in jobs['diagnostic']['worker_result']['reports'] if r['outcome'] == 'failed']
assert {r['nodeid'] for r in failed} == {n for n, c in inventory.items() if c == 'B'}
assert set(jobs['diagnostic']['worker_result']['deselected']) == {n for n, c in inventory.items() if c == 'C'}
win = load(logs / 'postseal-windows-quality.json')
assert all(r['source_pins'] == pins and r['exit_code'] == (2 if r['kind'] == 'refused-runner' else 0) for r in win)
assert load(logs / 'linux-static-ruff-hardened.json')['exit_code'] == 0
before = load(logs / 'read-and-preservation-before.json')
assert all(sha(root / n) == h for n, h in before['code_and_metadata_before'].items())
oldroot = root / 'docs/omegadata_v2/implementation/od05w/20261116T183719Z'
assert all(sha(oldroot / n) == row['sha256'] for n, row in before['entire_prior_dossier'].items())
stats = load(here / 'inputs/original-independent-stat.json')['rows']
for n, row in stats.items():
    s = (root / n).lstat()
    assert [s.st_size, s.st_mtime_ns, s.st_ino, s.st_nlink] == [row[k] for k in ('size', 'mtime_ns', 'ino', 'nlink')]
profile_prefix = Path(jobs['profile']['log']).name.removesuffix('-command.json')
probe = load(logs / (profile_prefix + '-native-probes.json'))
assert len(probe['probes']) == 12 and all(r['denied'] for r in probe['probes'])
assert probe['local_ipc_control']['bytes'] == 16
families = [r for r in all_commands if 'family-result.json' in r]
red = next(r for r in families if r['classification'] == 'BEFORE_CORRECTION')
green = next(r for r in families if r['classification'] == 'AFTER_CORRECTION')
assert red['exit_code'] == 1 and green['exit_code'] == 0 and red['probe_sha256'] == green['probe_sha256']
gate = load(here / '14_gatekeeper.json')
gate.update({'utc': datetime.now(UTC).isoformat(), 'final_source_pins': pins,
             'supersedes': '14_gatekeeper.json for final source identity and native-control revision only; old records/seal unchanged',
             'Linux_native_controls': '12_NATIVE_DENIALS_AND_LOCAL_IPC_CONTROL_EXECUTED',
             'network_default': 'Only AF_UNIX socket family; bind/listen/accept/accept4/connect/sendmsg denied; addressed sendto denied',
             'supplementary_negative_first': {'freeze': 'logs/network-family-negative-first-freeze.json',
                 'before': red['log'], 'after': green['log'], 'probe_source_sha256': green['probe_sha256']},
             'runtime_matrix': {n: {'command_log': row['log'], 'exit_code': row['worker_result']['exit_code'],
                 'counts': row['worker_result']['counts']} for n, row in jobs.items()},
             'Windows_static': 'logs/postseal-windows-quality.json', 'Linux_Ruff_static': 'logs/linux-static-ruff-hardened.json',
             'original_seal_files_verified_unchanged': len(initial['files']),
             'original_stat_records_verified_unchanged': len(stats)})
save('17_gatekeeper_final.json', gate)
save('18_final_preservation_and_native_controls.json', {'utc': datetime.now(UTC).isoformat(),
     'HEAD': head, 'source_pins': pins, 'code_snapshots': 'source-snapshots/',
     'existing_code_metadata_verified': len(before['code_and_metadata_before']), 'existing_changes': 0,
     'prior_dossier_verified': len(before['entire_prior_dossier']), 'prior_changes': 0,
     'original_phase_sealed_files_verified': len(initial['files']), 'initial_seal_changes': 0,
     'fresh_original_stat_records_verified': len(stats), 'fresh_stat_changes': 0,
     'original_payload_or_signing_content_hashed': False, 'native_controls': probe})
doc('16_native_network_default_deny_addendum.md', f'''# Final adversarial correction, appended after the first seal

The first closure package remains unchanged and valid for its recorded source revision. Final review then tested a remaining network-default concern. A new frozen non-market native probe actually created an AF_NETLINK descriptor and successfully bound a namespace-local Unix address under the earlier policy. No packets or peer connections occurred. listen/accept4 returned ordinary EINVAL rather than policy EPERM. This was an incomplete default-deny policy, not evidence of original-data access.

The minimal correction denies every socket family except AF_UNIX, and additionally denies bind/listen/accept/accept4. Connected socketpair IPC remains permitted. The identical probe changed from exit 1 to exit 0, with all four operations returning EPERM. Every accepted worker now proves twelve native denials before staging. Source hashes, exact commands, before/after errno and unchanged probe source hash are in [the final Gatekeeper](17_gatekeeper_final.json).

Fresh verification after correction again collected 808=A800+B4+C4; X 33 pass, OD05V 40 pass/1 skip, OD05W 39 pass, A795 pass/5 skips exit0, full diagnostic795 pass/4 fail/5 skips exit1 with C4 deselected. Existing B/C source files and assertions remain unchanged. Linux and Windows static quality checks pass; Windows pytest still refuses before copying. Current source and the earlier phase-authored code revision are retained as SHA-verified [code snapshots](source-snapshots/).

This is OD-05X only. The historical incident is not approved, Windows containment and regression remain blocked, original mounted Linux seed performance remains blocked, Windows INPUT_CHANGED cause remains unknown, and real financial validation remains BLOCKED_REAL_DATA. No earlier report, source policy, market file, signing material or release is rewritten.
''')
doc('19_final_phase_report.md', '''# Final OD-05X report — BLOCKED / BLOCKED_REAL_DATA

This report and [final Gatekeeper](17_gatekeeper_final.json) supersede the initial closure report only for the final source revision and supplementary adversarial correction. The original reports, failures and 277-file seal remain unchanged. [Initial full dossier report](15_final_phase_report.md), [hardening chronology](16_native_network_default_deny_addendum.md), [final preservation/native proof](18_final_preservation_and_native_controls.json).

Branch `feature/od01-source-rights`; HEAD `f7ebc463980fd5c1c80961c3e5ecece4e337911a`. Four additive script/test paths and this dossier are uncommitted; no existing tracked application/test file changed. All pre-existing environment and private untracked work remains excluded and preserved.

The Linux path implements namespaces, dropped capabilities, exact read-only input mounts, a single canonical staging API, receipt-pinned native metadata reuse, fresh disposable destinations and irreversible seccomp. Twelve native denial checks and a positive private-IPC control run before copying or pytest. No historical copy fallback is used. Windows Python 3.14/3.11 reject launch before manifest reads or destination creation; no Windows OS-boundary PASS is claimed.

| Fresh scope | Result |
|---|---|
| Linux collection | 808 = A800 + B4 + C4 |
| X01–X18 focused | 33 passed; supplemental native IPC/default-deny probes have separate frozen red/green evidence |
| OD05V / OD05W focused | 40 passed +1 platform skip /39 passed |
| Linux A | 795 passed, 5 skipped; exit0 |
| Full unchanged non-realdata diagnostic | 795 passed, 4 failed, 5 skipped, C4 deselected; exit1 |
| Linux mypy/dependencies/compilation | exit0 in restricted worker |
| Linux Ruff | exit0 in separately scoped read-only static namespace job |
| Windows 3.14/3.11 | static Ruff/mypy/dependencies/compilation exit0; pytest/stress NOT_RUN_OS_ISOLATION_CAPABILITY_BLOCKED; launcher exit2 |

All eighteen groups have genuine Linux negative-first evidence. Initial missing APIs are labelled NEW_FEATURE_ABSENT. Four direct-native/source-pin cases, the local-IPC defect and the network-family/bind gap were tested before their corrections. Early launcher refusals, the exit143 stalled A, six-failure diagnostic and focused legacy failure remain recorded. The final diagnostic still fails exactly the four original source-dependent B cases. No B assertion changed, no C execution occurred, and archived Windows skip counterparts are not fresh proof.

The historical Windows INPUT_CHANGED root cause remains UNKNOWN; Windows stress execution is blocked. Native Linux instrumentation recorded all requested stat dimensions, generation/process/thread/invocation, 100 serial reads, eight threaded readers, one underlying scan and known-mutation refusal. These do not explain the earlier Windows failure.

Fresh original metadata observations reconcile 3,626 present and size-matched paths: seed3596/cache30, hardlinked2760/single866. Content eligibility remains false. Native metadata profiling is separate from original Windows-host observations. One original WSL-mounted seed scan hit the unchanged 30-second budget; no repeat was used to force a PASS. Original byte integrity and financial authenticity are unmeasured.

Preservation verifies 168 existing code/metadata identities, all361 prior OD05W dossier files (358 sealed), the277-file first X seal and all3,626 fresh original payload stat identities without changes. The earlier 11,210-record archived-to-current metadata comparison is retained as such. No original market payload or signing content was read/hashed/copied, no source policy/routing/database/release was changed, and the historical39-file incident remains pending human review—not self-approved. Financial rows inspected/independently verified: **0**. Existing robustness fixtures contribute **0** real-financial acceptance.

**Software regression: BLOCKED for missing required Windows execution. Host containment: BLOCKED for missing Windows enforcement proof. Overall safe engineering: BLOCKED. Financial: BLOCKED_REAL_DATA.** Linux scoped results pass; they do not certify Windows or production readiness. Review is same-agent, with independent kernel mechanisms and separate metadata observations, not independent human approval.

**One next owner action:** supply an operator-approved Windows OS-isolated runner environment/configuration for Python3.14 and3.11, covering filesystem access, native child execution and network refusal, then rerun only OD05X. No publisher-permission loop is needed for that engineering step.

STOP after OD-05X. No commit, push, merge, release, signing, real-source acquisition or OD-06.
''')
save('evidence-sha256-final.json', {'initial_seal_sha256': sha(here / 'evidence-sha256.json'),
    'scope': 'All phase-owned code/evidence/metadata and phase-authored source snapshots; no original market/key content',
    'excluded': ['evidence-sha256-final.json', 'final-postseal-validation.json'],
    'files': {p.relative_to(here).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
              for p in sorted(here.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}})
final = load(here / 'evidence-sha256-final.json')
assert all(sha(here / n) == row['sha256'] for n, row in final['files'].items())
save('final-postseal-validation.json', {'utc': datetime.now(UTC).isoformat(), 'all_match': True,
    'files_verified': len(final['files']), 'seal_sha256': sha(here / 'evidence-sha256-final.json'),
    'initial_seal_unchanged': True, 'original_market_or_signing_content_hashed': False})
print(json.dumps({'verdict': gate['safe_engineering'], 'financial': gate['financial'],
                  'final_sealed_files': len(final['files']), 'new_source_pins': pins,
                  'native_denials': len(probe['probes']),
                  'matrix': gate['runtime_matrix']}, indent=2))
