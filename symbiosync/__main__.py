"""
SymbioSync - run with: python -m symbiosync

Privacy-first BLE device controller.
No cloud. No accounts. No telemetry. Just Bluetooth.
"""

import argparse
import sys
import webbrowser
import threading

from . import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="symbiosync",
        description="SymbioSync - Privacy-first BLE device controller",
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

    # Lazy import so --help is fast
    import uvicorn
    from .server import app, set_config

    set_config(host=args.host, port=args.port)

    url = f"http://{args.host}:{args.port}"
    if args.host == "0.0.0.0":
        url = f"http://127.0.0.1:{args.port}"

    print(f"SymbioSync v{__version__}")
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


if __name__ == "__main__":
    main()
