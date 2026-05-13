"""Test plugin dormant/active toggle."""
import subprocess, sys, time, urllib.request, json

PORT = 8092
proc = subprocess.Popen(
    [sys.executable, "-m", "symbiosync", "--no-browser", "--host", "0.0.0.0", "--port", str(PORT)],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
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
    # 1. Check initial state
    plugins = api("GET", "/api/plugins")["plugins"]
    assert len(plugins) == 1
    assert plugins[0]["type"] == "lovense"
    assert plugins[0]["dormant"] == False
    print("1. Initial state: Lovense active - OK")

    # 2. Check status has dormant_plugins
    status = api("GET", "/api/status")
    assert "dormant_plugins" in status
    assert status["dormant_plugins"] == []
    print("2. Status includes dormant_plugins: [] - OK")

    # 3. Toggle to dormant
    result = api("POST", "/api/plugins/lovense/toggle")
    assert result["ok"] == True
    assert result["state"] == "dormant"
    print("3. Toggle -> dormant - OK")

    # 4. Verify dormant in plugins list
    plugins = api("GET", "/api/plugins")["plugins"]
    assert plugins[0]["dormant"] == True
    print("4. Plugins list shows dormant: true - OK")

    # 5. Verify dormant in status
    status = api("GET", "/api/status")
    assert "lovense" in status["dormant_plugins"]
    print("5. Status dormant_plugins: ['lovense'] - OK")

    # 6. Toggle back to active
    result = api("POST", "/api/plugins/lovense/toggle")
    assert result["ok"] == True
    assert result["state"] == "active"
    print("6. Toggle -> active - OK")

    # 7. Verify active again
    plugins = api("GET", "/api/plugins")["plugins"]
    assert plugins[0]["dormant"] == False
    status = api("GET", "/api/status")
    assert status["dormant_plugins"] == []
    print("7. Back to active, dormant_plugins: [] - OK")

    print("\n=== DORMANT TOGGLE TEST PASSED ===")
except Exception as e:
    print(f"\nFAILED: {e}")
    import traceback
    traceback.print_exc()

proc.terminate()
proc.wait(timeout=5)
