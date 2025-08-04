#!/usr/bin/env python3
"""
Run all components of AI Game Story Generator
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path

def check_port(port):
    """Check if port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0

def kill_existing_processes():
    """Kill existing python processes running uvicorn or streamlit"""
    if sys.platform == "win32":
        # Windows
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq *uvicorn*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq *streamlit*"], capture_output=True)
        # Also try to kill by process name
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq *localhost:8000*"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq *localhost:8501*"], capture_output=True)
    else:
        # Unix-like
        subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
        subprocess.run(["pkill", "-f", "streamlit"], capture_output=True)

def main():
    print("Starting AI Game Story Generator - All Components")
    print("=" * 50)
    print()
    
    # Check virtual environment
    venv_python = Path("venv/Scripts/python.exe") if sys.platform == "win32" else Path("venv/bin/python")
    if not venv_python.exists():
        print("ERROR: Virtual environment not found! Please set up the project first.")
        sys.exit(1)
    
    # Check ports and ask to kill existing processes
    ports_in_use = []
    if not check_port(8000):
        ports_in_use.append(8000)
    if not check_port(8501):
        ports_in_use.append(8501)
    
    if ports_in_use:
        print(f"WARNING: Ports {ports_in_use} are already in use.")
        response = input("Kill existing processes and continue? (y/n): ")
        if response.lower() == 'y':
            print("Stopping existing processes...")
            kill_existing_processes()
            time.sleep(2)  # Wait for processes to die
        else:
            print("Exiting without starting new processes.")
            sys.exit(0)
    
    processes = []
    
    try:
        # Start API server
        print("Starting API server on http://localhost:8000...")
        api_process = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "src.api.main:app", "--reload", "--port", "8000"],
            cwd=os.getcwd()
        )
        processes.append(api_process)
        
        # Wait for API to start
        time.sleep(3)
        
        # Start Streamlit UI
        print("Starting Streamlit UI on http://localhost:8501...")
        streamlit_process = subprocess.Popen(
            [str(venv_python), "-m", "streamlit", "run", "streamlit_app.py", 
             "--server.port", "8501", "--server.address", "localhost"],
            cwd=os.getcwd()
        )
        processes.append(streamlit_process)
        
        print("\n" + "=" * 50)
        print("All components started!")
        print()
        print("- Streamlit UI: http://localhost:8501")
        print("- API Server: http://localhost:8000")
        print("- API Docs: http://localhost:8000/docs")
        print()
        print("Press Ctrl+C to stop all services...")
        print("=" * 50)
        
        # Wait for processes
        for p in processes:
            p.wait()
            
    except KeyboardInterrupt:
        print("\n\nStopping all services...")
        for p in processes:
            if p.poll() is None:  # Process is still running
                if sys.platform == "win32":
                    p.terminate()
                else:
                    os.kill(p.pid, signal.SIGTERM)
        
        # Wait for processes to terminate
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        
        print("All services stopped.")

if __name__ == "__main__":
    main()