@echo off
echo Starting AI Game Story Generator UI...
echo.

REM Activate virtual environment
call venv\Scripts\activate

REM Check if streamlit is installed
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Installing Streamlit...
    pip install streamlit streamlit-option-menu streamlit-aggrid streamlit-extras plotly
)

REM Run the Streamlit app
echo Launching UI at http://localhost:8501
streamlit run streamlit_app.py --server.port 8501 --server.address localhost

pause