# Launch the app using the project virtual environment (no activation needed).
Set-Location $PSScriptRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "No .venv found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}
& .\.venv\Scripts\python.exe -m streamlit run app.py
