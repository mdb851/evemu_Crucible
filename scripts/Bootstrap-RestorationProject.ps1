#requires -Version 5.1
<#
.SYNOPSIS
  Links your GitHub Project (v2), adds custom fields, creates restoration issues, and adds them to the project.

.DESCRIPTION
  Run once after:
    gh auth login
    gh auth refresh -s project

  Find ProjectNumber in the project URL:
    https://github.com/users/mdb851/projects/<NUMBER>

.PARAMETER ProjectNumber
  The numeric project ID from the URL above.

.PARAMETER Owner
  GitHub login owning the project (default: mdb851).

.PARAMETER Repo
  Repository name without owner (default: evemu_Crucible).
#>
param(
    [Parameter(Mandatory = $true)]
    [int] $ProjectNumber,

    [string] $Owner = "mdb851",

    [string] $Repo = "evemu_Crucible"
)

$ErrorActionPreference = "Stop"
$gh = Join-Path ${env:ProgramFiles} "GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    Write-Error "GitHub CLI not found at $gh. Install with: winget install GitHub.cli"
}

& $gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error @"
Not authenticated. Run:
  & `"$gh`" auth login
  & `"$gh`" auth refresh -s project
"@
}

$repoFull = "${Owner}/${Repo}"

Write-Host "Linking project $ProjectNumber to repository $repoFull ..."
& $gh project link $ProjectNumber --owner $Owner -R $repoFull

Write-Host "Creating custom fields (ignore errors if they already exist) ..."
$fieldDefs = @(
    @{ Name = "Priority"; Options = "High,Medium,Low" },
    @{ Name = "Slice"; Options = "PvP,Mining,Contracts,Industry,Scanning,CorpMarket,Other" },
    @{ Name = "Live status"; Options = "Unchecked,InProgress,Blocked,LivePASS" }
)
foreach ($fd in $fieldDefs) {
    & $gh project field-create $ProjectNumber --owner $Owner --name $fd.Name --data-type SINGLE_SELECT --single-select-options $fd.Options 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  (skip or duplicate field): $($fd.Name)"
    }
}

Write-Host "Ensuring label 'restoration' exists ..."
& $gh label create "restoration" --repo $repoFull --description "Crucible restoration / verification slice" --color "0E8A16" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  (label may already exist)"
}

function IssueBody {
    param(
        [string] $Slice,
        [string] $Priority,
        [string] $Goal,
        [string] $ShortSha = "unknown"
    )
    @"
## Slice
$Slice

## Priority (project field)
**$Priority** — also set the **Priority** column on the project board.

## Goal
$Goal

## Steps (minimal repro)
1. 
2. 

## Expected
(Client + server / DB — be specific.)

## Actual / evidence
(Paste or link.)

## Server branch / commit
``master`` @ ``$ShortSha``

## Related
- ``EVEMU_RESTORATION_STATE.md`` — verification matrix
"@
}

$issueSpecs = @(
    @{
        Title    = "[Restore] PvP — aggression → kill → cleanup"
        Slice    = "PvP aggression → damage → kill → cleanup"
        Priority = "High"
        Goal     = "PvP combat resolves damage, death, and cleanup correctly end-to-end."
    },
    @{
        Title    = "[Restore] Mining — cycle → ore hold → persistence"
        Slice    = "Mining cycle → ore to hold / persistence"
        Priority = "High"
        Goal     = "Mining cycle deposits ore into the appropriate hold and survives relog / DB state."
    },
    @{
        Title    = "[Restore] Contracts — create → accept → complete → ISK/items"
        Slice    = "Contracts create → accept → complete → ISK/items"
        Priority = "High"
        Goal     = "Item exchange and courier flows complete with correct wallets and item ownership."
    },
    @{
        Title    = "[Restore] Industry — manufacturing jobs"
        Slice    = "Industry / manufacturing jobs"
        Priority = "Medium"
        Goal     = "Manufacturing jobs install, run, and deliver outputs consistently."
    },
    @{
        Title    = "[Restore] Exploration — scanning"
        Slice    = "Exploration / scanning"
        Priority = "Medium"
        Goal     = "Scanning interactions match Crucible-era expectations without server exceptions."
    },
    @{
        Title    = "[Restore] Corporation market"
        Slice    = "Corporation market (personal sell-side already PASS)"
        Priority = "Medium"
        Goal     = "Corp-facing market flows behave correctly beyond personal sell-side."
    }
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$gitCmd = if (Get-Command git -ErrorAction SilentlyContinue) { "git" } else { "C:\Program Files\Git\cmd\git.exe" }
$shortSha = if (Test-Path (Join-Path $repoRoot ".git")) {
    & $gitCmd -C $repoRoot rev-parse --short HEAD 2>$null
} else {
    "unknown"
}

foreach ($spec in $issueSpecs) {
    $body = IssueBody -Slice $spec.Slice -Priority $spec.Priority -Goal $spec.Goal -ShortSha $shortSha
    Write-Host "Creating issue: $($spec.Title)"
    $url = & $gh issue create --repo $repoFull --title $spec.Title --body $body --label "restoration" --json url --jq .url
    if (-not $url) { Write-Error "issue create failed for $($spec.Title)" }
    Write-Host "  -> $url"
    & $gh project item-add $ProjectNumber --owner $Owner --url $url
}

Write-Host @"

Done.

Next in the GitHub UI:
1. Open the project → set **Slice** and **Live status** on each row (defaults: Slice matches title; Live status = Unchecked).
2. Optional: add a **Board** view grouped by **Live status**.

"@
