"""Test the /api/plugins endpoint returns valid plugin data."""
import subprocess, sys, time, urllib.request, json

PORT = 8091
proc = subprocess.Popen(
    [sys.executable, "-m", "symbiosync", "--no-browser", "--host", "0.0.0.0", "--port", str(PORT)],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
)

time.sleep(3)

try:
    resp = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/plugins", timeout=3)
    data = json.loads(resp.read().decode())
    plugins = data.get("plugins", [])
    print(f"Plugins: {len(plugins)}")
    for p in plugins:
        print(f"\n  Type: {p['type']}")
        print(f"  Label: {p['label']}")
        print(f"  Description: {p['description']}")
        print(f"  HTML: {len(p.get('html', ''))} chars")
        print(f"  JS: {len(p.get('js', ''))} chars")
        print(f"  Enabled: {p.get('enabled')}")

        # Verify HTML has key elements
        html = p.get("html", "")
        if p["type"] == "lovense":
            checks = ["lvs-vibrate-slider", "lvs-device-selector", "lvs-ambient-slider",
                       "STOP ALL LOVENSE", "pattern-btn"]
            for check in checks:
                status = "OK" if check in html else "MISSING"
                print(f"    HTML check '{check}': {status}")

            js = p.get("js", "")
            js_checks = ["lvsSendVibrate", "lvsStopAmbient", "lvsUpdateSelector",
                          "_pluginStatusHooks"]
            for check in js_checks:
                status = "OK" if check in js else "MISSING"
                print(f"    JS check '{check}': {status}")

    print("\n=== PLUGIN API TEST PASSED ===")
except Exception as e:
    print(f"FAILED: {e}")

proc.terminate()
proc.wait(timeout=5)
