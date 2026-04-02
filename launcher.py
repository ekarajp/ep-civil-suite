import os
import sys
import time
import socket
import threading
import webbrowser
import subprocess

from streamlit.web import bootstrap

HOST = "127.0.0.1"
PORT = 8501
APP_URL = f"http://{HOST}:{PORT}"

IDLE_TIMEOUT = 8.0
CHECK_INTERVAL = 1.0
STARTUP_TIMEOUT = 20.0


def get_base_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def is_port_open(host: str, port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def wait_and_open_browser():
    start = time.time()
    opened = False

    while time.time() - start < STARTUP_TIMEOUT:
        if is_port_open(HOST, PORT):
            if not opened:
                webbrowser.open(APP_URL, new=1)
                opened = True
            return
        time.sleep(0.5)


def count_established_connections(port: int) -> int:
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return 0

        count = 0
        target = f":{port}"

        for line in result.stdout.splitlines():
            line = line.strip()
            if target not in line or "ESTABLISHED" not in line:
                continue

            parts = line.split()
            if len(parts) < 4:
                continue

            proto = parts[0]
            local_addr = parts[1]
            state = parts[3]

            if proto.upper() == "TCP" and local_addr.endswith(target) and state.upper() == "ESTABLISHED":
                count += 1

        return count
    except Exception:
        return 0


def force_exit():
    os._exit(0)


def idle_shutdown_monitor():
    idle_start = None
    grace_start = time.time()

    while True:
        # ช่วงเริ่มต้น อย่าเพิ่งรีบปิด
        if time.time() - grace_start < STARTUP_TIMEOUT:
            time.sleep(CHECK_INTERVAL)
            continue

        connections = count_established_connections(PORT)

        if connections > 0:
            idle_start = None
        else:
            if idle_start is None:
                idle_start = time.time()
            elif time.time() - idle_start >= IDLE_TIMEOUT:
                force_exit()

        time.sleep(CHECK_INTERVAL)


def main():
    base_dir = get_base_dir()
    app_path = os.path.join(base_dir, "main.py")

    os.chdir(base_dir)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    if not os.path.exists(app_path):
        raise FileNotFoundError(f"main.py not found at: {app_path}")

    threading.Thread(target=wait_and_open_browser, daemon=True).start()
    threading.Thread(target=idle_shutdown_monitor, daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--server.headless=true",
        f"--server.port={PORT}",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
    ]

    bootstrap.run(app_path, False, [], {})


if __name__ == "__main__":
    main()