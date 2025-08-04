@echo off
echo Starting Lite API Server (Memory Safe)...
echo.
echo This version uses simplified modules to avoid memory issues.
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

echo Starting API server in lite mode...
echo.
echo API will be available at: http://localhost:8000
echo API documentation: http://localhost:8000/docs
echo.

REM Use lite version without heavy dependencies
python -m uvicorn src.api.main_lite:app --reload --host 0.0.0.0 --port 8000

pause