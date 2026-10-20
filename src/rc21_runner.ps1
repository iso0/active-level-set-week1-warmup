# RC21 continuation inside the remaining RC20 window (owner instruction 2026-10-20 evening; the RC20 clock is NOT restarted: t0 /
# deadline in runner/PLAN.json are the RC20 ones). Copy of src/rc20_runner.ps1 with the runner directory opus_rc21/runner only.
# RC20 header: RC20 bounded continuation (owner instruction 2026-10-20; own 24-hour clock in runner/PLAN.json t0_utc / deadline_utc) — Opus worker
# runner. Copy of src/rc19_runner.ps1 with: (i) runner directory outputs/research_campaign_20261020/opus_rc20/runner; (ii) deadline
# and t0 read from PLAN.json (the completed 48-hour campaign record is not changed); (iii) rc20_ workers count as 1 slot.
# RC19 derivation notes (unchanged): derived from src/rc18_runner.ps1 with:
#   (a) job dependencies: a job with "after": [names] becomes claimable only when every listed job is finished;
#   (b) Astra's processes are also recognised by her workspace path in the command line (\Codex\ or astra_), because her live
#       workers are neither listed in her share's jobs nor descendants of codex.exe (observed 2026-10-19);
#   (c) atomic launch: capacity re-check, worker start and the Opus job-list update happen inside the coordination-record lock.
# Original header (rules unchanged):
#
# * Single instance: exclusive handle on <runner directory>/runner.lock.
# * Reads runner/PLAN.json every cycle (jobs are added, paused or resized by editing the plan, never by a second runner) and the
#   single coordination record outputs/joint_depth_label_development/pool/POOL_PLAN.json (Opus share, Astra share, deadline).
# * Capacity: the Opus share is 2 threads. opus_used = live runner workers + other numerical leaf processes that are not Astra's
#   (1 slot if started with --threads 1 / thread env, else 4). Astra's processes (descendants of codex.exe or PIDs listed in her
#   share) count against her reserved 2 threads, never against ours, and her share is never used by this runner.
#   A worker starts only if opus_used + 1 <= min(Opus share, PLAN.runner_slots) and astra_used + opus_used + 1 <= 4.
# * Jobs: kind "pool" = "python -m <module> work ..." claims units with O_EXCL lock files (PID inside), checkpoints each unit
#   atomically, skips finished/failed units and exits when nothing is claimable; kind "once" = a single command run at most
#   max_attempts times. Finished units are never rerun. Locks of dead PIDs are released (the unit resumes from its own state).
# * Failure: a worker exit code != 0 is logged; 2 consecutive failures of a job pause that job only (runner/STATE.json);
#   other jobs continue. A paused job restarts only after the plan's "resume_token" for it is changed (a deliberate repair).
# * Deadline: no worker starts after the campaign deadline; workers receive RC18_DEADLINE_UTC and stop claiming units then.
# * Heartbeat: runner/HEARTBEAT.json every cycle (30 s); runner/STATUS.md every 5 min; events in runner/runner_log.jsonl.
# Entry point (resumable, idempotent):
#   powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_start_runner.ps1      (detached launch via WMI)
#   powershell -NoProfile -ExecutionPolicy Bypass -File src\rc18_runner.ps1            (foreground)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RDir = Join-Path $Root 'outputs\research_campaign_20261020\opus_rc21\runner'
$PlanFile = Join-Path $RDir 'PLAN.json'
$StateFile = Join-Path $RDir 'STATE.json'
$LogFile = Join-Path $RDir 'runner_log.jsonl'
$HbFile = Join-Path $RDir 'HEARTBEAT.json'
$StatusFile = Join-Path $RDir 'STATUS.md'
$WDir = Join-Path $RDir 'workers'
$CoordPath = Join-Path $Root 'outputs\joint_depth_label_development\pool\POOL_PLAN.json'
$CoordLock = Join-Path $Root 'outputs\joint_depth_label_development\pool\COORDINATION.lock'
$Python = @{ system = 'C:\Users\ozgur\AppData\Local\Microsoft\WindowsApps\python.exe'; venv = 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe' }
$Utf8 = New-Object System.Text.UTF8Encoding $false
New-Item -ItemType Directory -Force -Path $WDir | Out-Null

function UtcNow { return [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ') }
function Add-Log($obj) {
    $obj | Add-Member -NotePropertyName utc -NotePropertyValue (UtcNow) -Force
    [System.IO.File]::AppendAllText($LogFile, (($obj | ConvertTo-Json -Depth 8 -Compress) + "`n"), $Utf8)
}
function Read-Json([string]$path) { return ([System.IO.File]::ReadAllText($path, $Utf8).TrimStart([char]0xFEFF) | ConvertFrom-Json) }
function Write-JsonAtomic([string]$path, $obj) {
    $tmp = $path + '.tmp'; [System.IO.File]::WriteAllText($tmp, ($obj | ConvertTo-Json -Depth 10), $Utf8)
    Move-Item -LiteralPath $tmp -Destination $path -Force
}

function Get-Tree([int[]]$roots, $all) {
    $parent = @{}; foreach ($p in $all) { $parent[[int]$p.ProcessId] = [int]$p.ParentProcessId }
    $set = @{}
    foreach ($p in $all) {
        $id = [int]$p.ProcessId; $cur = $id
        for ($i = 0; $i -lt 16 -and $parent.ContainsKey($cur); $i++) {
            if ($roots -contains $cur) { $set[$id] = $true; break }
            $cur = $parent[$cur]
        }
    }
    return $set
}

function Get-Usage([int[]]$mine, $coord) {
    $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine)
    $num = @($all | Where-Object { $_.Name -match '^(python|pythonw|julia|Rscript)\.exe$' })
    $parents = @{}; foreach ($p in $num) { $parents[[int]$p.ParentProcessId] = $true }
    $myTree = Get-Tree $mine $all
    $astraRoots = @($all | Where-Object { $_.Name -match '^codex' } | ForEach-Object { [int]$_.ProcessId })
    try { foreach ($s in @($coord.coordination.shares)) { if ($s.owner -eq 'Astra') { foreach ($j in @($s.jobs)) { if ($j.pid) { $astraRoots += [int]$j.pid } } } } } catch { }
    $astraTree = Get-Tree $astraRoots $all
    $opusOther = 0; $astra = 0; $rows = @()
    foreach ($p in $num) {
        $id = [int]$p.ProcessId
        if ($parents.ContainsKey($id)) { continue }                     # launcher stub, its child is the leaf
        $slots = 4; if (([string]$p.CommandLine -match '--threads 1') -or ([string]$p.CommandLine -match 'rc1[89]_|rc2[0-9]_') -or ([string]$p.CommandLine -match 'run_pilot\.py')) { $slots = 1 }
        if ($myTree.ContainsKey($id)) { continue }
        if ($astraTree.ContainsKey($id) -or ([string]$p.CommandLine -match '\\Codex\\|astra_')) { $astra += $slots; $rows += ('astra:{0}:{1}' -f $id, $slots); continue }
        $opusOther += $slots; $rows += ('other:{0}:{1}' -f $id, $slots)
    }
    return [pscustomobject]@{ opus_other = $opusOther; astra = $astra; leaves = ($rows -join ' ') }
}

function Get-JobState($job) {
    $glob = Join-Path $Root ($job.done_glob -replace '/', '\')
    $dir = Split-Path -Parent $glob; $pat = Split-Path -Leaf $glob
    $done = 0; $lastName = $null; $lastUtc = $null
    if (Test-Path -LiteralPath $dir) {
        $files = @(Get-ChildItem -LiteralPath $dir -Filter $pat -File)
        $done = $files.Count
        if ($done -gt 0) { $l = $files | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1; $lastName = $l.Name; $lastUtc = $l.LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ') }
    }
    $failed = 0
    if ($job.failed_dir) { $fd = Join-Path $Root ($job.failed_dir -replace '/', '\'); if (Test-Path -LiteralPath $fd) { $failed = @(Get-ChildItem -LiteralPath $fd -Filter '*.json' -File).Count } }
    $locks = 0
    if ($job.locks_dir) { $ld = Join-Path $Root ($job.locks_dir -replace '/', '\'); if (Test-Path -LiteralPath $ld) { $locks = @(Get-ChildItem -LiteralPath $ld -Filter '*.lock' -File).Count } }
    $total = [int]$job.units_total
    return [pscustomobject]@{ done = $done; failed = $failed; locks = $locks; total = $total; finished = (($done + $failed) -ge $total); last_unit = $lastName; last_unit_utc = $lastUtc }
}

function Enter-CoordLock {
    for ($t = 0; $t -lt 40; $t++) {
        try {
            $fs = [System.IO.File]::Open($CoordLock, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            $b = $Utf8.GetBytes((@{ pid = $PID; host = $env:COMPUTERNAME; utc = (UtcNow) } | ConvertTo-Json -Compress)); $fs.Write($b, 0, $b.Length); $fs.Close(); return $true
        } catch {
            try { if (((Get-Date) - (Get-Item -LiteralPath $CoordLock).LastWriteTime).TotalSeconds -gt 120) { Remove-Item -LiteralPath $CoordLock -Force } } catch { }
            Start-Sleep -Milliseconds 500
        }
    }
    Add-Log ([pscustomobject]@{ event = 'COORD_LOCK_TIMEOUT' }); return $false
}
function Exit-CoordLock { Remove-Item -LiteralPath $CoordLock -Force -ErrorAction SilentlyContinue }
function Write-OpusJobs($jobs) {
    # caller holds the coordination lock (src/rc18_coord.py protocol): read, change only the Opus share, temp + replace
    $rec = Read-Json $CoordPath
    foreach ($s in @($rec.coordination.shares)) {
        if ($s.owner -eq 'Opus') {
            $s.jobs = @($jobs); $s | Add-Member -NotePropertyName jobs_updated_utc -NotePropertyValue (UtcNow) -Force
            $s | Add-Member -NotePropertyName runner -NotePropertyValue 'src/rc21_runner.ps1 (max 2 concurrent leaf processes x 1 thread)' -Force
        }
    }
    $rec.coordination | Add-Member -NotePropertyName last_update_utc -NotePropertyValue (UtcNow) -Force
    Write-JsonAtomic $CoordPath $rec
}
function Get-CoordJobRows($plan) {
    $cj = @()
    foreach ($k in $workers.Keys) {
        $w = $workers[$k]; $jdef = @($plan.jobs | Where-Object { $_.name -eq $w.job })[0]; $cmd = ''
        if ($null -ne $jdef) { $cmd = ('{0} {1}' -f [string]$jdef.python, (@($jdef.args) -join ' ')) }
        $kids = @(Get-CimInstance Win32_Process -Filter ("ParentProcessId={0}" -f $k) | ForEach-Object { [int]$_.ProcessId })
        $cj += [pscustomobject]@{ pid = $k; child_pids = $kids; job = $w.job; start_utc = $w.start; threads = 1; host = 'Burak'; command = $cmd; launched_by = 'src/rc21_runner.ps1' }
    }
    return $cj
}
function Update-CoordJobs($jobs) {
    # lock protocol of src/rc18_coord.py: exclusive lock file, read, change only the Opus share, temp + replace, delete lock
    for ($t = 0; $t -lt 40; $t++) {
        try { $fs = [System.IO.File]::Open($CoordLock, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None); break }
        catch {
            try { if (((Get-Date) - (Get-Item -LiteralPath $CoordLock).LastWriteTime).TotalSeconds -gt 120) { Remove-Item -LiteralPath $CoordLock -Force } } catch { }
            Start-Sleep -Milliseconds 500
        }
    }
    if ($null -eq $fs) { Add-Log ([pscustomobject]@{ event = 'COORD_LOCK_TIMEOUT' }); return }
    try {
        $b = $Utf8.GetBytes((@{ pid = $PID; host = $env:COMPUTERNAME; utc = (UtcNow) } | ConvertTo-Json -Compress)); $fs.Write($b, 0, $b.Length); $fs.Close()
        $rec = Read-Json $CoordPath
        foreach ($s in @($rec.coordination.shares)) {
            if ($s.owner -eq 'Opus') { $s.jobs = @($jobs); $s | Add-Member -NotePropertyName jobs_updated_utc -NotePropertyValue (UtcNow) -Force }
        }
        $rec.coordination | Add-Member -NotePropertyName last_update_utc -NotePropertyValue (UtcNow) -Force
        Write-JsonAtomic $CoordPath $rec
    } finally { Remove-Item -LiteralPath $CoordLock -Force -ErrorAction SilentlyContinue }
}

$lockPath = Join-Path $RDir 'runner.lock'
try { $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None) }
catch { Write-Output 'Another rc21 runner holds runner.lock; exiting.'; exit 2 }
$state = @{ paused = @{}; consecutive_failures = @{}; attempts = @{}; resume_tokens = @{} }
if (Test-Path -LiteralPath $StateFile) {
    $s0 = Read-Json $StateFile
    foreach ($k in @('paused', 'consecutive_failures', 'attempts', 'resume_tokens')) { if ($s0.$k) { foreach ($p in $s0.$k.PSObject.Properties) { $state[$k][$p.Name] = $p.Value } } }
}
$workers = @{}            # pid -> @{ job; n; proc; start; log }
$count = @{}
$startUtc = UtcNow; $cycle = 0; $lastStatus = [DateTime]::MinValue
try {
    Add-Log ([pscustomobject]@{ event = 'RUNNER_START'; pid = $PID })
    while ($true) {
        $cycle++
        $plan = Read-Json $PlanFile; $coord = Read-Json $CoordPath
        $deadline = [DateTime]::Parse($plan.deadline_utc).ToUniversalTime()
        $t0 = [DateTime]::Parse($plan.t0_utc).ToUniversalTime()
        $share = 2; foreach ($s in @($coord.coordination.shares)) { if ($s.owner -eq 'Opus') { $share = [int]$s.threads } }
        $slots = [Math]::Min($share, [int]$plan.runner_slots)
        $changed = $false
        # reap finished workers; release locks of dead ones
        foreach ($wpid in @($workers.Keys)) {
            $w = $workers[$wpid]
            if ($w.proc.HasExited) {
                $code = $w.proc.ExitCode; $job = @($plan.jobs | Where-Object { $_.name -eq $w.job })[0]; $released = 0
                if ($null -ne $job -and $job.locks_dir) {
                    $ld = Join-Path $Root ($job.locks_dir -replace '/', '\')
                    if (Test-Path -LiteralPath $ld) {
                        foreach ($lf in @(Get-ChildItem -LiteralPath $ld -Filter '*.lock' -File)) {
                            $c = ''; try { $c = [System.IO.File]::ReadAllText($lf.FullName).Trim() } catch { }
                            $n = 0; if ([int]::TryParse($c, [ref]$n) -and $null -eq (Get-Process -Id $n -ErrorAction SilentlyContinue)) { Remove-Item -LiteralPath $lf.FullName -Force; $released++ }
                        }
                    }
                }
                if ($code -ne 0) {
                    $state.consecutive_failures[$w.job] = 1 + [int]$state.consecutive_failures[$w.job]
                    Add-Log ([pscustomobject]@{ event = 'WORKER_FAILED'; job = $w.job; worker = $w.n; pid = $wpid; exit_code = $code; locks_released = $released; log = $w.log })
                    if ([int]$state.consecutive_failures[$w.job] -ge 2) {
                        $state.paused[$w.job] = (UtcNow); $state.resume_tokens[$w.job] = [string]$job.resume_token
                        Add-Log ([pscustomobject]@{ event = 'JOB_PAUSED'; job = $w.job; reason = '2 consecutive worker failures; change resume_token in PLAN.json after a recorded repair' })
                    }
                } else {
                    $state.consecutive_failures[$w.job] = 0
                    Add-Log ([pscustomobject]@{ event = 'WORKER_END'; job = $w.job; worker = $w.n; pid = $wpid; exit_code = $code; locks_released = $released })
                }
                $workers.Remove($wpid); $changed = $true
            }
        }
        # stale locks (PID in the lock file not alive)
        foreach ($job in @($plan.jobs)) {
            if (-not $job.locks_dir) { continue }
            $ld = Join-Path $Root ($job.locks_dir -replace '/', '\'); if (-not (Test-Path -LiteralPath $ld)) { continue }
            foreach ($lf in @(Get-ChildItem -LiteralPath $ld -Filter '*.lock' -File)) {
                $c = ''; try { $c = [System.IO.File]::ReadAllText($lf.FullName).Trim() } catch { continue }
                $n = 0
                if ([int]::TryParse($c, [ref]$n) -and $null -eq (Get-Process -Id $n -ErrorAction SilentlyContinue)) {
                    Remove-Item -LiteralPath $lf.FullName -Force; Add-Log ([pscustomobject]@{ event = 'STALE_LOCK_RELEASED'; job = $job.name; lock = $lf.Name; pid = $n })
                }
            }
        }
        # un-pause jobs whose resume_token changed (deliberate, recorded repair)
        foreach ($k in @($state.paused.Keys)) {
            $job = @($plan.jobs | Where-Object { $_.name -eq $k })[0]
            if ($null -ne $job -and [string]$job.resume_token -ne [string]$state.resume_tokens[$k]) {
                $state.paused.Remove($k); $state.consecutive_failures[$k] = 0; Add-Log ([pscustomobject]@{ event = 'JOB_RESUMED'; job = $k; resume_token = [string]$job.resume_token })
            }
        }
        $states = @{}
        foreach ($job in @($plan.jobs)) { $states[$job.name] = Get-JobState $job }
        $live = @{}; foreach ($w in $workers.Values) { $live[$w.job] = 1 + [int]$live[$w.job] }
        $now = [DateTime]::UtcNow; $pastDeadline = $now -ge $deadline
        $cand = @($plan.jobs | Where-Object {
                $_.enabled -and -not $state.paused.ContainsKey($_.name) -and -not $states[$_.name].finished -and
                ([int]$live[$_.name] -lt [int]$_.max_workers) -and
                ( ($_.kind -eq 'once' -and [int]$state.attempts[$_.name] -lt [int]$_.max_attempts) -or
                  ($_.kind -ne 'once' -and ($states[$_.name].total - $states[$_.name].done - $states[$_.name].failed - $states[$_.name].locks) -gt 0) ) } |
            Sort-Object @{ Expression = { [int]$_.priority } }, @{ Expression = { [int]$live[$_.name] } })
        # dependencies: a job is claimable only when every job named in its 'after' list is finished
        $cand = @($cand | Where-Object { $ok = $true; foreach ($dep in @($_.after)) { if ($dep -and $states.ContainsKey([string]$dep) -and -not $states[[string]$dep].finished) { $ok = $false } }; $ok })
        $mine = @(); foreach ($w in $workers.Values) { $mine += [int]$w.proc.Id }
        $u = Get-Usage $mine $coord
        $opusUsed = $workers.Count + $u.opus_other
        if ($cand.Count -gt 0 -and -not $pastDeadline -and ($opusUsed + 1 -le $slots) -and ($u.astra + $opusUsed + 1 -le 4)) {
            if (Enter-CoordLock) {
                try {
                    $coord = Read-Json $CoordPath; $u = Get-Usage $mine $coord; $opusUsed = $workers.Count + $u.opus_other     # re-check inside the lock
                    if (($opusUsed + 1 -le $slots) -and ($u.astra + $opusUsed + 1 -le 4)) {
                        $job = $cand[0]
                        $count[$job.name] = 1 + [int]$count[$job.name]; $n = $count[$job.name]
                        if ($job.kind -eq 'once') { $state.attempts[$job.name] = 1 + [int]$state.attempts[$job.name] }
                        $out = Join-Path $WDir ('{0}_{1}.log' -f $job.name, $n); $err = Join-Path $WDir ('{0}_{1}.err.log' -f $job.name, $n)
                        $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'
                        $env:PYTHONIOENCODING = 'utf-8'; $env:RC18_DEADLINE_UTC = $deadline.ToString('yyyy-MM-ddTHH:mm:ssZ'); $env:RC19_DEADLINE_UTC = $env:RC18_DEADLINE_UTC; $env:RC20_DEADLINE_UTC = $env:RC18_DEADLINE_UTC
                        $wd = $Root; if ($job.workdir) { $wd = Join-Path $Root ($job.workdir -replace '/', '\') }
                        $setEnv = @(); if ($job.env) { foreach ($ep in $job.env.PSObject.Properties) { Set-Item -Path ('env:' + $ep.Name) -Value ([string]$ep.Value); $setEnv += $ep.Name } }
                        $proc = Start-Process -FilePath $Python[[string]$job.python] -ArgumentList @($job.args) -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
                        $null = $proc.Handle
                        foreach ($en in $setEnv) { Remove-Item -Path ('env:' + $en) -ErrorAction SilentlyContinue }
                        $workers[[int]$proc.Id] = @{ job = $job.name; n = $n; proc = $proc; start = (UtcNow); log = $out }
                        Add-Log ([pscustomobject]@{ event = 'WORKER_START'; job = $job.name; worker = $n; pid = $proc.Id; opus_used_before = $opusUsed; astra_used = $u.astra; leaves = $u.leaves })
                        Start-Sleep -Milliseconds 300
                        Write-OpusJobs (Get-CoordJobRows $plan)
                    }
                } catch { Add-Log ([pscustomobject]@{ event = 'LAUNCH_ERROR'; error = $_.Exception.Message }) } finally { Exit-CoordLock }
            }
        }
        # heartbeat
        $wl = @(); foreach ($k in $workers.Keys) {
            $w = $workers[$k]; $cpu = $null
            $kids = @(Get-CimInstance Win32_Process -Filter ("ParentProcessId={0}" -f $k) | ForEach-Object { [int]$_.ProcessId })
            try { $cpu = [Math]::Round((Get-Process -Id $k).TotalProcessorTime.TotalSeconds, 1); foreach ($c in $kids) { $cpu += [Math]::Round((Get-Process -Id $c).TotalProcessorTime.TotalSeconds, 1) } } catch { }
            $wl += [pscustomobject]@{ pid = $k; child_pids = $kids; job = $w.job; worker = $w.n; start_utc = $w.start; cpu_s = $cpu; threads = 1; log = $w.log; host = 'Burak' }
        }
        $js = @{}; foreach ($k in $states.Keys) { $s = $states[$k]; $js[$k] = [pscustomobject]@{ done = $s.done; failed = $s.failed; locks = $s.locks; total = $s.total; remaining = [Math]::Max(0, $s.total - $s.done - $s.failed); last_unit = $s.last_unit; last_unit_utc = $s.last_unit_utc; paused = $state.paused.ContainsKey($k); live_workers = [int]$live[$k] } }
        $hb = [pscustomobject]@{ utc = (UtcNow); runner_pid = $PID; runner_start_utc = $startUtc; cycle = $cycle; host = 'Burak'
            state = $(if ($pastDeadline) { 'DEADLINE_REACHED_NO_NEW_STARTS' } elseif ($workers.Count -gt 0) { 'RUNNING' } else { 'IDLE' })
            budget = [pscustomobject]@{ t0_utc = $t0.ToString('s') + 'Z'; deadline_utc = $deadline.ToString('s') + 'Z'; elapsed_h = [Math]::Round(($now - $t0).TotalHours, 2); remaining_h = [Math]::Round(($deadline - $now).TotalHours, 2) }
            capacity = [pscustomobject]@{ opus_share = $share; runner_slots = $slots; opus_used = $workers.Count + $u.opus_other; opus_other_leaves = $u.opus_other; astra_used = $u.astra; leaves = $u.leaves }
            workers = $wl; jobs = $js
            restart = 'powershell -NoProfile -ExecutionPolicy Bypass -File src\rc21_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)' }
        Write-JsonAtomic $HbFile $hb
        $s1 = @{}; foreach ($k in @('paused', 'consecutive_failures', 'attempts', 'resume_tokens')) { $s1[$k] = $state[$k] }
        Write-JsonAtomic $StateFile ([pscustomobject]$s1)
        if ($changed) {
            $cj = @()
            foreach ($row in $wl) {
                $jname = $row.job; $jdef = @($plan.jobs | Where-Object { $_.name -eq $jname })[0]; $cmd = ''
                if ($null -ne $jdef) { $cmd = ('{0} {1}' -f [string]$jdef.python, (@($jdef.args) -join ' ')) }
                $cj += [pscustomobject]@{ pid = $row.pid; child_pids = $row.child_pids; job = $jname; start_utc = $row.start_utc; threads = 1; host = 'Burak'; command = $cmd; launched_by = 'src/rc21_runner.ps1' }
            }
            try { Update-CoordJobs $cj } catch { Add-Log ([pscustomobject]@{ event = 'COORD_UPDATE_ERROR'; error = $_.Exception.Message }) }
        }
        if ($changed -or (([DateTime]::UtcNow - $lastStatus).TotalMinutes -ge 5)) {
            $L = @("# Opus RC21 runner status (auto-generated)", "", ("Updated {0}. Runner PID {1} (started {2}). State **{3}**. Budget: elapsed {4} h, remaining {5} h (deadline {6})." -f $hb.utc, $PID, $startUtc, $hb.state, $hb.budget.elapsed_h, $hb.budget.remaining_h, $hb.budget.deadline_utc), "",
                   ("Capacity: Opus share {0} threads, runner slots {1}, Opus used {2}, Astra used {3} (her reserved share is 2). Leaves: {4}" -f $share, $slots, $hb.capacity.opus_used, $u.astra, $u.leaves), "",
                   "| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |", "|---|---|---|---|---|---|---|")
            foreach ($k in ($js.Keys | Sort-Object)) { $s = $js[$k]; $L += ("| {0} | {1}/{2} | {3} | {4} | {5} | {6} | {7} ({8}) |" -f $k, $s.done, $s.total, $s.failed, $s.remaining, $s.live_workers, $s.paused, $s.last_unit, $s.last_unit_utc) }
            $L += @("", "| worker PID | job | start (UTC) | CPU s | log |", "|---|---|---|---|---|")
            foreach ($w in $wl) { $L += ("| {0} (children {1}) | {2} | {3} | {4} | {5} |" -f $w.pid, ($w.child_pids -join ','), $w.job, $w.start_utc, $w.cpu_s, $w.log) }
            $L += @("", ("Restart (idempotent): ``{0}``" -f $hb.restart))
            [System.IO.File]::WriteAllText($StatusFile, ($L -join "`n") + "`n", $Utf8); $lastStatus = [DateTime]::UtcNow
        }
        if ($pastDeadline -and $workers.Count -eq 0) { Add-Log ([pscustomobject]@{ event = 'RUNNER_END'; reason = 'deadline reached and no live workers' }); break }
        if ($plan.stop_runner -and $workers.Count -eq 0) { Add-Log ([pscustomobject]@{ event = 'RUNNER_END'; reason = 'stop_runner set in PLAN.json and no live workers' }); break }
        Start-Sleep -Seconds 30
    }
} catch {
    Add-Log ([pscustomobject]@{ event = 'RUNNER_EXCEPTION'; error = $_.Exception.Message; line = $_.InvocationInfo.ScriptLineNumber })
    throw
} finally {
    $lock.Dispose()
}
