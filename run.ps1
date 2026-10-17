# Launch the app using the project virtual environment (no activation needed). Extra args go to Streamlit,
# e.g.  .\run.ps1 --server.port 8502
Set-Location $PSScriptRoot
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "No .venv found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}
& $venvPy -m streamlit run app.py @args
exit $LASTEXITCODE
