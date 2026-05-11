#Requires -Version 5.1
<#
.SYNOPSIS
    Tier A smoke: build (optional), compose up, DB ready, server log ready, ctrContracts schema columns.

.DESCRIPTION
    Run from repository root is recommended:
        pwsh .\scripts\smoke\docker-smoke.ps1

    Optional -PostClientAssertions runs Tier B SQL files for human inspection (exit code unchanged).

    Wait budget: each of MariaDB and server-log polling gets up to -MaxWaitSeconds (default 180).
    If the environment variable MAX_WAIT is set to a positive integer, it overrides -MaxWaitSeconds (same as docker-smoke.sh).
#>
[CmdletBinding()]
param(
    [switch] $SkipBuild,
    [switch] $SkipUp,
    [ValidateSet('none', 'contracts', 'paper', 'all')]
    [string] $PostClientAssertions = 'none',
    [int] $MaxWaitSeconds = 180
)

$ErrorActionPreference = 'Stop'

# Match docker-smoke.sh: optional MAX_WAIT env overrides -MaxWaitSeconds (e.g. CI sets MAX_WAIT=300).
if ($env:MAX_WAIT -match '^\d+$') {
    $MaxWaitSeconds = [int]$env:MAX_WAIT
}

function Get-RepoRoot {
    $here = $PSScriptRoot
    if (-not $here) { $here = Split-Path -Parent $MyInvocation.MyCommand.Path }
    return (Resolve-Path (Join-Path $here '..\..')).Path
}

function Invoke-DbSql {
    param([string] $Sql)
    $out = @($Sql | docker compose exec -T db mariadb -ueva -pevemu evemu 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "MariaDB command failed (exit $LASTEXITCODE): $($out -join "`n")"
    }
    return ($out -join "`n")
}

$RepoRoot = Get-RepoRoot
Push-Location $RepoRoot
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker not found on PATH."
    }

    if (-not $SkipBuild) {
        Write-Host '==> docker compose build server'
        docker compose build server
        if ($LASTEXITCODE -ne 0) { throw "docker compose build failed (exit $LASTEXITCODE)." }
    }

    if (-not $SkipUp) {
        Write-Host '==> docker compose up -d'
        docker compose up -d
        if ($LASTEXITCODE -ne 0) { throw "docker compose up failed (exit $LASTEXITCODE)." }
    }

    $dbDeadline = (Get-Date).AddSeconds($MaxWaitSeconds)

    Write-Host '==> Waiting for MariaDB (evemu database)...'
    $dbOk = $false
    while ((Get-Date) -lt $dbDeadline) {
        try {
            Invoke-DbSql 'SELECT 1 AS ok;' | Out-Null
            $dbOk = $true
            break
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    if (-not $dbOk) { throw "MariaDB not ready within $MaxWaitSeconds s." }
    Write-Host '    MariaDB OK.'

    # Fresh budget for server boot log (same semantics as docker-smoke.sh).
    $srvDeadline = (Get-Date).AddSeconds($MaxWaitSeconds)

    Write-Host '==> Waiting for game server log (TCP Server started on port)...'
    $srvOk = $false
    while ((Get-Date) -lt $srvDeadline) {
        $log = docker logs server --tail 500 2>&1 | Out-String
        if ($log -match 'TCP Server started on port') {
            $srvOk = $true
            break
        }
        Start-Sleep -Seconds 3
    }
    if (-not $srvOk) { throw "Server log did not show 'TCP Server started on port' within $MaxWaitSeconds s." }
    Write-Host '    Server log OK.'

    Write-Host '==> Schema: ctrContracts corp-routing columns...'
    $schemaSql = @"
SELECT IF(
  (SELECT COUNT(*) FROM information_schema.columns
   WHERE table_schema = DATABASE() AND table_name = 'ctrContracts'
     AND column_name IN ('acceptorCorpID', 'issuerWalletKey', 'acceptorWalletKey')) = 3,
  'OK', 'FAIL') AS ctrcontracts_smoke;
"@
    $schemaOut = Invoke-DbSql $schemaSql
    Write-Host $schemaOut
    if ($schemaOut -notmatch '(?m)OK') {
        throw "ctrContracts schema check failed (expected OK). Output: $schemaOut"
    }
    Write-Host '    Schema OK.'

    Write-Host '==> Optional: port 26000 reachability (localhost)...'
    try {
        $tcp = Test-NetConnection -ComputerName localhost -Port 26000 -WarningAction SilentlyContinue
        if ($tcp.TcpTestSucceeded) {
            Write-Host '    Port 26000 open.'
        } else {
            Write-Host '    Port 26000 not reachable (non-fatal; some Docker setups differ).'
        }
    } catch {
        Write-Host '    Port check skipped or inconclusive (non-fatal).'
    }

    if ($PostClientAssertions -ne 'none') {
        Write-Host '==> Post-client SQL (Tier B — inspect output manually; does not affect exit code)...'
        $sqlDir = [System.IO.Path]::Combine($RepoRoot, 'scripts', 'smoke', 'sql')
        $run = @()
        if ($PostClientAssertions -eq 'contracts' -or $PostClientAssertions -eq 'all') {
            $run += Join-Path $sqlDir 'contracts_courier_assertions.sql'
        }
        if ($PostClientAssertions -eq 'paper' -or $PostClientAssertions -eq 'all') {
            $run += Join-Path $sqlDir 'paper_doll_assertions.sql'
        }
        foreach ($f in $run) {
            Write-Host "---- $f"
            try {
                Get-Content -LiteralPath $f -Raw | docker compose exec -T db mariadb -ueva -pevemu evemu
            } catch {
                Write-Warning "SQL file failed: $f — $($_.Exception.Message)"
            }
        }
    }

    Write-Host '==> Tier A smoke PASSED.'
    exit 0
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Pop-Location
}
