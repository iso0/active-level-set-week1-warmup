# C1S (C1 stability) copy of src/c1c_runner.ps1 (owner instruction 2026-10-29): runner directory opus_c1_stability/runner, coordination only through
# C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (campaign id opus_c1_stability_20261029; Astra's files read only);
# one 48-hour window from t0 in PLAN.json (2026-10-29T00:10:41Z).
# C1C (C1 confirmation) copy of src/ea_runner.ps1 (owner instruction 2026-10-26, second task): runner directory opus_c1_confirmation/runner,
# coordination only through C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (campaign id opus_c1_stability_20261029;
# Astra's files read only); one 48-hour window from t0 in PLAN.json (2026-10-26T18:05:16Z).
# EA study copy of src/el_runner.ps1 (owner instruction 2026-10-26): runner directory opus_error_attribution/runner, coordination only through
# C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (Astra's files read only); one 48-hour window from t0 in PLAN.json.
# EL study runner (owner instruction 2026-10-24; ONE 48-hour window from t0 in runner/PLAN.json, never restarted).
# Copy of src/rc24_runner.ps1 with the coordination rules of the 2026-10-24 instruction:
#   (i)   runner directory outputs/research_campaign_20261029/opus_c1_stability/runner;
#   (ii)  NO shared coordination record: the runner never reads or writes POOL_PLAN.json. It writes ONLY its own state file
#         C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (temp + replace) and READS
#         astra_state.json there (never writes it) to recognise Astra's processes;
#   (iii) capacity: at most min(3, floor(3 x logical CPUs / 8), PLAN.runner_slots) single-thread numerical leaves for Opus
#         (8 logical CPUs -> 3). Opus usage = this runner's workers + every other numerical leaf that is not Astra's (heavy
#         analyses started by hand count too). Astra's reserved share is never used, even when it looks empty;
#   (iv)  memory guard: no worker starts while free physical memory < PLAN.min_free_mb (default 3072 MB);
#   (v)   every worker gets OMP/OPENBLAS/MKL/NUMEXPR_NUM_THREADS = 1 and RC18_DEADLINE_UTC = EL_DEADLINE_UTC = the window end.
# Unchanged from RC18-RC24: single instance (runner.lock), PLAN.json re-read every cycle, pool jobs claim units with O_EXCL
# lock files and checkpoint each unit atomically (finished units are never rerun; locks of dead PIDs are released), job
# dependencies ("after"), 2 consecutive failures pause a job until its resume_token changes, no start after the deadline,
# heartbeat every 30 s, STATUS.md every 5 min, events in runner_log.jsonl.
#   powershell -NoProfile -ExecutionPolicy Bypass -File src\c1s_start_runner.ps1      (detached launch via WMI, supervised)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RDir = Join-Path $Root 'outputs\research_campaign_20261029\opus_c1_stability\runner'
$PlanFile = Join-Path $RDir 'PLAN.json'
$StateFile = Join-Path $RDir 'STATE.json'
$LogFile = Join-Path $RDir 'runner_log.jsonl'
$HbFile = Join-Path $RDir 'HEARTBEAT.json'
$StatusFile = Join-Path $RDir 'STATUS.md'
$WDir = Join-Path $RDir 'workers'
$SharedDir = 'C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029'
$OpusState = Join-Path $SharedDir 'opus_state.json'
$AstraState = Join-Path $SharedDir 'astra_state.json'
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

function Get-AstraPids {
    # read-only: any pid / child_pids / pids fields in Astra's job rows
    $out = @()
    try {
        if (Test-Path -LiteralPath $AstraState) {
            $a = Read-Json $AstraState
            foreach ($j in @($a.jobs)) {
                foreach ($f in @('pid', 'worker_pid', 'runner_pid')) { if ($j.$f) { $out += [int]$j.$f } }
                foreach ($f in @('child_pids', 'pids')) { foreach ($x in @($j.$f)) { if ($x) { $out += [int]$x } } }
            }
        }
    } catch { }
    return $out
}

function Get-Usage([int[]]$mine) {
    $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, CommandLine)
    $num = @($all | Where-Object { $_.Name -match '^(python|pythonw|julia|Rscript)\.exe$' })
    $parents = @{}; foreach ($p in $num) { $parents[[int]$p.ParentProcessId] = $true }
    $myTree = Get-Tree $mine $all
    $astraRoots = @($all | Where-Object { $_.Name -match '^codex' } | ForEach-Object { [int]$_.ProcessId }) + @(Get-AstraPids)
    $astraTree = Get-Tree $astraRoots $all
    $opusOther = 0; $astra = 0; $rows = @()
    foreach ($p in $num) {
        $id = [int]$p.ProcessId
        if ($parents.ContainsKey($id)) { continue }                     # launcher stub, its child is the leaf
        if ($myTree.ContainsKey($id)) { continue }
        if ($astraTree.ContainsKey($id) -or ([string]$p.CommandLine -match '\\Codex\\|astra_|thesis_astra')) { $astra += 1; $rows += ('astra:{0}' -f $id); continue }
        $opusOther += 1; $rows += ('other:{0}' -f $id)
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

function Write-OpusState($plan, $status, $wl) {
    # the ONLY shared-folder write: Opus's own state file (temp + replace)
    $jobs = @()
    foreach ($row in @($wl)) {
        $jname = $row.job; $jdef = @($plan.jobs | Where-Object { $_.name -eq $jname })[0]; $cmd = ''
        if ($null -ne $jdef) { $cmd = ('{0} {1}' -f [string]$jdef.python, (@($jdef.args) -join ' ')) }
        $jobs += [pscustomobject]@{ pid = $row.pid; child_pids = $row.child_pids; job = $jname; start_utc = $row.start_utc; threads = 1; command = $cmd }
    }
    $o = [pscustomobject]@{ campaign_id = 'opus_c1_stability_20261029'; owner = 'Opus'; host = $env:COMPUTERNAME; max_workers = $script:capOpus; blas_threads = 1
        start_utc = [string]$plan.t0_utc; deadline_utc = [string]$plan.deadline_utc
        window_rule = 'one 48 h window from start_utc; quota waits, restarts and session changes never reset it; closed early when the work is done'
        jobs = $jobs; status = $status; runner_pid = $PID
        workspace = 'C:\Users\ozgur\Documents\thesis\.claude\worktrees\joint-depth-label-dev'; outputs = 'outputs/research_campaign_20261029/opus_c1_stability'
        writes = 'only this file (and own lock / temp files) in the shared folder; astra_state.json is read, never written'
        previous_campaign = [pscustomobject]@{ campaign_id = 'opus_c1_confirmation_20261026'; status = 'CLOSED'; closed_utc = '2026-10-26T21:45:49Z'; note = 'C1C closed before this task (shared folder campaign_20261026); its records are unchanged' }
        updated_utc = (UtcNow) }
    try { Write-JsonAtomic $OpusState $o } catch { Add-Log ([pscustomobject]@{ event = 'OPUS_STATE_WRITE_ERROR'; error = $_.Exception.Message }) }
}

$lockPath = Join-Path $RDir 'runner.lock'
try { $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None) }
catch { Write-Output 'Another C1S runner holds runner.lock; exiting.'; exit 2 }
$state = @{ paused = @{}; consecutive_failures = @{}; attempts = @{}; resume_tokens = @{} }
if (Test-Path -LiteralPath $StateFile) {
    $s0 = Read-Json $StateFile
    foreach ($k in @('paused', 'consecutive_failures', 'attempts', 'resume_tokens')) { if ($s0.$k) { foreach ($p in $s0.$k.PSObject.Properties) { $state[$k][$p.Name] = $p.Value } } }
}
$logical = [Environment]::ProcessorCount
$script:capOpus = [Math]::Max(1, [Math]::Min(3, [Math]::Floor(3 * $logical / 8)))
$workers = @{}            # pid -> @{ job; n; proc; start; log }
$count = @{}
$startUtc = UtcNow; $cycle = 0; $lastStatus = [DateTime]::MinValue; $lastOpusState = [DateTime]::MinValue
try {
    Add-Log ([pscustomobject]@{ event = 'RUNNER_START'; pid = $PID; logical_cpus = $logical; opus_cap = $script:capOpus })
    while ($true) {
        $cycle++
        $plan = Read-Json $PlanFile
        $deadline = [DateTime]::Parse($plan.deadline_utc).ToUniversalTime()
        $t0 = [DateTime]::Parse($plan.t0_utc).ToUniversalTime()
        $slots = [Math]::Min($script:capOpus, [int]$plan.runner_slots)
        $minFree = 3072; if ($plan.min_free_mb) { $minFree = [int]$plan.min_free_mb }
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
        $cand = @($cand | Where-Object { $ok = $true; foreach ($dep in @($_.after)) { if ($dep -and $states.ContainsKey([string]$dep) -and -not $states[[string]$dep].finished) { $ok = $false } }; $ok })
        $mine = @(); foreach ($w in $workers.Values) { $mine += [int]$w.proc.Id }
        $u = Get-Usage $mine
        $opusUsed = $workers.Count + $u.opus_other
        $freeMB = 0; try { $freeMB = [int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1024) } catch { $freeMB = 0 }
        if ($cand.Count -gt 0 -and -not $pastDeadline -and -not $plan.stop_runner -and ($opusUsed + 1 -le $slots) -and ($freeMB -ge $minFree)) {
            try {
                $job = $cand[0]
                $count[$job.name] = 1 + [int]$count[$job.name]; $n = $count[$job.name]
                if ($job.kind -eq 'once') { $state.attempts[$job.name] = 1 + [int]$state.attempts[$job.name] }
                $out = Join-Path $WDir ('{0}_{1}.log' -f $job.name, $n); $err = Join-Path $WDir ('{0}_{1}.err.log' -f $job.name, $n)
                $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'
                $env:PYTHONIOENCODING = 'utf-8'; $env:RC18_DEADLINE_UTC = $deadline.ToString('yyyy-MM-ddTHH:mm:ssZ'); $env:EL_DEADLINE_UTC = $env:RC18_DEADLINE_UTC
                $wd = $Root; if ($job.workdir) { $wd = Join-Path $Root ($job.workdir -replace '/', '\') }
                $proc = Start-Process -FilePath $Python[[string]$job.python] -ArgumentList @($job.args) -WorkingDirectory $wd -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
                $null = $proc.Handle
                $workers[[int]$proc.Id] = @{ job = $job.name; n = $n; proc = $proc; start = (UtcNow); log = $out }
                Add-Log ([pscustomobject]@{ event = 'WORKER_START'; job = $job.name; worker = $n; pid = $proc.Id; opus_used_before = $opusUsed; astra_used = $u.astra; free_mb = $freeMB; leaves = $u.leaves })
                Start-Sleep -Milliseconds 300; $changed = $true
            } catch { Add-Log ([pscustomobject]@{ event = 'LAUNCH_ERROR'; error = $_.Exception.Message }) }
        }
        # heartbeat
        $wl = @(); foreach ($k in $workers.Keys) {
            $w = $workers[$k]; $cpu = $null
            $kids = @(Get-CimInstance Win32_Process -Filter ("ParentProcessId={0}" -f $k) | ForEach-Object { [int]$_.ProcessId })
            try { $cpu = [Math]::Round((Get-Process -Id $k).TotalProcessorTime.TotalSeconds, 1); foreach ($c in $kids) { $cpu += [Math]::Round((Get-Process -Id $c).TotalProcessorTime.TotalSeconds, 1) } } catch { }
            $wl += [pscustomobject]@{ pid = $k; child_pids = $kids; job = $w.job; worker = $w.n; start_utc = $w.start; cpu_s = $cpu; threads = 1; log = $w.log; host = $env:COMPUTERNAME }
        }
        $js = @{}; foreach ($k in $states.Keys) { $s = $states[$k]; $js[$k] = [pscustomobject]@{ done = $s.done; failed = $s.failed; locks = $s.locks; total = $s.total; remaining = [Math]::Max(0, $s.total - $s.done - $s.failed); last_unit = $s.last_unit; last_unit_utc = $s.last_unit_utc; paused = $state.paused.ContainsKey($k); live_workers = [int]$live[$k] } }
        $st = $(if ($pastDeadline) { 'DEADLINE_REACHED_NO_NEW_STARTS' } elseif ($workers.Count -gt 0) { 'RUNNING' } else { 'IDLE' })
        $hb = [pscustomobject]@{ utc = (UtcNow); runner_pid = $PID; runner_start_utc = $startUtc; cycle = $cycle; host = $env:COMPUTERNAME; state = $st
            budget = [pscustomobject]@{ t0_utc = $t0.ToString('s') + 'Z'; deadline_utc = $deadline.ToString('s') + 'Z'; elapsed_h = [Math]::Round(($now - $t0).TotalHours, 2); remaining_h = [Math]::Round(($deadline - $now).TotalHours, 2) }
            capacity = [pscustomobject]@{ logical_cpus = $logical; opus_cap = $script:capOpus; runner_slots = $slots; opus_used = $workers.Count + $u.opus_other; opus_other_leaves = $u.opus_other; astra_used = $u.astra; free_mb = $freeMB; min_free_mb = $minFree; leaves = $u.leaves }
            workers = $wl; jobs = $js
            restart = 'powershell -NoProfile -ExecutionPolicy Bypass -File src\c1s_start_runner.ps1   (idempotent; skips finished units; lock prevents a second runner)' }
        Write-JsonAtomic $HbFile $hb
        $s1 = @{}; foreach ($k in @('paused', 'consecutive_failures', 'attempts', 'resume_tokens')) { $s1[$k] = $state[$k] }
        Write-JsonAtomic $StateFile ([pscustomobject]$s1)
        if ($changed -or (([DateTime]::UtcNow - $lastOpusState).TotalMinutes -ge 5)) { Write-OpusState $plan $st $wl; $lastOpusState = [DateTime]::UtcNow }
        if ($changed -or (([DateTime]::UtcNow - $lastStatus).TotalMinutes -ge 5)) {
            $L = @("# Opus C1S runner status (auto-generated)", "", ("Updated {0}. Runner PID {1} (started {2}). State **{3}**. Window: elapsed {4} h, remaining {5} h (deadline {6})." -f $hb.utc, $PID, $startUtc, $hb.state, $hb.budget.elapsed_h, $hb.budget.remaining_h, $hb.budget.deadline_utc), "",
                   ("Capacity: Opus cap {0} single-thread leaves (logical CPUs {1}), runner slots {2}, Opus used {3}, Astra used {4} (her share is never used), free memory {5} MB (min {6}). Leaves: {7}" -f $script:capOpus, $logical, $slots, $hb.capacity.opus_used, $u.astra, $freeMB, $minFree, $u.leaves), "",
                   "| job | done | failed | remaining | live workers | paused | last completed unit (UTC) |", "|---|---|---|---|---|---|---|")
            foreach ($k in ($js.Keys | Sort-Object)) { $s = $js[$k]; $L += ("| {0} | {1}/{2} | {3} | {4} | {5} | {6} | {7} ({8}) |" -f $k, $s.done, $s.total, $s.failed, $s.remaining, $s.live_workers, $s.paused, $s.last_unit, $s.last_unit_utc) }
            $L += @("", "| worker PID | job | start (UTC) | CPU s | log |", "|---|---|---|---|---|")
            foreach ($w in $wl) { $L += ("| {0} (children {1}) | {2} | {3} | {4} | {5} |" -f $w.pid, ($w.child_pids -join ','), $w.job, $w.start_utc, $w.cpu_s, $w.log) }
            $L += @("", ("Restart (idempotent): ``{0}``" -f $hb.restart))
            [System.IO.File]::WriteAllText($StatusFile, ($L -join "`n") + "`n", $Utf8); $lastStatus = [DateTime]::UtcNow
        }
        if ($pastDeadline -and $workers.Count -eq 0) { Write-OpusState $plan 'DEADLINE_REACHED' @(); Add-Log ([pscustomobject]@{ event = 'RUNNER_END'; reason = 'deadline reached and no live workers' }); break }
        if ($plan.stop_runner -and $workers.Count -eq 0) {
            $fin = 'IDLE'; if ($plan.campaign_closed) { $fin = 'CLOSED' }
            Write-OpusState $plan $fin @(); Add-Log ([pscustomobject]@{ event = 'RUNNER_END'; reason = 'stop_runner set in PLAN.json and no live workers' }); break
        }
        Start-Sleep -Seconds 30
    }
} catch {
    Add-Log ([pscustomobject]@{ event = 'RUNNER_EXCEPTION'; error = $_.Exception.Message; line = $_.InvocationInfo.ScriptLineNumber })
    throw
} finally {
    $lock.Dispose()
}
