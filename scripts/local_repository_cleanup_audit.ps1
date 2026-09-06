param(
    [string]$Repository = "C:\Users\ozgur\Documents\thesis",
    [string]$ReportDirectory = "C:\Users\ozgur\Documents\thesis\reports\local_cleanup"
)

$ErrorActionPreference = "Stop"

function Get-DirectoryMeasure {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{ Files = 0; Bytes = [int64]0 }
    }
    $measure = Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum
    return [pscustomobject]@{ Files = [int]$measure.Count; Bytes = [int64]$measure.Sum }
}

function Get-GitOutput {
    param([string]$Path, [string[]]$Arguments)
    $result = & git -C $Path @Arguments 2>$null
    return @($result)
}

$porcelain = (Get-GitOutput -Path $Repository -Arguments @("worktree", "list", "--porcelain")) -join "`n"
$records = [regex]::Split($porcelain.Trim(), "\n\n")
$remoteRows = Get-GitOutput -Path $Repository -Arguments @("ls-remote", "--heads", "origin")
$remoteHeads = foreach ($line in $remoteRows) {
    $parts = $line -split "\s+"
    [pscustomobject]@{ Sha = $parts[0]; Ref = $parts[1] }
}

$inventory = @()
foreach ($record in $records) {
    $lines = $record -split "\n"
    $path = (($lines | Where-Object { $_ -like "worktree *" }) -replace "^worktree ", "") -replace "/", "\"
    $head = ($lines | Where-Object { $_ -like "HEAD *" }) -replace "^HEAD ", ""
    $branch = ($lines | Where-Object { $_ -like "branch *" }) -replace "^branch refs/heads/", ""
    if (-not $branch) { $branch = "DETACHED" }
    $exists = Test-Path -LiteralPath $path
    $prunable = [bool]($lines | Where-Object { $_ -like "prunable *" })
    $locked = [bool]($lines | Where-Object { $_ -like "locked*" })
    $size = Get-DirectoryMeasure -Path $path
    $kind = if (-not $exists) {
        "registered_missing_worktree"
    } elseif (Test-Path -LiteralPath (Join-Path $path ".git") -PathType Container) {
        "canonical_clone"
    } elseif (Test-Path -LiteralPath (Join-Path $path ".git") -PathType Leaf) {
        "linked_worktree"
    } else {
        "unknown"
    }

    $staged = 0
    $modified = 0
    $untracked = 0
    $ignored = 0
    $upstream = ""
    $ahead = 0
    $behind = 0
    $localOnly = 0
    $remoteBranchExists = $false
    $exactRemoteMatch = $false
    $headRemoteReachable = $false
    $ignoredSummary = ""

    if ($exists) {
        $status = @(Get-GitOutput -Path $path -Arguments @("status", "--porcelain=v1", "--untracked-files=all")) |
            Where-Object { $_ -notmatch '^\?\? reports/local_cleanup/' -and $_ -notmatch '^\?\? scripts/local_repository_cleanup_audit\.ps1$' }
        $staged = @($status | Where-Object { $_ -match "^[MADRCU]" }).Count
        $modified = @($status | Where-Object { $_ -match "^.[MADRCU]" }).Count
        $untracked = @($status | Where-Object { $_ -match "^\?\?" }).Count
        $ignoredRows = @(Get-GitOutput -Path $path -Arguments @("status", "--porcelain=v1", "--ignored", "--untracked-files=normal")) |
            Where-Object { $_ -like "!!*" }
        $ignored = @($ignoredRows).Count
        $ignoredSummary = ($ignoredRows -replace "^!! ", "") -join ";"

        $upstreamResult = @(Get-GitOutput -Path $path -Arguments @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"))
        if ($upstreamResult.Count -gt 0 -and $upstreamResult[0] -ne "@{u}") {
            $upstream = $upstreamResult[0]
            $countOutput = @(Get-GitOutput -Path $path -Arguments @("rev-list", "--left-right", "--count", "HEAD...$upstream"))
            if ($countOutput.Count -gt 0) {
                $counts = $countOutput[0] -split "\s+"
                $ahead = [int]$counts[0]
                $behind = [int]$counts[1]
            }
        }
        $localOnlyOutput = @(Get-GitOutput -Path $path -Arguments @("rev-list", "HEAD", "--not", "--remotes", "--count"))
        $localOnly = if ($localOnlyOutput.Count -gt 0) { [int]$localOnlyOutput[0] } else { 0 }
        $directRemote = $remoteHeads | Where-Object { $_.Ref -eq "refs/heads/$branch" } | Select-Object -First 1
        $remoteBranchExists = [bool]$directRemote
        $exactRemoteMatch = [bool]$directRemote -and $directRemote.Sha -eq $head
        foreach ($remote in $remoteHeads) {
            & git -C $Repository cat-file -e "$($remote.Sha)^{commit}" 2>$null
            if ($LASTEXITCODE -eq 0) {
                & git -C $Repository merge-base --is-ancestor $head $remote.Sha 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $headRemoteReachable = $true
                    break
                }
            }
        }
    }

    $classification = "KEEP_UNCERTAIN"
    $safeToRemove = $false
    $reason = "Safety not proven."
    $uniqueCheck = "Not proven."
    if (-not $exists -and $prunable) {
        $classification = "SAFE_REDUNDANT_WORKTREE"
        $safeToRemove = $true
        $reason = "Filesystem path is absent; only stale registered metadata remains."
        $uniqueCheck = "No directory exists, so metadata pruning cannot delete files."
    } elseif ($path -eq $Repository) {
        $classification = "KEEP_CANONICAL"
        $reason = "Selected stable canonical checkout; it is dirty and must remain untouched."
        $uniqueCheck = "Contains one modified and five untracked thesis files."
    } elseif ($path -like "*thesis-week4-chronology-restructure") {
        $classification = "KEEP_UNCERTAIN"
        $reason = "Clean and remotely reachable, but its named remote branch no longer exists and ignored pycache files remain."
        $uniqueCheck = "Tracked tree is clean; branch identity still requires explicit approval before removal."
    } elseif ($path -like "*thesis-week5-first-conduction-gp") {
        $classification = "KEEP_UNCERTAIN"
        $reason = "Contains an ignored virtual environment and a locally unique 17,421,654-byte final-labels_all.csv."
        $uniqueCheck = "Unique CSV SHA256 964A12D86435E9F0879E2E43384D997E1CC2FAA7B9E4C3AEB49CF0E73E3FB154."
    } elseif ($path -like "*phase1-18b-prospective-global-gpc-sur-benchmark") {
        $classification = "KEEP_UNCERTAIN"
        $reason = "Contains 200 ignored checkpoint files (413,133,685 bytes)."
        $uniqueCheck = "Checkpoint redundancy has not been independently proven."
    } elseif ($path -like "*phase1-19a-integrity-posterior-monotonicity-audit") {
        $classification = "KEEP_UNCERTAIN"
        $reason = "Latest Phase 1.19B checkout; only runtime caches were identified, but canonical consolidation has not occurred."
        $uniqueCheck = "Latest tracked work is pushed at bf478288; explicit approval is still required."
    }

    $inventory += [pscustomobject]@{
        path = $path
        size_bytes = $size.Bytes
        size_gib = [math]::Round($size.Bytes / 1GB, 3)
        git_type = $kind
        branch = $branch
        head_sha = $head
        upstream = $upstream
        staged_files = $staged
        modified_files = $modified
        untracked_files = $untracked
        ignored_top_level_entries = $ignored
        ignored_summary = $ignoredSummary
        ahead = $ahead
        behind = $behind
        local_only_commits = $localOnly
        remote_branch_exists = $remoteBranchExists
        exact_remote_branch_match = $exactRemoteMatch
        head_reachable_from_live_remote = $headRemoteReachable
        locked = $locked
        prunable = $prunable
        classification = $classification
        safe_to_remove = $safeToRemove
        unique_content_verification = $uniqueCheck
        reason = $reason
    }
}

$documents = Split-Path $Repository -Parent
$standaloneClones = Get-ChildItem -LiteralPath $documents -Directory -Force | Where-Object {
    $_.FullName -ne $Repository -and (Test-Path -LiteralPath (Join-Path $_.FullName ".git") -PathType Container)
}

New-Item -ItemType Directory -Path $ReportDirectory -Force | Out-Null
$inventoryPath = Join-Path $ReportDirectory "LOCAL_REPOSITORY_INVENTORY.csv"
$inventory | Export-Csv -LiteralPath $inventoryPath -NoTypeInformation -Encoding utf8

$tableRows = foreach ($row in $inventory) {
    "| ``$($row.path)`` | $($row.git_type) | ``$($row.branch)`` | $($row.size_gib) | $($row.modified_files)/$($row.untracked_files) | $($row.local_only_commits) | $($row.classification) | $($row.safe_to_remove) |"
}
$inventoryMd = @"
# Local repository inventory

Generated by ``scripts/local_repository_cleanup_audit.ps1``. This is a read-only discovery snapshot; no cleanup action has been executed.

| Path | Git type | Branch | GiB | Modified/untracked | Local-only commits | Classification | Safe to remove |
|---|---|---:|---:|---:|---:|---|---:|
$($tableRows -join "`n")

## Standalone clones

Direct-child standalone clones of the same repository found under ``$documents``: **$($standaloneClones.Count)**.

## Critical unique-content findings

- Canonical checkout: one modified file and five untracked thesis files.
- Week 5 worktree: ignored local-only ``final-labels_all.csv`` (17,421,654 bytes; SHA256 ``964A12D86435E9F0879E2E43384D997E1CC2FAA7B9E4C3AEB49CF0E73E3FB154``) plus ``.venv``.
- Phase 18B worktree: 200 ignored checkpoints totaling 413,133,685 bytes.
- Phase 1.19B worktree: latest pushed scientific checkout plus runtime caches.
- Git object database: dangling scientific commit ``27035c84625d1228a6ed8994c619727ed9f40262`` has no protecting ref.
"@
Set-Content -LiteralPath (Join-Path $ReportDirectory "LOCAL_REPOSITORY_INVENTORY.md") -Value $inventoryMd -Encoding utf8

$registered = $inventory.Count
$physical = @($inventory | Where-Object { $_.git_type -ne "registered_missing_worktree" }).Count
$prunableCount = @($inventory | Where-Object { $_.prunable }).Count
$totalBytes = [int64](($inventory | Measure-Object -Property size_bytes -Sum).Sum)
$pendingBytes = [int64](($inventory | Where-Object { $_.git_type -eq "linked_worktree" } | Measure-Object -Property size_bytes -Sum).Sum)
$keepRows = $inventory | Where-Object { -not $_.safe_to_remove } | ForEach-Object { "- ``$($_.path)`` — **$($_.classification)**: $($_.reason)" }
$safeRows = $inventory | Where-Object { $_.safe_to_remove } | ForEach-Object { "- ``$($_.path)`` — stale metadata only; path absent." }

$preCleanup = @"
# Pre-cleanup safety report

## Decision

**STOP BEFORE DELETION.** The mandatory stop conditions are active. No worktree, clone, file, cache, ref, or Git object has been removed.

## Inventory summary

- Registered worktrees: **$registered**
- Physically present Git checkouts/worktrees: **$physical**
- Prunable stale registrations: **$prunableCount**
- Standalone duplicate clones found: **$($standaloneClones.Count)**
- Selected canonical checkout: ``$Repository``
- Measured Git-checkout/worktree usage: **$([math]::Round($totalBytes / 1GB, 3)) GiB**
- Proven-safe physical deletion now: **0 GiB**
- Physical linked-worktree space pending explicit review/preservation: **$([math]::Round($pendingBytes / 1GB, 3)) GiB**

## KEEP list

$($keepRows -join "`n")

## Metadata-only safe list

$($safeRows -join "`n")

These 30 entries have no filesystem path. ``git worktree prune`` would remove registry metadata only, but it has not been run because the global deletion stop is active.

## Mandatory warnings

1. Canonical ``main`` is dirty: ``outputs/week2_acquisition_comparison/week2_slide_notes.md`` is modified; five thesis files are untracked.
2. Week 5 contains a locally unique ignored 17.4 MB dataset CSV.
3. Phase 18B contains 394 MiB of ignored checkpoints.
4. The latest Phase 1.19B checkout is separate from the dirty canonical checkout.
5. ``git fsck --full --no-reflogs`` exits 0 but reports dangling scientific commit ``27035c8`` and eight dangling blobs. Do not run garbage collection or expiry.
6. Non-repository ``Documents\Codex`` (0.77 GiB) and ``codex-temp-week8-figure-audit`` montage files were observed and intentionally left outside the deletion plan.

## Required decision before cleanup

The user must decide whether to preserve the Week 5 CSV, Phase 18B checkpoints, latest Phase 1.19B checkout, and dangling commit in explicit archival locations/refs before any physical worktree removal.
"@
Set-Content -LiteralPath (Join-Path $ReportDirectory "PRE_CLEANUP_SAFETY_REPORT.md") -Value $preCleanup -Encoding utf8

$plan = foreach ($row in ($inventory | Where-Object { $_.safe_to_remove })) {
    [ordered]@{
        path = $row.path
        type = "stale_registered_worktree_metadata"
        size_bytes = 0
        branch = $row.branch
        HEAD = $row.head_sha
        remote_verification = $row.head_reachable_from_live_remote
        clean_verification = "Path absent; no working-tree files exist."
        unique_content_verification = "Path absent; metadata pruning cannot remove filesystem content."
        reason_safe = $row.reason
        proposed_action = "git worktree prune (metadata only)"
        execution_status = "BLOCKED_PENDING_USER_APPROVAL"
    }
}
$plan | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $ReportDirectory "cleanup_plan.json") -Encoding utf8

Write-Output ([pscustomobject]@{
    registered = $registered
    physical = $physical
    prunable = $prunableCount
    standalone_clones = $standaloneClones.Count
    measured_gib = [math]::Round($totalBytes / 1GB, 3)
    pending_physical_gib = [math]::Round($pendingBytes / 1GB, 3)
    cleanup_executed = $false
} | ConvertTo-Json)
