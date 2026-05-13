#Requires -Version 5.1
<#
.SYNOPSIS
  Restore start.ini after Launch_EVEmu_Isolated.ps1 (return client to pre-isolated state).
#>
param(
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'

$LauncherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StatePath = Join-Path $LauncherRoot 'backup\isolated_launcher_state.json'
$BackupDir = Join-Path $LauncherRoot 'backup'
$BackupOriginal = Join-Path $BackupDir 'start.ini.original'

if (-not (Test-Path -LiteralPath $StatePath)) {
    if ($ValidateOnly) {
        Write-Host "ValidateOnly: No active launcher state at '$StatePath'. Nothing to restore."
        exit 0
    }
    Write-Host "No isolated launcher state found (nothing to restore). If start.ini is still wrong, restore manually from your own backup."
    exit 0
}

$state = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
$clientRoot = $state.ClientRoot
$startIni = Join-Path $clientRoot 'start.ini'

if ($ValidateOnly) {
    Write-Host "ValidateOnly: Would restore client at:"
    Write-Host "  $clientRoot"
    Write-Host "  HadOriginalIni=$($state.HadOriginalIni)  BackupFile=$($state.BackupFile)"
    exit 0
}

if (-not $clientRoot -or -not (Test-Path -LiteralPath $clientRoot)) {
    throw "State file references missing ClientRoot '$clientRoot'. Restore backup\start.ini.original manually into your client bin folder."
}

if ($state.HadOriginalIni -eq $true) {
    if (-not (Test-Path -LiteralPath $BackupOriginal)) {
        Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
        throw "Backup '$BackupOriginal' is missing; cannot restore start.ini automatically. State file cleared. Fix start.ini manually in:`n  $startIni"
    }
    Copy-Item -LiteralPath $BackupOriginal -Destination $startIni -Force
    Write-Host "Restored original start.ini from backup."
} else {
    if (Test-Path -LiteralPath $startIni) {
        Remove-Item -LiteralPath $startIni -Force
        Write-Host "Removed launcher-created start.ini (no original existed)."
    }
}

Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $BackupOriginal) {
    Remove-Item -LiteralPath $BackupOriginal -Force -ErrorAction SilentlyContinue
}

Write-Host "Restore complete. You can use your normal client launcher again."
