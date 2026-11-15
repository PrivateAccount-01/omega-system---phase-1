"""Render dossier from actual machine evidence; exclusive new reports."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'
def read(name):return json.loads((LOGS/name).read_text())
def write(name,body):
 with (HERE/name).open('x',encoding='utf-8') as out:out.write(body.strip()+'\n')
HEADER='''OD04R_REVERIFY_AND_REMEDIATE_ONLY; run20261115T181120Z. Reviewed branch feature/od01-source-rights @44090a42958869faaab57a42b65f7ad8571d924d.

Evidence: RUN=current commands; ARCH=immutable historical records; TEST/SYN=synthetic fixtures; CLAIM=unreproduced external assertion; UNK=unknown. Same-model procedural review, no independent human/model signoff.
'''
def report(name,title,body):write(name,'# '+title+'\n\n'+HEADER+'\n'+body)
report('00_PREFLIGHT_AND_IDENTITY.md','Preflight and identity','''
Actual branch and starting HEAD exactly match the requested identities; both remain unchanged. Main remains d4b5a58f0c50dc348e0d4e1150a725cc6fab5674. Before edits tracked tree was clean; untracked .venv-linux, phase prompt and three signing-path items were already present. No reset/stash/checkout/index/commit/push/merge. [Initial status](logs/git-status.txt), [history](logs/git-history.txt), [main...HEAD comparison](logs/main-diff.txt), [final status](logs/final-status.txt). Main comparison was recorded after edits, but both commits were unchanged and main...HEAD excludes working edits.

Before application correction: full [preservation snapshot](logs/preservation-before.json), [exact Git-blob copy/47-fixture allowlist](logs/copy.json), [red source/test hashes](logs/red-source-identity.json), [prior accepted hash comparison](logs/accepted-old-identity-match.json), [design freeze](02_THREAT_MODEL_AND_CONTRACT.md) and asserted red run existed. This narrative report was assembled after verification; no claim it existed earlier. Five pre-edit working hashes match all prior accepted final source/test hashes. Initial red copy matches reviewed source.

Authorized changes: reproduced raw scan/inventory defects, read-only verifier semantics, one new test module and fresh evidence/helpers. Downloader unchanged. No config/policy/registry/dependency/ORM/Parquet/release/CI/signing change. Previous Gatekeeper ARCH OD04_BLOCKED; no owner exception.

Fresh clean rooms contain exact tracked src/scripts/tests/config plus README/pyproject; only 47 previously approved root fixture paths added after SHA match. No .env, environments, production DB, keys, releases or unknown raw directory copied. Fixture labels remain historical claims, not authenticated financial truth. [All 146 tested source/config/test files](logs/reviewed-final-tested-identities.json) match on all three copies; exact additional fixture list is in copy.json. Separate Windows3.14/Windows3.11/Linux copies prevent concurrent overlay races. Existing runtimes3.14.3/3.11.15/3.12.3 reused; no installs. [Runtime matrix](logs/current-runtime-matrix.json) records executable/OS/UTC/versions/packages/argv/cwd. Linux process roots are native persistent /home/parilrupani; pytest writes only disposable storage. Filesystem type is recorded only where actually probed; no remote/NFS or hardware durability certification.

[Preservation](logs/reviewed-preservation-comparison.json):12,137 original records compared; only two authorized application files differ. All old tests/evidence/data/DBs/releases/config bytes unchanged. Signing metadata unchanged; key contents never opened/hashed/copied. Pre-existing untracked environment contents were not exhaustively hashed; no command mutates them. The untracked phase prompt was read only. [Before/after ledger](logs/reviewed-before-after-file-ledger.json).
''')
old=read('prior-evidence-reconciled.json')
table=[]
for r in old['A01_A28']:
 nodes='; '.join('`'+n.split('::')[-1]+'`' for n in r['exact_function_token_nodes']) or 'Dedicated process/runtime/measurement evidence'
 table.append('| '+r['requirement']+' | '+r['requirement_text']+' | '+nodes+' | ARCH technical proof; chronology BLOCKED |')
report('01_PRIOR_EVIDENCE_INDEPENDENT_RECONCILIATION.md','Prior evidence reconciliation','''
Read all OD04 numbered00â€“10 reports, accepted source/runtime logs and relevant exact process/corpus output. [Machine reconciliation](logs/prior-evidence-reconciled.json) records raw/metadata SHA, actual exits/times/counts and corrected full node lists; [process history](logs/prior-process-reconciled.json) preserves accepted and superseded identities. No missing accepted raw log or mismatched accepted source identity observed.

| Subject | Supported | Unverified | Contradicted |
|---|---|---|---|
| Identities | Five prior final working hashes match reviewed checkout; all accepted platform overlays match final preservation | Immutable upstream/dependency checkout identity | None |
| Prior totals | ARCH Win451pass/10skip/4deselected; Linux459/2/4; targeted340/10 versus348/2; accepted exits0 | Independent physical-host CI | Skips cannot count as pass |
| Gate2 chronology | Four old-storage reds plus three later isolated reds recorded | Complete pre-core A01â€“A28 execution | Full ordering NOT satisfied; OD04_BLOCKED remains |
| A25 attribution | Actual Windows/Linux process/platform logs exist | Object-model test cannot prove OS execution | sha256 parameter falsely matched a25 substring |
| Grouped nodes | Actual assertions plus process logs support bounded invariants | Every grouped parameter proving every named ID | Some per-parameter attribution overbroad |
| Linux corpus | Persistent18/13 plus missing-root negative is accepted proof | Hardware/NFS durability | Earlier transient0/0 success was vacuous, excluded |
| Current CI | Connector statuses[] and PR-workflow_runs[] | First-page PR filter is not exhaustive all-events absence proof | No CI validates local corrections |

A07/A08/A10/A11/A21 additionally require process logs; A25 platform/filesystem records; A26/A27 full/collection/static/package commands; A28 actual local measurements. Corrected exact-function attribution below avoids matching parameter text. No row means retroactive negative-first compliance.

| ID | Requirement | Actual function-token nodes | Status |
|---|---|---|---|
'''+ '\n'.join(table)+'''

Historical d24e9c... is the pre-edit OD04 Git baseline; final overlays identify the code subsequently committed at44090a.... [Historical Gatekeeper](../../od04/20261115T124835Z/09_gatekeeper_verdict.md) is immutable. Current RUN proof is separately executed; ARCH is never promoted by paraphrase.
''')
report('04_CODE_REVIEW_AND_MINIMAL_DIFF.md','Code review and minimal diff','''
Maker/Design Reviewer froze02 before edits. Implementer corrected only after eight existing-behavior assertion failures. Code Reviewer inspected complete raw archive, downloader, acquisition, source-rights, policy, verifier/dry-run and storage paths, inherited tests and exact [application patch](logs/application.patch). Gatekeeper/Historian reconcile commands, identities and preservation. All roles are the same model.

Reproduced defects: vacuous successful scans of absent/empty/incomplete or invalid directory namespaces, and silently suppressed directory traversal error. _inventory now raises INTEGRITY on os.walk errors, preventing incomplete inventory from silently bypassing resource accounting. Missing-root recover_staging remains an explicitly UNVERIFIED read-only inventory; it is not archive completeness proof.

Strict scan checks safe directory roots/namespaces before/after inventory and after replay; missing root NOT_FOUND, invalid layout INTEGRITY, zero default evidence EMPTY_ARCHIVE. Additive strict nonnegative expected_count gives COUNT_MISMATCH when separately pinned count differs; expected0 permits only a pristine existing empty directory. Nonempty default verifies discovered committed snapshot, not exhaustive historical completeness. Output is versioned raw-verification/v2. On-disk object/observation/commit v1 and pinned replay unchanged; no migration. CLI ALL propagates optional count; non-ALL misuse rejects. Existing v1 scan clients must explicitly handle v2 and refusal; no silent compatibility downgrade.

| Component | Current review / proof |
|---|---|
| Frozen request/object/observation/commit | Extra-forbid, revalidated models; known source/era/date/UTC/ID/path/hash/length; no synthetic origin escalation; legal decision strings are consistency, not human attestation |
| put | Validate request and STORE_RAW; validate claimed structure; kernel+thread lock; full request/bytes/current-policy idempotence; bounded reservation; exclusive stage/object/observation then final policy refresh/marker-last verification |
| _publish | fsync stage, full hash check, exclusive hardlink, existing-byte equality, POSIX directory sync; no Windows directory-fsync/hardware-loss promise |
| _verified/read_verified | Current rights/purpose before IO and after replay; source/date before bytes; seed scope; JSON/schema/observation hash/object length+full hash and commit references checked |
| recover_staging | Bounded inventory, no promotion/deletion, marker count explicitly UNVERIFIED; retained stages consume quota |
| scan_verified | R01 v2 correction; mixed namespace refuses instead of silently omitting; external expected-count optional |
| DownloadManager | Opt-in archive injection preserved; legacy cache LEGACY_UNVERIFIED; cache-only miss no fetch; rights rechecks; ArchiveError propagates; unchanged legacy/default paths |
| acquisition/source_rights | Bounded strict validation, denial terminal, redirects disabled, external egress disabled; no edits |
| legacy script/storage | Dry-run reads/hashes without import/write/relabel; known fixed Parquet overwrite remains OD10 |

Only raw_archive.py and verify_raw_archive.py application edits; one new27-case test module. Initial red18-case bytes later reconstructed exactly after helper formatting/additional positives, SHA matched to frozen pre-edit ledger in [red-test-exact.py](logs/red-test-exact.py). Nine later controlled-positive/counterexample cases are not labeled pre-fix reds. Initial lint preview failed on dict style in the new test helper; formatting corrected, assertions unchanged. Old tests untouched. [Ledger](logs/reviewed-before-after-file-ledger.json), [complete tested identities](logs/reviewed-final-tested-identities.json). New critical guard/count/walk lines all execute under coverage; older rare IO/lock/model branches remain partial and reported. Rollback in08; no code migration/GC.
''')

report('05_PROCESS_CRASH_AND_INDEPENDENT_ORACLE.md','Crash, concurrency and independent byte oracle','''
Reused audited worker/guard architecture with fresh disposable roots and exact launcher logs. Parent allows only issued exact worker argv; children deny DNS/TCP/UDP/process and protected writes. Four guard-negative probes per OS succeed. This protects against accidental side effects, not arbitrary malicious Python. [Windows result](logs/win-process-result.json), [Linux result](logs/linux-process-result.json) retain executable/platform/UTC/duration/PID/exits/raw output, worker hashes and both application source hashes. Source code did not change after these experiments; subsequent changes added tests only.

| Process proof | Windows3.14.3 | Linux3.12.3 |
|---|---|---|
| Same bytes | 3writers,3events/1object, concurrent reader | Same |
| Different bytes | 3writers,3events/3objects, concurrent reader | Same |
| Conflicting ID | Two workers, exactly one0 and one2 | Same |
| Forced crash boundaries | All5, killed exit1, no marker, fresh-process retry succeeds | All5, killed exit-9, no marker, retry succeeds |
| Independent corpus | 18observations/13objects | 18observations/13objects |
| Oracle order | Missing1 then positive0; moved-old-root1 then moved-positive0 | Same |

Readers verify three committed payloads each; paused-publication unit tests also prove NOT_COMMITTED until complete. Five crash points: before_stage,after_stage,after_object,after_observation,before_commit. Existing bytes remain; retained staging is not promoted/deleted. Recovery inventory for same namespace reports3markers explicitly UNVERIFIED; independent byte oracle supplies trust. Killed/losing/negative exits are expected experiments, never pytest successes.

[Independent oracle](independent_oracle.py) uses stdlib and imports no archive code. Counts and payloads are separately pinned, never read from service inventory: same3/1,different3/3,conflict1/1,five crashes each1/1,benchmark6/3. Every full SHA/size, canonical marker/observation bytes, duplicate-key refusal, operation/file/observation identity, raw observation SHA/commit link, content-derived object path and source/date checked. All modes SYNTHETIC_TEST_ONLY; published_at null and SOURCE_REFERENCE_PENDING. Conflict winner may be either of two known frozen candidates; no fabricated deterministic winner.

First missing-root negative runs before positive assertions. Then only each run's exact recorded disposable corpus is moved after absolute parent/prefix/destination checks; old path must fail and new path independently verify18/13. [Windows moved positive](logs/win-oracle-moved-positive.txt), [Linux moved positive](logs/linux-oracle-moved-positive.txt), corresponding negative and relocation argv/UTC/exits retained. No old/source-data root moved. Native Linux /home corpus survives separate WSL launches; no vacuous transient/tmp result accepted.

Local measurements include4KiB/64KiB/1MiB put/read/recovery time, tracemalloc, logical retained bytes and hardlink-aware inode bytes in process JSON. Single synthetic local samples, no p95/third-party speedup claim. Hardlink versus kernel-lock/rename pilots are feasibility controls; rename pilot is not adopted as an alternate transaction engine. No physical-host, hardware power-loss, Windows directory-fsync, NFS or hostile-owner guarantee.
''')

runtime_rows=[]
for r in read('reviewed-current-runtime-matrix.json'):
 c=r['commands'];t=c['targeted']['counts'];f=c['full']['counts']
 runtime_rows.append(f"| {r['label']} | {c['full']['python'].split()[0]} | {t['passed']}/{t.get('skipped',0)} | {f['passed']}/{f.get('skipped',0)}/{len(c['full']['deselected'])} | all0 | {r['coverage']['percent_covered']:.4f}% | {r['archive_coverage']['percent_covered']:.4f}% | {r['sqlite_resource_warning_lines']} |")
report('06_CROSS_PLATFORM_REGRESSION.md','Complete offline runtime matrix','''
All required commands actually executed. [Machine matrix](logs/reviewed-current-runtime-matrix.json) retains exact absolute executable/argv/cwd/OS/UTC/duration/actual exits/raw references and skips; per-node raw JSON remains authoritative. [All146 tested source/config/test identities](logs/reviewed-final-tested-identities.json) match. Second reviewed matrix includes27new tests; earlier final matrix includes20 and is retained, not overwritten. No application code changed between these matrices.

Full selected denominator488, total492 including4realdata deselected. Windows478pass+10skip=488; Linux486+2=488. Targeted denominator377. Collection covers all offline unit/integration tests, not only archive files.

| Runtime | Python | Targeted pass/skip | Full pass/skip/deselected | Collection,targeted,full,ruff,mypy,pip exits | Whole combined line/branch | Archive combined | SQLite warning lines |
|---|---|---|---|---|---|---|---|---|
'''+ '\n'.join(runtime_rows)+'''

Ruff checks --no-cache src/omegadata tests scripts; mypy strict49source files; pip check no broken requirements. Existing exact installed distributions recorded, no installs/locks/CI modifications. No online advisory/CVE clearance claimed. Editor Problems checked; git diff --check0. Initial lint preview1 found new helper dict style and was corrected. Display-only PowerShell ConvertFrom-Json failed on coverage property names; actual coverage JSON was successfully read using Python. First reconciliation helper failed on Windows3.11 backslash coverage paths; fixed only helper normalization and successful exclusive reconciliation recorded. An oversized report-authoring shell command was rejected before execution; switched to direct patches. All are harness/report issues, not application reds.

Ten Windows file-symlink privilege skips are matched by exact passing Linux nodes. Two Linux Windows-junction skips pass on Windows. [Dedicated actual-symlink run](logs/linux312-symlink-proof.json) passes9selected cases; all3original file-link cases actually execute, observed links true and outside reads0. No skip counted as pass. Four realdata deselections preserved. Existing SQLite warnings are retained P2, no suppression. WSL stale D/G PATH warnings retained.

Whole and archive coverage are compared with prior accepted measured coverage; newly critical scan/root/count/walk-error lines execute. Old rare IO/model/lock branches remain partial, not100% coverage. Guard negatives execute for DNS/TCP/UDP/subprocess/protected-write, including Linux dir_fd paths. Tests do not authenticate official source/financial truth.

[CI observation](logs/ci-observed.json): reviewed-SHA statuses[] and first-page PR-workflow_runs[]; no successful feature-SHA CI observed. Query limitation prevents universal all-events absence claim. No CI validates local uncommitted corrections. WSL is the same physical host.
''')

report('07_RIGHTS_SECURITY_AND_REUSE_DECISION.md','Rights, security and repository-first reuse','''
[All13real policies](logs/production-policy-status.json) remain PENDING_REVIEW,0APPROVED with empty operations. Unchanged source registry/config SHA; fixture approval providers are injected only in protected tests. READ_CACHED/purpose before IO and after replay; STORE_RAW refreshed before marker; seed scope distinct. Unknown/missing/revoked/nested malformed/scope cases refuse. Real HTTPX/urllib/curl egress remains BLOCKED_EXTERNAL_EGRESS. No provider, broker, paid service or scraping.

Financial boundary: byte hash is not exchange authenticity, availability time, economic correctness or trading suitability. All corpus payloads synthetic, published_at null, SOURCE_REFERENCE_PENDING. Historical official fixture labels are not promoted to RUN financial references; source-era hypotheses need future separately authorized evidence.

Reopened [exact prior reuse decision](../../../decisions/od04-raw-archive-reuse.md). KEEP existing stdlib wrapper, Pydantic, rights/acquisition contracts and opt-in downloader: fresh crash/concurrency/integrity evidence supports required raw storage capabilities without a new engine. Raw immutable byte observations are distinct from mutable analytical/lakehouse tables.

| Candidate | Repository/pin/license primary source | Relevant scope and decision |
|---|---|---|
| Python stdlib | Existing3.14.3/3.11.15/3.12.3; hashlib/pathlib/json/os.link/fcntl/msvcrt | KEEP: small rights intercept, exclusive commit, bounded local recovery; local tests only, trusted filesystem |
| DVC | [repository](https://github.com/iterative/dvc), [3.59.2license](https://raw.githubusercontent.com/iterative/dvc/3.59.2/LICENSE) | DEFER: version/cache capability relevant; observation/rights wrapper still needed; extra package/operations, no demonstrated gap requiring adoption |
| delta-rs | [repository](https://github.com/delta-io/delta-rs), [python-v0.25.0license](https://raw.githubusercontent.com/delta-io/delta-rs/python-v0.25.0/LICENSE.txt) | DEFER: analytical table transactions do not replace raw observations/rights; native/table migration burden |
| lakeFS | [repository](https://github.com/treeverse/lakeFS), [v1.48.0license](https://raw.githubusercontent.com/treeverse/lakeFS/v1.48.0/LICENSE) | DEFER: object version administration adds service/storage operations without a local-byte necessity |
| PyArrow | [repository](https://github.com/apache/arrow), [apache-arrow-23.0.1license](https://raw.githubusercontent.com/apache/arrow/apache-arrow-23.0.1/LICENSE.txt) | KEEP unchanged existing analytical dependency23.0.1; DEFER raw transactional role; columnar tables separate contract |

RUN web tool reopened all four exact tag-specific license files: Apache-2.0, Arrow also third-party notices. Exact upstream commit pins UNK; tags are not immutable checkouts. No cloning/install/third-party engine tests. License-family identification is not transitive/legal/advisory clearance. Current runtime/platform support and third-party benchmark results UNK; no unsupported popularity/speed claim. Local stdlib pilots measure only synthetic put/read/recovery/tracemalloc/retained inode bytes. Web access limited to upstream license references and read-only GitHub CI connector, never market endpoints.

Pytest guard denies DNS/TCP/UDP/process/protected writes during collection/execution; dedicated process guard only admits exact issued disposable workers. Linux descriptor-relative writes checked using /proc/self/fd; static/package commands do not run app jobs. Signing bytes never read. Guards are not malicious-code/hostile-owner sandboxes. D01/D04 P0 signing/release findings and deferred analytical defects remain. No source approval, signing, release or OD05 authority.
''')

categories=[
('R01','Vacuous completeness','old nonempty scan test only','new test_r01_*; missing/moved independent oracle','8 asserted reds;7 API errors excluded','v2 root/count and walk-error guards','missing/moved1,positive0'),
('R02','Lost equal-byte events','test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay','test_r18_independent_link_oracle_and_missing_object','unchanged positive; no defect','none','same3events/1object'),
('R03','Version overwrite','test_a01_a02_a03_a23_exact_bytes_events_and_historical_replay','pinned independent raw byte inputs','not reproduced','none','different3events/3objects'),
('R04','Changed retry semantics','test_a04_a05_idempotence_conflict_and_frozen_models;test_a04_policy_identity_change_is_not_idempotent','same frozen request; conflicting candidates','not reproduced','none','one0,one2'),
('R05','Stale rights/revocation','test_a16_revocation_at_commit_boundary;test_a16_read_consumer_scope_enforced;test_a16_explicit_revoked_or_missing_before_io','fresh policy-denial assertions and real-register SHA','not reproduced','none','no marker after refusal'),
('R06','Crash partial success','test_a06_a07_a08_fault_boundaries_recover_without_promoting','forced death at5points plus raw retry oracle','not reproduced','none','5perOS'),
('R07','Cross-process corruption','test_a09_a21_thread_writers_and_reader;old workers','fresh independent OS processes','not reproduced','none','same,different,conflict'),
('R08','Partial trusted reads','test_a21_reader_during_publication','concurrent readers with3writers','not reproduced','none','2readers perOS'),
('R09','Wrong-size prior object','test_a12_a14_corruption_refuses','test_r09_existing_wrong_size_object_refuses_without_overwrite','passes unchanged; no defect','none','full byte/hash oracle'),
('R10','Malformed/versioned JSON','test_a12_a14_corruption_refuses','strict unique-key canonical raw oracle','not reproduced','none','canonical links'),
('R11','Links/traversal/IDs','test_a13_real_directory_link_escape;OD01R/OD02V link tests','actual Linux file links,Windows junctions','not reproduced','none','trusted owner boundary'),
('R12','IO false success','test_a20_storage_faults_typed_no_success;five fault boundaries','test_r12_marker_link_failure_preserves_existing_evidence','controlled positive; no defect red','none','crashes,old bytes retained'),
('R13','Retained-stage budget bypass','test_a19_metadata_and_entry_budget;test_a19_payload_and_total_budget','test_r13_retained_stage_accumulation_is_bounded_read_only','later counterexample passes; no defect','none','retained stage logical quota'),
('R14','Origin escalation','test_a15_synthetic_cannot_be_relabelled;OD02 cache/seed tests','test_r14_r15_invalid_contract_before_io;18synthetic modes','later counterexamples pass','none','no authenticity upgrade'),
('R15','False era/parser/date/source','test_a24_structural_state_requires_actual_validator;OD02 validators','test_r14_r15_invalid_contract_before_io;test_r15_source_mismatch_refuses;test_r18_namespace_mixing_refuses','later counterexamples pass','none','pinned source/date'),
('R16','Token leakage','test_a22_url_confidentiality_and_a24_policy;OD02V v04','fresh synthetic secret-marker assertions','not reproduced','none','URL redaction'),
('R17','Legacy relabel/overwrite','test_a17_legacy_facade_is_read_only;test_a18_dry_run_migration_and_cli_verifier','before/after fixture bytes and rights refusals','not reproduced','none','legacy unchanged'),
('R18','Vacuous recovery oracle','test_a12_a23_scan_is_read_only_deterministic_and_refuses_corruption','test_r18_*;independent_oracle pinned18/13','3initial unchanged positives;R01 separate','R01 scan only','missing-first,moved-first thenpositive')]
columns=['requirement','defect_suspicion','original_test_identity','fresh_independent_oracle','new_red_status','minimal_change','Windows314','Windows311','Linux','process_proof','unresolved_uncertainty','Gatekeeper']
rows=[];machine=[]
for rid,susp,orig,oracle,red,change,process in categories:
 vals=[rid,susp,orig,oracle,red,change,'PASS RUN','PASS RUN','PASS RUN',process,'trusted local only;official truth/CI UNK','technical pass;owner exception pending']
 rows.append('| '+' | '.join(vals)+' |');machine.append(dict(zip(columns,vals)))
with (LOGS/'R01-R18-test-matrix.json').open('x') as out:json.dump(machine,out,indent=2)
report('03_NEW_RED_GREEN_TEST_MATRIX.md','Fresh negative-first and adversarial matrix','''
[Initial red](logs/win314-red.json) exit1:18cases,15failed/3passed. Exactly8 DID NOT RAISE failures prove existing behavior: six absent/empty/incomplete/invalid-layout cases, post-inventory directory move and suppressed walk error. Seven expected_count TypeErrors are additive missing-API contract failures, NOT defect proof. Three independent unchanged-code counterexamples pass: wrong-size preexisting object, missing-object/commit-link integrity and mixed-date refusal. [Classification](logs/red-classification.json), [frozen identities](logs/red-source-identity.json), [exact initial bytes](logs/red-test-exact.py).

After minimal correction, focused old+new archive run76pass/0skip/exit0. Final new module27cases comprises18initial plus9later controlled positives/counterexamples: marker-specific IO and CLI, five invalid model variants, source mismatch and retained-stage accumulation. All later counterexamples pass without further application changes. Final old+new archive subset85passes; all27new and58old cases pass in every current full/targeted suite. No old test edited; no API/import failure counted as genuine red; no claim that later positives existed pre-fix. Source identity current proof is the second reviewed matrix; first20-case run retained.

| Requirement | Defect suspicion | Original test identity | Fresh independent oracle | New red status | Minimal change | Windows3.14 | Windows3.11 | Linux | Process proof | Unresolved uncertainty | Gatekeeper |
|---|---|---|---|---|---|---|---|---|---|---|---|
'''+ '\n'.join(rows)+'''

Machine [R01â€“R18 matrix](logs/R01-R18-test-matrix.json) and full [per-environment evidence](logs/reviewed-current-runtime-matrix.json). Source/date/purpose mismatches, nested policy model/status checks, unknown source, mixed archive namespaces, initialized empty/orphan roots, duplicate JSON/commit identity and negative attempts use explicit new/inherited assertions. Grouped IDs do not mean every parameter proves every named invariant. Separate process proof is never added to pytest totals.
''')

report('08_REMAINING_DEFECTS_AND_ROLLBACK.md','Remaining limitations and rollback','''
| Severity | Remaining status |
|---|---|
| P1 process acceptance | Full historical A01â€“A28 negative-first ordering not met; human exception NO, never repaired retroactively |
| Current scoped archive | Reproduced R01/traversal suppression fixed; no uncorrected high-severity defect observed within executed trusted-local boundary |
| P2 compatibility | Scan v2 changes empty/missing success into refusal; existing consumers must handle v2 and explicit independently pinned expected_count; on-disk formats unchanged |
| P2 operation bounds | Retained staging consumes bounded quota; no GC approved. Count-match does not authenticate provenance or ensure external historical completeness |
| P2 warnings | Existing disposable SQLite cleanup ResourceWarnings retained; no production DB touched |
| UNK | Hostile concurrent owner swap, hardware power-loss,NFS,Windows directory fsync, independent physical host/CI, official source truth, comprehensive advisory clearance |
| Inherited P0/P1 | Signing/release-export blockers, fixed analytical Parquet overwrite/current-state knowledge and financial-reference gaps remain outside scope |

Rollback plan only, not executed: freeze/review [patch](logs/application.patch) and [hash ledger](logs/reviewed-before-after-file-ledger.json); pause strict-scan consumers. After explicit owner approval, restore only two application files from reviewed44090a... with current-hash checks and no overwrite of intervening user edits. Keep all new tests/evidence as audit history. Reverting reintroduces vacuous verification, so empty/missing scans must remain administratively blocked if rollback is chosen. No reset/clean, history rewrite, data deletion, stage promotion, GC, migration or policy rollback. Disable optional archive injection for approved legacy facade if needed; retain every raw object/observation/marker and historical release. No rollback performed.

[Preservation](logs/reviewed-preservation-comparison.json) compares12,137 originals; only authorized two application paths differ. Old tests/evidence/data/DBs/releases/config unchanged, signing metadata only unchanged. Local changes remain unstaged/uncommitted; commit/push requires a separate instruction. No source enablement, signing, publication, merge or later phase.
''')
report('09_GATEKEEPER_VERDICT.md','Gatekeeper verdict','''
**OD04R_TECHNICALLY_REVERIFIED_PROCESS_EXCEPTION_PENDING**

Current technical gates pass: requested branch/HEAD; eight genuine red-first existing-behavior failures before minimal correction;27new and58old archive cases pass; complete collection/targeted/full/lint/type/dependency verification on Windows3.14.3,Windows3.11.15,Linux3.12.3. Exact skip nodes paired on other OS; dedicated actual Linux file-link evidence. Fresh independent-process readers/writers/conflict plus5forced crashes per OS; missing/moved expected-root refusal and independent pinned18observations/13objects byte/hash/length/canonical-link/input oracle. Complete tested source identities match;12,137 original records preserved except two authorized application paths;13real policies pending.

Full results: Windows478pass/10skip/4deselected each; Linux486pass/2skip/4deselected. Targeted367/10 versus375/2. All final acceptance command exits0. Oracle negatives1, killed children1/-9 and conflict loser2 are expected refusals. Initial red15fail/3pass includes only8genuine assertion defects;7missing additive API errors excluded. Initial lint/helper/report issues retained and distinguished; no hidden skips/warning suppression. [Runtime matrix](06_CROSS_PLATFORM_REGRESSION.md), [new matrix](03_NEW_RED_GREEN_TEST_MATRIX.md), [process proof](05_PROCESS_CRASH_AND_INDEPENDENT_ORACLE.md), [identities](logs/reviewed-final-tested-identities.json), [preservation](logs/reviewed-preservation-comparison.json).

Historical OD04_BLOCKED remains immutable. Complete original Gate2 chronology NOT met. No named accountable human supplied an exception; this execution prompt does not grant it. Same-model Makerâ†’Design Reviewerâ†’Implementerâ†’Code Reviewerâ†’Gatekeeperâ†’Historian is procedural review, not independent human/security/financial signoff. [Owner decision](10_OWNER_EXCEPTION_DECISION_REQUEST.md) remains open.

No CI validates local uncommitted changes; WSL is same physical host. Trusted-filesystem, partial coverage and provenance limitations remain in07/08. This is not live-source/release/trading certification. No source approval, signing, publication, merge, commit/push, real acquisition or OD05/other later phase performed. Stop after OD04R.

Valid only with [fresh final mechanical acceptance](logs/final-acceptance.json) checking reports/links, exact identities, preservation, policy counts and actual command exits. Mechanical pass cannot grant a human exception or later-phase approval.
''')
report('10_OWNER_EXCEPTION_DECISION_REQUEST.md','Owner exception decision request â€” pending','''
Named accountable human owner: NOT PROVIDED. Exception approved: **NO**. Approval reference/rationale/date: NONE. Do not auto-fill or construe this review request as acceptance.

Single next action: human project owner reviews the dossier and explicitly decides whether to accept the historical OD04 Gate2 ordering deviation for reviewed44090a42958869faaab57a42b65f7ad8571d924d plus exact remediation hashes in [ledger](logs/reviewed-before-after-file-ledger.json), run20261115T181120Z. Record named owner, actual decision, rationale, acknowledged chronology/residual filesystem/provenance/security/CI risks and exact reviewed code/run identities. Independent human/security review is advisable before acceptance; same-model roles/green tests do not substitute.

Acceptance would cover the past ordering deviation only; it would not relabel historical OD04 as PASS, approve source rights, enable collection, certify releases/signing, authorize merge or grant OD05. Rejection retains the blocker. No acceptance was generated here.

OD05 is prospective planning context only: independently authorized historical-era reference documents/corpora and deterministic parser/provenance work. Inherited NSE2020/BSE variants remain hypotheses, not official truth. OD05 requires a separate explicit user instruction after owner disposition. No implementation started.
''')
print('Wrote ten exclusive reports; retained pre-edit02 unchanged.')
