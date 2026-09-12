# Start Aegis IDS API + frontend (Windows PowerShell)
# Usage: powershell -File scripts\start_all.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "models\trained_models\binary_best.joblib")) {
  Write-Host "Models missing. Run: python scripts/01_prepare_data.py ; python scripts/02_train_models.py"
  exit 1
}

Write-Host "Starting API on http://127.0.0.1:8000 ..."
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$root'; python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"
)

Start-Sleep -Seconds 2
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) {
  Write-Host "Installing frontend deps..."
  npm install
}

Write-Host "Starting UI on http://127.0.0.1:5173 ..."
Start-Process powershell -ArgumentList @(
  "-NoExit", "-Command",
  "Set-Location '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Open UI:  http://127.0.0.1:5173/"
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "Demo script: docs\DEMO.md"
