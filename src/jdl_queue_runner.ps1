# Idempotent continuation runner for Opus's own joint-depth-label queue (outputs/joint_depth_label_development/queue/QUEUE.json).
#
# * Never touches another process, lock, priority or file outside this worktree's outputs; it only reads the process
#   list and Astra's PIPELINE_STATE.json.
# * Single instance: an exclusive handle on queue/runner.lock.
# * One job at a time, one BLAS thread, "--threads 1" on its command line (so that Astra's host count sees one slot).
# * Capacity rule: used = sum over leaf numerical processes (python/pythonw/julia/Rscript) outside Astra's process tree of
#   1 slot if the command line has "--threads 1", else 4; plus 1 slot reserved for Astra's pipeline while it is active.
#   A job starts only if used + 1 <= 4 at two snapshots 60 s apart.  This PowerShell process is not a numerical worker.
# * Tasks run in queue order once their dependencies are done, their required gates have passed and their wait
#   conditions hold; a completed task is detected from its outputs and never rerun; a failed command or gate is
#   recorded, blocks only its dependants, and is never retried automatically.
# * After a successful task its declared outputs (and this queue's state/logs) are committed by path and pushed;
#   a git failure is recorded and does not stop the queue.
# Entry point (resumable):  powershell -NoProfile -ExecutionPolicy Bypass -File src\jdl_queue_runner.ps1 [-DryRun]
param([switch]$DryRun)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$QDir = Join-Path $Root 'outputs\joint_depth_label_development\queue'
$QueueFile = Join-Path $QDir 'QUEUE.json'
$StateFile = Join-Path $QDir 'QUEUE_STATE.json'
$LogFile = Join-Path $QDir 'queue_log.jsonl'
$LogDir = Join-Path $QDir 'logs'
$AstraState = 'C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_balanced_decision_acquisition\PIPELINE_STATE.json'
$SystemPython = 'C:\Users\ozgur\AppData\Local\Microsoft\WindowsApps\python.exe'
$VenvPython = 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe'
$Utf8 = New-Object System.Text.UTF8Encoding $false
$CoAuthor = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-JsonFile([string]$path, $obj) {
    $tmp = $path + '.tmp'
    [System.IO.File]::WriteAllText($tmp, ($obj | ConvertTo-Json -Depth 12), $Utf8)
    Move-Item -LiteralPath $tmp -Destination $path -Force
}
function Add-Log($obj) {
    $obj | Add-Member -NotePropertyName utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    [System.IO.File]::AppendAllText($LogFile, (($obj | ConvertTo-Json -Depth 8 -Compress) + "`n"), $Utf8)
}
function Read-Json([string]$path) { return ([System.IO.File]::ReadAllText($path, $Utf8) | ConvertFrom-Json) }
function Invoke-Git([string[]]$GitArgs) {
    # .NET process with captured streams: git's stderr never becomes a PowerShell error record.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'git'
    $psi.Arguments = (($GitArgs | ForEach-Object { if ($_ -match '[\s"<>]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }) -join ' ')
    $psi.UseShellExecute = $false; $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $Root
    $p = [System.Diagnostics.Process]::Start($psi)
    $o = $p.StandardOutput.ReadToEnd(); $e = $p.StandardError.ReadToEnd(); $p.WaitForExit()
    return [pscustomobject]@{ code = $p.ExitCode; out = $o; err = $e }
}

function Get-AstraInfo {
    $info = @{ active = $false; tree = @(); state = 'absent' }
    if (-not (Test-Path -LiteralPath $AstraState)) { return $info }
    try { $s = Read-Json $AstraState } catch { $info.active = $true; $info.state = 'unreadable (treated as active)'; return $info }
    $info.state = [string]$s.state
    $wrapper = [int]$s.wrapper_pid
    $alive = $null -ne (Get-Process -Id $wrapper -ErrorAction SilentlyContinue)
    $terminal = ($info.state -like 'STOPPED*') -or ($info.state -eq 'COMPUTATION_FINISHED_REVIEW_REQUIRED')
    $info.active = $alive -and (-not $terminal)
    if ($alive) {
        $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
        $parent = @{}; foreach ($p in $all) { $parent[[int]$p.ProcessId] = [int]$p.ParentProcessId }
        foreach ($p in $all) {
            $id = [int]$p.ProcessId; $cur = $id
            for ($i = 0; $i -lt 12 -and $parent.ContainsKey($cur); $i++) {
                if ($cur -eq $wrapper) { $info.tree += $id; break }
                $cur = $parent[$cur]
            }
        }
    }
    return $info
}

function Get-Snapshot {
    $procs = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|julia|Rscript)\.exe$' })
    $parents = @{}; foreach ($p in $procs) { $parents[[int]$p.ParentProcessId] = $true }
    $astra = Get-AstraInfo
    $used = 0; $rows = @()
    foreach ($p in $procs) {
        $id = [int]$p.ProcessId
        if ($parents.ContainsKey($id)) { continue }
        if ($astra.tree -contains $id) { continue }
        $cmd = [string]$p.CommandLine
        $slots = 4; if ($cmd -match '--threads 1') { $slots = 1 }
        $used += $slots
        $rows += [pscustomobject]@{ pid = $id; slots = $slots; cmd = $cmd.Substring(0, [Math]::Min(110, $cmd.Length)) }
    }
    if ($astra.active) { $used += 1 }
    return [pscustomobject]@{ used = $used; astra_active = $astra.active; astra_state = $astra.state; leaves = $rows }
}

function Test-Done($task) {
    $d = $task.done
    switch ($d.type) {
        'file' { return (Test-Path -LiteralPath (Join-Path $Root $d.path)) }
        'committed' {
            if (-not (Test-Path -LiteralPath (Join-Path $Root $d.path))) { return $false }
            $r = Invoke-Git @('log', '--format=%H', '--', $d.path)
            return ($r.code -eq 0 -and $r.out.Trim().Length -gt 0)
        }
        'json_field' {
            $p = Join-Path $Root $d.path
            if (-not (Test-Path -LiteralPath $p)) { return $false }
            try { $o = Read-Json $p; return ($null -ne $o.($d.field)) } catch { return $false }
        }
        'count' {
            $dir = Split-Path -Parent (Join-Path $Root $d.glob); $pat = Split-Path -Leaf $d.glob
            if (-not (Test-Path -LiteralPath $dir)) { return $false }
            return (@(Get-ChildItem -LiteralPath $dir -Filter $pat).Count -ge [int]$d.n)
        }
        'never' { return $false }
    }
    return $false
}

function Test-Gate($task) {
    if ($null -eq $task.gate) { return $true }
    $p = Join-Path $Root $task.gate.path
    if (-not (Test-Path -LiteralPath $p)) { return $false }
    try { $o = Read-Json $p; return ([string]$o.($task.gate.field) -eq [string]$task.gate.equals) } catch { return $false }
}

function Test-Wait($task) {
    if ($null -eq $task.wait_for) { return $true }
    if ($task.wait_for.type -eq 'svgp_complete') {
        $f = Join-Path $Root 'outputs\joint_depth_label_development\temporal_repair\svgp_ngd_fits.jsonl'
        $n4 = 0; $n8 = 0
        foreach ($line in [System.IO.File]::ReadAllLines($f, $Utf8)) {
            if ($line.Trim().Length -eq 0) { continue }
            if ($line -match '"inducing_points": 400') { $n4++ } elseif ($line -match '"inducing_points": 800') { $n8++ }
        }
        $workers = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and ([string]$_.CommandLine) -match 'jdl_temporal_svgp fit' }).Count
        return ($n4 -ge [int]$task.wait_for.m400 -and $n8 -ge [int]$task.wait_for.m800 -and $workers -eq 0)
    }
    return $false
}

function Invoke-Commit($task, $state) {
    $paths = @($task.commit | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) }) + @('outputs/joint_depth_label_development/queue')
    try {
        $a = Invoke-Git (@('add', '--') + $paths)
        $c = Invoke-Git (@('commit', '-q', '-m', [string]$task.message, '-m', $CoAuthor, '--') + $paths)
        $sha = (Invoke-Git @('rev-parse', '--short', 'HEAD')).out.Trim()
        $detail = ($a.err + ' ' + $c.out + ' ' + $c.err).Trim()
        Add-Log ([pscustomobject]@{ event = 'COMMIT'; task = $task.id; ok = ($c.code -eq 0); head = $sha; detail = $detail.Substring(0, [Math]::Min(300, $detail.Length)) })
        $p = Invoke-Git @('push', '-q', 'origin', 'joint-depth-label-dev')
        $pd = ($p.out + ' ' + $p.err).Trim()
        Add-Log ([pscustomobject]@{ event = 'PUSH'; task = $task.id; ok = ($p.code -eq 0); detail = $pd.Substring(0, [Math]::Min(300, $pd.Length)) })
        return $sha
    } catch {
        Add-Log ([pscustomobject]@{ event = 'COMMIT_ERROR'; task = $task.id; error = $_.Exception.Message })
        return $null
    }
}

# ------------------------------------------------------------------------------------------------ single instance
$lockPath = Join-Path $QDir 'runner.lock'
try {
    $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
    Write-Output 'Another runner instance holds queue/runner.lock; exiting.'
    exit 2
}
try {
    $queue = Read-Json $QueueFile
    if (Test-Path -LiteralPath $StateFile) { $state = Read-Json $StateFile } else { $state = [pscustomobject]@{ tasks = [pscustomobject]@{} } }
    foreach ($t in $queue.tasks) {
        if ($null -eq $state.tasks.($t.id)) { $state.tasks | Add-Member -NotePropertyName $t.id -NotePropertyValue ([pscustomobject]@{ status = 'pending' }) }
    }
    $state | Add-Member -NotePropertyName runner_pid -NotePropertyValue $PID -Force
    $state | Add-Member -NotePropertyName started_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    Write-JsonFile $StateFile $state
    Add-Log ([pscustomobject]@{ event = 'RUNNER_START'; pid = $PID; dry_run = [bool]$DryRun })
    $lastWaitLog = [DateTime]::MinValue
    while ($true) {
        $ready = $null; $open = 0
        foreach ($t in $queue.tasks) {
            $st = $state.tasks.($t.id)
            if ($st.status -in @('done', 'failed', 'blocked', 'gate_failed')) { continue }
            if (($t.done.type -ne 'never') -and (Test-Done $t)) {
                $st.status = 'done'; $st | Add-Member -NotePropertyName note -NotePropertyValue 'outputs already present; not rerun' -Force
                if ($null -ne $t.gate -and -not (Test-Gate $t)) { $st.status = 'gate_failed' }
                Write-JsonFile $StateFile $state; continue
            }
            $open++
            $blockedBy = @()
            foreach ($d in @($t.depends)) {
                if ($null -eq $d) { continue }
                $ds = $state.tasks.$d.status
                if ($ds -in @('failed', 'blocked', 'gate_failed') -and -not $t.allow_blocked_dependencies) { $blockedBy += "$d ($ds)" }
            }
            foreach ($g in @($t.gate_requires)) {
                if ($null -eq $g) { continue }
                if ($state.tasks.$g.status -eq 'gate_failed') { $blockedBy += "$g (gate failed)" }
            }
            if ($blockedBy.Count -gt 0) {
                $st.status = 'blocked'; $st | Add-Member -NotePropertyName blocked_by -NotePropertyValue ($blockedBy -join '; ') -Force
                Add-Log ([pscustomobject]@{ event = 'BLOCKED'; task = $t.id; by = ($blockedBy -join '; ') })
                Write-JsonFile $StateFile $state; continue
            }
            $depsDone = $true
            foreach ($d in @($t.depends)) {
                if ($null -eq $d) { continue }
                $ds = $state.tasks.$d.status
                if (-not ($ds -eq 'done' -or ($t.allow_blocked_dependencies -and $ds -in @('failed', 'blocked', 'gate_failed')))) { $depsDone = $false }
            }
            if (-not $depsDone) { continue }
            if (-not (Test-Wait $t)) { continue }
            $ready = $t; break
        }
        if ($null -eq $ready) {
            if ($open -eq 0) { break }
            if (([DateTime]::UtcNow - $lastWaitLog).TotalMinutes -ge 30) { Add-Log ([pscustomobject]@{ event = 'WAIT_DEPENDENCIES'; open_tasks = $open }); $lastWaitLog = [DateTime]::UtcNow }
            if ($DryRun) { break }
            Start-Sleep -Seconds 120; continue
        }
        # ----------------------------------------------------------------------------- capacity (two snapshots)
        $snap1 = Get-Snapshot
        if ($DryRun) {
            Add-Log ([pscustomobject]@{ event = 'DRY_RUN'; next_task = $ready.id; used = $snap1.used; astra_active = $snap1.astra_active; astra_state = $snap1.astra_state })
            Write-Output ("next task {0}; used slots {1}; Astra active {2} ({3})" -f $ready.id, $snap1.used, $snap1.astra_active, $snap1.astra_state)
            $snap1.leaves | Format-Table -AutoSize | Out-String | Write-Output
            break
        }
        if ($snap1.used + 1 -gt 4) {
            if (([DateTime]::UtcNow - $lastWaitLog).TotalMinutes -ge 30) {
                Add-Log ([pscustomobject]@{ event = 'WAIT_CAPACITY'; next_task = $ready.id; used = $snap1.used; astra_active = $snap1.astra_active }); $lastWaitLog = [DateTime]::UtcNow
            }
            Start-Sleep -Seconds 60; continue
        }
        Start-Sleep -Seconds 60
        $snap2 = Get-Snapshot
        if ($snap2.used + 1 -gt 4) { continue }
        # ----------------------------------------------------------------------------- run
        $st = $state.tasks.($ready.id)
        $py = $SystemPython; if ($ready.python -eq 'venv') { $py = $VenvPython }
        $out = Join-Path $LogDir ($ready.id + '.log'); $err = Join-Path $LogDir ($ready.id + '.err.log')
        $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'; $env:PYTHONIOENCODING = 'utf-8'
        $st.status = 'running'; $st | Add-Member -NotePropertyName started_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
        Write-JsonFile $StateFile $state
        Add-Log ([pscustomobject]@{ event = 'START'; task = $ready.id; used_before = $snap2.used; astra_active = $snap2.astra_active; python = $py; args = ($ready.args -join ' ') })
        $t0 = Get-Date
        $proc = Start-Process -FilePath $py -ArgumentList $ready.args -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
        $null = $proc.Handle
        $proc.WaitForExit()
        $code = $proc.ExitCode; $secs = [Math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
        $st | Add-Member -NotePropertyName exit_code -NotePropertyValue $code -Force
        $st | Add-Member -NotePropertyName seconds -NotePropertyValue $secs -Force
        $st | Add-Member -NotePropertyName finished_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
        if ($code -ne 0) {
            $st.status = 'failed'
            Add-Log ([pscustomobject]@{ event = 'END'; task = $ready.id; exit_code = $code; seconds = $secs; status = 'failed' })
        } else {
            $st.status = 'done'
            if ($null -ne $ready.gate) {
                $pass = Test-Gate $ready
                $st | Add-Member -NotePropertyName gate_passed -NotePropertyValue $pass -Force
                if (-not $pass) { $st.status = 'gate_failed' }
            }
            Add-Log ([pscustomobject]@{ event = 'END'; task = $ready.id; exit_code = 0; seconds = $secs; status = $st.status })
        }
        Write-JsonFile $StateFile $state
        if ($st.status -in @('done', 'gate_failed') -and $null -ne $ready.commit) {
            $sha = Invoke-Commit $ready $state
            $st | Add-Member -NotePropertyName commit -NotePropertyValue $sha -Force
            Write-JsonFile $StateFile $state
        }
    }
    $state | Add-Member -NotePropertyName finished_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    Write-JsonFile $StateFile $state
    Add-Log ([pscustomobject]@{ event = 'RUNNER_END'; dry_run = [bool]$DryRun })
} catch {
    Add-Log ([pscustomobject]@{ event = 'RUNNER_EXCEPTION'; error = $_.Exception.Message })
    throw
} finally {
    $lock.Dispose()
}
