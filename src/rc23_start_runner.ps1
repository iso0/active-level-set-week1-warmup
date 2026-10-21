# RC22 copy of the RC21 script (runner directory opus_rc22/runner).
# RC21 copy of the RC20 script (runner directory opus_rc21/runner; RC20 window not restarted).
# Detached launch of the rc20 runner supervisor (RC20 continuation, own 24-hour clock in runner/PLAN.json).
# Created through WMI (Win32_Process.Create), so the supervisor is not a child of the Claude/terminal process tree and keeps
# running when the chat or the desktop app closes. It does NOT survive a reboot or log-off: after one, run this script again.
# Idempotent: a second runner exits at once (runner.lock held, exit 2) and its supervisor then ends; nothing is duplicated.
#   powershell -NoProfile -ExecutionPolicy Bypass -File src\rc23_start_runner.ps1
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Sup = Join-Path $Root 'src\rc23_supervisor.ps1'
$RDir = Join-Path $Root 'outputs\research_campaign_20261021\opus_rc23\runner'
New-Item -ItemType Directory -Force -Path $RDir | Out-Null
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $Sup
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $Root }
if ($r.ReturnValue -ne 0) { Write-Output ('WMI create failed: {0}' -f $r.ReturnValue); exit 1 }
Write-Output ('supervisor launched detached, pid {0}' -f $r.ProcessId)
