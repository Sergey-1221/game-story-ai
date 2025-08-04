@echo off
echo Starting Streamlit UI...
echo.
call venv\Scripts\activate
venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8501 --server.headless true --logger.level error
pause