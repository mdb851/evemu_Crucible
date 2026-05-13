#Requires -Version 5.1
<#
.SYNOPSIS
  Temporarily point a patched Crucible EVE client at the isolated EVEmu stack (localhost:26100 / 26101).

.NOTES
  - Backs up the client's start.ini once per "session" (see backup\isolated_launcher_state.json).
  - Does not touch hosts, Tranquility prefs, or Docker. Legacy stack unchanged.
  - Re-run launch while a session is active: starts ExeFile again (use -ForceRefreshIni to rewrite start.ini from template).
  - Run Restore_EVEmu_Isolated_Client.ps1 (or Restore_Normal_Client.bat) when finished testing.
  - blue_patcher requires common.ini cryptoPack=Placebo; see README if ExeFile exits immediately.
#>
param(
    [switch]$ValidateOnly,
    [switch]$ForceRefreshIni
)

$ErrorActionPreference = 'Stop'

$LauncherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StatePath = Join-Path $LauncherRoot 'backup\isolated_launcher_state.json'
$BackupDir = Join-Path $LauncherRoot 'backup'
$LogPath = Join-Path $LauncherRoot 'backup\launcher_last_run.log'
$ClientPathFile = Join-Path $LauncherRoot 'client_path.local.txt'

function Write-LaunchLog([string]$Message) {
    Write-Host $Message
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Message"
    try {
        if (-not (Test-Path -LiteralPath $BackupDir)) {
            New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
        }
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
}

function Get-ClientExePath([string]$ClientRoot) {
    foreach ($name in @('ExeFile.exe', 'exefile.exe')) {
        $p = Join-Path $ClientRoot $name
        if (Test-Path -LiteralPath $p) {
            return (Get-Item -LiteralPath $p).FullName
        }
    }
    return $null
}

$PortGame = if ($env:EVEMU_ISOLATED_PORT0) { [int]$env:EVEMU_ISOLATED_PORT0 } else { 26100 }
$PortProxy = if ($env:EVEMU_ISOLATED_PORT1) { [int]$env:EVEMU_ISOLATED_PORT1 } else { 26101 }

if ($ValidateOnly) {
    Write-Host "ValidateOnly: Launcher root: $LauncherRoot"
    Write-Host "  Target host: 127.0.0.1  game=$PortGame  proxy=$PortProxy (env EVEMU_ISOLATED_PORT0 / EVEMU_ISOLATED_PORT1)"
    if (-not (Test-Path -LiteralPath $ClientPathFile)) {
        Write-Host "  client_path.local.txt: MISSING - copy client_path.example.txt, then edit (expected before first launch)."
        exit 0
    }
}

function Read-ClientRoot {
    if (-not (Test-Path -LiteralPath $ClientPathFile)) {
        throw "Missing '$ClientPathFile'. Copy client_path.example.txt to client_path.local.txt and set ONE line: folder containing exefile.exe OR full path to exefile.exe"
    }
    $raw = (Get-Content -LiteralPath $ClientPathFile -Raw).Trim()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "client_path.local.txt is empty. Set one line: client bin directory or path to exefile.exe"
    }
    $line = ($raw -split "`r?`n", 2)[0].Trim()
    if ($line -match '(?i)exefile\.exe$') {
        return (Split-Path -Parent $line)
    }
    return $line.TrimEnd('\')
}

function Write-StartIniNoBom([string]$Path, [string]$Content) {
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Get-ResolvedCommonIniPath([string]$ClientRoot) {
    $inBin = Join-Path $ClientRoot 'common.ini'
    if (Test-Path -LiteralPath $inBin) { return $inBin }
    $installRoot = Split-Path -Parent $ClientRoot
    $inParent = Join-Path $installRoot 'common.ini'
    if (Test-Path -LiteralPath $inParent) { return $inParent }
    return $null
}

function Test-ClientBinReadiness([string]$ClientRoot) {
    $notes = @()
    $blueDll = Join-Path $ClientRoot 'blue.dll'
    if (-not (Test-Path -LiteralPath $blueDll)) {
        $notes += 'blue.dll missing in bin (must sit next to ExeFile). If you only opened the 2of2 archive half, copy blue.dll from eveonline_360229_1of2\bin or use Fix_Split_Crucible_Client.ps1 / a merged EVE_360229_MERGED install.'
    }
    if (-not (Get-ResolvedCommonIniPath $ClientRoot)) {
        $notes += 'common.ini not found in bin or in the folder above bin (CCP layout: installroot\common.ini).'
    }
    return $notes
}

function Test-CommonIniPlacebo([string]$ClientRoot) {
    $commonIni = Get-ResolvedCommonIniPath $ClientRoot
    if (-not $commonIni) {
        return @{ Ok = $false; Detail = 'common.ini not found in bin or install parent (folder above bin).' }
    }
    $txt = Get-Content -LiteralPath $commonIni -Raw
    if ($txt -match '(?im)^\s*cryptoPack\s*=\s*Placebo\s*$') {
        return @{ Ok = $true; Detail = "common.ini OK ($commonIni): cryptoPack=Placebo." }
    }
    if ($txt -match '(?im)^\s*cryptoPack\s*=\s*CryptoAPI\s*$') {
        return @{ Ok = $false; Detail = "common.ini ($commonIni) still has cryptoPack=CryptoAPI. Set Placebo (see blue_patcher README) or run Fix_Split_Crucible_Client.ps1." }
    }
    return @{ Ok = $false; Detail = "common.ini ($commonIni): cryptoPack=Placebo not detected; verify blue_patcher README." }
}

function Ensure-StartIniContent([int]$game, [int]$proxy) {
    # Matches blue_patcher guidance: server= must NOT stay Tranquility; [machoNet] for port/proxy.
    # Written UTF-8 without BOM (BOM can break legacy INI readers).
    @"
; Generated by EVEmu temp launcher - isolated stack (localhost / $game / $proxy)
; Restore with Restore_Normal_Client.bat or Restore_EVEmu_Isolated_Client.ps1

[main]
role=client
aid=0
edition=premium
server=127.0.0.1
port=$game

[app]
appname=eve
Role=client

[localization]
language=en

[machoNet]
address=127.0.0.1
port=$game
proxyport=$proxy

"@
}

$clientRoot = Read-ClientRoot
$exefile = Get-ClientExePath $clientRoot
$startIni = Join-Path $clientRoot 'start.ini'

if (-not $exefile) {
    throw "No ExeFile.exe / exefile.exe found under '$clientRoot'. Fix client_path.local.txt (see client_path.example.txt)."
}

if ($ValidateOnly) {
    Write-Host "ValidateOnly: OK"
    Write-Host "  Client root: $clientRoot"
    Write-Host "  Client exe:  $exefile"
    Write-Host "  start.ini:   $startIni (exists=$(Test-Path -LiteralPath $startIni))"
    Write-Host "  Target:      127.0.0.1  game=$PortGame  proxy=$PortProxy"
    Write-Host "  State file:  $StatePath (exists=$(Test-Path -LiteralPath $StatePath))"
    $p = Test-CommonIniPlacebo $clientRoot
    Write-Host "  $($p.Detail)"
    foreach ($n in (Test-ClientBinReadiness $clientRoot)) {
        Write-Host "  Client bin: $n"
    }
    exit 0
}

New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
Write-LaunchLog "==== EVEmu isolated launch session ===="

if (Test-Path -LiteralPath $StatePath) {
    try {
        $prev = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    } catch {
        throw "Corrupt state file at '$StatePath'. Move it aside or delete it after copying backup\start.ini.original if needed."
    }
    if ($prev.ClientRoot -ne $clientRoot) {
        throw "Active isolated session for different client root: '$($prev.ClientRoot)'. Run Restore_Normal_Client.bat first."
    }
    foreach ($n in (Test-ClientBinReadiness $clientRoot)) {
        Write-LaunchLog "WARNING: $n"
    }
    $placebo = Test-CommonIniPlacebo $clientRoot
    if (-not $placebo.Ok) {
        Write-LaunchLog "WARNING: $($placebo.Detail)"
    } else {
        Write-LaunchLog $placebo.Detail
    }
    if ($ForceRefreshIni) {
        Write-LaunchLog "ForceRefreshIni: rewriting start.ini from template (UTF-8 no BOM)."
        Write-StartIniNoBom $startIni (Ensure-StartIniContent $PortGame $PortProxy)
    }
    Write-LaunchLog "Isolated session already active; launching again: $exefile"
    $proc = Start-Process -FilePath $exefile -WorkingDirectory $clientRoot -PassThru
    Write-LaunchLog "Start-Process returned PID=$($proc.Id) Name=$($proc.ProcessName)"
    Write-LaunchLog "If no window appeared, check Task Manager for ExeFile/eve, or read: $LogPath"
    exit 0
}

$backupOriginal = Join-Path $BackupDir 'start.ini.original'
$hadOriginal = Test-Path -LiteralPath $startIni

if ($hadOriginal) {
    Copy-Item -LiteralPath $startIni -Destination $backupOriginal -Force
    Write-LaunchLog "Backed up existing start.ini to: $backupOriginal"
} else {
    Write-LaunchLog "No existing start.ini; creating one for isolated use."
}

foreach ($n in (Test-ClientBinReadiness $clientRoot)) {
    Write-LaunchLog "WARNING: $n"
}

$placebo = Test-CommonIniPlacebo $clientRoot
if (-not $placebo.Ok) {
    Write-LaunchLog "WARNING: $($placebo.Detail)"
} else {
    Write-LaunchLog $placebo.Detail
}

Write-StartIniNoBom $startIni (Ensure-StartIniContent $PortGame $PortProxy)

$state = [ordered]@{
    Version        = 1
    CreatedUtc     = (Get-Date).ToUniversalTime().ToString('o')
    ClientRoot     = $clientRoot
    Exefile        = $exefile
    HadOriginalIni = [bool]$hadOriginal
    BackupFile     = if ($hadOriginal) { $backupOriginal } else { $null }
    PortGame       = $PortGame
    PortProxy      = $PortProxy
}
$json = $state | ConvertTo-Json -Depth 5
Write-StartIniNoBom $StatePath $json

Write-LaunchLog "Wrote isolated start.ini (127.0.0.1:$PortGame / proxy $PortProxy)."
Write-LaunchLog "Launching: $exefile"
try {
    $proc = Start-Process -FilePath $exefile -WorkingDirectory $clientRoot -PassThru
    Write-LaunchLog "Start-Process returned PID=$($proc.Id) Name=$($proc.ProcessName)"
} catch {
    Write-LaunchLog "Start-Process failed: $($_.Exception.Message)"
    throw
}
Write-LaunchLog "If the client window did not appear, see Task Manager or log: $LogPath"
