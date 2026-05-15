"""Smoke test plugin dormant/active toggles."""

import json
import subprocess
import sys
import time
import urllib.request


PORT = 8092
proc = subprocess.Popen(
    [sys.executable, "-m", "symbiosync", "--no-browser", "--host", "127.0.0.1", "--port", str(PORT)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
time.sleep(3)


def api(method, path, expect=200):
    url = f"http://127.0.0.1:{PORT}{path}"
    req = urllib.request.Request(url, method=method)
    resp = urllib.request.urlopen(req, timeout=3)
    data = json.loads(resp.read().decode())
    assert resp.status == expect, f"Expected {expect}, got {resp.status}"
    return data


try:
    plugins = api("GET", "/api/plugins")["plugins"]
    by_type = {p["type"]: p for p in plugins}
    assert "lovense" in by_type
    assert "colmi" in by_type
    assert by_type["lovense"]["dormant"] is False
    print("1. Initial plugins include Lovense and Colmi; Lovense active - OK")

    status = api("GET", "/api/status")
    assert "dormant_plugins" in status
    assert "lovense" not in status["dormant_plugins"]
    print("2. Status includes dormant_plugins without Lovense - OK")

    result = api("POST", "/api/plugins/lovense/toggle")
    assert result["ok"] is True
    assert result["state"] == "dormant"
    print("3. Toggle Lovense -> dormant - OK")

    plugins = api("GET", "/api/plugins")["plugins"]
    by_type = {p["type"]: p for p in plugins}
    assert by_type["lovense"]["dormant"] is True
    print("4. Plugins list shows Lovense dormant - OK")

    status = api("GET", "/api/status")
    assert "lovense" in status["dormant_plugins"]
    print("5. Status dormant_plugins includes Lovense - OK")

    result = api("POST", "/api/plugins/lovense/toggle")
    assert result["ok"] is True
    assert result["state"] == "active"
    print("6. Toggle Lovense -> active - OK")

    plugins = api("GET", "/api/plugins")["plugins"]
    by_type = {p["type"]: p for p in plugins}
    assert by_type["lovense"]["dormant"] is False
    status = api("GET", "/api/status")
    assert "lovense" not in status["dormant_plugins"]
    print("7. Lovense active again - OK")

    print("\n=== DORMANT TOGGLE TEST PASSED ===")
except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback

    traceback.print_exc()
    raise
finally:
    proc.terminate()
    proc.wait(timeout=5)
