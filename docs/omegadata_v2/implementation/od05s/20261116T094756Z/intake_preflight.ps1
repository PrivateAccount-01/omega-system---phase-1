$ErrorActionPreference = 'Stop'
$started = [DateTime]::UtcNow.ToString('o')
$repo = (Get-Location).Path
$outRoot = $PSScriptRoot
$logs = Join-Path $outRoot 'logs'
if (Test-Path -LiteralPath $logs) { throw 'Fresh log directory required' }
New-Item -ItemType Directory -Path $logs | Out-Null
function Save-Json($name, $body) {
    $target = Join-Path $logs $name
    if (Test-Path -LiteralPath $target) { throw 'Evidence overwrite refused' }
    $body | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $target -Encoding UTF8
}
function Digest($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$head = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne '25fb5aa4a2f4312e7bfafb9084c29aa95ee2bd48') { throw 'HEAD mismatch' }
$branch = (git branch --show-current).Trim()
if ($branch -ne 'feature/od01-source-rights') { throw 'Branch mismatch' }
$status = @(git status --porcelain=v1)
$mergeBase = (git merge-base main HEAD).Trim()
Save-Json 'repo.json' @{head=$head;branch=$branch;merge_base_main=$mergeBase;status=$status;utc=$started}
$before = @{}
$paths = @(git ls-files -- src tests scripts config docs/omegadata_v2/implementation/od05r docs/omegadata_v2/implementation/od05_impl)
foreach ($path in $paths) {
    if ($path -match '(^|/)(gnupg|private-keys-v1.d|openpgp-revocs.d)(/|$)') { throw 'Secret path outside allowlist' }
    $before[$path] = Digest $path
}
Save-Json 'preservation-before.json' $before
$oldRoot = 'docs/omegadata_v2/implementation/od05r/20261116T084526Z'
$oldHashes = Get-Content -LiteralPath "$oldRoot/logs/evidence-sha256.json" -Raw | ConvertFrom-Json
$checked = 0
foreach ($p in $oldHashes.PSObject.Properties) {
    if ((Digest "$oldRoot/$($p.Name)") -ne $p.Value) { throw "Prior evidence identity mismatch: $($p.Name)" }
    $checked++
}
$oldFreeze = Get-Content -LiteralPath "$oldRoot/logs/reviewed-source-freeze.json" -Raw | ConvertFrom-Json
foreach ($p in $oldFreeze.files.PSObject.Properties) {
    if ((Digest $p.Name) -ne $p.Value) { throw 'Prior source identity mismatch' }
}
$priorRuns = @()
foreach ($runtime in @('win314','win311','linux312')) {
    $record = Get-Content -LiteralPath "$oldRoot/logs/$runtime-reviewed-full.json" -Raw | ConvertFrom-Json
    $priorRuns += @{runtime=$runtime;exit_code=$record.exit_code;counts=$record.call_counts;deselected=@($record.deselected).Count;classification='ARCH_ONLY_NOT_RERUN'}
}
Save-Json 'prior-evidence-reconciliation.json' @{evidence_files_verified=$checked;source_files_verified=@($oldFreeze.files.PSObject.Properties).Count;archived_full_runs=$priorRuns;fresh_tests_executed=0}
$policyPath = 'config/source_rights_policy.v1.json'
$policy = Get-Content -LiteralPath $policyPath -Raw | ConvertFrom-Json
Save-Json 'source-rights.json' @{path=$policyPath;sha256=(Digest $policyPath);policies=@($policy.policies | Select-Object source_key,status,approval_evidence_ref,approved_by,approved_at,permitted_operations)}
$names = @(rg --files data -g '*.manifest.json')
if ($LASTEXITCODE -ne 0) { throw 'Manifest discovery failed' }
$inventory = @()
$errors = @()
foreach ($name in $names) {
    try {
        $body = Get-Content -LiteralPath $name -Raw | ConvertFrom-Json
        $inventory += @{path=$name.Replace('\','/');metadata_sha256=(Digest $name);source_key=$body.source_key;as_of=$body.as_of;storage_mode=$body.storage_mode;used_url_scheme=($body.used_url -split ':')[0];source_repo_url=$body.source_repo_url;claimed_payload_sha256=$body.checksum;has_approval_evidence=([bool]$body.approval_evidence_ref);has_reviewer_evidence=([bool]$body.reviewer_evidence_ref);assessment='UNVERIFIED_CANDIDATE_NOT_REAL_DATA_ACCEPTANCE'}
    } catch { $errors += @{path=$name.Replace('\','/');reason='METADATA_PARSE_FAILED'} }
}
Save-Json 'local-archive-metadata.json' @{metadata_records_inspected=$inventory.Count;metadata_errors=$errors;records=$inventory;payload_bytes_opened=0;market_rows_inspected=0;limits='Metadata only; missing fields do not prove no separate rights evidence exists. Owner must identify scoped external evidence.'}
$candidates = @(rg --files data docs tests/fixtures/official_source config -g '*.pdf' -g '*expected*corpus*' -g '*permission*' -g '*review*' -g '*reference*' -g '*pin*')
Save-Json 'reference-path-discovery.json' @{command='rg --files data docs tests/fixtures/official_source config -g *.pdf -g *expected*corpus* -g *permission* -g *review* -g *reference* -g *pin*';paths=$candidates;scope='Named repository paths only; not an exhaustive search of external owner storage';owner_supplied_pack_path=$null;owner_supplied_external_pin_path=$null}
$leadRegistry = Get-Content -LiteralPath "$oldRoot/reference_registry.od05r.json" -Raw | ConvertFrom-Json
Save-Json 'reference-review-inventory.json' @{status='REFERENCE_PACK_ABSENT_WITHIN_INSPECTED_SCOPE';prior_leads=$leadRegistry.entries;authenticated_original_documents=0;owner_authorized_sample_packs=0;independently_reviewed_expected_row_sets=0;external_pin_manifest=$null;new_network_requests=0;new_synthetic_market_data=0}
$scorecard = @{schema_version='od05s.real-data-scorecard/v1';status='BLOCKED_REAL_DATA';market_records_inspected=0;market_records_independently_verified=0;field_mismatches=$null;missing_sessions=$null;rejected_market_records=0;rejected_market_records_note='No market payload processed; zero is not an acceptance result';coverage=$null;coverage_denominator=$null;metadata_records_inspected=$inventory.Count;accepted_real_data_packs=0;uncertainties=@('Publisher origin','Reference and sample permissions','Document/version applicability','Independent expected values','Trading session authority','Instrument and series identity','Numerical values and units','Completeness','Point-in-time availability');synthetic_results_in_acceptance=0}
Save-Json 'real-data-scorecard.json' $scorecard
$matrix = 1..24 | ForEach-Object { @{group=('S{0:00}' -f $_);engineering_execution='NOT_EXECUTED_PREFLIGHT_STOP';real_data_acceptance='BLOCKED_REFERENCE';test_first_sequence_claimed=$false} }
Save-Json 'S01-S24-status.json' @($matrix)
Save-Json 'runtime-matrix.json' @{fresh_runtime_checks=@('Windows Python 3.14','Windows Python 3.11','WSL Linux Python 3.12') | ForEach-Object { @{runtime=$_;collection='NOT_RUN';targeted='NOT_RUN';full_regression='NOT_RUN';ruff='NOT_RUN';mypy='NOT_RUN';pip='NOT_RUN';compile='NOT_RUN';coverage=$null;reason='Stopped at authentic-input gate before application edits or fixtures'} };archived_claims_not_fresh=$true}
$changed = @()
foreach ($path in $before.Keys) { if ((Digest $path) -ne $before[$path]) { $changed += $path } }
Save-Json 'preservation-comparison.json' @{scoped_existing_files=$before.Count;changed=$changed;signing_contents_read=$false;data_payloads_read=$false;new_application_files=0;new_tests=0}
if ($changed.Count) { throw 'Original-file preservation failure' }
Save-Json 'command.json' @{argv=@('powershell','-NoProfile','-File',$MyInvocation.MyCommand.Path);cwd=$repo;script_sha256=(Digest $MyInvocation.MyCommand.Path);start_utc=$started;end_utc=[DateTime]::UtcNow.ToString('o');exit_code=0;meaning='Successful metadata inspection, not successful OD05S implementation or financial validation';gatekeeper='OD05S_BLOCKED';reason_codes=@('REFERENCE_PACK_ABSENT','BLOCKED_REFERENCE','BLOCKED_REAL_DATA','NEW_SYNTHETIC_MARKET_FIXTURES_NOT_AUTHORIZED')}
Write-Output "Metadata inspected: $($inventory.Count); prior evidence hashes verified: $checked; preserved scoped files: $($before.Count). OD05S_BLOCKED. No market records validated."
