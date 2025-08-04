@echo off
echo Starting AI Game Story Generator - All Components
echo ================================================
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Check if python-multipart is installed (needed for API)
python -c "import multipart" 2>nul
if errorlevel 1 (
    echo Installing python-multipart for API...
    pip install python-multipart
)

REM Start API server in new window
echo Starting API server on http://localhost:8000...
start "API Server" cmd /k "venv\Scripts\python.exe -m uvicorn src.api.main:app --reload --port 8000"

REM Wait a bit for API to start
timeout /t 3 /nobreak > nul

REM Start Streamlit UI in new window
echo Starting Streamlit UI on http://localhost:8501...
start "Streamlit UI" cmd /k "venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501 --server.address localhost"

echo.
echo ================================================
echo All components started!
echo.
echo - Streamlit UI: http://localhost:8501
echo - API Server: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
echo Close this window to keep services running.
echo Press any key to stop all services...
echo ================================================

pause > nul

REM Kill processes when user presses a key
echo.
echo Stopping all services...
taskkill /FI "WindowTitle eq API Server*" /T /F 2>nul
taskkill /FI "WindowTitle eq Streamlit UI*" /T /F 2>nul
echo All services stopped.
pause