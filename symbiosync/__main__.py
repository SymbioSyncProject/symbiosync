"""
SymbioSync - run with: python -m symbiosync

Private habitat supporting truthful interface:
human <-> companion agents <-> devices <-> embodied state.
"""

import argparse
import json
import socket
import sys
import webbrowser
import threading
from urllib.request import urlopen

from . import __version__


def _display_url(host: str, port: int) -> str:
    if host == "0.0.0.0":
        return f"http://127.0.0.1:{port}"
    return f"http://{host}:{port}"


def _connect_host(host: str) -> str:
    if host == "0.0.0.0":
        return "127.0.0.1"
    return host


def _port_accepts_connections(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return True when something already accepts TCP connections on host:port."""
    try:
        with socket.create_connection((_connect_host(host), port), timeout=timeout):
            return True
    except OSError:
        return False


def _existing_symbiosync_status(url: str, timeout: float = 2.0) -> dict | None:
    """Return /api/status JSON if the occupied port is an existing SymbioSync."""
    try:
        with urlopen(f"{url}/api/status", timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = response.read(1024 * 1024).decode("utf-8")
            data = json.loads(payload)
            if isinstance(data, dict) and "devices" in data and "remembered" in data:
                return data
    except Exception:
        return None
    return None


def main():
    parser = argparse.ArgumentParser(
        prog="symbiosync",
        description="SymbioSync - private habitat supporting truthful interface",
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="Bind address (default: 0.0.0.0 for LAN/WSL access, use 127.0.0.1 for local only)",
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="HTTP port (default: 8080)",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't auto-open browser on startup",
    )
    parser.add_argument(
        "--version", action="version", version=f"SymbioSync {__version__}",
    )
    args = parser.parse_args()

    url = _display_url(args.host, args.port)

    print(f"SymbioSync v{__version__}")
    print("Private habitat supporting truthful interface:")
    print("human <-> companion agents <-> devices <-> embodied state")
    print()

    if _port_accepts_connections(args.host, args.port):
        existing = _existing_symbiosync_status(url)
        if existing is not None:
            connected_count = len(existing.get("devices") or {})
            remembered_count = len(existing.get("remembered") or {})
            print(f"Port {args.port} is already in use by a reachable SymbioSync server.")
            print(f"Opening existing server at {url}")
            print(f"Current status: {connected_count} connected, {remembered_count} remembered.")
            if not args.no_browser:
                webbrowser.open(url)
            return 0

        print(f"Port {args.port} is already in use, but SymbioSync did not answer at {url}.")
        print("Another process may be holding the port, or an old SymbioSync process may be wedged.")
        print("Run stop.bat, close the old server window, or choose another port with --port.")
        return 1

    # Lazy import so --help and already-running checks stay fast and side-effect-light.
    import uvicorn
    from .server import app, set_config

    set_config(host=args.host, port=args.port)

    print(f"Starting on {url}")
    print(f"Press Ctrl+C to stop\n")

    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
