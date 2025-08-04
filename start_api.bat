@echo off
echo Starting API Server...
echo.
call venv\Scripts\activate
venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --log-level critical
pause