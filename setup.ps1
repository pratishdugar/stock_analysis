# One-time (safe to re-run) setup for Windows. From the project folder run:  .\setup.ps1
# Native tools report failure through $LASTEXITCODE, which is checked explicitly after each step.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

# Returns the Python version for a launcher like "py -3.12" or "python", or $null if unusable.
function Get-PyVersion([string]$launcher) {
    $parts = $launcher.Split(" ")
    $exe = $parts[0]
    $pre = @(); if ($parts.Length -gt 1) { $pre = $parts[1..($parts.Length - 1)] }
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $null }
    $out = & $exe @pre -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
    try { return [version](($out | Select-Object -First 1).ToString().Trim()) } catch { return $null }
}

# Prefer 3.12 / 3.13 (what CI tests); accept any 3.11+.
$py = $null
foreach ($cand in @("py -3.12", "py -3.13", "py -3.11", "py -3", "python")) {
    $v = Get-PyVersion $cand
    if ($v -and $v -ge [version]"3.11") { $py = $cand; Write-Host "Found Python $v via '$cand'"; break }
}
if (-not $py) {
    Fail "Python 3.11+ not found. Install Python 3.12 from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'), open a NEW PowerShell window and re-run .\setup.ps1"
}

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    if (Test-Path ".venv") { Write-Host "Found an incomplete .venv - recreating it."; Remove-Item -Recurse -Force ".venv" }
    $parts = $py.Split(" "); $pre = @(); if ($parts.Length -gt 1) { $pre = $parts[1..($parts.Length - 1)] }
    & $parts[0] @pre -m venv .venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) { Fail "Failed to create the .venv virtual environment." }
}

& $venvPy -m pip install --upgrade pip --disable-pip-version-check -q
& $venvPy -m pip install -r requirements.txt --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Fail "Dependency install failed. Check your internet connection / proxy and re-run .\setup.ps1" }

& $venvPy -c "import streamlit, pandas, numpy, plotly, yfinance, feedparser, google.genai, dotenv; print('Imports OK')"
if ($LASTEXITCODE -ne 0) { Fail "Import check failed. Re-run .\setup.ps1; if it persists, delete the .venv folder and re-run." }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env - optionally open it in Notepad and set GEMINI_API_KEY and GEMINI_MODEL."
} else {
    Write-Host ".env already exists - left untouched."
}
Write-Host "Setup complete. Start the app with:  .\run.ps1" -ForegroundColor Green
