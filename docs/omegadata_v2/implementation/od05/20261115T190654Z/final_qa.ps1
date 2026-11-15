$ErrorActionPreference='Stop'
$start=[datetime]::UtcNow
$timer=[Diagnostics.Stopwatch]::StartNew()
$root=(Get-Location).Path
$here=$PSScriptRoot
$logs=Join-Path $here 'logs'
function Save-Exclusive([string]$Name,$Value) {
 $bytes=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 20))
 $stream=[IO.File]::Open((Join-Path $logs $Name),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
 try {$stream.Write($bytes,0,$bytes.Length)} finally {$stream.Dispose()}
}
try {
 $head=(& git rev-parse HEAD).Trim()
 $branch=(& git branch --show-current).Trim()
 if($head -ne 'bbc38716d902fe27192f80affaca29c6f51e9890' -or $branch -ne 'feature/od01-source-rights') {throw 'Git identity changed'}
 $working= & git diff --name-only
 $staged= & git diff --cached --name-only
 if($working -or $staged) {throw 'Unexpected tracked/index changes'}
 & git diff --check
 if($LASTEXITCODE -ne 0) {throw 'Whitespace failure'}
 $preservation=Get-Content -Raw -Encoding UTF8 (Join-Path $logs 'preservation-comparison.json') | ConvertFrom-Json
 if(-not $preservation.passed -or @($preservation.changes).Count -ne 0 -or $preservation.original_records -ne 12449) {throw 'Preservation mismatch'}
 $evidence=Get-Content -Raw -Encoding UTF8 (Join-Path $logs 'od04r-evidence-check.json') | ConvertFrom-Json
 if(-not $evidence.eleven_reports_match -or @($evidence.six_current_source_hashes).Count -ne 6) {throw 'OD04R evidence mismatch'}
 foreach($row in $evidence.six_current_source_hashes) {
  if((Get-FileHash -LiteralPath $row.path -Algorithm SHA256).Hash.ToLower() -ne $row.sha256) {throw 'Current source changed after audit'}
 }
 $policy=Get-Content -Raw -Encoding UTF8 config/source_rights_policy.v1.json | ConvertFrom-Json
 if(@($policy.policies).Count -ne 13 -or @($policy.policies | Where-Object status -ne 'PENDING_REVIEW').Count -ne 0) {throw 'Policy state changed'}
 $docs=@(Get-ChildItem -LiteralPath $here -File | Where-Object Name -match '^\d\d_.*\.md$' | Sort-Object Name)
 if($docs.Count -ne 12) {throw 'Missing required planning report'}
 $links=@();$manifest=[ordered]@{}
 foreach($doc in $docs) {
  $text=Get-Content -Raw -Encoding UTF8 -LiteralPath $doc.FullName
  if(-not $text.Trim()) {throw 'Empty report'}
  foreach($match in [regex]::Matches($text,'\]\(([^)]+)\)')) {
   $target=$match.Groups[1].Value
   if($target -match '^(https?://|#)') {continue}
   $target=($target -split '#')[0]
   # This exact future self-reference is created exclusively below.
   if($target -eq 'logs/final-qa.json') {continue}
   if(-not (Test-Path -LiteralPath (Join-Path $here $target))) {$links+=[ordered]@{report=$doc.Name;target=$target}}
  }
  $manifest[$doc.Name]=(Get-FileHash -LiteralPath $doc.FullName -Algorithm SHA256).Hash.ToLower()
 }
 if($links.Count) {throw ('Broken links: '+($links | ConvertTo-Json -Compress))}
 $matrix=Get-Content -Raw -Encoding UTF8 (Join-Path $here '04_negative_first_matrix.md')
 if([regex]::Matches($matrix,'(?m)^\| T\d{2} \|').Count -ne 32) {throw 'Incomplete planned32group matrix'}
 if(Test-Path -LiteralPath 'tests/unit/test_od05_era_parsing.py') {throw 'Unexpected OD05 test-source creation'}
 $references=Get-Content -Raw -Encoding UTF8 (Join-Path $here 'reference_registry.json') | ConvertFrom-Json
 if($references.official_reference_verified_count -ne 0 -or $references.owner_exception_accepted -or $references.implementation_authorized) {throw 'Unwarranted approval/reference promotion'}
 $old='docs/omegadata_v2/implementation/od04r/20261115T181120Z'
 $oldReports=Get-Content -Raw -Encoding UTF8 (Join-Path $old 'logs/report-sha256.json') | ConvertFrom-Json
 foreach($entry in $oldReports.PSObject.Properties) {
  if((Get-FileHash -LiteralPath (Join-Path $old $entry.Name) -Algorithm SHA256).Hash.ToLower() -ne $entry.Value) {throw 'Historical OD04R report changed'}
 }
 Save-Exclusive 'document-sha256.json' $manifest
 $status= & git status --short | Out-String
 Save-Exclusive 'final-status.json' ([ordered]@{utc=[datetime]::UtcNow.ToString('o');branch=$branch;head=$head;status=$status;tracked_diff=@($working);index_diff=@($staged)})
 Save-Exclusive 'final-qa.json' ([ordered]@{
  command="& 'docs/omegadata_v2/implementation/od05/20261115T190654Z/final_qa.ps1'";shell_executable=(Get-Process -Id $PID).Path;cwd=$root;
  start_utc=$start.ToString('o');end_utc=[datetime]::UtcNow.ToString('o');duration_seconds=$timer.Elapsed.TotalSeconds;
  exit_code=0;mechanical_checks_passed=$true;branch=$branch;head=$head;original_records=12449;original_changes=@();
  reports=$docs.Name;planned_groups=32;executed_od05_groups=0;fresh_runtime_tests=$false;official_reference_verified_count=0;
  source_policy_pending=13;source_policy_approved=0;human_exception_approved=$false;separate_od05_authorization=$false;
  execution_scope='READ_ONLY_AUDIT_AND_PLAN_ONLY';gatekeeper='OD05_BLOCKED';stop_reason='OD05_GATE_BLOCKED_OWNER_DECISION';
  secondary_blockers=@('OD05_GATE_BLOCKED_AUTHORIZATION','BLOCKED_REFERENCE');
  signing='Metadata only; original contents never opened/hashed/copied';git_lifecycle_mutation=$false;later_phase_started=$false
 })
 if(-not (Test-Path -LiteralPath (Join-Path $logs 'final-qa.json'))) {throw 'Missing final self-reference'}
 Write-Output 'Documentation/scope QA passed. OD05 implementation remains BLOCKED_OWNER_DECISION.'
} catch {
 Save-Exclusive ('qa-failure-'+[datetime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'.json') ([ordered]@{start_utc=$start.ToString('o');end_utc=[datetime]::UtcNow.ToString('o');exit_code=1;error=$_.Exception.Message})
 throw
}
