#!/usr/bin/env python3
"""
Simple reliable startup script
"""
import subprocess
import sys
import time
import os
from pathlib import Path

def kill_processes_on_ports():
    """Kill processes using our ports"""
    if sys.platform == "win32":
        # Kill processes using port 8000
        subprocess.run(["netstat", "-ano"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/PID", "$(netstat -ano | findstr :8000 | awk '{print $5}')"], 
                      shell=True, capture_output=True)
        subprocess.run(["taskkill", "/F", "/PID", "$(netstat -ano | findstr :8501 | awk '{print $5}')"], 
                      shell=True, capture_output=True)
    time.sleep(2)

def main():
    print("Starting AI Game Story Generator")
    print("=" * 40)
    
    # Check virtual environment
    venv_python = Path("venv/Scripts/python.exe") if sys.platform == "win32" else Path("venv/bin/python")
    if not venv_python.exists():
        print("ERROR: Virtual environment not found!")
        sys.exit(1)
    
    # Kill existing processes
    print("Cleaning up existing processes...")
    kill_processes_on_ports()
    
    # Set minimal environment
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    print("\n1. Starting API server...")
    api_cmd = [
        str(venv_python), "-c", 
        "import uvicorn; uvicorn.run('src.api.main:app', host='127.0.0.1', port=8000, log_level='critical')"
    ]
    
    print("\n2. Starting Streamlit UI...")
    streamlit_cmd = [
        str(venv_python), "-c",
        "import streamlit.web.cli as stcli; import sys; sys.argv=['streamlit', 'run', 'streamlit_app.py', '--server.port=8501', '--server.headless=true']; stcli.main()"
    ]
    
    try:
        # Start API
        api_proc = subprocess.Popen(api_cmd, env=env)
        time.sleep(8)  # Wait for API to fully start
        
        if api_proc.poll() is not None:
            print("API failed to start!")
            return False
        
        # Start Streamlit
        streamlit_proc = subprocess.Popen(streamlit_cmd, env=env)
        time.sleep(5)  # Wait for Streamlit
        
        if streamlit_proc.poll() is not None:
            print("Streamlit failed to start!")
            api_proc.terminate()
            return False
        
        print("\n" + "=" * 40)
        print("SUCCESS! Both services are running:")
        print("- API Server: http://localhost:8000")
        print("- Streamlit UI: http://localhost:8501")
        print("=" * 40)
        print("\nPress Ctrl+C to stop...")
        
        # Keep running
        while True:
            time.sleep(1)
            if api_proc.poll() is not None or streamlit_proc.poll() is not None:
                print("A service crashed!")
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        try:
            api_proc.terminate()
            streamlit_proc.terminate()
        except:
            pass
        print("Stopped.")

if __name__ == "__main__":
    main()