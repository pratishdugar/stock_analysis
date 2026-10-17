# One-time (re-runnable) setup for Windows. Run from the project folder:  .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Find Python 3.11+ (3.12 recommended)
$py = $null
foreach ($cand in @("py -3.12", "py -3.13", "py -3.11", "python")) {
    try {
        $parts = $cand.Split(" ")
        $ver = & $parts[0] $parts[1..($parts.Length)] -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$ver -ge [version]"3.11") { $py = $cand; break }
    } catch { }
}
if (-not $py) {
    Write-Host "Python 3.11+ not found. Install Python 3.12 from https://www.python.org/downloads/ (tick 'Add to PATH') and re-run." -ForegroundColor Red
    exit 1
}
Write-Host "Using Python launcher: $py"

if (-not (Test-Path ".venv")) {
    $parts = $py.Split(" ")
    & $parts[0] $parts[1..($parts.Length)] -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host "Failed to create .venv" -ForegroundColor Red; exit 1 }
}
$venvPy = ".\.venv\Scripts\python.exe"
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "Dependency install failed. Check your internet connection and re-run." -ForegroundColor Red; exit 1 }

& $venvPy -c "import streamlit, pandas, numpy, plotly, yfinance, feedparser, google.genai, dotenv; print('Imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "Import check failed." -ForegroundColor Red; exit 1 }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env - open it in Notepad and add GEMINI_API_KEY and GEMINI_MODEL (optional)."
} else {
    Write-Host ".env already exists - left untouched."
}
Write-Host "Setup complete. Start the app with:  .\run.ps1" -ForegroundColor Green
