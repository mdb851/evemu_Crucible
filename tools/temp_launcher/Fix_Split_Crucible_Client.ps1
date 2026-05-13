#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot repair for split Crucible archives (1of2 / 2of2): copy blue.dll into 2of2\bin and set cryptoPack=Placebo on install-root common.ini.

.DESCRIPTION
  Does NOT replace a full blue_patcher run if your tree is wrong build — only wires the usual split layout:
  - eveonline_*_2of2\common.ini (often CryptoAPI)
  - eveonline_*_1of2\bin\blue.dll
  - eveonline_*_2of2\bin\ExeFile.exe

  Backs up targets once (*.bak_evemu) before overwriting.

.PARAMETER BinPath
  Path to ...\something_2of2\bin (folder containing ExeFile.exe). If omitted, reads first line of client_path.local.txt next to this script.
#>
param(
    [string]$BinPath,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$LauncherRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$clientList = Join-Path $LauncherRoot 'client_path.local.txt'

if ([string]::IsNullOrWhiteSpace($BinPath)) {
    if (-not (Test-Path -LiteralPath $clientList)) {
        throw "Pass -BinPath '...\\eveonline_360229_2of2\\bin' or create client_path.local.txt with that one line."
    }
    $BinPath = ((Get-Content -LiteralPath $clientList -Raw).Trim() -split "`r?`n")[0].Trim()
    if ($BinPath -match '(?i)exefile\.exe$') { $BinPath = Split-Path -Parent $BinPath }
}

if (-not (Test-Path -LiteralPath (Join-Path $BinPath 'ExeFile.exe'))) {
    throw "ExeFile.exe not found under BinPath: $BinPath"
}

$install2 = Split-Path -Parent $BinPath
$leaf = Split-Path -Leaf $install2
$grand = Split-Path -Parent $install2

if ($leaf -notmatch '2of2') {
    Write-Warning "Folder name does not look like a 2of2 half ('$leaf'). This script is only for the usual 1of2/2of2 split. For a merged tree, point client_path at EVE_*_MERGED\bin instead."
}

$leaf1 = $leaf -replace '2of2', '1of2'
$install1 = Join-Path $grand $leaf1
$blueSrc = Join-Path $install1 'bin\blue.dll'
$blueDst = Join-Path $BinPath 'blue.dll'
$commonIni = Join-Path $install2 'common.ini'

Write-Host "BinPath:        $BinPath"
Write-Host "blue.dll src:  $blueSrc (exists=$(Test-Path -LiteralPath $blueSrc))"
Write-Host "blue.dll dst:  $blueDst"
Write-Host "common.ini:     $commonIni (exists=$(Test-Path -LiteralPath $commonIni))"

if (-not (Test-Path -LiteralPath $blueSrc)) {
    throw "Source blue.dll not found. Adjust paths or use a merged client install."
}
if (-not (Test-Path -LiteralPath $commonIni)) {
    throw "common.ini not found next to 2of2 bin parent. Wrong layout for this repair script."
}

if ($WhatIf) {
    Write-Host "WhatIf: would copy blue.dll -> $blueDst"
} else {
    if (Test-Path -LiteralPath $blueDst) {
        Copy-Item -LiteralPath $blueDst -Destination ($blueDst + '.bak_evemu') -Force -ErrorAction SilentlyContinue
    }
    Copy-Item -LiteralPath $blueSrc -Destination $blueDst -Force
    Write-Host "Copied blue.dll into bin."
}

$txt = Get-Content -LiteralPath $commonIni -Raw
if ($txt -notmatch '(?im)cryptoPack\s*=') {
    throw "common.ini has no cryptoPack= line; not editing."
}
if ($txt -match '(?im)cryptoPack\s*=\s*Placebo') {
    Write-Host "common.ini already has cryptoPack=Placebo."
} else {
    $newTxt = $txt -replace '(?im)(cryptoPack\s*=\s*)CryptoAPI', '$1Placebo'
    if ($newTxt -eq $txt) {
        Write-Warning "cryptoPack line not updated (unexpected format). Edit common.ini manually."
    } else {
        if ($WhatIf) {
            Write-Host "WhatIf: would set cryptoPack=Placebo in $commonIni"
        } else {
            Copy-Item -LiteralPath $commonIni -Destination ($commonIni + '.bak_evemu') -Force
            $utf8 = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllText($commonIni, $newTxt, $utf8)
            Write-Host "Set cryptoPack=Placebo in common.ini (backup: common.ini.bak_evemu)."
        }
    }
}

Write-Host "Done. Run: Restore_Normal_Client.bat then Launch_EVEmu_Isolated.bat -ForceRefreshIni"
