param([ValidateSet('before','after','commands','evidence')][string]$Mode='commands')
$ErrorActionPreference='Stop'
$repo=(Get-Location).Path
$here=$PSScriptRoot
$logs=Join-Path $here 'logs'
function Save-Exclusive([string]$Name,$Value) {
 $path=Join-Path $logs $Name
 $bytes=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 30))
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
}
function Run-Git([string]$Label,[string[]]$GitArgs) {
 $start=[datetime]::UtcNow; $timer=[Diagnostics.Stopwatch]::StartNew()
 $raw= & git @GitArgs 2>&1 | Out-String; $code=$LASTEXITCODE
 Save-Exclusive ($Label+'.json') ([ordered]@{command=@('git')+$GitArgs;cwd=$repo;start_utc=$start.ToString('o');end_utc=[datetime]::UtcNow.ToString('o');elapsed_seconds=$timer.Elapsed.TotalSeconds;exit_code=$code;output=$raw})
 if($code -ne 0) {throw "$Label exit $code"}
}
function Snapshot {
 $paths=New-Object 'System.Collections.Generic.SortedSet[string]'
 foreach($name in (& git ls-files)) { [void]$paths.Add($name.Replace('\','/')) }
 foreach($base in @('data','artifacts')) {
  if(Test-Path -LiteralPath $base) {
   foreach($file in Get-ChildItem -LiteralPath $base -Recurse -File -Force) {
    [void]$paths.Add($file.FullName.Substring($repo.Length+1).Replace('\','/'))
   }
  }
 }
 foreach($file in Get-ChildItem -LiteralPath $repo -File -Force) {
  if($file.Extension -in @('.db','.sqlite','.sqlite3')) { [void]$paths.Add($file.Name) }
 }
 [void]$paths.Add('docs/verification/OMEGADATA_OD05_CODEX_MASTER_PROMPT_2026-11-16.md')
 $records=[ordered]@{}
 foreach($name in $paths) {
  $p=Join-Path $repo $name
  if(-not (Test-Path -LiteralPath $p -PathType Leaf)) {throw "Missing original path: $name"}
  $item=Get-Item -LiteralPath $p -Force
  if($name -match '(^|/)(gnupg|private-keys-v1.d|openpgp-revocs.d)(/|$)' -or $item.Name -eq '.env') {
   $records[$name]=[ordered]@{length=$item.Length;last_write_utc=$item.LastWriteTimeUtc.ToString('o');content='NOT_OPENED_OR_HASHED'}
  } else {
   $records[$name]=[ordered]@{length=$item.Length;sha256=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower()}
  }
 }
 return $records
}
if($Mode -in @('before','after')) {
 $records=Snapshot
 Save-Exclusive ('preservation-'+$Mode+'.json') $records
 if($Mode -eq 'after') {
  $initial=Get-Content -Raw -Encoding UTF8 (Join-Path $logs 'preservation-before.json') | ConvertFrom-Json
  $changes=@()
  foreach($property in $initial.PSObject.Properties) {
   $current=$records[$property.Name]
   if(($property.Value | ConvertTo-Json -Compress) -ne ($current | ConvertTo-Json -Compress)) {$changes+=$property.Name}
  }
  Save-Exclusive 'preservation-comparison.json' ([ordered]@{original_records=@($initial.PSObject.Properties).Count;changes=$changes;signing='metadata only; no contents opened/hashed';passed=($changes.Count -eq 0)})
  if($changes.Count) {throw "Unexpected original changes: $($changes -join ', ')"}
 }
 Write-Output "$Mode preservation completed: $($records.Count) records"
} elseif($Mode -eq 'commands') {
 Run-Git 'branch' @('branch','--show-current')
 Run-Git 'head' @('rev-parse','HEAD')
 Run-Git 'source-tree' @('rev-parse','HEAD^{tree}')
 Run-Git 'merge-base-main' @('merge-base','main','HEAD')
 Run-Git 'main-diff' @('diff','--name-status','main...HEAD')
 Run-Git 'working-diff' @('diff','--name-status')
 Run-Git 'index-diff' @('diff','--cached','--name-status')
 Run-Git 'whitespace' @('diff','--check')
 Save-Exclusive 'host.json' ([ordered]@{utc=[datetime]::UtcNow.ToString('o');os=[Environment]::OSVersion.VersionString;powershell=$PSVersionTable.PSVersion.ToString();cwd=$repo;python_invoked=$false;test_execution='NOT_RUN_OWNER_GATE_BLOCKED'})
} else {
 $old=Join-Path $repo 'docs/omegadata_v2/implementation/od04r/20261115T181120Z'
 $ledger=Get-Content -Raw -Encoding UTF8 (Join-Path $old 'logs/reviewed-before-after-file-ledger.json') | ConvertFrom-Json
 $hashes=@()
 foreach($entry in $ledger.PSObject.Properties) {
  $current=(Get-FileHash -LiteralPath $entry.Name -Algorithm SHA256).Hash.ToLower()
  if($current -ne $entry.Value.working_sha256) {throw "Reviewed source mismatch: $($entry.Name)"}
  $hashes+=[ordered]@{path=$entry.Name;sha256=$current;matches_od04r=$true}
 }
 $reports=Get-Content -Raw -Encoding UTF8 (Join-Path $old 'logs/report-sha256.json') | ConvertFrom-Json
 foreach($entry in $reports.PSObject.Properties) {
  if((Get-FileHash -LiteralPath (Join-Path $old $entry.Name) -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) {throw "OD04R report mismatch: $($entry.Name)"}
 }
 $runtimes=@()
 foreach($label in @('win314-reviewed','win311-reviewed','linux312-reviewed')) {
  $commands=@()
  foreach($gate in @('environment','collection','targeted','full','ruff','mypy','pip')) {
   $path=Join-Path $old "logs/$label-$gate.json"
   $row=Get-Content -Raw -Encoding UTF8 $path | ConvertFrom-Json
   if($row.exit_code -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $old ('logs/'+$row.output)))) {throw "Invalid archived gate $label-$gate"}
   $commands+=[ordered]@{gate=$gate;exit_code=$row.exit_code;argv=$row.command;cwd=$row.cwd;utc=$row.start_utc;counts=$row.call_counts;deselected=$row.deselected;metadata_sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()}
  }
  $runtimes+=[ordered]@{label=$label;evidence='ARCH';commands=$commands}
 }
 $policy=Get-Content -Raw -Encoding UTF8 config/source_rights_policy.v1.json | ConvertFrom-Json
 $pending=@($policy.policies | Where-Object status -eq 'PENDING_REVIEW').Count
 if($pending -ne 13 -or @($policy.policies).Count -ne 13) {throw 'Unexpected policy approval/status change'}
 Save-Exclusive 'od04r-evidence-check.json' ([ordered]@{observed_utc=[datetime]::UtcNow.ToString('o');reviewed_head='bbc38716d902fe27192f80affaca29c6f51e9890';six_current_source_hashes=$hashes;eleven_reports_match=$true;runtime_evidence=$runtimes;fresh_runtime_tests_run=$false;pending_real_sources=13;approved_real_sources=0;owner_exception=$false;separate_od05_implementation_authorization=$false})
}
