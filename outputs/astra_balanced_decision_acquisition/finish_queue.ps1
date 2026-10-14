$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskPython = 'C:\Users\ozgur\Documents\thesis\.venv\Scripts\python.exe'
$taskChecks = Join-Path $taskRoot 'INDEPENDENT_CHECKS.json'
$taskState = Join-Path $taskRoot 'PIPELINE_STATE.json'
Set-Location -LiteralPath $taskRoot
function Write-TaskState([string]$state, [string]$detail) {
    $taskValue = [pscustomobject]@{ utc = [DateTime]::UtcNow.ToString('o'); state = $state; detail = $detail; wrapper_pid = $PID }
    $taskTemp = $taskState + '.tmp'
    $taskValue | ConvertTo-Json | Set-Content -LiteralPath $taskTemp -Encoding utf8
    [System.IO.File]::Move($taskTemp, $taskState, $true)
}
# This handle protects only this package against accidental duplicate launch.
# It does not reserve a host thread or touch any other user's/job's lock.
try {
    $taskLock = [System.IO.File]::Open((Join-Path $taskRoot 'pipeline.lock'), [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
    Write-Output 'Another copy of this local pipeline already holds its own handle; exiting.'
    exit 2
}
try {
    Write-TaskState 'REFERENCE_CHECKS_OR_HOST_QUEUE' 'One check worker; it waits while all four shared numerical slots are occupied.'
    & $taskPython -u 'run_controlled.py' checks *>> (Join-Path $taskRoot 'checks_stdout.log')
    if ($LASTEXITCODE -ne 0) {
        Write-TaskState 'STOPPED_REFERENCE_EXCEPTION' 'Reference process returned nonzero. Preserve its section records, charges and log; no automatic retry.'
        exit $LASTEXITCODE
    }
    $taskCheckObject = Get-Content -LiteralPath $taskChecks -Raw | ConvertFrom-Json
    if (-not $taskCheckObject.acceptance_pass) {
        Write-TaskState 'STOPPED_REFERENCE_GATE' 'Independent checks did not pass; no controlled fits launched.'
        exit 1
    }
    Write-TaskState 'CONTROLLED_RUN' 'References passed. One worker; source hashes and shared-host slots checked by runner.'
    & $taskPython -u 'run_controlled.py' run *>> (Join-Path $taskRoot 'controlled_stdout.log')
    if ($LASTEXITCODE -ne 0) {
        Write-TaskState 'STOPPED_RUN' 'Runner returned nonzero. Preserve all artifacts; review before resumption.'
        exit $LASTEXITCODE
    }
    & $taskPython -u 'summarize_results.py' *>> (Join-Path $taskRoot 'summary_stdout.log')
    if ($LASTEXITCODE -ne 0) {
        Write-TaskState 'STOPPED_SUMMARY' 'Comparisons preserved; postprocessing needs review.'
        exit $LASTEXITCODE
    }
    Write-TaskState 'COMPUTATION_FINISHED_REVIEW_REQUIRED' 'Results and report tables saved. Final scientific and artifact review still required.'
} catch {
    Write-TaskState 'STOPPED_WRAPPER_EXCEPTION' $_.Exception.Message
    $_ | Out-String | Add-Content -LiteralPath (Join-Path $taskRoot 'pipeline_errors.log') -Encoding utf8
    exit 1
} finally {
    $taskLock.Dispose()
}
