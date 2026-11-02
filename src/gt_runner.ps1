# GT queue runner (PROTOCOL_GT.md section 2). Starts N single-thread workers on one job; each worker claims units through
# src.rc18_common.run_units (unit checkpoints, lock files, failed records). Restart = run the same command again: finished units are
# skipped and locks of dead workers are removed first. Status: -Status. No unit is claimed after the study deadline.
#   powershell -File src\gt_runner.ps1 -Job gt-dev -Module src.gt_dev -Workers 6
#   powershell -File src\gt_runner.ps1 -Job gt-dev -Module src.gt_dev -Status
param([Parameter(Mandatory = $true)][string]$Job, [string]$Module = "src.gt_dev", [int]$Workers = 6, [switch]$Status)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$out = Join-Path $root "outputs\research_campaign_20261102\opus_geometry_temperature"
$jobdir = Join-Path $out $Job
$runner = Join-Path $out "runner"
New-Item -ItemType Directory -Force $runner | Out-Null
function Count($sub, $filter) { $d = Join-Path $jobdir $sub; if (Test-Path $d) { (Get-ChildItem $d -Filter $filter -File).Count } else { 0 } }
if ($Status) {
    $alive = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match [regex]::Escape($Job) })
    $s = [ordered]@{ job = $Job; utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"); done = (Count "units" "*.json.gz");
                     failed = (Count "failed" "*.json"); locks = (Count "locks" "*.lock"); workers_alive = $alive.Count }
    $s | ConvertTo-Json -Compress
    ($s | ConvertTo-Json) | Set-Content -Encoding utf8 (Join-Path $runner "STATUS_$Job.json")
    exit 0
}
$env:RC18_DEADLINE_UTC = "2026-11-03T17:45:00+00:00"
foreach ($k in "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS") { Set-Item -Path "env:$k" -Value "1" }
$lockdir = Join-Path $jobdir "locks"
if (Test-Path $lockdir) {
    Get-ChildItem $lockdir -Filter *.lock -File | ForEach-Object {
        $p = (Get-Content $_.FullName -ErrorAction SilentlyContinue | Select-Object -First 1)
        if (-not ($p -and (Get-Process -Id ([int]$p) -ErrorAction SilentlyContinue))) { Remove-Item $_.FullName -Force }
    }
}
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
for ($i = 1; $i -le $Workers; $i++) {
    $log = Join-Path $runner "$Job`_w$i`_$stamp.log"; $err = Join-Path $runner "$Job`_w$i`_$stamp.err"
    $p = Start-Process -FilePath python -ArgumentList "-m", $Module, "work", $Job, "--threads", "1" -WorkingDirectory $root `
        -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden -PassThru
    "started worker $i pid $($p.Id) -> $log"
    Start-Sleep -Milliseconds 400
}
"restart command: powershell -File src\gt_runner.ps1 -Job $Job -Module $Module -Workers $Workers" | Set-Content -Encoding utf8 (Join-Path $runner "RESTART_$Job.txt")
