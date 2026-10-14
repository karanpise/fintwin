
import subprocess
import sys
import time

processes = []

try:
    backend = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ])
    processes.append(backend)

    time.sleep(2)

    if backend.poll() is not None:
        raise RuntimeError("FastAPI failed to start. Check the error above.")

    frontend = subprocess.Popen([
        sys.executable, "-m", "streamlit",
        "run", "frontend/Dashboard.py",
        "--server.address", "127.0.0.1",
        "--server.port", "8501"
    ])
    processes.append(frontend)

    print("\nFinTwin is starting...")
    print("Frontend: http://localhost:8501")
    print("API docs: http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to stop both.\n")

    while True:
        if any(p.poll() is not None for p in processes):
            break
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping FinTwin...")

except RuntimeError as error:
    print(error)

finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
