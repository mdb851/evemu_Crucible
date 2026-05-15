#Requires -Version 5.1
<#
.SYNOPSIS
  OOTP 27 Realistic Announcer — full ElevenLabs build of the professional pack (109 lines).

.DESCRIPTION
  Part of the ootp27-realistic-announcer project. Put your API key in a ONE-LINE file named .elevenlabs_api_key in the repo root
  (that file is gitignored). Or set ELEVENLABS_API_KEY / ELEVENLABS_API_KEY_FILE yourself.

  Then run this script from anywhere:
    powershell -ExecutionPolicy Bypass -File .\scripts\run-elevenlabs-professional-full.ps1
#>
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$keyPath = Join-Path $RepoRoot '.elevenlabs_api_key'
if (Test-Path $keyPath) {
  $env:ELEVENLABS_API_KEY_FILE = $keyPath
  Write-Host "Using API key file: $keyPath"
}

Remove-Item Env:ELEVENLABS_API_KEY -ErrorAction SilentlyContinue

$python = $null
foreach ($candidate in @(
    (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
    (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
    (Join-Path $env:ProgramFiles 'Python312\python.exe')
  )) {
  if ($candidate -and (Test-Path $candidate)) {
    $python = $candidate
    break
  }
}
if (-not $python) {
  Write-Error 'Python 3.12+ not found. Install Python or add it to PATH.'
}

Write-Host "Python: $python"
& $python -m ootp_announcer verify-elevenlabs
if ($LASTEXITCODE -ne 0) {
  Write-Host ''
  Write-Host 'Fix: create ' -NoNewline
  Write-Host $keyPath -ForegroundColor Yellow -NoNewline
  Write-Host ' with your ElevenLabs API key on a single plain-text line (Notepad), save, re-run.'
  exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'Starting full build (109 lines). Expect several minutes...' -ForegroundColor Cyan
& $python -m ootp_announcer build `
  --config packs\professional_broadcast\announcer.elevenlabs.example.toml `
  --script packs\professional_broadcast\lines.csv `
  --out build\voice-pack-professional

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host ''
Write-Host 'Done. Output folder:' -ForegroundColor Green
Write-Host (Join-Path $RepoRoot 'build\voice-pack-professional')
