$env:APP_ENV = "development"
$env:ENABLE_WORKER = "true"
$env:ENABLE_DEMO_ENGINE = "true"
$env:MARKET_DATA_MODE = "live"

Set-Location (Join-Path $PSScriptRoot "..")

& ".\venv\Scripts\python.exe" -m uvicorn trading_bot_backend.app.main:app --host 127.0.0.1 --port 8003
