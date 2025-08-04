@echo off
echo ============================================
echo Starting API Server (Memory Safe Mode)
echo ============================================
echo.
echo This will start the API server without heavy ML dependencies
echo to avoid memory issues.
echo.

cd /d "%~dp0"

if not exist venv (
    echo Error: Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

echo Activating virtual environment...
call venv\Scripts\activate

echo.
echo Setting environment variables for safe mode...
set DISABLE_HEAVY_IMPORTS=1
set USE_SIMPLE_KNOWLEDGE_BASE=1

echo.
echo Starting API server...
echo.
echo Server will be available at:
echo - API: http://localhost:8000
echo - Documentation: http://localhost:8000/docs
echo - Interactive docs: http://localhost:8000/redoc
echo.

REM Try lite version first
echo Attempting to start lite API server...
python -m uvicorn src.api.main_lite:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo Lite server failed. Trying regular server with limited imports...
    python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --limit-concurrency 10
)

pause