# Supervisor for src\rc19_runner.ps1 (RC19 pooled; research campaign 20261018 budget). Launched detached by src\rc19_start_runner.ps1.
# Restarts the runner after an unexpected exception (exit code 1), at most 6 times per rolling 6 hours, 60 s apart.
# Stops when the runner ends normally (exit 0: deadline reached or stop_runner) or another runner holds the lock (exit 2).
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Runner = Join-Path $Root 'src\rc19_runner.ps1'
$RDir = Join-Path $Root 'outputs\research_campaign_20261018\opus_pooled\runner'
$Log = Join-Path $RDir 'supervisor_log.jsonl'
$Utf8 = New-Object System.Text.UTF8Encoding $false
function Add-Log($o) { $o['utc'] = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'); [System.IO.File]::AppendAllText($Log, (($o | ConvertTo-Json -Compress) + "`n"), $Utf8) }
$starts = New-Object System.Collections.ArrayList
Add-Log @{ event = 'SUPERVISOR_START'; pid = $PID }
while ($true) {
    $now = [DateTime]::UtcNow
    while ($starts.Count -gt 0 -and ($now - $starts[0]).TotalHours -gt 6) { $starts.RemoveAt(0) }
    if ($starts.Count -ge 6) { Add-Log @{ event = 'SUPERVISOR_GIVE_UP'; reason = '6 runner starts within 6 h' }; break }
    [void]$starts.Add($now)
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Runner) -WorkingDirectory $Root `
        -RedirectStandardOutput (Join-Path $RDir 'runner_stdout.txt') -RedirectStandardError (Join-Path $RDir 'runner_stderr.txt') -NoNewWindow -PassThru
    $null = $p.Handle
    Add-Log @{ event = 'RUNNER_LAUNCH'; runner_pid = $p.Id }
    $p.WaitForExit()
    $code = $p.ExitCode
    Add-Log @{ event = 'RUNNER_EXIT'; runner_pid = $p.Id; exit_code = $code }
    if ($code -eq 0 -or $code -eq 2) { break }
    Start-Sleep -Seconds 60
}
Add-Log @{ event = 'SUPERVISOR_END' }
