Write-Host "Starting AI Game Story Generator - All Components" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "Virtual environment not found! Please run setup first." -ForegroundColor Red
    exit 1
}

# Function to check if port is in use
function Test-Port {
    param($Port)
    $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
    return $connection
}

# Check if ports are already in use
if (Test-Port 8000) {
    Write-Host "Port 8000 is already in use. API server might be running." -ForegroundColor Yellow
}
if (Test-Port 8501) {
    Write-Host "Port 8501 is already in use. Streamlit might be running." -ForegroundColor Yellow
}

# Start API server
Write-Host "Starting API server on http://localhost:8000..." -ForegroundColor Cyan
$api = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "src.api.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory $PWD `
    -PassThru `
    -WindowStyle Normal

# Wait for API to start
Start-Sleep -Seconds 3

# Start Streamlit UI
Write-Host "Starting Streamlit UI on http://localhost:8501..." -ForegroundColor Cyan
$streamlit = Start-Process -FilePath "venv\Scripts\python.exe" `
    -ArgumentList "-m", "streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "localhost" `
    -WorkingDirectory $PWD `
    -PassThru `
    -WindowStyle Normal

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "All components started!" -ForegroundColor Green
Write-Host ""
Write-Host "- Streamlit UI: " -NoNewline; Write-Host "http://localhost:8501" -ForegroundColor Cyan
Write-Host "- API Server: " -NoNewline; Write-Host "http://localhost:8000" -ForegroundColor Cyan
Write-Host "- API Docs: " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Green

# Keep script running and handle Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    
    # Stop processes
    if ($api -and !$api.HasExited) {
        Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue
    }
    if ($streamlit -and !$streamlit.HasExited) {
        Stop-Process -Id $streamlit.Id -Force -ErrorAction SilentlyContinue
    }
    
    # Also kill any orphaned processes
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*streamlit*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    
    Write-Host "All services stopped." -ForegroundColor Green
}