<#
Finalize the local thesis workspace (written 2026-11-02 during the finalization; see docs/final/REPOSITORY_MAP.md).

What it does (nothing is ever deleted; every step is checked first and logged):
  1. The Research Hub worktree that still holds the branch 'main' (Documents\thesis-research-hub-main-2026-10-28)
     is switched to a detached HEAD at the same commit. Its files do not change. This frees 'main'.
  2. The canonical folder Documents\thesis is fetched, switched from 'week20-active-temporal-dev' to 'main' and
     fast-forwarded to origin/main (the finalized state). Untracked and ignored files (data\raw, caches, the advisor
     deck, meeting pages, agent settings) stay where they are.
  3. Only with -Archive: the Research Hub worktrees, the Sept. consolidation snapshot and the staging copies that no
     code depends on are MOVED into Documents\thesis_archive\ (worktrees with 'git worktree move', so git stays
     consistent; plain folders with Move-Item). A README with the old -> new map is written there. Folders that code
     or provenance reads by absolute path are never moved (listed below).

Usage (PowerShell, from the canonical folder):
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\finalize_local_workspace_20261102.ps1 -DryRun
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\finalize_local_workspace_20261102.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\finalize_local_workspace_20261102.ps1 -Archive
#>
param([switch]$Archive, [switch]$DryRun)
$ErrorActionPreference = 'Stop'
$Docs    = Join-Path $env:USERPROFILE 'Documents'
$Canon   = Join-Path $Docs 'thesis'
$HubMain = Join-Path $Docs 'thesis-research-hub-main-2026-10-28'
$Arch    = Join-Path $Docs 'thesis_archive'
$Log     = Join-Path $Arch 'FINALIZE_LOCAL_LOG.txt'
New-Item -ItemType Directory -Force -Path $Arch | Out-Null

function Say([string]$m) {
  $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m
  Write-Host $line
  Add-Content -LiteralPath $Log -Value $line -Encoding utf8
}
function Invoke-Git([string]$Dir, [string[]]$GitArgs) {
  # git writes progress and "Switched to ..." to stderr; in Windows PowerShell 5.1 that must not become an error.
  $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try { $out = & git -C $Dir @GitArgs 2>&1 | ForEach-Object { "$_" } } finally { $ErrorActionPreference = $prev }
  if ($LASTEXITCODE -ne 0) { throw ("git -C {0} {1} failed (exit {2}):`n{3}" -f $Dir, ($GitArgs -join ' '), $LASTEXITCODE, ($out -join "`n")) }
  return (($out | Where-Object { $_ -ne $null }) -join "`n").Trim()
}
function Act([string]$What, [scriptblock]$Do) { if ($DryRun) { Say "DRY-RUN would: $What" } else { Say $What; & $Do } }

Say "=== finalize_local_workspace start (Archive=$Archive DryRun=$DryRun)"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'git not found' }
if (-not (Test-Path (Join-Path $Canon '.git'))) { throw "canonical repository not found: $Canon" }

# --- 0. checks ----------------------------------------------------------------------------------------------------
$dirty = Invoke-Git $Canon @('status', '--porcelain', '--untracked-files=no')
if ($dirty) { throw "the canonical folder has modified tracked files; nothing was changed:`n$dirty" }
Act 'fetch origin in the canonical folder' { Invoke-Git $Canon @('fetch', 'origin', '--prune') | Out-Null }
$originMain = Invoke-Git $Canon @('rev-parse', 'origin/main')
Say "origin/main = $originMain"

# --- 1. free 'main' from the Hub worktree -------------------------------------------------------------------------
if (Test-Path $HubMain) {
  $br = Invoke-Git $HubMain @('branch', '--show-current')
  if ($br -eq 'main') {
    $hubDirty = Invoke-Git $HubMain @('status', '--porcelain')
    if ($hubDirty) { throw "the Hub worktree holding main has local changes; nothing was changed:`n$hubDirty" }
    Act "detach HEAD in $HubMain (same commit; files unchanged)" { Invoke-Git $HubMain @('switch', '--detach') | Out-Null }
  } else { Say "Hub worktree is on '$br', not main: nothing to do" }
}

# --- 2. canonical folder -> main ----------------------------------------------------------------------------------
$cur = Invoke-Git $Canon @('branch', '--show-current')
Say "canonical folder branch before: $cur"
if ($cur -ne 'main') { Act 'switch the canonical folder to main' { Invoke-Git $Canon @('switch', 'main') | Out-Null } }
Act 'fast-forward main to origin/main' { Invoke-Git $Canon @('merge', '--ff-only', 'origin/main') | Out-Null }
if (-not $DryRun) {
  $head = Invoke-Git $Canon @('rev-parse', 'HEAD')
  if ($head -ne $originMain) { throw "canonical HEAD $head is not origin/main $originMain" }
  Say "canonical folder is on main at $head"
}

# --- 3. optional archive of folders nothing depends on ------------------------------------------------------------
if ($Archive) {
  # Stay in place on purpose: thesis-week4-*, thesis-week5-*, thesis-week9-phase1-18b-*, thesis-week9-phase1-19a-*
  # (src/week9_phase1_21_repeat_audit_driver.py and the Phase 1.10 scripts read them by absolute path);
  # thesis_external_quarantine (src/week11_external_oracle_deriver.py); thesis_shared_runtime (campaign coordination);
  # thesis-preservation-staging (offline Astra archive of the Research Hub); thesis-research-outputs
  # (outputs/astra_round3/PROVENANCE.json); hf-sph-v2-old-data-monitor-restoration (Phase 1.22 audit); Documents\Codex.
  $worktrees = @('thesis-complete-consolidation', 'thesis-research-hub-main-2026-10-28', 'thesis-research-hub-publish', 'thesis-research-hub-review')
  $plain = @('thesis-curated-evidence-staging-2026-10-28', 'thesis-graphify-audit', 'thesis-graphify-sync-2026-10-29',
             'thesis-research-hub-public-draft', 'thesis-research-hub-staging', 'codex-temp-week8-figure-audit')
  $wtDst = Join-Path $Arch 'old_worktrees'; $stDst = Join-Path $Arch 'staging_and_copies'
  if (-not $DryRun) { New-Item -ItemType Directory -Force -Path $wtDst, $stDst | Out-Null }
  $map = @()
  foreach ($n in $worktrees) {
    $src = Join-Path $Docs $n; $dst = Join-Path $wtDst $n
    if (-not (Test-Path $src)) { Say "skip (absent): $n"; continue }
    if (Test-Path $dst) { Say "skip (target exists): $n"; continue }
    Act "git worktree move $src -> $dst" { Invoke-Git $Canon @('worktree', 'move', $src, $dst) | Out-Null }
    $map += "| $src | $dst | git worktree (moved with git worktree move) |"
  }
  foreach ($n in $plain) {
    $src = Join-Path $Docs $n; $dst = Join-Path $stDst $n
    if (-not (Test-Path $src)) { Say "skip (absent): $n"; continue }
    if (Test-Path $dst) { Say "skip (target exists): $n"; continue }
    Act "move $src -> $dst" { Move-Item -LiteralPath $src -Destination $dst }
    $map += "| $src | $dst | plain folder |"
  }
  if (-not $DryRun -and $map.Count -gt 0) {
    $readme = Join-Path $Arch 'README_ARCHIVE_MOVES.md'
    $hdr = @('# Folders moved into thesis_archive on ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'), '',
             'Nothing was deleted. Old absolute paths in dated records resolve through this map.', '',
             '| old path | new path | kind |', '|---|---|---|')
    Add-Content -LiteralPath $readme -Value ($hdr + $map) -Encoding utf8
    (Invoke-Git $Canon @('worktree', 'list')) -split "`n" | ForEach-Object { Say "worktree: $_" }
  }
}
Say '=== finalize_local_workspace done'
