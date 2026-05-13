"""Start server, wait for it to be ready, then exit.
This tests that uvicorn + fastapi + our app actually boot."""
import subprocess
import sys
import time
import urllib.request

PORT = 8090
proc = subprocess.Popen(
    [sys.executable, "-m", "symbiosync", "--no-browser", "--host", "0.0.0.0", "--port", str(PORT)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

print(f"Started PID {proc.pid}, waiting for server...")

ready = False
for i in range(20):
    time.sleep(0.5)
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/status", timeout=2)
        data = resp.read().decode()
        print(f"[{i*0.5:.1f}s] /api/status -> {resp.status}")
        print(f"  Response: {data[:200]}")
        ready = True
        break
    except Exception as e:
        if i % 4 == 0:
            print(f"[{i*0.5:.1f}s] Not ready yet: {type(e).__name__}")

if ready:
    # Test the index page
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=2)
        html = resp.read().decode()
        print(f"\n/ -> {resp.status} ({len(html)} bytes)")
        if "SymbioSync" in html:
            print("  UI loads correctly!")
        else:
            print("  WARNING: UI loaded but 'SymbioSync' not found in HTML")
    except Exception as e:
        print(f"\n/ -> FAILED: {e}")

    # Test legacy endpoint
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/status", timeout=2)
        data = resp.read().decode()
        print(f"\n/status (legacy) -> {resp.status}")
        print(f"  Response: {data[:200]}")
    except Exception as e:
        print(f"\n/status (legacy) -> FAILED: {e}")

    # Test logs endpoint
    try:
        resp = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/logs", timeout=2)
        data = resp.read().decode()
        print(f"\n/api/logs -> {resp.status}")
        print(f"  Response: {data[:300]}")
    except Exception as e:
        print(f"\n/api/logs -> FAILED: {e}")

    print("\n=== SERVER BOOT TEST PASSED ===")
else:
    print("\n=== SERVER FAILED TO START ===")
    # Dump whatever output we got
    out = proc.stdout.read()
    if out:
        print(f"Server output:\n{out[:2000]}")

proc.terminate()
proc.wait(timeout=5)
print(f"Server stopped (exit code {proc.returncode})")
