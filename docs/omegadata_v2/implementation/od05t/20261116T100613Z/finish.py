"""Mechanical evidence reconciliation and truthful two-dimensional Gatekeeper."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path.cwd();HERE=Path(__file__).resolve().parent;LOGS=HERE/'logs'

def read(name):return json.loads((LOGS/name).read_text(encoding='utf-8-sig'))
def save(name,body):
    with (LOGS/name).open('x',encoding='utf-8') as f:json.dump(body,f,indent=2)
def report(name,body):
    with (HERE/name).open('x',encoding='utf-8') as f:
        f.write('OD-05T | run 20261116T100613Z | branch feature/od01-source-rights | HEAD db087fb9ee12887d3d9c787b797bb6968ad45440.\n\n'+body.strip()+'\n')

freeze={r['path']:r['sha256'] for r in read('accepted-source-freeze.json')['files']}
assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in freeze.items())
matrices={};commands={};runtime=[];fulls={};pairing=[];groups={};performances={}
for label in ('win314','win311','linux312'):
    matrices[label]=read(label+'-accepted-matrix.json')
    assert not any(matrices[label]['results'].values())
    for command in matrices[label]['results']:
        row=read(label+'-accepted-'+command+'.json');assert row['exit_code']==0
        inputs=read(label+'-accepted-'+command+'-inputs.json')
        assert all(inputs[p]==h for p,h in freeze.items()),(label,command)
        commands[label+'-'+command]=row['command']
    full=read(label+'-accepted-full.json');new=read(label+'-accepted-new.json')
    coverage=read(label+'-accepted-full-coverage.json')
    module=next(v for p,v in coverage['files'].items() if p.endswith('archive_candidate_inventory.py'))
    runtime.append({'runtime':label,'python':full['python'].split()[0],'platform':full['platform'],
        'full':full['call_counts'],'deselected_realdata':len(full['deselected']),
        'new_metadata_engineering':new['call_counts'],'global_coverage_percent':coverage['totals']['percent_covered'],
        'new_module_coverage_percent':module['summary']['percent_covered'],'quality_exits':matrices[label]['results']})
    fulls[label]=full
    pergroup={}
    for r in new['test_reports']:
        match=re.search(r'::test_m(\d\d)',r['nodeid'])
        if match:
            group='M'+match[1];pergroup.setdefault(group,[]).append({k:r[k] for k in ('nodeid','when','outcome','reason')})
    assert set(pergroup)=={'M%02d'%n for n in range(1,19)}
    assert not any(r['outcome']=='failed' for records in pergroup.values() for r in records)
    groups[label]=pergroup
    performances[label]=(LOGS/(label+'-accepted-performance.txt')).read_text(encoding='utf-8')
for label,full in fulls.items():
    for r in full['test_reports']:
        if r['outcome']!='skipped':continue
        peers=[peer for peer,other in fulls.items() if peer!=label and any(t['nodeid']==r['nodeid'] and t['outcome']=='passed' for t in other['test_reports'])]
        assert peers,(label,r['nodeid'])
        pairing.append({'runtime':label,'nodeid':r['nodeid'],'reason':r['reason'],'passed_on':peers})
save('runtime-matrix.json',runtime);save('skip-pairing.json',pairing)
save('M01-M18-results.json',groups);save('accepted-command-index.json',commands)
save('R01-R06-results.json',{'R%02d'%n:{'status':'NOT_RUN_BLOCKED_REFERENCE','reason':'No owner-authorized authentic pack, external publisher/row pins and human-reviewed values supplied'} for n in range(1,7)})
preserve=read('preservation.json');assert not preserve['changed'] and not preserve['changed_data_metadata']
prior={}
for phase,path in [('OD05','od05_impl/20261115T201333Z'),('OD05R','od05r/20261116T084526Z'),('OD05S','od05s/20261116T094756Z')]:
    base=ROOT/'docs/omegadata_v2/implementation'/path
    manifest=json.loads((base/'logs/evidence-sha256.json').read_text(encoding='utf-8-sig'))
    for name,sha in manifest.items():
        target=base/name;assert target.resolve().is_relative_to(base.resolve())
        assert hashlib.sha256(target.read_bytes()).hexdigest()==sha,(phase,name)
    prior[phase]={'files_matching_recorded_hashes':len(manifest),'historical_verdict_unchanged':True}
save('prior-evidence-reconciliation.json',prior)
scan=read('original-metadata-scan.json')
assert not scan['guard_denials']
assert all(g['independent_oracle_match'] for g in scan['groups'].values())
count=sum(g['manifest_count'] for g in scan['groups'].values())
score={'schema_version':'od05t.real-data-scorecard/v1','status':'BLOCKED_REAL_DATA',
    'metadata_only_manifests_inspected':count,'metadata_identity_mismatches':0,
    'authentic_market_files_independently_verified':0,'market_records_inspected':0,
    'market_records_independently_verified':0,'official_reference_verified':0,
    'financial_mismatches':None,'missing_sessions':None,'rejected_market_records':0,
    'rejected_market_records_note':'No financial payload processed, not zero-error acceptance',
    'coverage':None,'coverage_denominator':None,'synthetic_results_in_real_acceptance':0,
    'publisher_origin':'UNVERIFIED','source_schema_by_era':'BLOCKED_REFERENCE',
    'rights_for_payload_review':'NOT_SUPPLIED','independent_row_expectations':'NOT_SUPPLIED',
    'PIT_availability':'UNVERIFIED','engineering_result':'OD05T_METADATA_TOOL_TECHNICAL_PASS_REAL_DATA_PENDING'}
with (HERE/'real-data-scorecard.json').open('x',encoding='utf-8') as f:json.dump(score,f,indent=2)
template_fields=('file_role','local_private_path','publisher','publisher_url','document_id','publication_date','format_id','data_date','sha256_independent_pin','byte_length','acquired_at','permission_scope','permission_evidence','reviewer_identity','reviewed_at','expected_fields','expected_values_ref','PIT_publication_evidence')
with (HERE/'owner-pack-manifest-template.json').open('x',encoding='utf-8') as f:
    json.dump({'status':'TEMPLATE_ONLY_NO_AUTHORIZATION','files':[{k:None for k in template_fields}],
        'required_roles':['original_publisher_document','real_sample','reviewed_expected_values','separate_independent_pins'],
        'permission_dimensions':['documentation_consultation','local_parse_research','retention','derived_use','publication','redistribution']},f,indent=2)
policy=json.loads((ROOT/'config/source_rights_policy.v1.json').read_text())
assert len(policy['policies'])==13 and all(p['status']=='PENDING_REVIEW' for p in policy['policies'])
save('source-policy-identity.json',{'sha256':hashlib.sha256((ROOT/'config/source_rights_policy.v1.json').read_bytes()).hexdigest(),'pending':13,'approved':0})
table='| Runtime | Full pass / skip / realdata excluded | New metadata pass / skip | Global / new-module coverage |\n|---|---|---|---|\n'
for r in runtime:
    table+=f"| {r['runtime']} Python {r['python']} | {r['full']['passed']} / {r['full'].get('skipped',0)} / {r['deselected_realdata']} | {r['new_metadata_engineering']['passed']} / {r['new_metadata_engineering'].get('skipped',0)} | {r['global_coverage_percent']:.2f}% / {r['new_module_coverage_percent']:.2f}% |\n"

report('00_identity_scope_and_rights.md',f'''# Scope and preservation

Execution mode: OD05T_REAL_DATA_PROVENANCE_TRIAGE_AND_PACK_READINESS_ONLY. Exact reviewed branch/HEAD and clean tracked diff verified in [entry commands](logs/entry.json). Existing untracked environment, prompt and signing paths were preserved. No commit, push, merge, publication or later phase.

The user authorizes metadata-only read/stat in two explicit source directories, existing code/evidence inspection, copied real metadata and non-market malformed metadata probes. It does not authorize payload reads, exchange requests, source approval, data migration, production routing or signing. Historical G0/G1 was not reopened.

[Preservation](logs/preservation.json): {preserve['original_hashed_files']} original source/test/config/evidence files match their initial SHA; {preserve['original_data_metadata']} data/artifact/database/signing metadata records retain length/mtime. Source payload contents were NOT opened or hashed. The newly authored oracle existed at initial snapshot; its formatting delta is explicitly phase-owned, not an original-file change. This is scoped preservation evidence, not hardware integrity certification.

[Prior evidence](logs/prior-evidence-reconciliation.json) independently matches the recorded OD05/OD05R/OD05S manifests; their verdicts and limitations remain unchanged.''')
report('01_existing_archive_manifest_inventory.md',f'''# Actual selected-source metadata

Fresh guarded [original-metadata scan](logs/original-metadata-scan.json), independent of the inventory implementation's count/digest calculation: {count} selected NSE CM manifest identities, zero malformed metadata or pinned-identity mismatches. Seed directory: {scan['groups']['seed']['manifest_count']}; versioned-cache directory: {scan['groups']['cache']['manifest_count']}. This is narrower than OD05S's broad 3,676-manifest tree, not a claim that the remaining paths disappeared.

Exact roots: repository data/seed_raw/omega_phase2_repo/nse_equity_bhavcopy and data/raw/nse_equity_bhavcopy. The committed [frozen metadata pins](logs/frozen-metadata-pins.json) contain only relative metadata identities/counts/SHA/length, never payloads. Canonical seed digest: `{scan['groups']['seed']['metadata_sha256']}`; cache digest: `{scan['groups']['cache']['metadata_sha256']}`.

Aggregates include declared modes, date/month counts, missing evidence, rights pending, same-date observations and duplicate metadata bytes. Metadata checksums and HTTPS strings remain unverified claims. Multiple same-date revisions and same-byte separate files are retained. No equality of manifest bytes implies equality or validity of market observations.''')
report('02_candidate_era_and_sample_readiness.md','''# Era/date readiness

[Fresh boundary-date matrix](logs/original-metadata-scan.json) explicitly records manifest counts for 2019-12-31, 2020-01-01/02, 2024-06-21/24/25 and 2024-07-04/05/08/09. Every session_verified value is false. Full metadata date/month distributions provide other observed-date controls without inventing sessions.

These are candidate file dates, not verified exchange trading days. January 2020 UDiFF routing remains unverified. Project start, schema/tag changes, large-file splitting, availability/overlap and July discontinuation must remain distinct documentary questions. No live documentation or publisher reference was newly fetched; OD05R indexed leads remain archived leads only. R01-R06 remain NOT_RUN_BLOCKED_REFERENCE. No opt-in real-format profile or production routing change.''')
report('03_metadata_contract_and_implementation.md','''# Additive contract and reuse decision

Added [archive_candidate_inventory.py](../../../../../src/omegadata/parsers/archive_candidate_inventory.py), [CLI](../../../../../scripts/audit_existing_market_archive.py), [engineering tests](../../../../../tests/unit/test_od05t_archive_inventory.py) and [stdlib oracle](../../../../../tests/unit/od05t_metadata_oracle.py). Exact final identities are [frozen](logs/accepted-source-freeze.json), with per-command matching hashes. No existing application/test/config file was edited.

Frozen ExpectedMetadata pins relative manifest names, full SHA and length. Nonempty corpus, exact expected names/count and bytes are checked; untrusted index contents cannot set their own pass threshold. The oracle froze these metadata expectations before application code, but they are not independent human publisher or row attestations. Inventory rows are frozen and canonical identity is enumeration/OS independent.

Metadata-only authority is an explicit caller-controlled root; CLI limits its production entry point to the two named NSE CM directories. It never dereferences declared artifact paths. Reuse OD05R no_links/read_file for lstat/reparse/hardlink and descriptor identity checks, plus duplicate-key refusal. Stdlib dataclasses/hashlib/json/pathlib and the existing dependency stack suffice; no new packages, copied downloader, Pandera or transport client. No external repository/advisory/license-clearance claim is made.

Limits: 5,000 manifests, 20,000 entries, depth 12, 65,536 bytes per manifest, 64 MB total manifest bytes, 30 seconds per production scan; strict bounded caller reductions only. Separate pin JSON cap 2 MB. Code-only public errors, URL scheme categories only, unsafe absolute artifact claims redacted. Caller permission/reviewer strings stay PRESENT_UNVERIFIED/RIGHTS_PENDING and never grant payload use.

CLI requires --manifest-root, separately supplied --expected-pins and --metadata-only. Source/date filters, --dry-run and fresh external --output-dir supported. Success exit 0 means metadata engineering only; --require-real-data always exits 3; unsafe/incomplete/error requests exit 2. Help/usage are argparse exits. No operational default imports/integration added.

Separate reviewed-attestation design: an accountable external human must bind exact original document/sample/expected-value hashes, publisher receipt, role/date and granular operation rights to independently held pins. This tool only exposes missing declarations; it has no trust anchor, cannot ingest a self-approved authority, and does not mint DOCUMENT_IDENTITY_PINNED, reference approval, source permission or release eligibility.''')
report('04_negative_first_and_honest_chronology.md','''# Executed negative-first chronology

[Original pre-code freeze](logs/precode-freeze.json) covers all 18 M groups and the stdlib oracle, with original metadata pins independently frozen first. Both application files were absent. First red run: 39 failed plus two fixture errors; pytest's oversized generated metadata parameter ID caused Windows fixture path failure. Short parameter IDs corrected the harness, with [separate pre-code correction freeze](logs/precode-harness-correction-freeze.json), without assertion changes. Corrected red: 40 failed due to missing API, NEW_FEATURE_ABSENT, not a reproduced old bug.

First implementation: 38 pass/2 unavailable-privilege link skips on Windows. Later six adversarial cases reproduced non-string storage-mode handling and portable device-name acceptance; [red](logs/win314-review-red.json) then [green](logs/win314-review-green.json) retained. Later two canary tests reproduced attempted non-JSON pin-name reads; [red](logs/win314-pin-review-red.json) and [green](logs/win314-pin-review-green.json) retained. No actual environment/key contents were read; disposable canaries and monkeypatched pre-open assertions were used.

Final suite has 48 cases and every M01-M18 group executes. Formatting/import cleanup did not weaken expectations. Later cases are not retroactively claimed pre-code. Initial *-final Windows matrices precede the pin-name hardening and are superseded by *-accepted matrices. [Per-node group ledger](logs/M01-M18-results.json), [runtime matrix](logs/runtime-matrix.json) and [R01-R06 status](logs/R01-R06-results.json) preserve separate scopes. No synthetic financial acceptance or fabricated market fixture.''')
report('05_independent_metadata_oracle.md','''# Independent metadata comparator

The stdlib-only oracle imports no application inventory/validator methods. Before application creation it enumerated only *.manifest.json under two explicit real source directories, pinned names/count/SHA/length, and computed a canonical digest. Positive count is mandatory. Tests compare independently frozen counts and digests, check original bytes against those pins, and reject missing/moved/empty/tampered/count-mismatched corpora and duplicate/mutable/unsafe expected pins.

[Frozen original metadata pins](logs/frozen-metadata-pins.json), [pre-code identities](logs/precode-freeze.json), [fresh original-scan comparison](logs/original-metadata-scan.json) and final runtime node results establish metadata reproducibility. Identical semantic code/tests are SHA-checked before every accepted command. Actual Linux and Windows inputs derive from the same private copied original metadata and pins.

This is a separately implemented mechanical comparator authored by the same agent, not an independent human financial review. It verifies neither publisher provenance nor payload hash/schema/numerical values. Metadata SHA matches never enter financial correctness metrics.''')
report('06_real_data_acceptance_scorecard.md',f'''# Real-data acceptance: BLOCKED_REAL_DATA

[Machine scorecard](real-data-scorecard.json): {count} real existing manifest metadata records inspected; zero authentic market files or observations independently verified; zero market rows parsed; zero publisher references authenticated. Financial mismatches, missing sessions, expected-session denominator and coverage are unknown/null. Zero rejected market records means no payload processed, not zero-error success. Synthetic contribution is zero.

All six real-reference groups are [NOT_RUN_BLOCKED_REFERENCE](logs/R01-R06-results.json). Original publisher documents, sample permissions, independent original-byte pins and reviewed literal row expectations were not supplied. No honest real-data accuracy/degradation/performance comparison is available. Technical PASS applies only to metadata engineering.''')
report('07_security_rights_and_source_authenticity.md','''# Security and rights

Root confinement, absolute private paths, lexical traversal/UNC/device/reparse/symlink/hardlink refusal, deterministic bounds, duplicate keys, mixed-source refusal and privacy redaction have executed negative probes. Manifest artifact_path is never opened. Expected pin files must be non-hidden JSON before any open. Metadata-only declarations never grant source/payload/reviewer authority. CLI output destination is fresh, external to repository and approved source trees, with validated non-link ancestors. Caller/operator must own private local roots; no hostile concurrent directory-owner/kernel/power-loss certificate is claimed.

Each runtime executes five reviewed guard probes: DNS, TCP/UDP, subprocess, protected-copy write and fictional signing-path read denial. Full tests run under that guard with disposable DB/storage/env paths. Static compile/type commands run on disposable code copies. The original metadata scan has its own audit hook restricting reads to allowlisted manifest names and denying writes/network/process creation while scanning. Its guard-denial count is zero; no payload/key open attempted.

Eight actual trusted CLI worker processes test help, invalid args, dry run, real-acceptance refusal, fresh/existing/protected output and unexpected source; [exact argv/exits and redacted summaries](logs/cli-process-probes.json). They are offline CLI smoke processes; the in-process cross-runtime CLI tests run under the stricter inherited guard.

[Source policy identity](logs/source-policy-identity.json): 13 pending, zero approved, unchanged. Metadata read authority is not payload-research permission, publisher authentication, source acquisition approval, redistribution or legal clearance. Current advisory feeds/transitive license review were not contacted; pip check is dependency consistency only.''')
report('08_cross_platform_quality_matrix.md',f'''# Fresh accepted runtime matrix

{table}
All accepted environment/collection/new/targeted/full/guard/performance/Ruff/strict-mypy/pip/compile commands exit 0. [Actual argv index](logs/accepted-command-index.json) and per-command JSON/text retain exact executable, cwd, platform, UTC start/end, exit, raw warnings, skips and realdata exclusions. Four live-marked tests are excluded per full runtime, never called verified. Inherited legacy tests are engineering regression only.

[Skip pairing](logs/skip-pairing.json) requires each exact skipped node to pass on another OS, including actual Linux links and Windows junctions; no privilege skip is a pass. WSL uses native Linux storage but shares the Windows physical host; no hosted CI result or independent host certification. WSL inherited stale PATH translation warnings occurred during preparation/launch, retained in the tool transcript. Full logs retain duplicate-ZIP and any runtime cleanup warnings.

M16 measures 1/8/32 copied real manifest metadata files with elapsed time and tracemalloc allocations; three passes each runtime. Raw values are in *-accepted-performance.txt. These are Python allocation measurements, not RSS or financial throughput. The original guarded metadata scan also records end-to-end time including the separate oracle and peak Python allocations; this combined duration is not the production scan's 30-second deadline or a market-price processing benchmark.

Initial Windows *-final matrices are superseded after the two pin-reader tests/correction. Only *-accepted results support this verdict. Compilation writes bytecode only into disposable copies; no package installation or original-environment replacement.''')
report('09_remaining_defects_and_rollback.md','''# Remaining risks and rollback

- P0 inherited signing custody and release-promotion findings remain untouched, unwaived and publication blocking. No private key contents or signatures were accessed.
- P1 actual publisher origin, scoped sample/reference rights, real row/schema/date/units/numerical expectations and historical completeness remain unverified. January 2020 routing remains unverified and unchanged; June-July 2024 reference semantics remain unresolved.
- P1 PIT knowledge-time/calendar/instrument identity and historical corrections, corporate-action revision semantics and fixed analytical Parquet versioning remain assigned to separate phases. Metadata readiness cannot waive them.
- P2 SQLite/runtime warning history remains a limitation; retained full logs describe observed warnings. Python-only guard/private-root limits and same-host Windows/WSL limitations remain. No broader P3 audit performed.

Rollback is removal of only the four new phase-owned code/test files in a separately reviewed change; no existing function/default route was modified and no data migration is required. Keep all historical and new evidence unchanged. No automatic cleanup of private copies/outputs, source-policy edits, key remediation, release work or later phase.''')
verdict='OD05T_METADATA_TOOL_TECHNICAL_PASS_REAL_DATA_PENDING'
report('10_gatekeeper_verdict.md',f'''# {verdict}

Financial verdict remains BLOCKED_REAL_DATA / BLOCKED_REFERENCE. All M01-M18 engineering groups execute with bounded, pinned existing real manifest metadata and non-market adversarial metadata probes. All three accepted guarded runtime matrices, full regressions and quality commands pass; exact platform skips have named passing peers. Independent count/hash oracle agrees on {count} metadata identities; source/test identity and original-file preservation checks pass.

R01-R06: six NOT_RUN_BLOCKED_REFERENCE, zero authentic market files or independently verified rows. No official-reference/sample/schema/numerical/PIT/completeness/trading/performance/production acceptance is granted. No original archive bytes were opened. Provider rights, source policies and publisher authority are unchanged.

Maker/Reviewer/Implementer/Gatekeeper/Historian are same-agent procedures, not invented human consensus. Late tests/corrections, superseded matrices and original OD04 chronology are retained honestly. No Git lifecycle action, release/signing, production routing or OD06. Stop after OD05T.

See [runtime evidence](08_cross_platform_quality_matrix.md), [real-data scorecard](real-data-scorecard.json), [preservation](logs/preservation.json) and [single owner handoff](11_owner_reference_pack_handoff.md).''')
report('11_owner_reference_pack_handoff.md','''# One owner handoff request

Paril/source-reference owner: nominate one bounded privately held authentic NSE CM pack, including (1) original dated/versioned publisher schema/circular/annexure, (2) permitted actual sample files/rows near the disputed 2019/2020 and June-July 2024 boundaries, (3) separately reviewed literal field/date/identity/Decimal-price/integer-volume/unit expectations and row/member order, (4) granular reference/sample permission evidence, and (5) separately owned original full SHA/length/provenance pins. Existing cache candidates may be nominated only with those same independent proofs; metadata filename/URL/hash alone is insufficient.

Use the [file-by-file blank template](owner-pack-manifest-template.json). Leave unknown facts null. Distinguish document consultation, local parse/research, retention, derived use, publication and redistribution. Provide actual reviewer identity/date and scoped authority, not self-authorizing JSON. PIT publication evidence can remain null but then PIT eligibility remains blocked. Keep original files private, outside Git, until precise redistribution approval exists.

This is one corpus-supply/review request, not a new G0/G1 loop, permission for live collection, a claim that fee-free rights exist, or an OD06/production/signing/release/Git authorization. No alternative public dump/vendor was silently substituted. No access or fee determination was made; an alternative authentic source requires separate owner approval.''')
save('final-acceptance.json',{'utc':datetime.now(UTC).isoformat(),'mechanical_checks_passed':True,
    'gatekeeper':verdict,'financial_status':'BLOCKED_REAL_DATA','metadata_manifests':count,
    'actual_market_files_verified':0,'actual_market_rows_verified':0,'real_reference_groups_blocked':6,
    'new_cases_per_runtime':48,'source_hashes':freeze,'original_preservation':preserve,
    'runtime_results':runtime,'all_platform_skips_have_passing_peer':True,'committed_pushed_merged':False})
manifest={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
          for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
save('evidence-sha256.json',manifest)
print(json.dumps({'verdict':verdict,'runtime_results':runtime,'evidence_files_hashed':len(manifest)},indent=2))
