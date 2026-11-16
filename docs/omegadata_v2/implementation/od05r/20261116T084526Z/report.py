"""OD05R dossier from actual local execution and explicitly indexed research."""
import ast
import hashlib
import json
import re
import subprocess
from dataclasses import asdict
from datetime import UTC, date, datetime

import control

ROOT,HERE,LOGS=control.ROOT,control.HERE,control.LOGS
load=lambda name:json.loads((LOGS/name).read_text(encoding='utf-8-sig'))
save=control.save


def write(name,body):
    with (HERE/name).open('x',encoding='utf-8') as out:
        out.write(body.rstrip()+'\n')


labels=['win314-reviewed','win311-reviewed','linux312-reviewed']
freeze=load('reviewed-source-freeze.json')['files']
all_inputs={}
quality=[]
full={}
table=['| Runtime | Full pass/skip/deselect | Targeted pass/skip | OD05R pass/skip | Original OD05 | Coverage total/new verifier | Quality exits |',
       '|---|---|---|---|---|---|---|']
for label in labels:
    matrix=load(label+'-matrix.json')
    assert all(code==0 for code in matrix['results'].values())
    all_inputs[label]=matrix['files']
    for command in matrix['results']:
        inputs=load(label+'-'+command+'-inputs.json')
        assert all(inputs[p]==sha for p,sha in freeze.items())
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in freeze.items())
    record=load(label+'-full.json');full[label]=record
    new=[r for r in record['test_reports'] if 'test_od05r_reference_evidence.py::' in r['nodeid']]
    old=[r for r in record['test_reports'] if 'test_od05_era_parsing.py::' in r['nodeid'] and r['when']=='call']
    assert len(old)==94 and all(r['outcome']=='passed' for r in old)
    assert sum(r['outcome']=='passed' and r['when']=='call' for r in new)==60
    assert sum(r['outcome']=='skipped' for r in new)==1
    target=load(label+'-targeted.json')
    coverage=load(label+'-full-coverage.json')
    files=[v for p,v in coverage['files'].items() if p.replace('\\','/').endswith(('/reference_evidence.py','/era_matrix.py'))]
    assert len(files)==2
    covered=sum(v['summary']['covered_lines']+v['summary']['covered_branches'] for v in files)
    total=sum(v['summary']['num_statements']+v['summary']['num_branches'] for v in files)
    row={'runtime':label,'python':record['python'],'platform':record['platform'],
        'passed':record['call_counts']['passed'],'skipped':sum(r['outcome']=='skipped' for r in record['test_reports']),
        'deselected':len(record['deselected']),'od05r_passed':60,'od05r_skipped':1,'original_od05_passed':94,
        'targeted_passed':target['call_counts']['passed'],
        'targeted_skipped':sum(r['outcome']=='skipped' for r in target['test_reports']),
        'combined_coverage':coverage['totals']['percent_covered'],'new_verifier_combined_coverage':100*covered/total,
        'quality_exits':matrix['results']}
    quality.append(row)
    table.append(f"| {label} | {row['passed']}/{row['skipped']}/{row['deselected']} | {row['targeted_passed']}/{row['targeted_skipped']} | 60/1 | 94 pass | {row['combined_coverage']:.4f}% / {100*covered/total:.4f}% | all 0 |")
assert all(value==next(iter(all_inputs.values())) for value in all_inputs.values())
save('runtime-matrix.json',quality)
save('cross-runtime-inputs.json',{'all_equal':True,'files':len(next(iter(all_inputs.values()))),
    'current_source_matches':True,'every_precommand_freeze_matches':True,'final_freeze':freeze})
pairings=[]
for label,record in full.items():
    for node in [r for r in record['test_reports'] if r['outcome']=='skipped']:
        peers=[other for other,run in full.items() if other!=label and any(r['when']=='call'
            and r['outcome']=='passed' and r['nodeid']==node['nodeid'] for r in run['test_reports'])]
        assert peers,node['nodeid']
        pairings.append({'runtime':label,'nodeid':node['nodeid'],'reason':node['reason'],'passed_on':peers})
save('skip-pairing.json',pairings)
functions=[node.name for node in ast.parse((ROOT/'tests/unit/test_od05r_reference_evidence.py').read_text(encoding='utf-8')).body if isinstance(node,ast.FunctionDef)]
groups={f'R{n:02}':[f for f in functions if f.startswith(f'test_r{n:02}_')] for n in range(1,25)}
assert all(groups.values())
save('R01-R24-results.json',{group:{'test_ids':names,'baseline':'NEW_API_ABSENT (not legacy-defect proof)',
    'final':'PASS_SYNTHETIC with exact paired platform skips','runtime_nodes':{label:[r for r in record['test_reports']
        if any('::'+name in r['nodeid'] for name in names)] for label,record in full.items()}}
    for group,names in groups.items()})
save('F01-F12-results.json',{f'F{n:02}':{'status':'BLOCKED_REFERENCE','reason':'No authenticated publisher bytes, human reference-use permission and independently reviewed original sample rows; no official parser extension'} for n in range(1,13)})
performance={}
for label in ('win314','linux312'):
    record=load(label+'-performance.json')
    assert record['exit_code']==0 and record['call_counts']=={'passed':3}
    lines=(LOGS/(label+'-performance.txt')).read_text(encoding='utf-8')
    performance[label]=[json.loads(m.group(0)) for m in re.finditer(r'\{[^\n]+\}',lines)]
    assert len(performance[label])==3
save('performance-summary.json',performance)

# Fresh generated uncertainty matrix: no authenticated references means no supported cells.
import sys
sys.path.insert(0,str(ROOT/'src'))
from omegadata.parsers.era_matrix import build_matrix
dates=tuple(date.fromisoformat(s) for s in ('2019-12-31','2020-01-01','2020-01-02',
    '2024-06-21','2024-06-24','2024-06-25','2024-07-04','2024-07-05','2024-07-08','2024-07-09',
    '2024-07-16','2024-07-17','2024-07-18'))
cells=[asdict(cell)|{'business_date':cell.business_date.isoformat(),'calendar_session':'UNKNOWN',
    'sample_date':None,'schema_version':None,'permissions':'PENDING_REFERENCE'} for cell in build_matrix((),dates)]
assert len(cells)==13 and all(not c['supported'] for c in cells)
save('generated-cutover-matrix.json',{'generator':'omegadata.parsers.era_matrix.build_matrix',
    'source_sha256':freeze['src/omegadata/parsers/era_matrix.py'],'authenticated_references':0,
    'independently_expected_cells':13,'cells':cells})

research={
    'mode':'PUBLIC_SEARCH_INDEX_ONLY; no direct publisher/market/sample request',
    'instrumented_query_start_utc':'2026-11-16T08:50:01Z','instrumented_query_end_utc':'2026-11-16T08:50:03Z',
    'earlier_interactive_query_timestamps':'Not separately instrumented; tool transcript retained; no timestamp invented',
    'original_document_retrieved_at':None,'official_reference_verified':0,
    'entries':[
      {'issuer':'NSE','source':'NSE_EQUITY_BHAVCOPY','segment':'CM','document_id':'NSE reports page / 62424 citation',
       'url':'https://www.nseindia.com/all-reports/','version':None,
       'lead':'Indexed discontinuation of earlier CM products effective 2024-07-08, cites circular62424 dated2024-06-12; not earliest UDiFF proof'},
      {'issuer':'NSE','source':'NSE_EQUITY_BHAVCOPY','segment':'CM','document_id':'Forms/Formats catalogue',
       'url':'https://www.nseindia.com/static/resources/forms-formats-members','version':'Indexed links v1.0-v4.0, exact applicability UNKNOWN',
       'lead':'CM formats/sample-test links and circulars59694/59875/62142 indexed; linked files not downloaded'},
      {'issuer':'NSE','source':'NSE_EQUITY_BHAVCOPY','segment':'CM','document_id':'UDiFF guidance V2023.10',
       'url':'https://nsearchives.nseindia.com/web/sites/default/files/inline-files/UDiFF%20guidance%20document_Ver1.0.pdf','version':'V2023.10 indexed only',
       'lead':'Standardization exercise began in2020; this is not proof that CM UDiFF bhavcopy was disseminated from2020-01-01'},
      {'issuer':'NSE','source':'NSE_EQUITY_BHAVCOPY','segment':'CM','document_id':'NSE/MSD/59875 dated2023-12-21',
       'url':'https://archives.nseindia.com/content/circulars/MSD59875.pdf','version':None,
       'lead':'Indexed official circular points to guidance and trade/bhavcopy formats/sample test files, citing59694 dated2023-12-11'},
      {'issuer':'NSE claimed; third-party mirror unverified','source':'UNVERIFIED','segment':'CM/FO/CD scope unresolved',
       'document_id':'NSE/MSD/62424 dated2024-06-12 (mirror lead)',
       'url':'https://avantiscdnprodstorage.blob.core.windows.net/legalupdatedocs/32584/NSE_issued_a_circular_regarding_the_Standardization_of_Exchange_to_Member_Interface_files_in_Unified_Distilled_File_Formats_UDiFF_June122024.pdf',
       'version':None,'lead':'Mirror text links June24 preponing specifically to pointC large-file splitting; July5 parallel dissemination and July8 discontinuation are leads requiring original/annexure/segment reconciliation, not a universal initial-format date'},
      {'issuer':'NSE','source':'NSE_EQUITY_BHAVCOPY','segment':'CM','document_id':'NSE/CMTR/45038 dated2020-07-17',
       'url':'https://nsearchives.nseindia.com/content/circulars/CMTR45038.pdf','version':None,
       'lead':'Indexed 2020 bhavcopy structure lead, not authenticated proof of UDiFF CSV semantics or January boundary'},
      {'issuer':'NSE','source':'all website content','segment':None,'document_id':'Copyright policy',
       'url':'https://www.nseindia.in/static/nse-copyright','version':'Indexed updated2025-10-21',
       'lead':'Indexed personal/noncommercial/educational conditions do not establish permission for commercial quant use; no legal clearance inferred'}]}
for entry in research['entries']:
    entry.update(status='SCHEMA_REFERENCE_PENDING',acquisition_method='INDEX_ONLY',
        original_sha256=None,original_length=None,rights='NOT_SUPPLIED',human_review=None,
        sample_sha256=None,sample_proof=None,blockers=['ORIGINAL_DOCUMENT_MISSING','REFERENCE_USE_PERMISSION_MISSING','ROW_TRUTH_MISSING'])
with (HERE/'reference_registry.od05r.json').open('x',encoding='utf-8') as out:
    json.dump(research,out,indent=2)
save('research-method.json',{k:v for k,v in research.items() if k!='entries'})

header=f'OD05R_REFERENCE_AND_PARSER_VERIFICATION_ONLY; run20261116T084526Z; evaluated {datetime.now(UTC).isoformat()}. Branch feature/od01-source-rights; HEAD {control.HEAD}. RUN=fresh commands; TEST/SYN=synthetic; ARCH=prior evidence; REF-DOC=indexed documentary lead only; UNK=unverified. Same-model procedural review, no independent human/legal/financial certification.\n\n'
matrix='\n'.join(table)
write('00_preflight_and_permissions.md',header+'''# Entry scope and preserved authority

Reviewed branch/HEAD match. Current direct user instruction authorizes only OD05R reference/verifier work, guarded disposable tests, bounded public-document discovery, and fresh evidence. OD05 G0/G1 direct owner record is recognized unchanged, not regenerated or reopened. [Prior evidence reconciliation](logs/od05-evidence-reconciliation.json): all293prior dossier bytes and seven tested source/helper identities match. Historical572/580regression totals remain ARCH, not fresh OD05R results. The original OD04 chronology deviation/Gatekeeper remain immutable.

Read root instructions/master/phase plan and all OD05 numbered evidence; inspected current synthetic contracts/dispatch/decoder/registry, legacy era/call paths and rights-aware archive behavior. Current tracked worktree/index unchanged; merge-base main d4b5a58f0c50dc348e0d4e1150a725cc6fab5674. Entry untracked: supplied OD05R contract, existing Linux environment and three private/revocation signing files, all retained. No signing contents opened/hashed/copied; preservation helper uses metadata only. No package/environment changes, provider acquisition, source-policy edit, release, signing, migration, Git lifecycle or OD06.

13real policies pending,0approved. Public search-index research allowed by phase is separate from provider transport, which remains off. No direct publisher page/PDF/sample/API/CSV/ZIP request was made. Authentication/reference-use and row gates A/B remain absent; no official parser extension. GateC production-route authority is not granted. Only two new application modules and two new test/helper files plus this dossier are authored.
''')
write('01_publisher_reference_inventory.md',header+'''# Indexed documentation is not authenticated original bytes

[Machine registry](reference_registry.od05r.json) records seven leads, actual indexed-query UTC window, URLs, claimed versions/issuer/source scope and null original byte/hash/sample/human permission values. Earlier queries were not individually timed; timestamps are not invented. Search results are not original retrieved publisher files. No authentic local documents or lawfully permitted representative rows were supplied. All official cases remain BLOCKED_REFERENCE.

[Official reports page](https://www.nseindia.com/all-reports/) corroborates the announced July8discontinuation and cites62424; [Forms/Formats](https://www.nseindia.com/static/resources/forms-formats-members) indexes catalogue versions1–4 and CM-specific format/sample links. Original linked files/annexures are not received. The indexed [guidance note](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/UDiFF%20guidance%20document_Ver1.0.pdf) says the harmonization exercise began in2020; that does not prove a January2020CMfile route. Indexed [MSD59875](https://archives.nseindia.com/content/circulars/MSD59875.pdf) supplies a December2023documentation lead. No actual 2019/2020 row semantics or samples are authenticated.

The third-party62424mirror is expressly unverified and never a substitute for an NSE-hosted original. Its June24statement concerns large-file splitting in pointC; treating it as the initial universal UDiFF introduction would overstate evidence. Indexed May22/June21 and June12/June24 statements need exact version/annexure/change-type/CM scope reconciliation; they need not describe the same change. July5parallel dissemination and July8withdrawal do not prove exclusive format availability before/after each instant. No F&O evidence certifies CM or BSE.

Indexed copyright terms allow certain personal/noncommercial/educational use; this does not establish rights for this commercial-quant purpose. Permission remains unknown; original circulars/sample bundles were not downloaded, copied into Git, or certified. BSE independent references and official calendar amendments/session evidence remain missing. Existing official-labeled fixtures remain ARCHIVED_UNVERIFIED.
''')
write('02_era_transition_evidence_matrix.md',header+'''# Generated uncertainty and cutover matrix

[Generated13-cell JSON](logs/generated-cutover-matrix.json) calls the new era_matrix.build_matrix with zero authenticated references and independently pinned13expected dates. Every official cell is UNKNOWN/unsupported; indexed documentary leads are separately annotated here, not promoted into evidence capabilities.

| Dates | Documentary clue | Scope/session/schema/sample/rights |
|---|---|---|
|2019-12-31 /2020-01-01 /2020-01-02|Existing registry uses2020; guidance's standardization exercise2020is not file availability|All UNKNOWN/PENDING_REFERENCE|
|2024-06-21 /06-24 /06-25|May22change lead vs mirrored June12large-file-splitting revision; scope needs originals|No authenticated overlap interval, CM row schema or actual session proof|
|2024-07-04 /07-05|Mirrored parallel-delivery lead throughJuly5|Retain potential OVERLAP as unverified; no official support|
|2024-07-08 /07-09|Official indexed reports page announces discontinuation/successor|Announcement is not earliest availability, calendar session or row oracle|
|2024-07-16 /07-17 /07-18 controls|Prior annual2024calendar excerpt ARCH only|No fresh positive-session/amendment proof; no weekday inference|

The generator preserves all supplied version/reference IDs, inclusive applicability intervals, OVERLAP and same-document/version conflicting bytes/format/field semantics; it never silently selects a winner or marks supported=true. R09/R10/R11 execute synthetic conflict/overlap/supersession cases. Source production2020route and duplicated backfill/probe assumptions remain untouched. No blind2020→2024replacement, data relabeling or recalculation.
''')
write('03_reference_contract_and_repo_selection.md',header+'''# ADR-OD05R-001 — additive offline verifier

EXTEND_EXISTING stdlib and installed Pydantic frozen/extra-forbid patterns. No new library, network client, DB service, dependency or license adoption. Pandera/Arrow do not establish publisher identity, rights or human authority; new roles DEFER without measured same-corpus benefit and legal/runtime review. Existing package identities are recorded per-runtime; no latest-version/security clearance claim.

The pre-code [design](design.md) fixes strict bounded envelope identity/source/version/acquisition/permission-claim/field-section semantics and optional sample metadata. Pure verify_reference accepts exact bytes plus separate local blobs. SHA/length prove byte identity only. original_identity_verified means the hash matches bytes *declared* original, not authenticated publisher origin. Metadata owner/reviewer/permission values are claims and never trusted approval capabilities. SCHEMA_REFERENCE_VERIFIED/ROW_REFERENCE_VERIFIED/OFFICIAL_REFERENCE_VERIFIED cannot be minted in this phase; all results retain TRUSTED_REVIEW_REQUIRED and official_eligible=false. A future independent authority-root/review-ingestion mechanism is unimplemented by design, not bypassed with test booleans.

ExpectedCorpus independently pins nonzero index/ref/file identity, rejects mutable containers, case collisions and unsafe names. read_bundle performs bounded read-only flat allowlisted loading with links/reparse/hardlink refusal, descriptor identity checks, zero/orphan/moved corpus refusal and typed public code-only errors. Strict UTF8/duplicate-free JSON; UTC and ISOdates; HTTPS without credentials/query/fragment/control/escaped path. Canonical digest od05r.semantic/v1 binds document, scope, version, semantics, permission claims and applicability; excludes operational acquisition/review times, which remain in raw metadata SHA. Publisher announcement/effective dates remain semantic and separate. Restricted ASCII/unescaped canonical URLs are a conservative subset; more general URL/document-format handling needs a reviewed extension.

Bounds: metadata/index64KiB, each blob1MB,16references,32blob entries,64field meanings,64matrix dates,96-character flat filenames,128-character labels. No production-capacity claim. Pure functions have no I/O/import side effects; the loader only reads selected local roots. Existing parser/reference_registry/source policies are not changed. [Measured allocations/times](logs/performance-summary.json) are three bounded synthetic sizes with16envelope calls each, tracemalloc only (not total RSS); no advertised speedup or worst-case guarantee.
''')
write('04_precode_R01_R24_and_F01_F12.md',header+'''# Frozen tests and exact chronology

[Pre-code freeze](logs/preimplementation-freeze.json) at08:52:25UTC binds both new test files before application modules existed; first guarded baseline54API-absence errors, exit1. Missing API is new-feature absence, not a legacy behavioral defect. First implementation53pass/1Windows file-link skip. Later five review tests:55pass/1skip/3fail (root .. traversal, untyped malformed file value, accepted orphan pin). Corrections58pass/1skip. Later two tests reproduced field-semantics conflict misclassified as overlap and mutable expected pins (2fail/59deselected); corrections60pass/1skip. Later tests and scoped Ruff formatting are honestly post-initial-code, never backdated or old-test edits.

Every R01–R24 group existed at freeze, including the external R24 runtime gate represented by a replay vector. [Exact per-node results](logs/R01-R24-results.json) link all current cases and complete runtime metadata. Original frozen SHA and [final freeze](logs/reviewed-source-freeze.json) remain separate. All tests are synthetic; the real OS link/junction cases operate only disposable storage and have passing counterparts.

F01–F12 were declared BLOCKED_REFERENCE in pre-code design: original source SHA, real ZIP/member/schema, era, dates, Decimal, volume units, ordinals, identity, optional columns, reviewed rows, invalid-format negatives, replay/rights/lineage. [F matrix](logs/F01-F12-results.json) counts no official successes. A+B absent; no official-format parser code/fixtures are fabricated. All original OD05 tests/oracle remain byte-identical and pass94cases each runtime.

Initial broad evidence read output was truncated; corrected reads completed remaining numbered reports, and all293prior evidence files were mechanically rehashed. Original inventory was slow but completed read-only; no process was terminated or file overwritten. One new-test patch failed to match formatting and made no edits; corrected patch then executed the negative tests. All executed failing test logs are retained.
'''+ '\n'.join(f'- {group}: '+', '.join(names) for group,names in groups.items()))
write('05_code_delta_and_compatibility.md',header+'''# Exact additive delta

New src/omegadata/parsers/reference_evidence.py: frozen evidence schema, deterministic identity/refusal evaluator, independently pinned corpus contract and safe read-only loader. New era_matrix.py: bounded conflict/overlap/unknown matrix, no source route selection. New tests/unit/test_od05r_reference_evidence.py and od05r_reference_oracle.py:24groups,61parameterized cases, independent literal/hash oracle. [Source SHA ledger](logs/reviewed-source-freeze.json); every runtime's per-command *-inputs.json and [comparison](logs/cross-runtime-inputs.json) establish tested identity.

No existing application/parser/test/oracle/policy/config/CI/dependency/UI/source script modified. The five original OD05 package files, its94case suite and independent oracle remain exact. Public parse/parse_archive semantics and default production flow unchanged; full rights/acquisition/archive/API/storage regressions pass. No route, migration, cached/seed/historical rewrite, production DB/Parquet, release/pointer/signing write. Entry environment/signing/owner prompt retained. New documentation/helpers/logs only under this run. No commit/push/PR/merge.
''')
write('06_independent_reference_oracle.md',header+'''# Independent envelope and corpus oracle

The stdlib-only new oracle never imports verifier/parser code to derive expected fields/hashes. Pre-code literals bind67synthetic PDF-like bytes (explicit SYNTHETIC_TEST_ONLY, not an authentic circular), one independent index/ref/doc count and zero samples, deterministic canonical layout and separate synthetic numeric sample. [Expected vector metadata](logs/reviewed-oracle-vectors.json) includes actual raw and semantic SHA. All three runtimes assert the same digest; test edits of issuer/UTC/original SHA/version/length/sample numeric content/count cause typed refusal or oracle mismatch as appropriate. Valid operational time change preserves semantic SHA but changes metadata SHA; invalid/nonUTCtimes refuse. Raw index pin catches any time-byte mutation during bundle loading.

Missing/empty/truncated/moved/wrong-count corpus and unused file pins fail; counts are not inferred from service inventory. R23 sample10.10→10.11 mutation breaks independent pinned byte identity, not claimed financial truth. Sample-only cannot certify schema, document-only cannot certify rows; invented reviewer/official/approval flags never grant authority. Paraphrase/index/mirror/synthetic/cached/seed identity remains unverified official origin. This is algorithmic independence by the same agent, not independent human consensus or publisher authentication. All official row oracles BLOCKED_REFERENCE.
''')
write('07_source_rights_PIT_security.md',header+'''# Source rights, confidentiality and temporal limits

Real source policies unchanged13PENDING_REVIEW/0APPROVED. Transport off; no provider HTTP/API/browser/curl/sample acquisition. Public search-index research is separately authorized, never source permission or original bytes. Optional permission_ref/reviewer_ref in submitted metadata is merely attributable claimed evidence, not a policy capability; official eligibility always false. A hash cannot authenticate issuer or lawfulness. No original copyrighted bundles or real market records copied into Git.

UTCacquisition/review, announcement, effective scope, actual sample date and PITknown-time are different. No date in a document establishes actual market session or decision-time eligibility. Canonical semantic identity excludes operational time only; metadata raw SHA preserves it. Unknown source terms/date/units/identity remain pending. The reference service never invokes legacy PriceRecord writers.

Guard proofs5cases on each runtime deny DNS/TCP/UDP/subprocess/outside-sandbox writes and fictional signing reads. Every test collection/execution uses guarded disposable roots; test outputs only in fresh logs/sandboxes. File-link/junction/UNC/drive/traversal and nonregular/hardlink paths refuse, with actual cross-platform counterparts. Guard is trusted Python, not a kernel/native-extension sandbox; the local filesystem and directory ownership must be trusted. Parent-check/descriptor mechanisms do not certify arbitrary malicious-owner races, network filesystems or hardware power loss. No signing contents read/hashed/copied; metadata comparison only. Offline rights/security tests plus pipcheck are not a fresh advisory-feed or legal/transitive-license clearance.
''')
write('08_runtime_coverage_evidence.md',header+'# Fresh final verification\n\n'+matrix+'''

Every reviewed environment/collection/targeted/full/Ruff/mypy/pip/compile exit0; all61new cases are accounted for with one actual platform skip per runtime. Original94OD05cases execute unchanged. [Runtime metadata](logs/runtime-matrix.json), [skip pairing](logs/skip-pairing.json), [input identities](logs/cross-runtime-inputs.json). Full stdout/stderr and argv/executable/cwd/UTC/exit/source/fixture hashes are immutable logs/*-reviewed-*.json/.txt and *-inputs.json. Four realdata deselections are not passes. Windows new file-link skip runs on Linux; Linux new junction skip runs on Windows; inherited ten/two skips likewise paired.

Initial accepted-labelled59case full matrices passed but are superseded by final reviewed61case matrices after two additional demonstrated defects. No current claim uses their stale source hashes. Preliminary Ruff9findings/import/semicolon issues corrected only in new files; current qualitychecks pass. DuplicateZIPwarning and Windows3.14SQLite ResourceWarnings retained; no suppression. WSL stale PATH translation messages are launcher warnings, not hidden command errors. Native Linux test copy on /home filesystem; same physical host, no independent CI certificate claimed. No current hosted branch CI success was established by this offline run.

Guard5cases each and performance3cases Windows/Linux pass separately, not added to full regression totals. Exact measured allocations/time in [performance summary](logs/performance-summary.json). Initial imports missingnewAPI, later actual3+2new-code failures, formatting attempts and successful corrected runs remain chronological; no retroactive pre-code claim.
''')
write('09_remaining_defects_and_rollback.md',header+'''# Remaining defects and rollback

Corrected only newly reproduced defects: traversal root, untyped malformed file list, orphan-pinned files, semantic conflict detection and mutable expected corpus pins. No genuine old-code defect correction was claimed from missing API errors. All original code stays intact.

Inherited P0D01signing-key custody/exposure and P0D04publication/export gate remain OPEN. P1production cash2020route/dated format truth, official identity/series/units/calendar/PITsemantics and fixed Parquet overwriteD03 remain outside this phase. No official parser or route integration until documentA/sampleB and separate routeC authority. Raw source/reference authenticity and legal permission unknown. No acceptance of those risks by synthetic tests or old G0process waiver.

P2limits: same-model reviewer/oracle, shared physical host, partial coverage, no online current advisories/transitive legal audit, conservative ASCII/unescaped URL subset, no authenticated human-review authority-root ingestion implemented, no arbitrary hostile directory-owner/kernel/native-extension/network-FS/power-loss certificate. No row-semantic certification from opaque sample byte hashes. Rollback: stop calling new standalone modules; all original paths are already unchanged. Preserve evidence, original records and historical Gatekeepers. No delete/cleanup/reset/stash/migration/relabeling or old fixture replacement.
''')
write('10_gatekeeper_verdict.md',header+'''# OD05R_REFERENCE_VERIFIER_TECHNICAL_PASS_REFERENCE_PENDING

Entry branch/HEAD valid; existing owner G0/G1 and OD05PASS evidence recognized unchanged. All24groups/independent literals frozen before new modules; APIabsence classified correctly. Later adversarial3+2defects red-first corrected with true chronology. Final guarded Windows3.14/3.11/native WSL3.12 full regression, targeted, collection, lint/type/pip/compile pass. Original94OD05cases unchanged; exact new61case accounting and paired OS skips; source/fixture identity before every command; bounded performance and guard denial experiments; preservation original records clean. Same-model procedural Maker/Reviewer/Implementer/Gatekeeper/Historian review, not invented independent human consensus.

Limited PASS applies to the reference verifier only. Official documentA/representative-rowB remain BLOCKED_REFERENCE; F01–F12noofficialpasses. No real publisher-byte/sample/permission/field-review corpus authenticated. Exact raw SHA proves identity only; caller metadata cannot grant official eligibility or change pending source policies. Schema/row verified states and official claims deliberately unavailable until a separately trusted human-review path is provisioned. Current era routing stays unverified/unchanged. GateCroute authority absent. No signing/release/trading/PITcertification, data migration, live acquisition, merge/commit/push or OD06.

Valid with [fresh final mechanical evidence](logs/final-acceptance.json), [runtime matrix](08_runtime_coverage_evidence.md), [reference inventory](01_publisher_reference_inventory.md) and [remaining risks](09_remaining_defects_and_rollback.md). No P0waiver or later phase implied. STOP after OD05R.
''')
write('11_single_next_request.md',header+'''# Exactly one next request

Owner supplies a bounded, lawfully obtained authentic NSE CM reference pack: original versioned publisher documents/annexures and representative dated rows for the disputed2020andJune24–July8,2024boundaries, their original SHA/length/provenance, actual reference-use permissions and independent human-reviewed field/date/unit/identity expectations. This is one corpus-supply/review request, not authorization for live downloads, production routing, release/signing, Git lifecycle or OD06. Until supplied, official cases remain BLOCKED_REFERENCE and the standalone verifier's limited technical result stands. STOP.
''')
save('report-sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.md')})
print(json.dumps(quality,indent=2))
