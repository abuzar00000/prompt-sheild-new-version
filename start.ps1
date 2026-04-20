# Run from repo root: .\start.ps1
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8080 --reload
