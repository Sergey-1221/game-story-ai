#!/usr/bin/env python3
"""
Safe launcher for all components with better error handling
"""
import subprocess
import sys
import time
import os
import signal
from pathlib import Path
import threading
import queue

def check_port(port):
    """Check if port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    return result != 0

def stream_output(process, name, output_queue):
    """Stream output from subprocess"""
    try:
        for line in iter(process.stdout.readline, b''):
            if line:
                output_queue.put(f"[{name}] {line.decode('utf-8', errors='ignore').rstrip()}")
    except Exception as e:
        output_queue.put(f"[{name}] Error reading output: {e}")

def main():
    print("Starting AI Game Story Generator - Safe Mode")
    print("=" * 50)
    print()
    
    # Check virtual environment
    venv_python = Path("venv/Scripts/python.exe") if sys.platform == "win32" else Path("venv/bin/python")
    if not venv_python.exists():
        print("ERROR: Virtual environment not found! Please set up the project first.")
        sys.exit(1)
    
    # Set environment variables to reduce verbosity
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Reduce TensorFlow warnings
    env['TOKENIZERS_PARALLELISM'] = 'false'  # Reduce tokenizer warnings
    
    processes = []
    output_queue = queue.Queue()
    
    try:
        # Start API server first
        print("Starting API server on http://localhost:8000...")
        api_process = subprocess.Popen(
            [str(venv_python), "-m", "uvicorn", "src.api.main:app", "--port", "8000", "--log-level", "error"],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env
        )
        processes.append(("API", api_process))
        
        # Start output thread for API
        api_thread = threading.Thread(target=stream_output, args=(api_process, "API", output_queue))
        api_thread.daemon = True
        api_thread.start()
        
        # Wait for API to start
        print("Waiting for API to initialize...")
        time.sleep(5)
        
        # Check if API is responding
        if not check_port(8000):
            print("[OK] API server started successfully")
        else:
            print("[ERROR] API server failed to start")
            raise Exception("API server failed to start")
        
        # Start Streamlit UI
        print("\nStarting Streamlit UI on http://localhost:8501...")
        streamlit_process = subprocess.Popen(
            [str(venv_python), "-m", "streamlit", "run", "streamlit_app.py", 
             "--server.port", "8501", "--server.address", "localhost",
             "--server.headless", "true", "--logger.level", "error"],
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env
        )
        processes.append(("Streamlit", streamlit_process))
        
        # Start output thread for Streamlit
        streamlit_thread = threading.Thread(target=stream_output, args=(streamlit_process, "Streamlit", output_queue))
        streamlit_thread.daemon = True
        streamlit_thread.start()
        
        # Wait for Streamlit to start
        print("Waiting for Streamlit to initialize...")
        time.sleep(5)
        
        # Check if Streamlit is responding
        if not check_port(8501):
            print("[OK] Streamlit UI started successfully")
        else:
            print("[ERROR] Streamlit UI failed to start")
            raise Exception("Streamlit UI failed to start")
        
        print("\n" + "=" * 50)
        print("All components started successfully!")
        print()
        print("- Streamlit UI: http://localhost:8501")
        print("- API Server: http://localhost:8000")
        print("- API Docs: http://localhost:8000/docs")
        print()
        print("Press Ctrl+C to stop all services...")
        print("=" * 50)
        print("\nLive logs:")
        print("-" * 50)
        
        # Monitor processes and output
        while True:
            # Check if processes are still running
            for name, p in processes:
                if p.poll() is not None:
                    print(f"\n[ERROR] {name} process terminated unexpectedly!")
                    raise Exception(f"{name} crashed")
            
            # Print output
            try:
                while True:
                    line = output_queue.get_nowait()
                    print(line)
            except queue.Empty:
                pass
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
    except Exception as e:
        print(f"\n\nError: {e}")
    finally:
        # Stop all processes
        print("Stopping all services...")
        for name, p in processes:
            if p.poll() is None:
                print(f"Stopping {name}...")
                if sys.platform == "win32":
                    p.terminate()
                else:
                    os.kill(p.pid, signal.SIGTERM)
        
        # Wait for processes to terminate
        for name, p in processes:
            try:
                p.wait(timeout=5)
                print(f"{name} stopped")
            except subprocess.TimeoutExpired:
                print(f"Force killing {name}...")
                p.kill()
        
        print("\nAll services stopped.")

if __name__ == "__main__":
    main()