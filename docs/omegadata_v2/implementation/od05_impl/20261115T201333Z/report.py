"""Generate fresh OD05 dossier from executed evidence, never author owner approval."""
import ast
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import control

HERE, LOGS, ROOT = control.HERE, control.LOGS, control.ROOT


def load(name):
    return json.loads((LOGS/name).read_text(encoding='utf-8-sig'))


def write(name, body):
    with (HERE/name).open('x',encoding='utf-8') as out:
        out.write(body+'\n')


def save(name, body):
    with (LOGS/name).open('x',encoding='utf-8') as out:
        json.dump(body,out,indent=2)


labels=['win314-accepted','win311-accepted','linux312-accepted']
matrices={label:load(label+'-matrix.json') for label in labels}
assert all(not any(m['results'].values()) for m in matrices.values())
freeze=load('final-source-freeze.json')['files']
for p,digest in freeze.items():
    assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest
    assert all(m['files'][p]==digest for m in matrices.values())
# Check every command's actual pre-command inputs, not only an end-of-run hash.
for label,m in matrices.items():
    for command in m['results']:
        inputs=load(label+'-'+command+'-inputs.json')
        assert all(inputs[p]==digest for p,digest in freeze.items())
baseline=next(iter(matrices.values()))['files']
assert all(m['files']==baseline for m in matrices.values())
preservation=load('preservation-comparison.json')
assert not preservation['unexpected_original_changes']
assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()==control.HEAD
assert not subprocess.check_output(['git','diff','--name-only'])
assert not subprocess.check_output(['git','diff','--cached','--name-only'])
policy=json.loads((ROOT/'config/source_rights_policy.v1.json').read_text())
assert len(policy['policies'])==13 and all(p['status']=='PENDING_REVIEW' for p in policy['policies'])

full={label:load(label+'-full.json') for label in labels}
pairings=[]
for label,run in full.items():
    for skipped in [r for r in run['test_reports'] if r['outcome']=='skipped']:
        peers=[other for other,record in full.items() if other!=label and any(
            r['nodeid']==skipped['nodeid'] and r['when']=='call' and r['outcome']=='passed'
            for r in record['test_reports'])]
        assert peers, skipped['nodeid']
        pairings.append({'runtime':label,'nodeid':skipped['nodeid'],'reason':skipped['reason'],'passed_on':peers})
save('skip-pairing.json',pairings)

table=['| Runtime | Full passed/skipped/deselected | Targeted passed/skipped | New cases | Total coverage | Parser coverage | Exits |',
       '|---|---|---|---|---|---|---|']
quality=[]
for label,run in full.items():
    targeted=load(label+'-targeted.json')
    coverage=load(label+'-full-coverage.json')
    parser_files={p:v for p,v in coverage['files'].items() if '/parsers/' in p.replace('\\','/')}
    covered=sum(v['summary']['covered_lines']+v['summary']['covered_branches'] for v in parser_files.values())
    total=sum(v['summary']['num_statements']+v['summary']['num_branches'] for v in parser_files.values())
    new=[r for r in run['test_reports'] if 'test_od05_era_parsing.py::' in r['nodeid'] and r['when']=='call']
    assert len(new)==94 and all(r['outcome']=='passed' for r in new)
    skipped=sum(r['outcome']=='skipped' for r in run['test_reports'])
    target_skipped=sum(r['outcome']=='skipped' for r in targeted['test_reports'])
    row={'runtime':label,'python':run['python'],'platform':run['platform'],
         'passed':run['call_counts']['passed'],'skipped':skipped,'deselected':len(run['deselected']),
         'new_cases_passed':len(new),'targeted_passed':targeted['call_counts']['passed'],
         'targeted_skipped':target_skipped,'combined_coverage':coverage['totals']['percent_covered'],
         'parser_combined_coverage':covered/total*100,
         'elapsed_seconds':run['elapsed_seconds'],'command_exits':matrices[label]['results']}
    quality.append(row)
    table.append(f"| {label} | {row['passed']}/{skipped}/{row['deselected']} | {row['targeted_passed']}/{target_skipped} | 94 PASS_SYNTHETIC | {row['combined_coverage']:.4f}% | {covered/total*100:.4f}% | all 0 |")
save('accepted-runtime-matrix.json',quality)
matrix_table='\n'.join(table)
test_source=(ROOT/'tests/unit/test_od05_era_parsing.py').read_text()
functions=[node.name for node in ast.parse(test_source).body if isinstance(node,ast.FunctionDef)]
groups={f'T{n:02}':[name for name in functions if name.startswith(f'test_t{n:02}_')] for n in range(1,33)}
assert all(groups.values())
group_results={}
for group,names in groups.items():
    group_results[group]={'test_ids':names,'synthetic':'PASS_SYNTHETIC',
        'official_subcase':'BLOCKED_REFERENCE' if group in {'T04','T05','T06','T07','T09','T15','T19','T21','T31'} else 'NOT_APPLICABLE_WITH_REASON: generic software invariant, no official certification',
        'baseline':'NEW_API_ABSENT, no old-behavior assertion defect proved',
        'fresh_results':{label:[r for r in record['test_reports'] if any('::'+name in r['nodeid'] for name in names)]
            for label,record in full.items()}}
save('32-group-results.json',group_results)
save('input-identity-comparison.json',{'all_runtime_inputs_equal':True,'frozen_source_test_files':freeze,
    'all_precommand_manifests_match':True,'shared_files_compared':len(baseline)})

header=f'OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY; run 20261115T201333Z. Evaluated {datetime.now(UTC).isoformat()}. Branch feature/od01-source-rights; unchanged local HEAD {control.HEAD}. RUN=new executed checks; TEST/SYN=synthetic fixtures; ARCH=prior evidence; UNK=unverified official semantics. Same-model procedural review, not independent human/financial/legal certification.\n\n'

write('00_authorization_and_branch_identity.md',header+'''# Human-supplied entry authority

G0: ACCEPT_EXCEPTION. Human user attests identity Paril, role Admin, decision date 16-11-2026. Direct task conversation is the supplied owner channel; no independent identity-provider validation or signature is claimed. Do not use the earlier conditional 15-11-2026 G0 date. Exact time of human decision was not supplied; no time is invented. UTC run directory date 2026-11-15 corresponds to local 2026-11-16 Asia/Kolkata; reports retain actual later generation timestamps.

User-supplied rationale: OD04R recorded cross-platform regression, integrity, concurrency, crash recovery and independent stored-artifact checks. The remaining historical deviation is the original test ordering rather than a reproduced unresolved defect within tested scope. Owner accepts the process exception only to permit controlled continuation, retaining findings and evidence and without waiving security, rights, financial, signing or production-release requirements.

Reviewed identities: OD04 44090a42958869faaab57a42b65f7ad8571d924d; OD04R bbc38716d902fe27192f80affaca29c6f51e9890; run 20261115T181120Z and its Gatekeeper/source-hash/verification evidence, identified in the user's preceding decision text. Human attestation completing both clauses: “i (Paril) confirm and continue now”. This records supplied authority; it is not an agent-authored decision or a retroactive change to the old Gatekeeper.

G1: previously explicit ACCEPT_EXCEPTION and AUTHORIZE selections, followed by stated AUTHORIZE_OD05_SYNTHETIC_PARSER_IMPLEMENTATION_ONLY and final owner attestation. Scope is the handoff at bf6f489: new pure parser package, new tests/helpers and fresh evidence only, disposable offline tests. Original G1 form included 15-11-2026; effective final attestation followed the clarified G0 date. No precise G1 timestamp is certified.

G2: synthetic-only scope approved; official formats remain SOURCE_REFERENCE_PENDING. No real source approvals, production routing, historical mutations, database migration, signing, releases, paid services, merges or later phases. No commit/push authorized by this implementation request.

Initial worktree: only pre-existing Linux environment, handoff Markdown and three private/revocation signing entries untracked. Current original tracked worktree/index clean. Only phase-owned new paths were written. [Preservation comparison](logs/preservation-comparison.json) and [final source identities](logs/final-source-freeze.json). Private signing contents never opened/hashed/copied; existing helper compares metadata only. No environments installed or modified by package management.
''')
write('01_format_reference_and_unknowns.md',header+'''# Source-format and era classification

| Format/period | Executable status | Reference meaning |
|---|---|---|
| legacy-illustrative / any explicitly supplied matching synthetic date | PARSED_UNVERIFIED or QUARANTINED | Frozen synthetic ISO-date CSV contract; not actual historical NSE schema |
| udiff-illustrative / explicitly selected synthetic date | Same | Synthetic newer-style columns; ZIP member exactly synthetic.csv; not actual UDiFF certification |
| disputed 2020 route | Production unchanged | Existing registry's 2020 start remains UNVERIFIED_ROUTING_ASSUMPTION; synthetic legacy-shaped 2020 case proves no implicit year dispatch in new parser only |
| 2019-12-31 / 2020-01-01 boundary | Official case BLOCKED_REFERENCE | Neither route nor actual session/field history authenticated here |
| 2024-06-24, 2024-07-05 | Candidate overlap/transition milestones | Prior documentary leads only, not authenticated row contracts |
| 2024-07-08 | Prior documented discontinuation/transition lead | Not proof of first UDiFF availability, exclusive use, complete semantics or sessions |
| unknown / ambiguous / official-2024-cutover | ERA_UNKNOWN quarantine | No guessing by year/member/header |
| BSE, F&O, other feeds | Unsupported/out of scope | No NSE masquerade; separate future reference work |

The prior [reference registry](../../od05/20261115T190654Z/reference_registry.json) remains immutable. Prior indexed NSE reports/circular62424 metadata is ARCH/REF-DOC, not original-document bytes or reference-use permission. Zero authenticated official document/sample corpus cases are added. No exchange endpoint, source sample or public documentation was fetched in this run. Calendar/session eligibility, TradDt/BizDt source semantics, official units and identity rules remain uncertified. The illustrative contract conservatively requires both dates equal the explicitly requested synthetic date; no real semantics are inferred.
''')
write('02_frozen_contract_and_test_hashes.md',header+'''# Frozen tests and honest chronology

All T01–T32 function groups existed before parser package creation. [Initial freeze](logs/preimplementation-freeze-initial.json), [complete pre-code freeze](logs/preimplementation-freeze.json). First baseline: 75 setup errors (API absent). Before application creation, corrected anticipated harness exception types and added revoked/purpose/pinned archive cases: 78 setup errors, API absent, exit1. Neither result proves an old financial defect; no old implementation file was changed. First implementation then passed all78.

Post-initial review added14 cases:89pass/3fail. Reproduced new-code issues: in-memory forged archive pin accepted; archive facade missing consumer purpose; decoded-size cap omitted for plain CSV. Minimal new-module corrections gave92pass. Later two cases: volume lexeme absent (one failure) and explicit synthetic2020 legacy selection (one pass); corrected only ParsedBar/new decoder to preserve volume_lexeme. Final94cases pass each runtime. These later cases are explicitly not pre-initial-implementation tests. Ruff-only import/literal/format changes also changed test bytes after the initial freeze; assertions were not weakened. Initial/final hashes and all failed logs retained.

T32 includes the replay vector plus external three-runtime collection/full/lint/type/package/coverage evidence; a passing unit function alone never proves T32 complete. REF-dependent subcases remain BLOCKED_REFERENCE; synthetic analogues are not official substitute successes. Independent expected-row/hash algorithm was authored and hashed before application code; serialized vector outputs were recorded later, not backdated.

Public contracts: frozen ParseRequest with source/date/full SHA/mode/format/parser/reference/optional observation/count; frozen exact Decimal/int ParsedBar with source/identity/row ordinal/trade/business dates, original price and volume lexemes, inert unknown fields and null publication; frozen ParseResult with refusal codes, raw/semantic hashes, columns and parser/reference identity. Only SYNTHETIC_TEST_ONLY input and syn-v1/synthetic-v1 contracts accepted. Protected pinned reads are separate from in-memory parsing.

Testing strategy: pure Python library, no UI/service/containers needed. Journeys: exact decode/replay; hostile refusal/file-wide quarantine; rights-aware pinned archive read; origin non-escalation; legacy regression. Existing guarded pytest runners use only disposable SQLite/raw/parquet/release roots; no service startup/browser tier applies to this additive library. All existing tests retained, not migrated/rewritten. DNS/TCP/UDP/subprocess and protected writes denied during collection/execution. Windows file-link privileges and Linux junction skips require actual opposite-platform counterparts. [Exact group/test/result mapping](logs/32-group-results.json), [final freeze](logs/final-source-freeze.json).
'''+ '\n'.join(f'- {group}: '+', '.join(names) for group,names in groups.items()))
write('03_reuse_and_design_adr.md',header+'''# ADR-OD05-SYN-001 — implemented within explicit owner synthetic scope

EXTEND_EXISTING: stdlib csv/zipfile/hashlib/datetime/decimal/dataclasses; existing rights-aware RawArchive facade unchanged. Frozen dataclasses keep the library small; existing Pydantic-backed archive/policy contracts remain in force at the optional facade. No new dependency, transport, writer or infrastructure. The parser package is opt-in by import/function call and unused by old production ingestion. No accepted official-format ADR or release approval is implied.

Pandera: DEFER; no same-corpus exactness/runtime/RSS or current transitive/license/advisory pilot; prior inspected tag metadata is historical, immutable SHA unverified. PyArrow: retain installed existing dependency; DEFER raw-parser role. Existing Python/Pydantic/Arrow installed identities are in per-runtime environment logs. No package install, upstream pin invention, external benchmark or speedup claim. Candidate licensing/security clearance is UNVERIFIED beyond existing recorded metadata. No dependency change justified by popularity.

Resource contract: compressed/raw input <=2,000,000 bytes; decoded bytes <=8,000,000; exactly one synthetic.csv ZIP member, no extraction; ratio<=100, rows<=10,000, headers<=64, header length<=128, field<=4096, identity<=128, price grammar <=12 integer/8 fractional ASCII digits, volume<=2^63-1. User limits can only tighten ceilings. These fixed budgets bound work; targeted checks assert prompt refusal within2seconds, not hardware CPU/memory certification. No independent RSS/throughput pilot was run. Per-command wall times are measured in logs.

Canonical digest includes explicit source/format/parser/reference classification, column manifest and exact numeric/identity/date/ordinal/inert-field content; input raw SHA separately distinguishes lexeme scale, ZIP metadata and line endings. Canonical decimal rendering avoids ambient context rounding. No clock, host path, inferred publication timestamp, corporate action or DB write in core.
''')
write('04_exact_implementation_diff.md',header+'''# Additive changes and compatibility

New package only: __init__.py documents opt-in scope; contracts.py frozen contracts/limits; reference_registry.py fixed illustrative profiles, no approval authority; nse_cm.py strict CSV/ZIP/Decimal/date/identity/quarantine; dispatch.py explicit selection and optional current-rights/pinned-observation facade. Two new test files: test_od05_era_parsing.py and od05_oracle.py. Evidence helpers/docs/logs remain under this new run.

No existing application/test/fixture/config/policy/dependency/UI/script/release/signing/DB file modified. Existing PriceRecord, acquisition validator, source registry, downloader, raw archive, loader and backfill/probe behavior unchanged. No global2020→2024 replacement. Old routing known uncertainty remains outside scope. No production integration toggle was added: default production path never imports/calls the parser.

Entry handoff remains owner-owned untracked content. Environment/private signing entries remain untracked and untouched. No cleanup/stash/reset/history rewrite, migration, source fetch, signing, release, merge, commit or push. Rollback is stop explicitly calling new functions; existing consumers already use their original path. Preserve evidence even if feature is later superseded. [Exact new code/test SHA ledger](logs/final-source-freeze.json); line references resolve in current new files.
''')
write('05_independent_numerical_oracle.md',header+'''# Independent synthetic numerical/reference comparator

The new test helper imports only stdlib, never production parser/Decimal parsing helpers. Literal independent expected identity000SYN/EQ/00001234, ordinal1, volume0, noteinert; scaled-integer O/H/L/C1010/1220/905/1115 at scale100. Independent integer lexical calculation compares each price output and lexeme; explicit dates/source/exchange/state/ref columns are checked in tests. Missing, empty, corrupt expected corpus fails; changed price/volume/ordinal fails comparison. Reference/hash tampering refuses. Both literal format vectors and explicit canonical semantic structure were frozen before application creation. Serialized expected hash output recorded later is honestly dated.

[Frozen vector outputs](logs/oracle-vectors.json). Legacy expected semantic610e8e4b4f77be8653e9ce94f61097f9c4c7a0a2325c06401c06b193489e22d6; modern9423408aac9dd38c2f13d1fd3493750bd8fe8ff5940e825bc8c03ffe3a94deba. Every required runtime independently asserts these exact values. Context precision2 cannot round parsed prices or change canonical digest. Volume raw lexeme000 remains000 while exact integer0 is retained.

Comparator is a separately authored algorithm by the same agent, not independent human consensus. Synthetic fixtures prove only explicitly assumed schemas/math. They prove no official prices/format timeline/calendar/units/legal rights/PIT availability. Official authentic reference subsets remain BLOCKED_REFERENCE.
''')
write('06_security_source_rights_and_pit.md',header+'''# Rights, security, provenance and time

13 real policies PENDING_REVIEW,0approved; no real provider requests or policy edits. Synthetic in-memory entry point refuses cached/seed/provider/official modes. It refuses caller-claimed archive observation IDs. Archive facade requires explicit observation and consumer purpose, calls existing RawArchive.read_verified(source,date,purpose), verifies source mode then parses verified bytes and carries the pinned observation identity. Pending/revoked/wrong-purpose fail before raw payload; no implicit latest or stored-policy override.

Malformed CSV quoting/encoding/counts/colliding/missing headers, wrong dates, duplicate identities, invalid prices/volume, ZIP traversal/link/member/CRC/encryption/codec/nested/bomb/trailer and resource limits have executed negative cases. Public refusal codes contain no payload excerpts. One invalid critical row quarantines the entire file. Unknown columns are immutable inert output, not approved strategy features. All fixtures identify synthetic origin; no private/provider payloads.

Trade/business/publication/observation/ingestion/decision times are different. Unknown published_at remainsNone; parsing does not grant PIT eligibility. No inferred ISIN, adjusted prices, identity mapping/calendar/CA transformation. [Guard proofs](guard_probe.py) pass5cases each on Windows3.14/3.11 and Linux3.12: actual denied DNS/TCP/UDP/process/protected-copy-write/fictional-key-read. No actual signing contents were requested. Guard protects accidental side effects, not hostile Python/native extensions or malicious filesystem owners. WSL shares physical host; no remote-filesystem/power-loss/trusted-key certification. Offline security/regression/pip checks are not a current CVE-feed or transitive-license clearance.
''')
write('07_cross_platform_test_matrix.md',header+'# Executed final matrix\n\n'+matrix_table+'''

Every accepted environment/collection/targeted/full/Ruff/mypy/pip/compilation exits0. Exact argv/executable/platform/UTC/duration/output and node-level skip/deselection evidence in logs/*-accepted-*.json/.txt; pre-command source/test/fixture hashes in *-inputs.json. [Runtime summary](logs/accepted-runtime-matrix.json); [exact skip pairing](logs/skip-pairing.json); [identities](logs/input-identity-comparison.json). All94new cases execute with no skip/xfail on every runtime. Ten Windows privilege skips have actual passing Linux nodes; two Linux junction skips have passing Windows nodes. Four realdata tests deselected per runtime, not counted passed. Coverage is combined lines+branches; no equal-percent assumption.

All attempts retained: initial75/complete78 API-absence errors (not defect proofs); first78green; new adversarial89pass/3fail then92green; lexeme1fail/1pass/92deselected then final94cases; lint9findings then scoped import/literal/format fixes; initial Windows full/collection2 due missing UI resources in sanitized copy, corrected copy not application; later reviewed92case suites successful but superseded by final94case accepted suites. Earlier broad shell read had a PowerShell brace parse error; corrected read used valid paths. An interactive PowerShell5 coverage JSON conversion failed due coverage's empty-key function mapping; Python JSON reader generated coverage summary without changing coverage data. No failed attempt is presented as pass.

Duplicate ZIP construction UserWarning retained. Windows3.14 SQLite ResourceWarnings retained in raw log (not suppressed); these predate parser scope. WSL launcher reports stale PATH drive translation warnings; Linux runtime/commands themselves execute successfully. Run prefix is initial UTC date, later command/report timestamps are actual; no wall-clock timestamp synthesized. No hosted CI or physical independent-host certificate is claimed. Full regression covers API via existing tests; pure parser does not require network service startup/browser/container rollout.
''')
write('08_defects_and_rollback.md',header+'''# Defects, remaining unknowns and rollback

Reproduced/corrected new-code defects after initial78green: forged in-memory observation provenance, optional archive consumer purpose, plain CSV decoded-byte limit. Later volume lexeme missing also red-first corrected; it was a missing additive result field, not proof of an old-system defect. All retained red logs reflect true order; later tests never relabeled pre-initial-code.

P0 inherited D01 signing custody/exposure and D04 release promotion/export remain OPEN and out of scope. P1 production era2020 assumption, official sample/schema/session/rights gaps, PIT temporal corrections, identity/calendar, and fixed Parquet overwrite D03 remain uncertified; latter assigned later storage scope. Parser is default unused; no correction/backfill/release publication to unverified data. Human process exception changes no technical/financial/source gate.

P2 limits: same-model oracle/review, same physical Windows+WSL host, partial branch coverage, no fresh online advisory/transitive legal review, no native-extension sandbox, arbitrary malicious-owner or hardware power-loss guarantee, existing SQLite warnings. No new dependency adopted. Retained historical original test-order deviation cannot be repaired or marked pre-code.

Rollback: discontinue explicit new parser invocation; current production paths unchanged. No database/schema migration, raw object/observation rewrite, version replacement, old report edits or cleanup. Keep immutable evidence and original Gatekeeper. Any new existing-file integration requires reproduced defect plus owner exact-file amendment and lawful reference gate where applicable.
''')
write('09_gatekeeper_verdict.md',header+'''# Gatekeeper — OD05_SYNTHETIC_TECHNICAL_PASS

G0/G1 supplied by directly attesting human owner; identity matches bf6f489. Complete original32group test file frozen/old-code run before package creation; API absence not declared a legacy defect. Later cases and corrections honestly separate. All94in-scope synthetic cases plus complete guarded three-runtime regression/lint/type/pip/compile pass; exact skip counterparts verified; source/test/fixture hashes agree in every pre-command and runtime manifest. Independent literal/scaled-integer comparator and tamper/missing negatives pass. Original files preserved; signing metadata only; 13pending/0approved policies. No external source request, old application mutation, production integration, signing/release/DB write, merge/commit/push/later phase.

This is SYNTHETIC technical acceptance only. All official reference-dependent subcases remain BLOCKED_REFERENCE; no 32/32official claim, official-data accuracy, lawful source access, PIT/production/release certification or independent human financial/security signoff. Original OD04_BLOCKED remains unchanged. Source-era2020 assumption not repaired; July2024 leads require original authenticated document/sample/reference-use permission and separate routing scope. Remaining inherited P0/P1 and platform/security limits remain in08. PASS valid with [final mechanical verification](logs/final-acceptance.json), not an agent grant of additional authority.

AEF procedures: Maker existing-pattern design, Reviewer adversarial new-code probes, Implementer scoped additive corrections, Gatekeeper exact command/hash/skip/preservation verification, Historian all failures and chronology retained. Same-model roles, not fabricated independent consensus. STOP after OD05.
''')
write('10_next_phase_request.md',header+'''# Single next action

Owner reviews this synthetic-only dossier and, if satisfied, separately authorizes a narrowly scoped OD05 official-reference completion review using lawfully supplied authenticated publisher format documents, original hashes/permissions and representative reviewed rows. Until then official cases stay BLOCKED_REFERENCE and production routing stays unchanged. No source acquisition, policy, signing/release, existing-file integration, Git lifecycle or OD06 action is implied. STOP.
''')
with (HERE/'reference_registry.json').open('x',encoding='utf-8') as f:
    previous=ROOT/'docs/omegadata_v2/implementation/od05/20261115T190654Z/reference_registry.json'
    json.dump({'classification':'SOURCE_REFERENCE_PENDING','previous_registry':str(previous.relative_to(ROOT)),
               'previous_registry_sha256':hashlib.sha256(previous.read_bytes()).hexdigest(),
               'new_official_verified_count':0,'synthetic_profiles':['legacy-illustrative','udiff-illustrative'],
               'reference_id':'synthetic-v1','permissions':'Direct owner attestation for offline synthetic testing only'},f,indent=2)
save('report-sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.md')})
print(json.dumps(quality,indent=2))
