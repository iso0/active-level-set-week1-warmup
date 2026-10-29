# C1S (C1 stability) copy of src/c1c_start_runner.ps1 (owner instruction 2026-10-29): runner directory opus_c1_stability/runner, coordination only through
# C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (campaign id opus_c1_stability_20261029; Astra's files read only);
# one 48-hour window from t0 in PLAN.json (2026-10-29T00:10:41Z).
# C1C (C1 confirmation) copy of src/ea_start_runner.ps1 (owner instruction 2026-10-26, second task): runner directory opus_c1_confirmation/runner,
# coordination only through C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (campaign id opus_c1_stability_20261029;
# Astra's files read only); one 48-hour window from t0 in PLAN.json (2026-10-26T18:05:16Z).
# EA study copy of src/el_start_runner.ps1 (owner instruction 2026-10-26): runner directory opus_error_attribution/runner, coordination only through
# C:\Users\ozgur\Documents\thesis_shared_runtime\campaign_20261029\opus_state.json (Astra's files read only); one 48-hour window from t0 in PLAN.json.
# EL study copy of src/rc24_start_runner.ps1 (runner directory opus_early_learning/runner; one 48-hour window, never restarted).
# Detached launch of the EL runner supervisor through WMI (Win32_Process.Create): it is not a child of the Claude/terminal process
# tree and keeps running when the chat or the desktop app closes. It does NOT survive a reboot or log-off: after one, run again.
# Idempotent: a second runner exits at once (runner.lock held, exit 2) and its supervisor then ends; nothing is duplicated.
#   powershell -NoProfile -ExecutionPolicy Bypass -File src\c1s_start_runner.ps1
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Sup = Join-Path $Root 'src\c1s_supervisor.ps1'
$RDir = Join-Path $Root 'outputs\research_campaign_20261029\opus_c1_stability\runner'
New-Item -ItemType Directory -Force -Path $RDir | Out-Null
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $Sup
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $Root }
if ($r.ReturnValue -ne 0) { Write-Output ('WMI create failed: {0}' -f $r.ReturnValue); exit 1 }
Write-Output ('supervisor launched detached, pid {0}' -f $r.ProcessId)
