"""Fresh OD04 evidence package; fail closed on process-order conformance."""
from __future__ import annotations
import difflib
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import control

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
RUNTIMES=['win314-accepted','win311-accepted','linux312-accepted']
CHANGES=['src/omegadata/track_a/raw_archive.py','src/omegadata/track_a/download_manager.py',
    'tests/unit/test_od04_raw_archive.py','scripts/verify_raw_archive.py','scripts/plan_legacy_raw_import.py']
REQUIRED=['00_preflight.md','01_existing_callgraph_and_repo_reuse.md','02_architecture_and_contracts.md',
    '03_negative_first_matrix.md','04_implementation_ledger.md','05_concurrency_crash_recovery.md',
    '06_cross_platform_and_compatibility.md','07_security_and_rights_review.md',
    '08_metrics_and_reproducibility.md','09_gatekeeper_verdict.md','10_next_phase_request.md']

def data(label):return json.loads((LOGS/(label+'.json')).read_text())
def process(mode):
    raw=(LOGS/('linux-process-persistent.txt' if mode=='linux' else 'win-process-accepted.txt')).read_text()
    return json.loads(raw[raw.index('{\n'):])
def reference(mode):
    raw=(LOGS/('linux-corpus-persistent.txt' if mode=='linux' else 'win-corpus-reference.txt')).read_text()
    return json.loads(raw[raw.index('{\n'):])
def write(name,text):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as out:out.write(text)
banner='Baseline d24e9cfd29c8a59e590aaee85983babe9e8bf182; feature/od01-source-rights. OD04 only, 20261115T124835Z. RUN/TEST/SYN evidence; inherited reports ARCH. Same-model procedural review, not independent human approval.\n\n'

def reports():
    write('00_preflight.md','# OD04 preflight\n\n'+banner+'''Required branch and exact HEAD matched before edits. Tracked worktree clean;
pre-existing untracked local Linux environment, supplied root OD04 prompt and
signing/revocation files retained. Requested docs/verification OD04 prompt path
was absent; complete supplied root prompt was read instead, not recreated.
Root AGENTS/OMEGADATA_AGENTS, controlling master, OD00 defects/plan/architecture,
OD01/01R/02/02V full Gatekeeper/next requests and applicable source inspected.
No deeper AGENTS found under source/tests/docs. Founder skill unavailable in
catalog; no invented instructions or paid agent consensus.

Actual required Git commands, UTC intervals and exits: [root](logs/git-root.json),
[branch](logs/git-branch.json), [HEAD](logs/git-head.json),
[status](logs/git-status.json), [diff](logs/git-diff.json),
[history](logs/git-history.json), [main](logs/git-main.json). All exits 0.
All original tracked and protected nonsecret records frozen in preservation-before;
signing paths metadata only, never opened or hashed. No key material or production
data copied into test trees. Final [preservation gate](logs/final-preservation.json)
compares every original record; unchanged HEAD/index/main required.

New disposable Windows copy contains exact baseline source/config/scripts/tests
and pyproject/README; precise OD02V 47-file/6,138,891-byte fixture allowlist reused
by hash, not the corpus wholesale. Linux gets a new native /home copy with tests
on native /tmp. See [copy provenance](logs/copy.json), [Linux setup](logs/linux-copy.json).
These are ARCH regression dependencies, not newly acquired official truth.
Environments: existing Windows 3.14.3 and prior disposable 3.11.15 and Linux 3.12.3;
all dependencies already usable, no install, no dependency/pin/CI modification.
Each final *-environment.txt records actual interpreter/OS/installed versions.

Fresh protected baseline Windows: **393 pass / 10 skip / 4 realdata deselected**,
exit 0, [raw](logs/baseline-win314.txt), [command](logs/baseline-win314.json).
Final suites retain all inherited tests unchanged. Network/protected-write guard
copied from OD02V, only evidence path and baseline label changed, not guard logic.
No unguarded pipeline/probe/release/DB command executed.

Preflight PowerShell Get-Date -AsUTC was unavailable; UTC used DateTime.UtcNow
instead. Missing requested prompt path was an observed discovery exit, not a
source-code defect. Both distinctions stay explicit. No Git lifecycle action.
''')
    write('01_existing_callgraph_and_repo_reuse.md','# Existing call graph and reuse\n\n'+banner+'''DownloadManager.download validates request options -> per-job bounded budget ->
_download_in_job -> READ_CACHED with consumer purpose -> raw/seed confined legacy
manifest parser, identity/length/checksum/structural checks. Cache-only miss raises
CACHE_MISS before candidates or storage. Uncached paths authorize FETCH/STORE_RAW,
render era and candidates -> per-profile _fetch_candidate -> bounded transport
and existing _validate_payload -> typed terminal denial escapes all fallbacks ->
fresh FETCH/STORE_RAW authorization -> old per-manager RLock -> storage boundary.

Legacy boundary uses date+12 hash prefix, conditional raw/manifest writes and
direct latest write. Four pre-change executable failures establish truncated
identity, collapsed events, existing corruption reuse and partial payload after
manifest failure. Existing default legacy path is retained, not certified immutable.

New constructor raw_archive opts into service put only AFTER valid candidate and
fresh rights checks; early return prevents legacy directory/pointer writes. Artifact
adds optional observation_id/commit_id/archive_state; prior fields retained. Explicit
operation_id/observed_at support retries; ordinary new acquisition gets new ID/time.
Archive fresh observations are SYNTHETIC_TEST_ONLY because actual egress is disabled.
Current cache return is unchanged except LEGACY_UNVERIFIED flag in opt-in mode;
cache/seed source_mode stays distinguishable. No implicit import/latest inference.

IngestionOrchestrator.ingest_raw_source -> its manager.download -> artifact.path;
public default remains compatible, orchestrator unchanged. ParquetStorage.store_daily
still writes fixed part-00000.parquet: D03 canonical analytical storage remains OD10.
No financial computation, ORM or release service changes.

[Repository selection](../../../decisions/od04-raw-archive-reuse.md): EXTEND_EXISTING,
stdlib filesystem/hash/JSON and existing Pydantic/OD02 validator/OD01 policy APIs.
DVC/lakeFS/delta-rs/DuckDB compared for fit/footprint/rollback; exact primary-source
tag licenses checked, runtime/advisory details unknown, external benchmarks
UNMEASURED and external tests NOT_RUN. No fetched library/code or new dependency.
Two local publish protocols exercised; selected exclusive hardlink with kernel
writer lock and final marker. No claim that rename alone is a transaction.
''')

    rows=[]
    matrix='# OD04 A01–A28 acceptance and negative-first ledger\n\n'+banner+'''**Process conformance BLOCKED.** Four real baseline assertion failures ran before
production edits. Many new unit contracts were authored before the core module,
but the complete A01–A28 tranche (notably separate process experiments and later
adversarial cases) was not authored/executed before implementation as Gate 2
required. That chronology cannot be retroactively called compliant. Missing API /
import errors are NOT used as old-code defect proof. Every final row below has
executed green evidence, but technical green does not waive that process gate.

Pre-change [red-old-storage](logs/red-old-storage.json)/[raw](logs/red-old-storage.txt):
exit 1, four assertion failures. Later new-implementation red cases:
[mode relabel](logs/red-mode-relabel.txt), [policy identity](logs/red-policy-identity.txt),
[false structural state](logs/red-structural-state.txt): each exit 1 before its
correction; each final assertion passes. First core green 40 pass/4 genuine Windows
symlink skips; new directory-link tests then use actual Windows junctions paired
with actual Linux symlinks, not a skipped test labeled pass. No inherited test edited.

| Acceptance | Executed node / experiment | Final technical outcome |
|---|---|---|
'''
    descriptions={
        1:'exact full digest and original bytes',2:'dedup bytes, retain distinct observations',3:'same-day different versions',
        4:'idempotence includes payload/request/policy identity',5:'conflicting operation reuse',6:'marker-last visibility',
        7:'five injected and forced-termination boundaries',8:'read-only inventory/retry after interrupted states',
        9:'twelve thread writers',10:'independent same-hash processes',11:'independent different-hash processes',
        12:'full bytes/length/link checks and deterministic corruption scan',13:'traversal/hash/drive/UNC and real directory-link confinement',
        14:'duplicate/invalid JSON and version refusal',15:'mode and synthetic-origin non-escalation',
        16:'pending/missing/revoked/scope and commit-time policy refresh',17:'cache-only no fetch / legacy read-only',
        18:'legacy dry-run and all-original preservation',19:'empty/oversize/metadata/entry/total budgets',
        20:'typed fsync/link ENOSPC/EACCES/EIO injection',21:'readers during paused publication and independent processes',
        22:'URL redaction in observation/structured refusal',23:'pinned replay and sorted read-only scan',
        24:'actual parser validation, exact era/date/schema/rights references, null published_at',
        25:'Windows and native Linux filesystem execution',26:'unchanged inherited/full offline suites',
        27:'imports/collection, Ruff, strict mypy49 and pip consistency',28:'measured 4KiB/64KiB/1MiB costs, disk and recovery'}
    unit=data('win314-accepted-targeted')['test_reports']
    for number,description in descriptions.items():
        token=f'a{number:02d}'
        nodes=sorted({r['nodeid'] for r in unit if 'test_od04_raw_archive.py' in r['nodeid'] and token in r['nodeid'].split('::')[-1]})
        if number in {7,8,10,11,21,25,28}:
            evidence=['win-process-accepted','linux-process-persistent']
        elif number==27:evidence=[r+'-'+gate for r in RUNTIMES for gate in ['collection','ruff','mypy','pip']]
        elif number==26:evidence=[r+'-full' for r in RUNTIMES]
        else:evidence=[r+'-targeted' for r in RUNTIMES]
        if number==18:evidence+=['win-corpus-reference','linux-corpus-persistent']
        metadata_keys={'command','cwd','baseline','platform','python','start_utc','end_utc','elapsed_seconds','exit_code','output'}
        rows.append(dict(id=f'A{number:02d}',requirement=description,nodes=nodes,
            commands=[{k:v for k,v in data(x).items() if k in metadata_keys} for x in evidence],
            final_source_hashes={r:data(r+'-source') for r in RUNTIMES},
            red_proof='four baseline storage failures; later adversarial reds linked; no invented red for already-correct/new-API contracts',
            final_technical='PASS',process_conformance='BLOCKED: complete pre-implementation Gate 2 tranche not satisfied'))
        display='; '.join('`'+n.split('::')[-1]+'`' for n in nodes[:3]) or ('separate guarded process experiments' if number in {10,11,28} else 'runtime matrix / preservation')
        matrix+=f'| A{number:02d}: {description} | {display}; [commands](logs/{evidence[0]}.json) | PASS technical; Gate 2 chronology BLOCKED |\n'
    matrix+='\n[Complete machine matrix](logs/acceptance-matrix.json) includes full nodes, exact argv/cwd/OS/interpreter/UTC/actual exits and tested source hashes, plus raw output references. No claim that all A01–A28 failed on unchanged code. Actual step order is retained.\n'
    control.save('acceptance-matrix.json',rows)
    write('03_negative_first_matrix.md',matrix)

    write('04_implementation_ledger.md','# Exact implementation ledger\n\n'+banner+'''Only one original application file changed: download_manager.py, additive optional
archive integration and artifact IDs, early return before legacy writes, legacy
cache label. New files: raw_archive.py; tests/unit/test_od04_raw_archive.py;
scripts/verify_raw_archive.py (pinned or ALL scoped verification); scripts/plan_legacy_raw_import.py
(single validated legacy candidate, dry-run mapping only); repository decision and
this fresh eleven-report evidence directory with narrowly scoped helpers/logs.

raw_archive: frozen strict schemas; full SHA paths, separate UUID events; immutable
request/policy identity; kernel lock timeout and quota reservation; same-filesystem
exclusive stage + fsync + hardlink; marker last; current rights before IO and commit;
verified replay/scan; read-only recovery inventory; conservative source-reference
warning and unknown published time. Structural validity requires actual OD02 validator.

First implementation corrections were driven by executable adversarial reds:
synthetic-origin relabeling refused; policy revision hash included in retry identity;
claimed structural validity reruns existing bounded validator and matches schema.
No changes to acquisition.py, source_rights.py, policies, analytical paths, ORM,
dependencies, config, workflows, old tests/evidence, actual data/releases/keys.

[Final patch](logs/implementation.patch) includes tracked diff and new source/test/
CLI content. [Final preservation](logs/final-preservation.json) verifies original
records and each final runtime's exact overlay hashes. [Design before code](02_architecture_and_contracts.md)
records interfaces, state machine, limits, risks and rollback. The ADR is technical
proposal, not external administrative approval. Code remains uncommitted/unstaged.
Rollback is opt-in removal/disablement after review, retain archive/evidence;
no deletion, migration or rollback executed.
''')

    concurrency='# Cross-process crash/recovery evidence\n\n'+banner
    for mode in ['win','linux']:
        p=process(mode);ref=reference(mode)
        concurrency+=f"## {mode}\n\n[controller command](logs/{mode}-process-accepted.json), [all worker commands/exits/output](logs/{mode}-process-accepted.txt). Overall exit 0, passed={p['passed']}. Five actual disposable workers killed, not exception mocks; Windows exit 1 and Linux -9 expected. Before-stage/after-stage/after-object/after-observation/before-marker have zero visible commit, then fresh worker retries same identity successfully. Kernel locks released on death.\n\nThree writers plus independent reader (maximum four simultaneous workers) tested same and different bytes; every reference object/observation link verified. One conflicting operation produces one success and one expected exit 2 refusal, never two conflicting successes. Independent stdlib scan: **{ref['observations']} observations / {ref['objects']} object files**, all full SHA/length/observation links valid; [scan](logs/{mode}-corpus-reference.txt).\n\n"
    concurrency+='''Both exclusive hardlink and kernel-lock+absent-destination rename prototypes
execute on both OSes. The second prototype establishes basic local feasibility,
not a full production alternative implementation/concurrency certification.
Selected hardlink writer has actual concurrent process/crash evidence. Publication
never overwrites existing final files; existing destinations are read/compared.

The earlier process-v1 attempt exited 1: Windows audits Popen argv as a string,
the strict list allowlist refused it before any worker. Exact-issued-command
comparison corrected without widening executable/script authority. process-v2
then exercised workers but prototype fsync on read-only Windows fd failed EBADF;
changed prototype to writable fd. These are harness errors, not application red
proofs. v3/reviewed/accepted logs retained; accepted source hashes are authoritative.

Trusted fixed child executable/script (worker hash recorded), isolated root and
fixed argument variants only. Four child negative probes refuse DNS, TCP,
subprocess and protected copy writes. Each child blocks egress/process creation;
parent allows only exact issued commands. This separate harness does not weaken
the unchanged pytest audit guard. It is trusted Python, not an arbitrary ctypes
or kernel security sandbox. No user process targeted.

Recovery inventories retain staging, orphan observations and immutable objects;
no automatic reprocessing/promotion/deletion/GC. Counts explicitly UNVERIFIED;
scan_verified is separate full integrity verification. Idempotent supplied-request
retry safely reuses only matching records. No operational cleanup is authorized.
OS process death is tested; sudden power-loss, remote filesystem semantics and
hostile concurrent directory-owner races are NOT certified. Windows directory
fsync unsupported; POSIX created-child directories and final links fsynced, root
parent durability remains caller responsibility. Private trusted local root only.
'''
    write('05_concurrency_crash_recovery.md',concurrency)

    portability='# Cross-platform and compatibility verification\n\n'+banner+'| Runtime | Targeted pass / skip | Full pass / skip / deselected | Combined coverage | Static/package exits |\n|---|---:|---:|---:|---|\n'
    for r in RUNTIMES:
        targeted=data(r+'-targeted');full=data(r+'-full');coverage=data(r+'-full-coverage')['totals']['percent_covered']
        c=targeted['call_counts'];f=full['call_counts']
        portability+=f"| {r} | {c.get('passed',0)} / {sum(x['outcome']=='skipped' for x in targeted['test_reports'])} | {f.get('passed',0)} / {sum(x['outcome']=='skipped' for x in full['test_reports'])} / {len(full['deselected'])} | {coverage:.4f}% | Ruff {data(r+'-ruff')['exit_code']}; mypy {data(r+'-mypy')['exit_code']}; pip {data(r+'-pip')['exit_code']} |\n"
    portability+='''
All final collection/targeted/full commands exit 0; mypy checks 49 files. Exact
command/exit/time/per-node metadata and complete raw output are paired under logs
using each runtime prefix above. 58 new OD04 cases execute on all three runtimes.
Windows retains 10 inherited real file-link privilege skips; Linux retains only
two Windows-junction skips. Linux actually executes the original three file-link
security cases; Windows actually executes junction cases. New archive directory
escape tests use real junctions on Windows and real symlinks on Linux, zero new
skips. Existing tests were not changed, xfailed or suppressed.

Default APIs, exact corpus identities, synthetic parser schemas, SQL/Parquet clients,
orchestration and rights/transport/resource denials all regress unchanged. Opt-in
cache miss produces no legacy/archive directories or request. Read-only legacy
facade has LEGACY_UNVERIFIED, absent commit ID; dry-run mapping hashes exact local
bytes and never updates latest. No in-place data migration or official relabeling.
Byte identity and ISO UTC times are stable; cached/seed transport distinction
preserved. No locales/case/path semantics beyond actual runtime tests certified.

Windows 3.14 SQLite ResourceWarnings remain unsuppressed; exact counts in metrics.
No warning filters added. WSL inherited missing-drive PATH warnings retained,
not interpreted as failed tests or silently removed. WSL shares physical host;
this is OS filesystem/runtime evidence, not an independent physical-host/CI run.
'''
    write('06_cross_platform_and_compatibility.md',portability)

    write('07_security_and_rights_review.md','# Security, rights and financial integrity\n\n'+banner+'''Real source operations remain 13 PENDING_REVIEW / zero APPROVED. Real live source
count **0**. Source rights module/register and BLOCKED_EXTERNAL_EGRESS transports
unchanged. New service requires current STORE_RAW before mkdir/write and refreshes
before marker; source/transport/host/consumer checked. Replay checks READ_CACHED
before record access, source/date before object open, seed scope and current rights
again before return. Policy strings are evidence, not legal authority. Synthetic
approvals are fixtures only; no administrative records altered.

Archive success means exact captured bytes, never financial/official approval.
Mode has no OFFICIAL/RELEASE_APPROVED variant. Explicit SYNTHETIC_TEST_ONLY origin
cannot become provider provenance; cache/seed transports cannot become provider
observations. Original era/date/parser/state/policy refs retained. Structurally
valid state requires OD02 validation; HTTP_RECEIVED allows uninterpreted bytes but
not financial trust. published_at null; observed time not retroactive availability.
safe_url strips credentials/query/fragment and recognized path credential fields;
arbitrary unlabeled opaque secrets cannot be inferred. Code-only typed archive
errors do not print input paths or payloads.

Full existing rights/acquisition/offline-enforcement tests retained. Negative
tests for pending/missing/revoked rights before IO, consumer scope, revocation
before marker, malformed/duplicate/versioned metadata, object/link corruption,
traversal/drive/UNC inputs, real junction/symlink escape, source mode and bounded
disk/metadata/payload/entry limits execute. Fault injections use deterministic
ENOSPC/EACCES/EIO for hard-to-force conditions; not claims of actual full disk or
hardware power failure. Test namespaces trusted/private; no descriptor-atomic
hostile parent-swap claim. Kernel ownership/ACL hardening remains operational.

D01 signing custody and D04 release promotion P0 remain OPEN. D03 analytical
Parquet overwrite still OD10; OD04 only raw opt-in observations. Financial PIT,
adjustments, official-era reference authenticity and independent human security/
financial review remain pending. No release build, signer action, warehouse/DB
migration, live source, paid API, browser or later phase. No trade/profit claim.
''')

    metrics={'runtimes':{},'processes':{}}
    text='# Metrics and reproduction\n\n'+banner
    for r in RUNTIMES:
        raw=(LOGS/(r+'-full.txt')).read_text()
        warnings=raw.count('ResourceWarning: unclosed')
        metrics['runtimes'][r]={'resource_warnings_unclosed':warnings,'coverage':data(r+'-full-coverage')['totals'],
            'source_hashes':data(r+'-source')}
        text+=f"- {r}: **{warnings}** unclosed SQLite ResourceWarning lines (tracemalloc hints separate). [coverage JSON](logs/{r}-full-coverage.json); [source identities](logs/{r}-source.json); [environment](logs/{r}-environment.txt).\n"
    for mode in ['win','linux']:
        p=process(mode);metrics['processes'][mode]={'benchmark':p['benchmark'],'corpus':reference(mode)}
        b=p['benchmark']
        text+=f"\n## {mode} measured synthetic corpus\n\n{reference(mode)['observations']} committed observations / {reference(mode)['objects']} raw object files. Benchmark subset: six events / three objects (4096, 65536, 1048576 bytes), {b['logical_bytes']} logical file bytes including staging/links, {b['hardlink_unique_bytes']} bytes counting unique filesystem inodes. Payload sharing avoids a second object per duplicate event. No promised throughput/SLA.\n\n| Bytes | Put seconds | Verified read seconds | tracemalloc peak bytes |\n|---:|---:|---:|---:|\n"
        for row in b['larger_samples']:
            text+=f"| {row['bytes']} | {row['put_seconds']:.6f} | {row['verified_read_seconds']:.6f} | {row['peak_bytes']} |\n"
        text+=f"\nRecovery inventory seconds: {b['recovery_seconds']:.6f}. tracemalloc is Python allocation peak, not OS RSS/disk-allocation blocks; kernel/cache effects and small sample size prohibit comparative product-performance claims.\n"
    control.save('metrics.json',metrics)
    text+='''
Reproduction: use same installed runtime with explicit -B and this fresh runner,
sanitized copy and new unique label. `matrix.py` freezes five exact changed-file
hashes before collection and sequential commands. Never reuse labels (exclusive
log opens), install over original env, or use production roots. Exact expanded
argv/cwd/OS/UTC/exit is in per-command JSON; portable command forms:

```text
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest --collect-only -q -m 'not realdata'
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest -q <five targeted unit modules> -m 'not realdata'
<python> -B verification_runner.py <unique-label> <disposable-copy> pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
<python> -B verification_runner.py <unique-label> <disposable-copy> ruff check --no-cache src/omegadata tests scripts
<python> -B verification_runner.py <unique-label> <disposable-copy> mypy src/omegadata
<python> -B verification_runner.py <unique-label> <disposable-copy> pip check
<python> -B process_experiments.py <disposable-copy> <unique-label>
```

Explicit trusted process runner is separate from the subprocess-denying pytest
guard. Child commands/worker hashes/actual exits accompany process logs. Independent
measure_corpus.py uses stdlib hashes/length/link verification, no service under
test to derive expected identity. Source identity all final copies must match
current working files; remaining baseline source/config/tests match Git object
hashes except expected generated packaging metadata (not original package writes).

Retained failing attempts: four baseline reds, three later adversarial reds,
initial mypy eight typing errors (platform-conditional imports, shadowed type and
Literal annotation), two process-harness failures described above. All final
gates rerun after corrections with fresh labels. Earlier all-green intermediate
runs remain ARCH within this run when source changed, not substituted for final
hash identity. No fresh CI success or upstream dependency vulnerability clearance.
'''
    write('08_metrics_and_reproducibility.md',text)

    write('09_gatekeeper_verdict.md','# OD04 Gatekeeper: OD04_BLOCKED\n\n'+banner+'''**OD04_BLOCKED.** Implementation and executed final technical tests are green,
subject to passing final preservation/identity check. The mandatory Gate 2 ordering
was not fully followed: the entire A01–A28 negative-first tranche was not completed
before application implementation; process experiments and additional adversarial
tests were added afterward. Four genuine baseline failures and later red/green
corrections do not retroactively satisfy the stronger explicit chronology rule.
This is an execution-process failure, not an unavailable runtime or hidden skip.
No false PASS, backdated design/test run or invented import-error defect proof.

Executed technical acceptance: full SHA objects, separate same/different-byte events,
request/policy-aware idempotence, exclusive writes, marker-last visibility, five
forced-death/restart boundaries on each OS, threads and independent processes,
concurrent readers, corruption/JSON/version/path/link refusal, rights/consumer
scope and source-mode non-escalation, exact legacy facade/dry-run, deterministic
scan/replay and measured bounded corpus. Three runtime matrices full/targeted/
collection/Ruff/mypy/pip exit 0. [Complete A01–A28 matrix](03_negative_first_matrix.md)
and [mechanical preservation](logs/final-preservation.json) establish actual scope.

No required current filesystem case is hidden: old Windows privilege skips have
actual paired Linux execution; Windows junctions execute. New archive cases all
execute on both. Remaining limits explicitly allowed/deferred by design: no power
failure or hostile directory-owner race certification, no remote filesystem or
independent physical host/CI certificate. Read-only recovery inventory is not
verified count; scoped scan performs actual full-byte verification and refuses
mixed-source/date roots. No automatic repair/cleanup/migration.

AEF procedures were same-model: Maker design/candidate decision; Reviewer old-code
reproductions and later adversarial failures; Implementer bounded archive and
adapter; Gatekeeper exact exits, chronology conformance and preservation; Historian
all attempts retained. Independent stdlib comparator is executed but not independent
human consensus. No independent financial/legal/security signoff invented.

Release readiness remains BLOCKED independently of OD04: D01/D04 P0 OPEN, 13 real
source policies pending / zero approved, live sources zero, official truth pending.
Code remains optional/local/uncommitted. Do not integrate later production
capabilities on the strength of these tests. [Single next request](10_next_phase_request.md).
STOP after OD04; no OD05/10/11/14 or Git lifecycle action authorized.
''')
    write('10_next_phase_request.md','# Single scoped next approval request\n\n'+banner+'''Request owner review and a separately authorized **OD04 verification/remediation
follow-up**, preferably with an independent reviewer, before any OD05 approval.
Review the chronology deviation and exact bounded implementation; independently
reproduce the full acceptance matrix and adversarial storage threats, writing new
executable negative proofs before any further correction. Owner must explicitly
decide acceptance of the process deviation; a model cannot waive Gate 2 or rewrite
history to fix it. No new production source/policy/data/release/signing action.

This is one request, not automatic work. OD05, analytical OD10, signing/release,
browser/live acquisition, migration/cleanup, package/CI changes, commit/push/PR/merge
all require their own explicit authority. Existing data/evidence remain preserved.
''')

def final(reviewed=False):
    before=data('preservation-before');after=control.snapshot()
    changed=[p for p,v in before.items() if after.get(p)!=v]
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CHANGES}
    copies={r:data(r+'-source')==hashes for r in RUNTIMES}
    checks={r:{gate:data(r+'-'+gate)['exit_code'] for gate in ['collection','targeted','full','ruff','mypy','pip']} for r in RUNTIMES}
    process_checks={m:process(m)['passed'] and data('linux-process-persistent' if m=='linux' else 'win-process-accepted')['exit_code']==0 and
        process(m)['source_hashes']=={k:v for k,v in hashes.items() if k.startswith('src/')} and
        reference(m)['reference_verified_all_commits'] and reference(m)['observations']==18 and reference(m)['objects']==13 for m in ['win','linux']}
    git={name:subprocess.check_output(['git',*args]).decode().strip() for name,args in {
        'head':['rev-parse','HEAD'],'branch':['branch','--show-current'],'main':['rev-parse','main'],'index':['diff','--cached','--name-only']}.items()}
    from omegadata.track_a.source_rights import load_policy_register
    policies=load_policy_register().policies
    pending=len(policies)==13 and all(p.status.value=='PENDING_REVIEW' for p in policies)
    missing=[p for p in REQUIRED if not (HERE/p).is_file()]
    broken=[]
    for name in REQUIRED:
        for target in re.findall(r'\]\(([^)]+)\)',(HERE/name).read_text(encoding='utf-8')):
            if '://' in target:continue
            path=(HERE/target).resolve()
            if not path.exists() and path not in {(LOGS/'final-preservation-reviewed.json').resolve(),(LOGS/'final-preservation.json').resolve(),(LOGS/'implementation.patch').resolve()}:broken.append([name,target])
    patch=subprocess.check_output(['git','diff','--binary','--','src/omegadata/track_a/download_manager.py'])
    for name in CHANGES:
        if name=='src/omegadata/track_a/download_manager.py':continue
        patch+=''.join(difflib.unified_diff([], (ROOT/name).read_text().splitlines(keepends=True),fromfile='/dev/null',tofile='b/'+name)).encode()
    if reviewed:
        assert (LOGS/'implementation.patch').read_bytes()==patch
    else:
        with (LOGS/'implementation.patch').open('xb') as out:out.write(patch)
    preserved=changed==['src/omegadata/track_a/download_manager.py'] and all(copies.values()) and pending
    preserved=preserved and git=={'head':control.HEAD,'branch':'feature/od01-source-rights','main':'d4b5a58f0c50dc348e0d4e1150a725cc6fab5674','index':''}
    mechanical=preserved and not missing and not broken and all(v==0 for row in checks.values() for v in row.values()) and all(process_checks.values())
    result=dict(utc=datetime.now(UTC).isoformat(),original_records=len(before),original_changes=changed,
        unexpected_original_changes=[p for p in changed if p!='src/omegadata/track_a/download_manager.py'],
        git=git,source_hashes=hashes,tested_copies_match=copies,checks=checks,process_checks=process_checks,
        pending_sources=13 if pending else None,approved_sources=0 if pending else None,
        missing_reports=missing,broken_links=broken,mechanical_checks_passed=mechanical,
        signing='metadata unchanged only; contents never opened/hashed/copied',
        gatekeeper='OD04_BLOCKED',blocking_reason='Entire A01-A28 negative-first tranche not completed before implementation')
    control.save('final-preservation-reviewed.json' if reviewed else 'final-preservation.json',result)
    print(json.dumps(result,indent=2))
    return 0 if mechanical else 1

if __name__=='__main__':
    reports()
    raise SystemExit(final())
