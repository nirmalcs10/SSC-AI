"""
Dedicated Application Launcher for Firefox.
Launches the Streamlit trading dashboard directly in Mozilla Firefox on fixed default port 8501.
"""
import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 8501

def find_firefox_path() -> str:
    """Detect Firefox executable on Windows."""
    candidates = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe")
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "firefox"


def free_port_if_occupied(port: int = DEFAULT_PORT):
    """If the default port is occupied by a stale process, terminate it cleanly."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        is_occupied = (s.connect_ex(("127.0.0.1", port)) == 0)

    if is_occupied:
        print(f"Port {port} is occupied. Cleaning up stale process to ensure fixed default port {port}...")
        try:
            # Find PID listening on the port in Windows
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"'
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            pids = set(output.split())
            current_pid = str(os.getpid())
            for pid in pids:
                if pid and pid != "0" and pid != current_pid:
                    print(f"Terminating stale process {pid} on port {port}...")
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
            time.sleep(1)
        except Exception as e:
            print(f"Port cleanup notice: {e}")


def launch():
    firefox_bin = find_firefox_path()
    port = DEFAULT_PORT
    free_port_if_occupied(port)
    app_url = f"http://localhost:{port}"
    
    print("=" * 60)
    print("Indian Stock Market Multi-Timeframe Trading Tool")
    print(f"Target Browser: Mozilla Firefox ({firefox_bin})")
    print(f"Fixed Default Port: {port}")
    print(f"Application URL: {app_url}")
    print("=" * 60)

    # Launch Streamlit server on fixed port 8501
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(BASE_DIR / "app.py"),
        "--server.headless", "true",
        "--server.port", str(port),
        "--browser.gatherUsageStats", "false"
    ]

    server_process = subprocess.Popen(cmd)

    # Wait for server startup
    time.sleep(2)

    # Open specifically in Mozilla Firefox
    if os.path.exists(firefox_bin):
        try:
            subprocess.Popen([firefox_bin, app_url])
            print("Successfully launched Firefox!")
        except Exception as e:
            print(f"Could not spawn Firefox directly: {e}, using browser fallback.")
            webbrowser.open(app_url)
    else:
        webbrowser.open(app_url)

    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\nStopping application server...")
        server_process.terminate()

if __name__ == "__main__":
    launch()
