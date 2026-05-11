#Requires -Version 5.1
<#
.SYNOPSIS
    Run Tier B SQL evidence against the compose MariaDB (after a manual client session).

.DESCRIPTION
    Assumes `docker compose` is usable from the repository root and services `db` / `evemu` DB match docker-compose.yml.
    Does not start Docker; use scripts/smoke/docker-smoke.ps1 first if needed.
#>
[CmdletBinding()]
param(
    [ValidateSet('contracts', 'paper', 'corpmarket', 'all')]
    [string] $Target = 'all'
)

$ErrorActionPreference = 'Stop'

function Get-RepoRoot {
    $here = $PSScriptRoot
    if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $here '..\..')).Path
}

$RepoRoot = Get-RepoRoot
$sqlDir = [System.IO.Path]::Combine($RepoRoot, 'scripts', 'smoke', 'sql')
Push-Location $RepoRoot
try {
    $files = @()
    if ($Target -eq 'contracts' -or $Target -eq 'all') {
        $files += [System.IO.Path]::Combine($sqlDir, 'contracts_courier_assertions.sql')
    }
    if ($Target -eq 'paper' -or $Target -eq 'all') {
        $files += [System.IO.Path]::Combine($sqlDir, 'paper_doll_assertions.sql')
    }
    if ($Target -eq 'corpmarket' -or $Target -eq 'all') {
        $files += [System.IO.Path]::Combine($sqlDir, 'corp_market_assertions.sql')
    }

    foreach ($f in $files) {
        if (-not (Test-Path -LiteralPath $f)) {
            Write-Warning "Missing SQL file: $f"
            continue
        }
        Write-Host "==== $f"
        Get-Content -LiteralPath $f -Raw | docker compose exec -T db mariadb -u evemu -pevemu evemu
        if ($LASTEXITCODE -ne 0) {
            throw "mariadb failed on $f (exit $LASTEXITCODE)"
        }
    }
    Write-Host '==== Post-client evidence SQL finished.'
}
finally {
    Pop-Location
}
