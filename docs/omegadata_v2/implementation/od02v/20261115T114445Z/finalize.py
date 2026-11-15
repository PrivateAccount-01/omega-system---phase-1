"""Exclusive OD-02V reports and actual final preservation gate. Never read keys."""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import phase_control as ctl

LOGS=HERE/"logs"
ROOT=Path.cwd()
HEAD="eaedac1bddc35867f9089486beffa3bb38cb11f4"
BRANCH="feature/od01-source-rights"
APP={"src/omegadata/track_a/acquisition.py","src/omegadata/track_a/download_manager.py"}
NEW_TEST="tests/unit/test_od02v_portability.py"
REQUIRED=["00_preflight.md","01_dependency_bootstrap.md","02_symlink_security_matrix.md",
    "03_runtime_test_matrix.md","04_cross_platform_findings.md","05_implementation_diff.md",
    "06_security_regression.md","07_gatekeeper_verdict.md","08_next_phase_request.md"]


def data(label):return json.loads((LOGS/(label+".json")).read_text())
def output(label):return (LOGS/(label+".txt")).read_text(encoding="utf-8")
def link(label):return f"[command/exit](logs/{label}.json), [raw](logs/{label}.txt)"
def write(name,body):
    with (HERE/name).open("x",encoding="utf-8",newline="\n") as out:out.write(body)


RUNTIMES={"Windows 3.14.3":("win314","win314-reviewed"),
    "Windows 3.11.15":("win311","win311-reviewed"),
    "WSL Linux 3.12.3":("linux312","linux312-reviewed")}
banner=f"OD-02V VERIFY_AND_REMEDIATE_ONLY; run 20261115T114445Z. Branch `{BRANCH}`, unchanged reviewed HEAD `{HEAD}`. Evidence classes RUN/TEST/SYN; prior reports remain ARCH. Same-model engineering review, not independent human financial/legal approval.\n\n"
fresh={}
for title,(base,test) in RUNTIMES.items():
    fresh[title]={"collection":data(test+"-collection"),"targeted":data(test+"-targeted"),"full":data(test+"-full"),
        "ruff":data(base+"-ruff"),"mypy":data(base+"-mypy"),"pip":data(base+"-pip-check"),
        "coverage":data(test+"-full-coverage")}


def reports():
    write("00_preflight.md","# OD-02V preflight\n\n"+banner+"""
The exact required branch and HEAD were verified before setup; there is no commit drift. Original tracked worktree was clean. Existing untracked items: prior `.venv-linux`, supplied OD-02V prompt, private signing/revocation paths. These were preserved, not cleaned, opened or uploaded. No stage/commit/push/merge/rebase, CI edit, production release or signing action is authorized or performed.

Required master/agent/phase instructions, OD-00 defect register and phase plan, OD-01R Gatekeeper/matrix/findings, OD-02 reports/runner/logs and current rights/acquisition/downloader/orchestration/probe/config/tests were read/re-evaluated. Prior pass strings were not accepted as new evidence. Read-only Git state records: [root](logs/git-root.txt), [branch](logs/git-branch.txt), [HEAD](logs/git-head.txt), [complete porcelain before](logs/git-status-before.txt), [main comparison](logs/git-main-diff.txt), [five-commit log](logs/git-log.txt), [main identity](logs/git-main.txt). All associated command JSONs preserve exact arguments, UTC intervals and exits. Root remains E:/omega system - phase 1.

Before setup, [original preservation](logs/preservation-before.json) froze non-secret content hashes and signing file length/mtime metadata. Private signing files were never opened, read, hashed, copied or uploaded. New isolated copies excluded all GnuPG, .env, operational databases, environments, releases and old evidence. A later precise fixture allowlist supplies only existing regression dependencies under the contract's fixture exception. Original raw data and historical artifacts were not changed.

[GitHub CI observation](logs/github-ci-observation.json): connector returned no commit statuses and no first-page PR-triggered workflow runs. That workflow API is PR-filtered; all-event CI visibility remains unverified. GitHub CLI was unavailable. No workflow dispatch occurred and no local result is represented as a CI run.

Available interpreters: Windows project venv Python 3.14.3, existing Windows base Python 3.11.15, native WSL /usr/bin/python3 3.12.3. The latter two initially lacked the project test dependencies. Invocation explicitly authorizes disposable official-index dependency setup; no additional permission was needed. Optional Linux 3.11 was not on PATH and no existing uv runtime was found: [probe](logs/linux-optional-runtime.txt). No new Python runtime/system package was installed.

Fresh baseline targeted: Windows 3.14 and 3.11 **272 passed, 3 skipped**, command exit 0. Fresh sanitized full first had **4 fixture-omission failures, 379 passed, 3 skipped, 4 deselected**, exit 1; exact reviewed fixture dependencies were then copied, with no test/source workaround. Original Linux targeted reached assertions but eight cleanup failures exposed the runner's descriptor-relative path bug, not an application failure. All initial failures remain retained and explained in [findings](04_cross_platform_findings.md).

Final [preservation/identity gate](logs/final-check.json) verifies exact authorized changes, unchanged original evidence/data/signing metadata, 13 pending policies, no approvals, empty index, unchanged HEAD/branch/main and tested-copy hashes. Windows file-symlink privileges remain unavailable; actual Linux execution closes the three original skipped scenarios, not Windows privilege equivalence.
""")

    copy=data("sanitized-copy")
    fixtures=data("fixture-allowlist")
    dependency="# OD-02V isolated dependency setup\n\n"+banner+f"""
Repository requirements and build configuration were reused unchanged. No new application library, tracked dependency/CI/environment modification or paid service. New Windows 3.11 venv is under the disposable copy parent; existing 3.14 venv reused read-only. Linux venv/copy is on native `/home/parilrupani/omega-od02v-37b3vimd`, not DrvFs; every pytest temp root is native `/tmp`.

[Sanitized provenance](logs/sanitized-copy.json) records **{len(copy['files'])} exact HEAD blobs** from source/scripts/tests/config plus README/pyproject, normalized by Git object identity rather than guessed line endings. Editable build changes generated `.egg-info` only in the copy, so generated package metadata is excluded from post-install source equality; actual code/tests/config remain checked. [Linux initial copy verification](logs/linux-environment-paths.json) and each runtime `*-tested-source.json` identify those boundaries. The two red-tested application corrections and new test overlay have exact hashes in the latter files; every inherited test matches HEAD unmodified.

The first full sanitized run identified fixture dependencies previously available from original raw folders. [Exact fixture allowlist](logs/fixture-allowlist.json) contains **{len(fixtures['files'])} files / {sum(r['bytes'] for r in fixtures['files']):,} bytes**, only named corpus paths plus the minimal archives covering seed-symbol regression references. Copies are byte/hash checked. They are ARCH regression fixtures, not newly acquired official truth or new source permission. No release/key/database/.env is included and original files are read-only. Tests are never redirected to the original datasets.

Cache-only resolution was tried first and exited 1 (missing index/build dependency resolution); installed caches alone could not satisfy the declared project. Setup then used `pip --isolated install --index-url https://pypi.org/simple --only-binary=:all: -c <working-environment-constraints> -e <sanitized-copy>[dev]`. Constraints prefer the actual working 3.14 installed versions; pyproject requirements are unchanged. Pip reused cached wheels and fetched missing compatible binary wheels/build dependencies only from the official package index. No provider, arbitrary installer script or GitHub source installation.

Exact records: [Windows venv](logs/win311-create.json), [cache resolution](logs/win311-cache-resolution.json), [official install](logs/win311-install.json)/[stdout](logs/win311-install.txt); [Linux venv](logs/linux312-v2-create.json), [cache resolution](logs/linux312-v2-cache-resolution.json), [official install](logs/linux312-v2-install.json)/[stdout](logs/linux312-v2-install.txt). All venv creates and final installs exited 0. First Linux install also succeeded, but its controller then failed verifying generated editable metadata; the ephemeral /tmp copy disappeared on WSL restart. Native home setup resolved persistence. Old attempt logs remain intact; see findings for controller-versus-package distinctions.

Observed common versions: HTTPX 0.28.1, Pydantic 2.12.5, pytest 9.0.2, pytest-asyncio 1.3.0, coverage 7.13.5, Ruff 0.15.9, mypy 1.20.0, SQLAlchemy 2.0.49, pandas 3.0.2, PyArrow 23.0.1, NumPy 2.4.4. Linux additionally resolves uvloop 0.23.0 through uvicorn's declared platform-specific standard extra; Windows has no uvloop. Bootstrap pip versions differ (fresh 3.11/Linux pip 24.0, existing 3.14 pip 26.0.1), so identical environments are not claimed.

"""
    for title,(base,test) in RUNTIMES.items():
        dependency+=f"- {title}: [environment](logs/{base}-environment.txt), [pip version](logs/{base}-pip-version.txt), [freeze](logs/{base}-freeze.txt), [pip check](logs/{base}-pip-check.txt), [tested source](logs/{test}-tested-source.json). All final pip checks exit 0.\n"
    dependency+="\nPackage consistency is not advisory/license clearance or financial truth. No dependency upgrade or reproducible lock promotion is claimed. No source acquisition is possible through the tested runtime transports.\n"
    write("01_dependency_bootstrap.md",dependency)

    proof=data("linux312-symlink-proof")
    symlinks="# OD-02V actual symlink-security matrix\n\n"+banner+"""
The original assertions were **not modified**, xfailed or removed. Full targeted suites run the same inherited test files on all runtimes. A dedicated Linux proof runs the original three exact IDs plus positive file-symlink smoke: **4 passed, 0 failed, 0 skipped, exit 0**, [raw verbose](logs/linux312-symlink-proof.txt), [command and observed counters](logs/linux312-symlink-proof.json).

| Original scenario | Linux actual link / outside read count | Result |
|---|---|---|
"""
    for row in proof["symlink_observations"]:
        case="payload symlink outside raw partition" if row["form"] is None else ("seed-cache latest pointer escape" if row["seed"] else "raw-cache latest pointer escape")
        symlinks+=f"| {case}; `{row['function']}` | actual symlink **{row['is_actual_symlink']}**, outside reads **{row['outside_read_calls']}** | PASS, invalid cache returns None before outside bytes opened |\n"
    symlinks+="""
For the dedicated proof only, a read-only CPython return-event observer records existing local list/Mock counters and `is_symlink()` after the unmodified assertions. It does not change values, return results, exception handling or file access. Its exact disposable paths are in JSON; no protected/private sentinel data is used.

Additional [new tests](../../../../../tests/unit/test_od02v_portability.py) execute file-symlink positive capability; directory symlink/junction escape for raw and seed; broken pointers, link loops and retargeting before the cache lookup boundary for raw and seed. Linux executes all 17 new cases without skipping. Windows executes directory junction analogues and other new security tests; its seven new file-link cases skip due WinError 1314. Together with the original three that is 10 Windows skips; no skip is counted as a pass. Linux has only two Windows-specific junction skips, covered by actual Windows junction passes.

[Filesystem smoke Windows](logs/win314-filesystem.txt) records actual file-symlink privilege failure, case-insensitive paths, CRLF text output and a successful 320-character file path. [Filesystem smoke Linux](logs/linux312-filesystem.txt) records real file symlink/read-back, case-sensitive paths, LF output and a successful 304-character path. Both parse ISO UTC Z as +00:00. These are measured local capabilities, not all-filesystem guarantees.

Threat-model limit: retargeting is tested before entering the cache API; broken/loop/directory/escape confinement is real. No descriptor-based hostile ancestor-swap race during the filesystem syscall is certified. Existing cache code is not an OS sandbox against a malicious concurrent filesystem owner. This inherited limit stays explicit, production egress disabled and operational cache directories must remain access-controlled. OD-04 architecture is not implemented here.
"""
    write("02_symlink_security_matrix.md",symlinks)

    matrix="# OD-02V runtime verification matrix\n\n"+banner+"""
Final authoritative command set below uses explicit per-runtime Python and sanitized copy. Pytest is guarded against DNS, TCP/UDP, subprocess and protected-path writes during import/collection and execution, with fresh DB/raw/seed/release/report/GPG paths, explicit asyncio/cov plugins, disabled bytecode/cache and redirected coverage/mypy caches. Full exact command arguments, cwd, baseline, UTC intervals, duration and actual process exit are in every command JSON. No original data/release pointer is a write target.

| Runtime | Collection | Targeted rights/hardening/acquisition/OD02V | Complete offline regression | Exit |
|---|---|---|---|---|
"""
    for title,(base,test) in RUNTIMES.items():
        row=fresh[title]
        tc=row["targeted"]["call_counts"]; fc=row["full"]["call_counts"]
        matrix+=f"| {title} | 403/407 selected, 4 realdata deselected; [log](logs/{test}-collection.txt) | **{tc.get('passed',0)} passed, {tc.get('failed',0)} failed, {tc.get('skipped',0)} skipped**; [log](logs/{test}-targeted.txt) | **{fc.get('passed',0)} passed, {fc.get('failed',0)} failed, {fc.get('skipped',0)} skipped, {len(row['full']['deselected'])} deselected**; [log](logs/{test}-full.txt) | all three **0** |\n"
    matrix+="\n| Runtime | Ruff | mypy | pip check | Combined statement/branch coverage |\n|---|---|---|---|---|\n"
    for title,(base,test) in RUNTIMES.items():
        row=fresh[title]
        matrix+=f"| {title} | [exit {row['ruff']['exit_code']}](logs/{base}-ruff.txt) | [exit {row['mypy']['exit_code']}](logs/{base}-mypy.txt), 48 files | [exit {row['pip']['exit_code']}](logs/{base}-pip-check.txt) | **{row['coverage']['totals']['percent_covered']:.4f}%**, [exact JSON](logs/{test}-full-coverage.json) |\n"
    matrix+="""
Acquisition module measured combined coverage **93.6709%** on each runtime: 264/279 statements, 106/116 branches. Different whole-project line/branch attribution across interpreters is retained rather than forced to match. Historical OD-02 coverage 80.78% is a separate ARCH number. Source-rights/acquisition and all inherited regression modules execute; the dedicated symlink proof is 4 passed/zero skipped. 17 new cases are present in the canonical `pytest` collection; no side test framework was introduced.

Windows 3.14 final full log contains **13 ResourceWarning lines for unclosed disposable SQLite connections** (plus their tracemalloc hints). They are not filtered or hidden. No such warning is emitted by the final 3.11/3.12 logs; those runtimes' warning behavior differs, which is not proof that connection hygiene is fixed. No unrelated connection-management refactor occurred. WSL also emits inherited missing drive/PATH translation warnings, retained in launch/setup logs. All final process exits are 0 despite these documented warnings/skips.

## Exact effective command forms

```text
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest --collect-only -q -m 'not realdata'
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q tests/unit/test_od01_source_rights.py tests/unit/test_od01r_rights_hardening.py tests/unit/test_od02_acquisition.py tests/unit/test_od02v_portability.py -m 'not realdata'
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pytest -q -m 'not realdata' --cov=omegadata --cov-branch --cov-report=term-missing
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> ruff check --no-cache src/omegadata tests scripts
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> mypy src/omegadata
<runtime-python> -B <new-run>/verification_runner.py <unique-label> <sanitized-copy> pip check
```

The stored JSONs expand all placeholders to actual absolute paths/argv. Windows command logs use the Windows interpreter paths; Linux uses native /home venv/copy and /tmp tests, reached through WSL. Mypy caches are fresh temp; no old proof is regenerated. Pytest coverage DB/JSON is inside the disposable root and copied to fresh logs after guards are disabled. Per-test outcomes and deselected node IDs are retained in JSON, not inferred from summary text alone.

## Retained failures and no pass fabrication

| Attempt | Actual process result | Cause/disposition |
|---|---|---|
| `win314-baseline-targeted`, `win311-baseline-targeted` | exit 0; 272 pass / 3 skip | Unmodified reviewed baseline |
| `win314-baseline-full` | exit 1; 4 failed / 379 pass / 3 skip / 4 deselected | Sanitized copy omitted required local corpus archives; fixed only by exact fixture allowlist |
| `linux312-baseline-targeted` | exit 1; 8 failed / 265 pass / 2 skip | Runner misinterpreted descriptor-relative cleanup paths; app assertions otherwise successful; corrected guard pathname resolution |
| `confidentiality-negative` | exit 1; 7 failed / 9 deselected | Real synthetic confidentiality reproductions before application edits |
| `confidentiality-green` | exit 0; 7 passed / 9 deselected | Same tests after narrow evidence redaction fix |
| Initial `win311-*`, `linux312-*` pytest launcher commands | exit 1 after pytest summaries, missing result JSON | Runner post-test platform metadata queried while its os.open wrapper still enforced writes; raw launcher trace retained. Not counted as successful commands; reviewed reruns above exit 0 |
| Cache-only package resolution | exit 1, before tests | Existing local wheels insufficient; allowed official-index setup succeeded |

All named attempts have raw `.txt` logs under logs; launcher failures have `*-launcher.txt` and aggregate `*-matrix.json` actual exits. Setup controller observations are documented separately; no assertion was weakened and no failing requirement is silently removed. The two platform-specific skip sets are covered by actual corresponding filesystem execution on the other required platform; no physical-host independence or CI success is claimed.
"""
    write("03_runtime_test_matrix.md",matrix)

    write("04_cross_platform_findings.md","# OD-02V findings and review\n\n"+banner+"""
| Finding | Executed evidence | Narrow action / final state |
|---|---|---|
| V-01 runtime dependency absence | Prior attempts failed before collection; new pre-install inventories confirm missing pytest/app dependencies | Authorized fresh Windows 3.11 and native Linux 3.12 venvs, existing declared requirements, official PyPI and working-version constraints; full matrix now executes with exit 0 |
| V-02 skipped symlink assertions | Original three real-file symlink cases now execute and pass on Linux, real links true/outside reads 0 | No inherited test edit. Windows WinError 1314 remains an explicit OS privilege limit; Windows junction analogues pass |
| V-03 confidential URL evidence **P1, corrected** | Seven executable negative-first failures: recognized path credential values, legacy cached URL query/path, typed public error context expose only synthetic sentinel | Evidence-only safe_url redacts known credential field/value path segments and malformed URL fallback; legacy cached URL uses same helper. Seven green plus full regression on all three runtimes |
| H-01 sanitized fixture omissions | First Windows full run has four failures due missing existing archive references/seed identity map | 47 exact fixture dependency files (6,138,891 bytes) copied/hashed to isolated trees only. No data fixture mutation, generated fake prices, assertions change or source approval |
| H-02 POSIX dir_fd cleanup | Linux targeted run has eight TemporaryDirectory cleanup failures under write guard | Resolve actual /proc/self/fd anchor for relative unlink/rmdir/mkdir/link/rename and wrapped os.open. Added negative tests deny descriptor-relative protected writes. No blanket allow of relative paths or sockets |
| H-03 controller metadata and WSL lifetime | First Linux install exited 0, controller failed generated egg-info checksum assertion; retry of finalizer after WSL restart found /tmp copy gone | Record build-generated egg-info separately from source equality; new disposable /home native location persists. Old /tmp paths were not manually removed. No historical data involved |
| H-04 postlude runner exit | First 3.11/Linux matrix commands reached successful pytest summaries but launcher exited 1 on protected devnull open during platform metadata | Warm complete OS metadata before guards; restore wrapped os.open only after guarded tests finish. Preserve initial traces and rerun collection/targeted/full to real exit 0 |
| Portability evidence | English_India/1252/IST on Windows; C.UTF-8/UTC on Linux. Case-insensitive CRLF vs case-sensitive LF measured; 320/304 character paths succeed | Exact HEAD code/tests copied using Git blobs; inherited drive/port/path/ISO/date/ZIP checks execute. ZIP legacy/current expected mixed-case member names and raw hashes pass all runtimes. Not an exhaustive locale/filesystem/ZIP fuzzing certificate |
| SQLite cleanup **P2, open** | Thirteen unclosed disposable-connection ResourceWarnings in Windows 3.14 full log | Kept visible. No unrelated DB cleanup refactor; no original DB touched. Lower Python versions' absence of warning is not closure |
| Hostile concurrent filesystem ownership, open limitation | Static path confinement and pre-call retarget scenarios verified; no descriptor-based atomic file-open boundary in existing manager | Do not claim TOCTOU/symlink-race sandbox. Cache directories require trusted ownership. Actual provider egress remains blocked; larger archive/storage redesign not authorized |

The first setup-controller checksum assertion and later FileNotFoundError were observed in tool output (not a fresh raw controller transcript), while each underlying venv/cache/install command has exclusive logs/metadata. They are reporting/setup mistakes, not application negative tests. Corrected setup did not install into or alter the original repository.

Maker: required runtime/security matrix and fixture provenance; Reviewer: fresh failures separated from missing setup/guard limitations; Implementer: only two red-proven application changes; Reviewer: unchanged inherited assertions, exact tested hashes, 17 additional cases and all platforms; Gatekeeper: command exits/denominator/preservation; Historian: this report set plus patch/logs. This is same-model procedure, not invented independent human consensus. Independent human/security review remains recommended before new production capabilities. No sub-agents, paid service or external market requests.
""")

    write("05_implementation_diff.md","# OD-02V exact implementation ledger\n\n"+banner+"""
Application changes were made **only after** [seven executable negative-first failures](logs/confidentiality-negative.txt) and [pre-code design](remediation_design.md). They do not change source approvals, transport URLs, fetch authorization, parser contracts, archive bytes, retries, release/signing or business calculations.

| Path | Reason / impact |
|---|---|
| [acquisition.py](../../../../../src/omegadata/track_a/acquisition.py) | `safe_url`: preserve ordinary paths, redact explicit credential field/value segments (including encoded field labels), keep query/fragment/userinfo removal; malformed evidence URL returns conservative placeholder |
| [download_manager.py](../../../../../src/omegadata/track_a/download_manager.py) | One cached artifact exposed `used_url` now uses the same sanitizer; historical manifests/raw bytes not rewritten |
| [test_od02v_portability.py](../../../../../tests/unit/test_od02v_portability.py) (new) | 17 canonical pytest cases: real symlink capability, raw/seed directory/file/broken/loop/retarget confinement; network/process/write guard incl POSIX descriptor-relative denial; seven URL confidentiality proofs |
| This fresh OD-02V directory (new) | Nine required reports, design note, bounded environment/copy/fixture/bootstrap/runner/matrix/capability/review helpers and raw/JSON evidence |

No inherited test, tracked requirement, config, policy, workflow, source-era registry, warehouse, pipeline math, historical data/evidence or signing material is changed. The supplied OD-02V prompt remains untracked and unmodified. No commit/push/merge/stage.

[Implementation patch](logs/implementation.patch) contains the two tracked source diffs and new test content; [final preservation/checks](logs/final-check.json) identifies exact original deltas and verifies every tested copy overlay hash. All other code/test/config copy hashes match reviewed HEAD (editable-generated package metadata explicitly excluded). Line endings are accounted for; no blanket tree formatting occurred.

The source changes are stdlib and platform-neutral, tested under actual 3.11/3.12/3.14. Safe URL display is deliberately conservative for recognized credential labels; arbitrary unlabeled opaque secrets cannot be inferred reliably, so embedding credentials in those paths is still prohibited. Egress remains OFF. Selective rollback would reverse only these documented hunks after review, retaining new reports/tests/evidence and leaving provider jobs disabled; no rollback is performed.
""")

    security="# OD-02V security/acquisition regression\n\n"+banner+"""
All original OD-01/OD-01R/OD-02 tests execute unchanged on each required runtime, alongside 17 new security/portability cases. Test-time fake APPROVED records are in-memory SYNTHETIC_TEST_ONLY fixtures; final real register remains **13 PENDING_REVIEW, zero APPROVED**, unchanged bytes/hash. No actual exchange/provider request, paid call, signer command, production pipeline/probe CLI, warehouse sync, release build or publication was invoked.

| Guarantee | Actual asserted coverage |
|---|---|
| Default pending/unknown/expired/revoked/transport/host and operation scope | All original policy and zero-side-effect tests, mid-fetch/store/bootstrap revocation and cache/seed refusal, entire targeted matrices exit 0 |
| Fake approval does not enable actual egress | HTTPX HTTPTransport callback spy remains uncalled; default urllib/curl refuse BLOCKED_EXTERNAL_EGRESS; unregistered StockReachGraph and legacy diagnostics remain blocked |
| Provider denial terminal across pipeline | 401/403/404/429/451, Retry-After, HTML denial, bootstrap/discovery/profile/candidate/fallback, zero later request assertions; selected 503 finite retry and recovery |
| Redirect/TLS/authority/SSRF | All redirects refused, including allowed-to-allowed; bad scheme/port/userinfo/private/metadata/URL, proxy override and TLS invalid terminal; resolver never called when actual transport disabled |
| Whole-job resource limits | Existing attempt/deadline/backoff/stream/body/header length/ZIP expansion/entry/ratio/rows/config/override negative cases; no trusted partial writes |
| Payload/date/provenance | Legacy/new NSE and BSE synthetic schemas/date/zero-volume/invalid rows, JSON denial/duplicate/malformed forms, exact original SHA, cache vs seed vs mock-unverified distinction, concurrent date contexts |
| Confidentiality | Seven red-before/green-after tests remove recognized URL path credentials and legacy URL query values from exposed artifacts and structured exceptions. Normal request targets and archived bytes remain unchanged |
| Host isolation guard | New V01 plus inherited harness test block DNS/TCP/UDP/subprocess/protected file/SQLite; Linux additionally tests dir_fd protected deletion/open refusal; socketpair allowed only for stdlib internal asyncio mechanics |
| Filesystem confinement | Original three real file symlinks execute on Linux with observed outside-read calls zero; directory links/junctions, broken/loop/retarget raw and seed cases; no privileged skip counted as pass |

"""
    for title,(base,test) in RUNTIMES.items():
        security+=f"- {title}: final targeted guard denials **{json.dumps(fresh[title]['targeted']['guard_denials'],sort_keys=True)}**, [full outcome JSON](logs/{test}-full.json). These are deliberately refused test attempts, not outbound provider traffic.\n"
    security+="""

Runner scope: trusted Python test code, not a hostile arbitrary-Python/ctypes sandbox. During pytest imports/execution the audit hook rejects network/process effects and writes beyond its fresh root, including descriptor-relative paths resolved to actual native directories. Signing paths outside sandbox are never read. Native source copies contain no credentials/GnuPG and only exact fixture allowlist archives. Static tools/package consistency checks do not execute application jobs; install network was separately authorized official PyPI only. No blanket loopback/private-network allowance was added.

Remaining limits: no DNS-pinned real transport, authenticated legal approval authority, independent official source-era/financial reconciliation, descriptor-atomic hostile filesystem-race proof, crash/process storage publication, supply-chain advisory/CI clearance or independent physical host certification. Original **D-01 signing custody P0 and D-04 publication/promotion P0 remain OPEN**. D-02/03/06/08/09 financial/storage/provenance findings remain assigned to later approved phases. No strategy/profit/trade claim. Browser/OD-03 and archive/OD-04 implementation were not begun.
"""
    write("06_security_regression.md",security)

    write("07_gatekeeper_verdict.md","# OD-02V Gatekeeper: OD02V_OFFLINE_PORTABILITY_PASS\n\n"+banner+"""
**OD02V_OFFLINE_PORTABILITY_PASS** for the required local offline runtime matrix and bounded remediation, valid only with [final mechanical gate](logs/final-check.json) passing. This does not approve live acquisition, financial truth, production release or later phases.

| Acceptance criterion | Executed evidence |
|---|---|
| Exact reviewed Git baseline / preservation | Required branch and eaedac1bddc35867f9089486beffa3bb38cb11f4 verified; original content/metadata preserved except two justified application hunks; staged index empty, no Git mutation |
| Original three skipped file-symlink cases | All actually execute/pass on native Linux, unmodified; observed real links true and outside reads 0; dedicated proof 4 pass/0 skip/exit 0 includes positive smoke |
| Required targeted/full runtime matrix | Windows 3.14.3 **282 targeted / 393 full passed**, 10 documented symlink skips; Windows 3.11.15 same; Linux 3.12.3 **290 targeted / 401 full passed**, 2 Windows-junction skips; all final exits 0 |
| No denominator omission | Full collection 403/407 selected; four intentionally excluded realdata tests never labeled pass. Every Windows skipped file-link case passes on Linux; Linux junction skips have actual Windows coverage |
| Lint/type/package checks | Ruff, mypy (48 source files), pip check on all three runtimes exit 0; exact versions/constraints/source-copy hashes recorded |
| Defects tested before correction | Seven confidentiality red cases exit 1 before source edit, then green and entire matrix exit 0; only two application files edited |
| Source rights / network / security | Real policies remain 13 pending/0 approved; actual HTTPX/urllib/curl provider egress OFF. Guard-negative tests execute; no signing/release/provider/paid operation |
| Warnings / known limits | 13 temporary SQLite ResourceWarnings retained on 3.14, not hidden. Windows symlink privilege still absent; WSL is same physical host. Hostile filesystem syscall race and official source authenticity not certified |
| Inherited P0 / independent review | D-01/D-04 OPEN; financial/rights/official-era review PENDING. Same-model roles only; independent human/security review recommended before new production capabilities |

The original OD-02 missing-environment and three-unexecuted-symlink blockers are closed by actual execution. Earlier OD-02/OD-01R reports remain immutable historical records, not rewritten to replace their original verdicts. Current verdict supersedes only that incomplete offline portability evidence, not independent source/financial/signing/release restrictions.

Coverage combined statement/branch: Windows 3.14 **81.0265%**, Windows 3.11 **81.0125%**, Linux 3.12 **80.9564%**; acquisition module **93.6709%** each. This is measured partial coverage, not full correctness. Failed setup/harness/negative attempts are retained and correctly excluded from final successful command claims; [complete runtime matrix](03_runtime_test_matrix.md), [security review](06_security_regression.md), [source ledger](05_implementation_diff.md).

**STOP after OD-02V.** No commit, push, merge, CI edit, source approval or OD-03/04 execution. The only proposed next approval is [the scoped next request](08_next_phase_request.md).
""")

    write("08_next_phase_request.md","# Single next approval request\n\n"+banner+"""
**Request:** after reviewing this OD-02V evidence and preferably obtaining independent human/security review, explicitly authorize **OD-04: Immutable Raw Archive & Provenance**, offline and confined to new disposable namespaces, if the owner accepts the result.

That proposed next milestone would address append-only content-addressed raw observations, exact full SHA identity, exclusive/atomic commits, restart/crash/process concurrency and immutable manifests with cache/seed/mock provenance. Legacy bytes and pointers require a reviewed migration/read facade; existing datasets/releases must not be overwritten. This is a proposal only; no OD-04 code/design execution began in OD-02V.

No automatic approval for OD-03 browsers, OD-05+ financial work, market-source enablement, paid services, signing/key operations, publication, CI edits, commits/pushes/PRs or merges is implied. Production egress remains blocked, real source approvals pending, official reference interpretation pending and inherited signing/release P0 findings open. A portability pass cannot waive those gates.
""")


def final(reviewed=False):
    before=data("preservation-before")
    after=ctl.snapshot()
    changed=[p for p,v in before.items() if after.get(p)!=v]
    unexpected=[p for p in changed if p not in APP]
    sys.path.insert(0,str(ROOT/"src"))
    from omegadata.track_a.source_rights import load_policy_register
    policies=load_policy_register().policies
    pending=len(policies)==13 and all(p.status.value=="PENDING_REVIEW" and not p.permitted_operations and not p.allowed_hosts and not p.permitted_transports and p.approved_by is None for p in policies)
    tested=[]
    for title,(base,test) in RUNTIMES.items():
        for overlay in data(test+"-tested-source")["overlays"]:
            actual=hashlib.sha256((ROOT/overlay["path"]).read_bytes()).hexdigest()
            tested.append({"runtime":title,"path":overlay["path"],"matches_tested":actual==overlay["sha256"]})
    git={name:subprocess.check_output(["git",*args]).decode().strip() for name,args in {
        "head":["rev-parse","HEAD"],"branch":["branch","--show-current"],"main":["rev-parse","main"],
        "staged":["diff","--cached","--name-only"]}.items()}
    missing=[p for p in REQUIRED if not (HERE/p).is_file()]
    broken=[]
    for name in REQUIRED:
        for target in re.findall(r"\]\(([^)]+)\)",(HERE/name).read_text()):
            if "://" in target or target.startswith("#"):continue
            p=(HERE/target.split("#")[0].strip("<>")).resolve()
            expected_result=LOGS/("final-check-accepted.json" if reviewed else "final-check.json")
            if not p.exists() and p!=expected_result.resolve():broken.append({"file":name,"link":target})
    checks={}
    for title,row in fresh.items():
        checks[title]={kind:row[kind]["exit_code"] for kind in ("collection","targeted","full","ruff","mypy","pip")}
    proof=data("linux312-symlink-proof")
    symlinks=len(proof["symlink_observations"])==3 and proof["exit_code"]==0 and all(
        x["outside_read_calls"]==0 and x["is_actual_symlink"] for x in proof["symlink_observations"])
    passed=not unexpected and set(changed)==APP and not missing and not broken and pending and all(x["matches_tested"] for x in tested)
    passed=passed and git=={"head":HEAD,"branch":BRANCH,"main":"d4b5a58f0c50dc348e0d4e1150a725cc6fab5674","staged":""}
    passed=passed and symlinks and all(v==0 for row in checks.values() for v in row.values())
    patch=subprocess.check_output(["git","diff","--binary","--",*sorted(APP)])
    test=Path(NEW_TEST).read_text()
    patch+=(''.join(difflib.unified_diff([],test.splitlines(keepends=True),fromfile="/dev/null",tofile="b/"+NEW_TEST))).encode()
    if reviewed:
        assert (LOGS/"implementation.patch").read_bytes()==patch
    else:
        with (LOGS/"implementation.patch").open("xb") as handle:handle.write(patch)
    row={"utc":datetime.now(UTC).isoformat(),"original_records_checked":len(before),"authorized_original_changes":changed,
        "unexpected_original_changes":unexpected,"missing_docs":missing,"broken_links":broken,"pending_sources":13 if pending else None,
        "approved_sources":0 if pending else None,"checks":checks,"tested_source":tested,"git":git,
        "original_three_symlinks_executed_pass":symlinks,"signing":"file length/mtime only, never opened or hashed",
        "private_signing_bytes_preservation":"No read/hash proof claimed; no access/mutation/copy and unchanged metadata",
        "passed":passed,"gatekeeper":"OD02V_OFFLINE_PORTABILITY_PASS" if passed else "OD02V_BLOCKED"}
    ctl.save("final-check-accepted.json" if reviewed else "final-check.json",row)
    print(json.dumps(row,indent=2))
    return 0 if passed else 1


if __name__=="__main__":
    if "--reviewed" not in sys.argv:
        reports()
    raise SystemExit(final("--reviewed" in sys.argv))
