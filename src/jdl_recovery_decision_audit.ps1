# Logged technical recovery of queue tasks T05-T08 (cached-posterior decision audit), authorized by the owner on
# 2026-10-14 after the console-serialization fix decision-audit-1.1.1.  One-shot sequence, separate from the live
# continuation runner, with new task IDs:
#   R04_PRESERVE                    copy the decision-audit-1.1 PASS validation file of queue T05 to preserved/ and commit it
#   R05_DECISION_VALIDATION_RETRY   python -m src.jdl_v2_decision_audit validate   (technical retry with 1.1.1; not a new experiment)
#   R06_DECISION_FREEZE             python -m src.jdl_v2_decision_audit manifest   (then commit the manifest; run() requires it)
#   R07_DECISION_RUN                python -m src.jdl_v2_decision_audit run        (decision-only readouts; zero fits)
#   R08_DECISION_EVALUATE           python -m src.jdl_v2_decision_audit evaluate   (exit 0 = summary written; exit 3 = PRIMARY_UNAVAILABLE)
# * Never reads or writes the live runner's QUEUE.json, QUEUE_STATE.json, queue_log.jsonl, logs or runner.lock: the original
#   T05 failure and the T06-T08 blocks stay recorded there as historical evidence.
# * Records: outputs/joint_depth_label_development/recovery/decision_audit_T05_T08/ (RECOVERY_STATE.json, RECOVERY_LOG.jsonl, logs/, preserved/).
# * Capacity: the runner's rule (leaf python/pythonw/julia/Rscript outside Astra's process tree count 1 slot with
#   "--threads 1", otherwise 4; plus 1 slot reserved while Astra's pipeline is active); a step starts only if
#   used + 1 <= 4 at two snapshots 60 s apart.  One job at a time, one BLAS thread, "--threads 1" on every command line.
#   This PowerShell process is not a numerical worker.
# * Single instance (exclusive handle on recovery.lock).  Idempotent: a done step is never rerun.  A failed step or gate
#   stops the sequence and is never retried automatically.
# * Gates: R05 needs exit code 0, status PASS, exactly 45 hard checks all true, audit_version decision-audit-1.1.1 and a
#   validated module hash equal to the current file; R06 needs exit 0, a manifest naming that validation hash and module
#   hash, and a successful commit; R07 needs exit 0 and 60 records; R08 accepts exit 0 or 3 (both recorded explicitly).
# * Git: explicit paths only; waits until the worktree index is not locked; retries a failed commit or push 3 times.
# Entry point:  powershell -NoProfile -ExecutionPolicy Bypass -File src\jdl_recovery_decision_audit.ps1
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = 'outputs/joint_depth_label_development'
$RRel = "$Out/recovery/decision_audit_T05_T08"
$RDir = Join-Path $Root ($RRel -replace '/', '\')
$StateFile = Join-Path $RDir 'RECOVERY_STATE.json'
$LogFile = Join-Path $RDir 'RECOVERY_LOG.jsonl'
$LogDir = Join-Path $RDir 'logs'
$PresDir = Join-Path $RDir 'preserved'
$AuditRel = "$Out/v2_decision_audit"
$AuditDir = Join-Path $Root ($AuditRel -replace '/', '\')
$ValFile = Join-Path $AuditDir 'DECISION_AUDIT_VALIDATION.json'
$ManFile = Join-Path $AuditDir 'DECISION_AUDIT_MANIFEST.json'
$CacheDir = Join-Path $Root 'outputs\joint_depth_label_development\_cache\decision_audit'
$Module = Join-Path $Root 'src\jdl_v2_decision_audit.py'
$AstraState = 'C:\Users\ozgur\Documents\Codex\2026-10-10\files-pasted-by-the-user-you\outputs\astra_balanced_decision_acquisition\PIPELINE_STATE.json'
$SystemPython = 'C:\Users\ozgur\AppData\Local\Microsoft\WindowsApps\python.exe'
$Utf8 = New-Object System.Text.UTF8Encoding $false
$CoAuthor = 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
$Version = 'decision-audit-1.1.1'
$OldModuleSha = '7af7a326c44f37d3baa8845976d942e82e41da5990cb790845f7f600dd3c7f7a'
$ExpectedHardChecks = 45
$Steps = @('R04_PRESERVE', 'R05_DECISION_VALIDATION_RETRY', 'R06_DECISION_FREEZE', 'R07_DECISION_RUN', 'R08_DECISION_EVALUATE')
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $PresDir | Out-Null

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
function Get-Sha([string]$path) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLower() }
function Invoke-Git([string[]]$GitArgs) {
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
        $rows += ('{0}:{1}' -f $id, $slots)
    }
    if ($astra.active) { $used += 1 }
    return [pscustomobject]@{ used = $used; astra_active = $astra.active; astra_state = $astra.state; leaves = ($rows -join ' ') }
}

function Wait-Capacity([string]$step) {
    $last = [DateTime]::MinValue
    while ($true) {
        $s1 = Get-Snapshot
        if ($s1.used + 1 -le 4) {
            Start-Sleep -Seconds 60
            $s2 = Get-Snapshot
            if ($s2.used + 1 -le 4) { return $s2 }
        }
        if (([DateTime]::UtcNow - $last).TotalMinutes -ge 30) {
            Add-Log ([pscustomobject]@{ event = 'WAIT_CAPACITY'; step = $step; used = $s1.used; astra_active = $s1.astra_active; leaves = $s1.leaves }); $last = [DateTime]::UtcNow
        }
        Start-Sleep -Seconds 60
    }
}

function Invoke-Step([string]$step, [string[]]$PyArgs) {
    $snap = Wait-Capacity $step
    $out = Join-Path $LogDir ($step + '.log'); $err = Join-Path $LogDir ($step + '.err.log')
    $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'; $env:NUMEXPR_NUM_THREADS = '1'; $env:PYTHONIOENCODING = 'utf-8'
    $moduleSha = Get-Sha $Module
    Add-Log ([pscustomobject]@{ event = 'START'; step = $step; used_before = $snap.used; astra_active = $snap.astra_active; astra_state = $snap.astra_state; leaves = $snap.leaves; python = $SystemPython; args = ($PyArgs -join ' '); module_sha256 = $moduleSha })
    $t0 = Get-Date
    $proc = Start-Process -FilePath $SystemPython -ArgumentList $PyArgs -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -NoNewWindow -PassThru
    $null = $proc.Handle
    $proc.WaitForExit()
    $code = $proc.ExitCode; $secs = [Math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Add-Log ([pscustomobject]@{ event = 'END'; step = $step; exit_code = $code; seconds = $secs })
    return [pscustomobject]@{ code = $code; seconds = $secs; started_utc = $t0.ToUniversalTime().ToString('o'); module_sha256 = $moduleSha }
}

function Wait-GitIdle {
    $gitDir = (Invoke-Git @('rev-parse', '--git-dir')).out.Trim()
    if (-not [System.IO.Path]::IsPathRooted($gitDir)) { $gitDir = Join-Path $Root $gitDir }
    $lockPath = Join-Path $gitDir 'index.lock'
    for ($i = 0; $i -lt 60 -and (Test-Path -LiteralPath $lockPath); $i++) { Start-Sleep -Seconds 5 }
}

function Invoke-Commit([string[]]$paths, [string]$message) {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        Wait-GitIdle
        $a = Invoke-Git (@('add', '--') + $paths)
        $c = Invoke-Git (@('commit', '-q', '-m', $message, '-m', $CoAuthor, '--') + $paths)
        if ($c.code -eq 0) {
            $sha = (Invoke-Git @('rev-parse', '--short', 'HEAD')).out.Trim()
            Add-Log ([pscustomobject]@{ event = 'COMMIT'; ok = $true; head = $sha; attempt = $attempt; message = $message.Substring(0, [Math]::Min(120, $message.Length)) })
            for ($k = 1; $k -le 3; $k++) {
                $p = Invoke-Git @('push', '-q', 'origin', 'joint-depth-label-dev')
                $pd = (($p.out + ' ' + $p.err).Trim() -replace '\s+', ' ')
                Add-Log ([pscustomobject]@{ event = 'PUSH'; ok = ($p.code -eq 0); attempt = $k; detail = $pd.Substring(0, [Math]::Min(200, $pd.Length)) })
                if ($p.code -eq 0) { break }
                Start-Sleep -Seconds 15
            }
            return $sha
        }
        $detail = (($a.err + ' ' + $c.out + ' ' + $c.err).Trim() -replace '\s+', ' ')
        Add-Log ([pscustomobject]@{ event = 'COMMIT_RETRY'; attempt = $attempt; detail = $detail.Substring(0, [Math]::Min(300, $detail.Length)) })
        Start-Sleep -Seconds 10
    }
    return $null
}

function Get-Records {
    # the recovery's own records that exist and contain files (an empty pathspec would make git refuse the commit)
    $r = @()
    foreach ($p in @("$RRel/RECOVERY_STATE.json", "$RRel/RECOVERY_LOG.jsonl")) { if (Test-Path -LiteralPath (Join-Path $Root ($p -replace '/', '\'))) { $r += $p } }
    if (@(Get-ChildItem -LiteralPath $LogDir -File -ErrorAction SilentlyContinue).Count -gt 0) { $r += "$RRel/logs" }
    return $r
}

function Set-Step([string]$step, [string]$status, $fields) {
    $st = $state.steps.$step
    $st.status = $status
    foreach ($k in $fields.Keys) { $st | Add-Member -NotePropertyName $k -NotePropertyValue $fields[$k] -Force }
    Write-JsonFile $StateFile $state
}

# ------------------------------------------------------------------------------------------------ single instance
$lockPath = Join-Path $RDir 'recovery.lock'
try {
    $lock = [System.IO.File]::Open($lockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
    Write-Output 'Another recovery instance holds recovery.lock; exiting.'
    exit 2
}
try {
    if (Test-Path -LiteralPath $StateFile) { $state = Read-Json $StateFile } else {
        $state = [pscustomobject]@{ recovery = 'logged technical recovery of queue T05-T08 (owner authorization of 2026-10-14); the original T05 failure and T06-T08 blocks stay recorded in queue/QUEUE_STATE.json'
                                    audit_version = $Version; steps = [pscustomobject]@{} }
    }
    foreach ($s in $Steps) { if ($null -eq $state.steps.$s) { $state.steps | Add-Member -NotePropertyName $s -NotePropertyValue ([pscustomobject]@{ status = 'pending' }) } }
    $state | Add-Member -NotePropertyName recovery_pid -NotePropertyValue $PID -Force
    $state | Add-Member -NotePropertyName started_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    Write-JsonFile $StateFile $state
    Add-Log ([pscustomobject]@{ event = 'RECOVERY_START'; pid = $PID; module_sha256 = (Get-Sha $Module) })
    foreach ($s in $Steps) {
        $st = $state.steps.$s
        if ($st.status -eq 'done') { continue }
        if ($st.status -eq 'failed') { Add-Log ([pscustomobject]@{ event = 'STOPPED_AT_FAILED_STEP'; step = $s }); break }
        switch ($s) {
            'R04_PRESERVE' {
                $dst = Join-Path $PresDir 'T05_decision-audit-1.1_DECISION_AUDIT_VALIDATION.json'
                if (-not (Test-Path -LiteralPath $dst)) {
                    if (-not (Test-Path -LiteralPath $ValFile)) { Set-Step $s 'failed' @{ reason = 'the 1.1 validation file is missing' }; break }
                    $v = Read-Json $ValFile
                    if (-not (([string]$v.audit_version -eq 'decision-audit-1.1') -and ([string]$v.status -eq 'PASS') -and ([string]$v.module_sha256 -eq $OldModuleSha))) {
                        Set-Step $s 'failed' @{ reason = 'the canonical validation file is not the decision-audit-1.1 PASS attempt of queue T05' }; break
                    }
                    Copy-Item -LiteralPath $ValFile -Destination $dst
                }
                $srcCommit = (Invoke-Git @('log', '-1', '--format=%H', '--', "$AuditRel/DECISION_AUDIT_VALIDATION.json")).out.Trim()
                $sha = Get-Sha $dst
                Set-Step $s 'done' @{ preserved = "$RRel/preserved/T05_decision-audit-1.1_DECISION_AUDIT_VALIDATION.json"; sha256 = $sha; original_commit = $srcCommit
                                      original_attempt = 'queue T05, 2026-10-14 22:20:46-22:20:50 UTC, exit code 1 at the console echo after writing status PASS (45/45)' }
                Add-Log ([pscustomobject]@{ event = 'PRESERVED'; step = $s; sha256 = $sha; original_commit = $srcCommit })
                $c = Invoke-Commit (@("$RRel/preserved") + (Get-Records)) 'Recovery R04: preserve the decision-audit-1.1 PASS validation file of failed queue T05'
                if ($null -eq $c) { Set-Step $s 'failed' @{ reason = 'commit of the preserved file failed' }; break }
            }
            'R05_DECISION_VALIDATION_RETRY' {
                $r = Invoke-Step $s @('-m', 'src.jdl_v2_decision_audit', 'validate', '--threads', '1')
                $ok = $false; $why = ''
                $f = @{ attempt_id = $s; exit_code = $r.code; seconds = $r.seconds; started_utc = $r.started_utc; module_sha256 = $r.module_sha256 }
                if ($r.code -ne 0) { $why = "exit code $($r.code)" }
                elseif (-not (Test-Path -LiteralPath $ValFile)) { $why = 'no validation file' }
                else {
                    $v = Read-Json $ValFile
                    $hc = @($v.hard_checks.PSObject.Properties)
                    $passed = @($hc | Where-Object { $_.Value -eq $true }).Count
                    $f['validation_status'] = [string]$v.status; $f['hard_checks'] = $hc.Count; $f['hard_checks_passed'] = $passed
                    $f['validation_sha256'] = Get-Sha $ValFile; $f['validated_module_sha256'] = [string]$v.module_sha256; $f['audit_version'] = [string]$v.audit_version
                    if ([string]$v.status -ne 'PASS') { $why = 'status ' + [string]$v.status }
                    elseif ($hc.Count -ne $ExpectedHardChecks) { $why = "expected $ExpectedHardChecks hard checks, found $($hc.Count)" }
                    elseif ($passed -ne $hc.Count) { $why = "$($hc.Count - $passed) hard checks not true" }
                    elseif ([string]$v.audit_version -ne $Version) { $why = 'audit_version ' + [string]$v.audit_version }
                    elseif ([string]$v.module_sha256 -ne (Get-Sha $Module)) { $why = 'validated module hash differs from the current module' }
                    else { $ok = $true }
                }
                if (-not $ok) { $f['reason'] = $why; Set-Step $s 'failed' $f; Add-Log ([pscustomobject]@{ event = 'GATE_FAILED'; step = $s; reason = $why }); break }
                Set-Step $s 'done' $f
                Add-Log ([pscustomobject]@{ event = 'GATE_PASSED'; step = $s; hard_checks = $f['hard_checks']; validation_sha256 = $f['validation_sha256'] })
                $c = Invoke-Commit (@("$AuditRel/DECISION_AUDIT_VALIDATION.json") + (Get-Records)) 'Recovery R05: decision-rule validation retry with decision-audit-1.1.1 (45/45 hard checks, exit 0)'
                if ($null -eq $c) { Set-Step $s 'failed' @{ reason = 'commit of the validation failed' }; break }
            }
            'R06_DECISION_FREEZE' {
                $r = Invoke-Step $s @('-m', 'src.jdl_v2_decision_audit', 'manifest', '--threads', '1')
                $f = @{ attempt_id = $s; exit_code = $r.code; seconds = $r.seconds; started_utc = $r.started_utc; module_sha256 = $r.module_sha256 }
                $why = ''
                if ($r.code -ne 0) { $why = "exit code $($r.code)" }
                elseif (-not (Test-Path -LiteralPath $ManFile)) { $why = 'no manifest' }
                else {
                    $m = Read-Json $ManFile
                    $f['manifest_sha256'] = Get-Sha $ManFile
                    if ([string]$m.audit_version -ne $Version) { $why = 'manifest audit_version ' + [string]$m.audit_version }
                    elseif ([string]$m.validation.sha256 -ne (Get-Sha $ValFile)) { $why = 'manifest does not name the current validation hash' }
                    elseif ([string]$m.code_sha256.'src/jdl_v2_decision_audit.py' -ne (Get-Sha $Module)) { $why = 'manifest does not name the current module hash' }
                }
                if ($why) { $f['reason'] = $why; Set-Step $s 'failed' $f; Add-Log ([pscustomobject]@{ event = 'GATE_FAILED'; step = $s; reason = $why }); break }
                $c = Invoke-Commit (@("$AuditRel/DECISION_AUDIT_MANIFEST.json") + (Get-Records)) 'Recovery R06: decision-audit manifest frozen against decision-audit-1.1.1 and its new validation, before any audit decision'
                $committed = (Invoke-Git @('log', '--format=%H', '--', "$AuditRel/DECISION_AUDIT_MANIFEST.json")).out.Trim()
                if (($null -eq $c) -or ($committed.Length -eq 0)) { $f['reason'] = 'manifest commit failed'; Set-Step $s 'failed' $f; break }
                $f['manifest_commit'] = $c
                Set-Step $s 'done' $f
            }
            'R07_DECISION_RUN' {
                $r = Invoke-Step $s @('-m', 'src.jdl_v2_decision_audit', 'run', '--threads', '1')
                $n = 0; if (Test-Path -LiteralPath $CacheDir) { $n = @(Get-ChildItem -LiteralPath $CacheDir -Filter 'NEW__*.json.gz').Count }
                $f = @{ attempt_id = $s; exit_code = $r.code; seconds = $r.seconds; started_utc = $r.started_utc; module_sha256 = $r.module_sha256; records = $n }
                if (($r.code -ne 0) -or ($n -ne 60)) { $f['reason'] = "exit code $($r.code), $n of 60 records"; Set-Step $s 'failed' $f; Add-Log ([pscustomobject]@{ event = 'GATE_FAILED'; step = $s; reason = $f['reason'] }); break }
                Set-Step $s 'done' $f
            }
            'R08_DECISION_EVALUATE' {
                $r = Invoke-Step $s @('-m', 'src.jdl_v2_decision_audit', 'evaluate', '--threads', '1')
                $f = @{ attempt_id = $s; exit_code = $r.code; seconds = $r.seconds; started_utc = $r.started_utc; module_sha256 = $r.module_sha256 }
                $sum = Join-Path $AuditDir 'DECISION_AUDIT_SUMMARY.json'; $una = Join-Path $AuditDir 'DECISION_AUDIT_UNAVAILABLE.json'
                if (($r.code -eq 0) -and (Test-Path -LiteralPath $sum)) { $f['outcome'] = [string](Read-Json $sum).audit_status; $f['result_file'] = 'DECISION_AUDIT_SUMMARY.json' }
                elseif (($r.code -eq 3) -and (Test-Path -LiteralPath $una)) { $f['outcome'] = [string](Read-Json $una).audit_status; $f['result_file'] = 'DECISION_AUDIT_UNAVAILABLE.json' }
                else { $f['reason'] = "exit code $($r.code) without its result file"; Set-Step $s 'failed' $f; Add-Log ([pscustomobject]@{ event = 'GATE_FAILED'; step = $s; reason = $f['reason'] }); break }
                Set-Step $s 'done' $f
                Add-Log ([pscustomobject]@{ event = 'AUDIT_OUTCOME'; step = $s; outcome = $f['outcome']; exit_code = $r.code })
                $c = Invoke-Commit (@($AuditRel) + (Get-Records)) ('Recovery R08: cached-posterior decision audit results (' + $f['outcome'] + '; decision-only, zero fits)')
                if ($null -eq $c) { Add-Log ([pscustomobject]@{ event = 'COMMIT_FAILED'; step = $s }) }
            }
        }
        if ($state.steps.$s.status -ne 'done') { break }
    }
    $allDone = @($Steps | Where-Object { $state.steps.$_.status -ne 'done' }).Count -eq 0
    $state | Add-Member -NotePropertyName finished_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    $state | Add-Member -NotePropertyName recovery_complete -NotePropertyValue $allDone -Force
    Write-JsonFile $StateFile $state
    Add-Log ([pscustomobject]@{ event = $(if ($allDone) { 'RECOVERY_COMPLETE' } else { 'RECOVERY_STOPPED' }) })
    $null = Invoke-Commit (Get-Records) ('Recovery T05-T08: sequence ' + $(if ($allDone) { 'complete' } else { 'stopped' }) + ' (records)')
} catch {
    Add-Log ([pscustomobject]@{ event = 'RECOVERY_EXCEPTION'; error = $_.Exception.Message })
    throw
} finally {
    $lock.Dispose()
}
