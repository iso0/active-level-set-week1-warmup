# Coordinated worker-pool runner for the joint-depth-label DEV studies (owner execution request of 2026-10-15).
#
# * Single instance: exclusive handle on outputs/joint_depth_label_development/pool/pool_runner.lock.
# * Reads pool/POOL_PLAN.json every cycle, so a study is added or enabled by editing the plan, never by a second runner.
# * Capacity is 4 threads in total, allocated here (no independent check-and-launch by several launchers):
#     external = leaf python/pythonw/julia/Rscript processes that are not descendants of this runner's workers, 1 slot
#                with "--threads 1" else 4, plus 1 reserved slot while Astra's pipeline is active (her tree excluded);
#     free = 4 - external - live workers.  A worker starts only if free >= 1 at two snapshots 60 s apart.
# * A worker is "python -m <module> work --threads 1": it claims units with O_EXCL lock files and exits when nothing is
#   claimable.  When a worker dies, lock files containing its PID are removed so that its unit can be reclaimed (the
#   units resume from their own atomic state).  Finished units are never rerun.
# * Logs: pool/pool_log.jsonl (every launch, end, reap, wait), pool/workers/<study>_<n>.log.
# Entry point (resumable):  powershell -NoProfile -ExecutionPolicy Bypass -File src\jdl_pool_runner.ps1
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PDir = Join-Path $Root 'outputs\joint_depth_label_development\pool'
$PlanFile = Join-Path $PDir 'POOL_PLAN.json'
$LogFile = Join-Path $PDir 'pool_log.jsonl'
$WDir = Join-Path $PDir 'workers'
$AstraState = 'C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_balanced_decision_acquisition\PIPELINE_STATE.json'
$Python = @{ system = 'C:\Users\ozgur\AppData\Local\Microsoft\WindowsApps\python.exe'; venv = 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe' }
$Utf8 = New-Object System.Text.UTF8Encoding $false
New-Item -ItemType Directory -Force -Path $WDir | Out-Null

function Add-Log($obj) {
    $obj | Add-Member -NotePropertyName utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    [System.IO.File]::AppendAllText($LogFile, (($obj | ConvertTo-Json -Depth 6 -Compress) + "`n"), $Utf8)
}
function Read-Json([string]$path) { return ([System.IO.File]::ReadAllText($path, $Utf8) | ConvertFrom-Json) }

function Get-Tree([int[]]$roots, $all) {
    $parent = @{}; foreach ($p in $all) { $parent[[int]$p.ProcessId] = [int]$p.ParentProcessId }
    $set = @{}
    foreach ($p in $all) {
        $id = [int]$p.ProcessId; $cur = $id
        for ($i = 0; $i -lt 12 -and $parent.ContainsKey($cur); $i++) {
            if ($roots -contains $cur) { $set[$id] = $true; break }
            $cur = $parent[$cur]
        }
    }
    return $set
}

function Get-External([int[]]$mine) {
    $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine)
    $num = @($all | Where-Object { $_.Name -match '^(python|pythonw|julia|Rscript)\.exe$' })
    $parents = @{}; foreach ($p in $num) { $parents[[int]$p.ParentProcessId] = $true }
    $myTree = Get-Tree $mine $all
    $astraActive = $false; $astraTree = @{}
    if (Test-Path -LiteralPath $AstraState) {
        try {
            $s = Read-Json $AstraState
            $w = [int]$s.wrapper_pid
            $alive = $null -ne (Get-Process -Id $w -ErrorAction SilentlyContinue)
            $terminal = ([string]$s.state -like 'STOPPED*') -or ([string]$s.state -eq 'COMPUTATION_FINISHED_REVIEW_REQUIRED')
            $astraActive = $alive -and (-not $terminal)
            if ($alive) { $astraTree = Get-Tree @($w) $all }
        } catch { $astraActive = $true }
    }
    $used = 0; $rows = @()
    foreach ($p in $num) {
        $id = [int]$p.ProcessId
        if ($parents.ContainsKey($id) -or $myTree.ContainsKey($id) -or $astraTree.ContainsKey($id)) { continue }
        $slots = 4; if ([string]$p.CommandLine -match '--threads 1') { $slots = 1 }
        $used += $slots; $rows += ('{0}:{1}' -f $id, $slots)
    }
    if ($astraActive) { $used += 1 }
    return [pscustomobject]@{ used = $used; astra_active = $astraActive; leaves = ($rows -join ' ') }
}

function Get-StudyState($st) {
    $glob = Join-Path $Root ($st.done_glob -replace '/', '\')
    $dir = Split-Path -Parent $glob; $pat = Split-Path -Leaf $glob
    $done = 0; if (Test-Path -LiteralPath $dir) { $done = @(Get-ChildItem -LiteralPath $dir -Filter $pat -File).Count }
    $ld = Join-Path $Root ($st.locks_dir -replace '/', '\')
    $locks = 0; if (Test-Path -LiteralPath $ld) { $locks = @(Get-ChildItem -LiteralPath $ld -Filter '*.lock' -File).Count }
    return [pscustomobject]@{ done = $done; locks = $locks; total = [int]$st.units_total; finished = ($done -ge [int]$st.units_total) }
}

$lockPath = Join-Path $PDir 'pool_runner.lock'
try { $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None) }
catch { Write-Output 'Another pool runner holds pool_runner.lock; exiting.'; exit 2 }
$workers = @{}            # pid -> @{ study; n; proc }
$count = @{}
try {
    Add-Log ([pscustomobject]@{ event = 'POOL_START'; pid = $PID })
    $lastWait = [DateTime]::MinValue
    while ($true) {
        $plan = Read-Json $PlanFile
        # reap finished workers and release the locks of dead ones
        foreach ($wpid in @($workers.Keys)) {
            $w = $workers[$wpid]
            if ($w.proc.HasExited) {
                $code = $w.proc.ExitCode
                $st = @($plan.studies | Where-Object { $_.name -eq $w.study })[0]
                $released = 0
                if ($null -ne $st) {
                    $ld = Join-Path $Root ($st.locks_dir -replace '/', '\')
                    if (Test-Path -LiteralPath $ld) {
                        foreach ($lf in @(Get-ChildItem -LiteralPath $ld -Filter '*.lock' -File)) {
                            $c = ''; try { $c = [System.IO.File]::ReadAllText($lf.FullName).Trim() } catch { }
                            if ($c -eq [string]$wpid) { Remove-Item -LiteralPath $lf.FullName -Force; $released++ }
                        }
                    }
                }
                Add-Log ([pscustomobject]@{ event = 'WORKER_END'; study = $w.study; worker = $w.n; pid = $wpid; exit_code = $code; locks_released = $released })
                $workers.Remove($wpid)
            }
        }
        $states = @{}; $open = 0
        foreach ($st in @($plan.studies)) {
            if (-not $st.enabled) { continue }
            $s = Get-StudyState $st; $states[$st.name] = $s
            if (-not $s.finished) { $open++ }
        }
        if ($open -eq 0 -and $workers.Count -eq 0) { Add-Log ([pscustomobject]@{ event = 'POOL_END'; reason = 'all enabled studies finished' }); break }
        # candidates: enabled, unfinished, unclaimed units, below their worker cap; highest priority first
        $live = @{}; foreach ($w in $workers.Values) { $live[$w.study] = 1 + [int]$live[$w.study] }
        $cand = @($plan.studies | Where-Object { $_.enabled -and $states.ContainsKey($_.name) -and -not $states[$_.name].finished -and
                    ($states[$_.name].total - $states[$_.name].done - $states[$_.name].locks) -gt 0 -and ([int]$live[$_.name] -lt [int]$_.max_workers) } |
                  Sort-Object @{ Expression = { [int]$_.priority } }, @{ Expression = { [int]$live[$_.name] } })
        if ($cand.Count -gt 0) {
            $mine = @($workers.Keys | ForEach-Object { [int]$_ })
            $s1 = Get-External $mine
            if (4 - $s1.used - $workers.Count -ge 1) {
                Start-Sleep -Seconds 60
                $mine = @($workers.Keys | ForEach-Object { [int]$_ })
                $s2 = Get-External $mine
                if (4 - $s2.used - $workers.Count -ge 1) {
                    $st = $cand[0]
                    $count[$st.name] = 1 + [int]$count[$st.name]
                    $n = $count[$st.name]
                    $out = Join-Path $WDir ('{0}_{1}.log' -f $st.name, $n); $err = Join-Path $WDir ('{0}_{1}.err.log' -f $st.name, $n)
                    $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'; $env:PYTHONIOENCODING = 'utf-8'
                    $proc = Start-Process -FilePath $Python[[string]$st.python] -ArgumentList @($st.args) -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
                    $null = $proc.Handle
                    $workers[[int]$proc.Id] = @{ study = $st.name; n = $n; proc = $proc }
                    Add-Log ([pscustomobject]@{ event = 'WORKER_START'; study = $st.name; worker = $n; pid = $proc.Id; external_used = $s2.used; live_workers = $workers.Count; astra_active = $s2.astra_active; leaves = $s2.leaves })
                    continue
                }
            }
            if (([DateTime]::UtcNow - $lastWait).TotalMinutes -ge 30) {
                Add-Log ([pscustomobject]@{ event = 'WAIT_CAPACITY'; external_used = $s1.used; live_workers = $workers.Count; astra_active = $s1.astra_active }); $lastWait = [DateTime]::UtcNow
            }
        }
        Start-Sleep -Seconds 30
    }
} catch {
    Add-Log ([pscustomobject]@{ event = 'POOL_EXCEPTION'; error = $_.Exception.Message })
    throw
} finally {
    $lock.Dispose()
}
