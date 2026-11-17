"""
Dedicated Application Launcher for Firefox.
Launches the Streamlit trading dashboard directly in Mozilla Firefox.
"""
import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

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

import socket

def get_available_port(default_port: int = 8501) -> int:
    """Check if default port is free, otherwise find next available port."""
    port = default_port
    while port < default_port + 20:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return default_port

def launch():
    firefox_bin = find_firefox_path()
    port = get_available_port(8501)
    app_url = f"http://localhost:{port}"
    
    print("=" * 60)
    print("Indian Stock Market Multi-Timeframe Trading Tool")
    print(f"Target Browser: Mozilla Firefox ({firefox_bin})")
    print(f"Application URL: {app_url} (Port {port})")
    print("=" * 60)

    # Launch Streamlit server in headless mode so it doesn't open default browser
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
