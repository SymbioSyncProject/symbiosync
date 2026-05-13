"""Quick import test - does the module load on this Python?"""
import sys
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")

try:
    import bleak
    bv = getattr(bleak, "__version__", "installed (no __version__)")
    print(f"bleak: {bv}")
except ImportError as e:
    print(f"bleak: MISSING ({e})")

try:
    import fastapi
    print(f"fastapi: {fastapi.__version__}")
except ImportError as e:
    print(f"fastapi: MISSING ({e})")

try:
    import uvicorn
    print(f"uvicorn: {uvicorn.__version__}")
except ImportError as e:
    print(f"uvicorn: MISSING ({e})")

try:
    from symbiosync import __version__
    print(f"symbiosync: {__version__}")
except ImportError as e:
    print(f"symbiosync: IMPORT FAILED ({e})")

try:
    from symbiosync.devices.base import Device, DeviceCapability
    print(f"devices.base: OK ({len(DeviceCapability)} capabilities)")
except Exception as e:
    print(f"devices.base: FAILED ({e})")

try:
    from symbiosync.devices.lovense import LovenseDevice, DEVICE_CAPABILITIES
    print(f"devices.lovense: OK ({len(DEVICE_CAPABILITIES)} device types)")
except Exception as e:
    print(f"devices.lovense: FAILED ({e})")

try:
    from symbiosync.logger import Logger
    print(f"logger: OK")
except Exception as e:
    print(f"logger: FAILED ({e})")

try:
    from symbiosync.manager import DeviceManager
    print(f"manager: OK")
except Exception as e:
    print(f"manager: FAILED ({e})")

try:
    from symbiosync.server import app
    print(f"server: OK (app={app.title})")
except Exception as e:
    print(f"server: FAILED ({e})")

print("\nAll imports passed!" if "FAILED" not in "" else "\nDone.")
