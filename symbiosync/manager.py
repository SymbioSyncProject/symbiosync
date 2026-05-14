"""
Device Manager for SymbioSync.

Handles scanning, connecting, remembering devices, and dispatching requests.
The manager is device-agnostic: it works through the Device ABC. Plugin
classes register themselves and the manager routes based on scan_filter().
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Type

from bleak import BleakScanner

from .devices.base import Device, DeviceInfo
from .devices.colmi import ColmiDevice, set_db_path as set_colmi_db_path
from .devices.lovense import LovenseDevice
from .logger import Logger


# All registered device plugins. Add new plugins here.
DEVICE_PLUGINS: list[Type[Device]] = [
    LovenseDevice,
    ColmiDevice,
]


class DeviceManager:
    """Manages BLE device lifecycle: scan, connect, remember, dispatch."""

    def __init__(self, config_path: Path, logger: Logger):
        self.config_path = config_path
        self.logger = logger

        # Active device instances (address -> Device)
        self.devices: dict[str, Device] = {}

        # Partnership profile (human-editable relational context for skill generation)
        self.partnership_profile: str = ""

        # Optional Colmi ring SQLite override. If empty, the Colmi plugin keeps
        # its legacy/default path (or SYMBIOSYNC_COLMI_DB_PATH if set).
        self.colmi_db_path: str = ""

        # Remembered devices from config (address -> {name, type, enabled})
        self.remembered: dict[str, dict] = {}

        # Background tasks
        self._keepalive_task: asyncio.Task | None = None
        self._reconnect_task: asyncio.Task | None = None

        # Last scan results
        self._last_scan: list[DeviceInfo] = []
        self._scan_lock = asyncio.Lock()
        self._scanning = False

        # Addresses currently mid-connection (prevents duplicate concurrent attempts)
        self._connecting: set[str] = set()

        self._load_config()

    # ------------------------------------------------------------------
    # Config persistence
    # ------------------------------------------------------------------

    def _load_config(self):
        """Load remembered devices and dormant plugins from config file."""
        if self.config_path.exists():
            try:
                # PowerShell's default UTF-8 writing on some Windows installs can
                # include a BOM; accept it so hand-edited config files still load.
                data = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
                self.remembered = data.get("devices", {})
                self.dormant_plugins = set(data.get("dormant_plugins", []))
                self.partnership_profile = data.get("partnership_profile", "")
                self.colmi_db_path = data.get("colmi_db_path", "")
                set_colmi_db_path(self.colmi_db_path)
                self.logger.log("CONFIG", f"Loaded {len(self.remembered)} remembered device(s)")
                if self.colmi_db_path:
                    self.logger.log("CONFIG", f"Colmi DB path: {self.colmi_db_path}")
                if self.dormant_plugins:
                    self.logger.log("CONFIG", f"Dormant plugins: {', '.join(self.dormant_plugins)}")
            except Exception as e:
                self.logger.log("CONFIG", f"Failed to load config: {e}", level="warn")
                self.remembered = {}
                self.dormant_plugins = set()
                self.colmi_db_path = ""
        else:
            self.remembered = {}
            self.dormant_plugins = set()
            self.colmi_db_path = ""

    def _save_config(self):
        """Persist remembered devices and dormant plugins to config file."""
        data = {
            "devices": self.remembered,
            "dormant_plugins": sorted(self.dormant_plugins),
            "partnership_profile": self.partnership_profile,
            "colmi_db_path": self.colmi_db_path,
        }
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            self.logger.log("CONFIG", f"Failed to save config: {e}", level="error")

    def is_plugin_dormant(self, plugin_type: str) -> bool:
        """Check if a plugin type is dormant."""
        return plugin_type in self.dormant_plugins

    def get_active_plugins(self) -> list[Type[Device]]:
        """Return only non-dormant plugins."""
        return [p for p in DEVICE_PLUGINS if p.device_type_name() not in self.dormant_plugins]

    async def set_plugin_dormant(self, plugin_type: str, dormant: bool):
        """Set a plugin to dormant or active state.

        When going dormant: disconnect all devices of that type.
        When waking: the plugin becomes available for scan/connect again.
        """
        if dormant:
            self.dormant_plugins.add(plugin_type)
            # Disconnect all devices of this type
            to_disconnect = [
                addr for addr, dev in self.devices.items()
                if dev.device_type == plugin_type
            ]
            for addr in to_disconnect:
                await self.disconnect_device(addr)
            self.logger.log("PLUGIN", f"{plugin_type} -> dormant ({len(to_disconnect)} device(s) disconnected)")
        else:
            self.dormant_plugins.discard(plugin_type)
            self.logger.log("PLUGIN", f"{plugin_type} -> active")
        self._save_config()

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    async def scan(self, timeout: float = 10.0) -> list[DeviceInfo]:
        """Scan for BLE devices that match any registered plugin."""
        async with self._scan_lock:
            self._scanning = True
            self.logger.log("SCAN", f"Scanning for {timeout}s...")
            try:
                found = await BleakScanner.discover(timeout=timeout)
            except Exception as e:
                self.logger.log("SCAN_FAIL", str(e), level="error")
                self._scanning = False
                return []

            results = []
            active_plugins = self.get_active_plugins()
            for d in found:
                name = d.name or ""
                addr = d.address.upper()
                for plugin_cls in active_plugins:
                    if plugin_cls.scan_filter(name, addr):
                        rssi = getattr(d, "rssi", 0) or 0
                        info = DeviceInfo(
                            address=addr,
                            name=name,
                            device_type=plugin_cls.device_type_name(),
                            signal_strength=rssi,
                            extra={"ble_device": d},
                        )
                        results.append(info)
                        self.logger.log("SCAN", f"Found {name} ({addr}) RSSI={rssi}", device=name)
                        break

            self._last_scan = results
            self._scanning = False
            if not results:
                self.logger.log("SCAN", "No compatible devices found")
            else:
                self.logger.log("SCAN", f"Found {len(results)} device(s)")
            return results

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def _create_device(self, info: DeviceInfo) -> Device:
        """Instantiate the right plugin for a device."""
        if self.is_plugin_dormant(info.device_type):
            raise ValueError(f"Plugin '{info.device_type}' is dormant")
        for plugin_cls in DEVICE_PLUGINS:
            if plugin_cls.device_type_name() == info.device_type:
                device = plugin_cls(info)
                device.set_event_callback(self._device_event)
                device.set_disconnect_callback(self._device_disconnected)
                return device
        raise ValueError(f"No plugin for device type: {info.device_type}")

    def _device_event(self, device: Device, event_type: str, detail: str):
        """Callback: device emits a log event."""
        level = "error" if "FAIL" in event_type else "warn" if "WARN" in event_type else "info"
        self.logger.log(event_type, detail, device=device.name, level=level)

    def _device_disconnected(self, device: Device):
        """Callback: device BLE dropped unexpectedly."""
        self.logger.log("DROP", f"{device.name} ({device.address}) dropped", device=device.name, level="warn")

    async def connect_device(self, address: str, name: str = "", device_type: str = "",
                             ble_device=None) -> bool:
        """Connect to a specific device by address.

        Args:
            ble_device: Optional BLEDevice from a fresh scan. On Windows, passing
                the BLEDevice object (not just the address string) is critical for
                short-advertising-window devices like the Colmi ring.
        """
        address = address.upper()

        # Check if already connected
        if address in self.devices and self.devices[address].connected:
            return True

        # Guard against duplicate concurrent connection attempts
        if address in self._connecting:
            self.logger.log("CONNECT_SKIP", f"Already connecting to {address}, skipping duplicate", level="warn")
            return False

        self._connecting.add(address)

        # Determine device type from remembered list or scan results
        # Also carry the BLEDevice object from scan (needed for Windows BLE)
        scan_info = None
        if not device_type:
            if address in self.remembered:
                device_type = self.remembered[address].get("type", "")
                name = name or self.remembered[address].get("name", "")
            for info in self._last_scan:
                if info.address == address:
                    device_type = device_type or info.device_type
                    name = name or info.name
                    scan_info = info
                    break

        if not device_type:
            self.logger.log("CONNECT_FAIL", f"Unknown device type for {address}", level="error")
            return False

        extra = scan_info.extra if scan_info else {}
        # Prefer explicit ble_device over scan_info's (reconnect passes fresh scan result)
        if ble_device:
            extra["ble_device"] = ble_device
        info = DeviceInfo(address=address, name=name, device_type=device_type, extra=extra)
        device = self._create_device(info)
        self.devices[address] = device

        try:
            ok = await device.connect()
        finally:
            self._connecting.discard(address)

        if not ok:
            del self.devices[address]
        return ok

    async def disconnect_device(self, address: str):
        """Disconnect a specific device."""
        address = address.upper()
        device = self.devices.get(address)
        if device:
            await device.disconnect()
            del self.devices[address]

    async def disconnect_all(self):
        """Disconnect all devices."""
        for addr in list(self.devices.keys()):
            await self.disconnect_device(addr)

    # ------------------------------------------------------------------
    # Remember / forget
    # ------------------------------------------------------------------

    def remember_device(self, address: str, name: str, device_type: str, enabled: bool = True):
        """Add device to remembered list and persist."""
        address = address.upper()
        self.remembered[address] = {
            "name": name,
            "type": device_type,
            "enabled": enabled,
        }
        self._save_config()
        self.logger.log("REMEMBER", f"{name} ({address})", device=name)

    def forget_device(self, address: str):
        """Remove device from remembered list."""
        address = address.upper()
        if address in self.remembered:
            name = self.remembered[address].get("name", address)
            del self.remembered[address]
            self._save_config()
            self.logger.log("FORGET", f"{name} ({address})", device=name)

    def set_device_enabled(self, address: str, enabled: bool):
        """Toggle whether a remembered device should auto-connect."""
        address = address.upper()
        if address in self.remembered:
            self.remembered[address]["enabled"] = enabled
            self._save_config()

    # ------------------------------------------------------------------
    # Request dispatch
    # ------------------------------------------------------------------

    async def send_request(self, address: str, request: str, **kwargs) -> dict:
        """Send a request to a specific device."""
        address = address.upper()
        device = self.devices.get(address)
        if not device:
            return {"ok": False, "error": "device not found"}
        if not device.connected:
            return {"ok": False, "error": "device not connected"}
        return await device.send_request(request, **kwargs)

    async def send_request_all(self, request: str, **kwargs) -> dict:
        """Send a request to all connected devices."""
        results = {}
        for addr, device in self.devices.items():
            if device.connected:
                results[addr] = await device.send_request(request, **kwargs)
        return results

    async def stop_all(self) -> dict:
        """Emergency stop all devices."""
        return await self.send_request_all("stop")

    # ------------------------------------------------------------------
    # Background tasks
    # ------------------------------------------------------------------

    async def start(self):
        """Start background tasks (keepalive, reconnect, auto-connect)."""
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())
        self.logger.log("MANAGER", "Background tasks started")

    async def stop(self):
        """Stop all background tasks and disconnect all devices."""
        for task in [self._keepalive_task, self._reconnect_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await self.disconnect_all()
        self.logger.log("MANAGER", "Stopped")

    async def _keepalive_loop(self):
        """Send keepalive to all connected devices periodically."""
        while True:
            await asyncio.sleep(12.0)
            for device in list(self.devices.values()):
                if device.connected:
                    try:
                        await device.keepalive()
                    except Exception:
                        pass

    async def _reconnect_loop(self):
        """Periodically scan for dropped devices and remembered-but-not-connected devices.

        This replaces the old split between _reconnect_loop (dropped only) and
        _auto_connect (startup only). Now a single loop handles both:
        1. Devices that were connected and dropped (reconnect)
        2. Remembered devices that haven't connected this session yet (auto-connect)

        Uses name-based scan matching (like ferri_server) because after a BLE drop,
        devices may re-advertise on a different address or the OS cache may be stale.
        Always passes the fresh BLEDevice object to BleakClient to avoid Windows
        address-string reconnect failures.
        """
        await asyncio.sleep(2.0)  # Let server start before first scan
        while True:
            # --- What needs connecting? ---

            # 1. Dropped devices (were in self.devices, now disconnected)
            dropped = [
                (addr, dev) for addr, dev in self.devices.items()
                if not dev.connected
            ]
            dropped_addrs = {addr for addr, _ in dropped}

            # 2. Remembered devices not yet connected this session
            connected_addrs = {addr for addr, dev in self.devices.items() if dev.connected}
            remembered_not_connected = {
                addr: info for addr, info in self.remembered.items()
                if info.get("enabled", True) and addr not in connected_addrs
                # Also exclude devices we already have (even if disconnected, they're in dropped)
                and addr not in self.devices
            }

            if not dropped and not remembered_not_connected:
                await asyncio.sleep(10.0)
                continue

            target_count = len(dropped) + len(remembered_not_connected)
            self.logger.log("RECONNECT", f"Scanning for {target_count} device(s)...")

            try:
                found = await BleakScanner.discover(timeout=5.0)
            except Exception as e:
                self.logger.log("RECONNECT", f"Scan error: {e}", level="warn")
                await asyncio.sleep(10.0)
                continue

            found_by_name = {d.name: d for d in found if d.name}
            found_by_addr = {d.address.upper(): d for d in found}

            # --- Reconnect dropped devices (match by name, like ferri_server) ---
            for addr, device in dropped:
                discovered = found_by_name.get(device.name) or found_by_addr.get(addr)
                if discovered:
                    self.logger.log("RECONNECT", f"Found {device.name}, reconnecting...")
                    new_info = DeviceInfo(
                        address=discovered.address.upper(),
                        name=device.name,
                        device_type=device.device_type,
                        extra={"ble_device": discovered},
                    )
                    new_device = self._create_device(new_info)
                    ok = await new_device.connect()
                    if ok:
                        if addr in self.devices:
                            del self.devices[addr]
                        self.devices[new_info.address] = new_device
                        self.logger.log("RECONNECT", f"Reconnected {device.name}")

            # --- Auto-connect remembered devices not yet in session ---
            for addr, info in remembered_not_connected.items():
                name = info.get("name", "")
                dtype = info.get("type", "")
                # Try name match first, then address match
                discovered = found_by_name.get(name) or found_by_addr.get(addr)
                if discovered:
                    self.logger.log("AUTOCONNECT", f"Found remembered {name}, connecting...")
                    await self.connect_device(
                        discovered.address.upper(),
                        discovered.name or name,
                        dtype,
                        ble_device=discovered,
                    )

            # If any devices are now connecting/connected, give BLE time to stabilise
            # before the next scan cycle — prevents hammering a device that just connected.
            any_active = any(
                addr in self._connecting or (addr in self.devices and self.devices[addr].connected)
                for addr in list(dropped_addrs) + list(remembered_not_connected.keys())
            )
            await asyncio.sleep(30.0 if any_active else 10.0)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Full system status for API."""
        devices = {}
        for addr, device in self.devices.items():
            devices[addr] = device.to_dict()

        remembered = {}
        for addr, info in self.remembered.items():
            remembered[addr] = {
                **info,
                "connected": addr in self.devices and self.devices[addr].connected,
            }

        return {
            "devices": devices,
            "remembered": remembered,
            "connected_count": sum(1 for d in self.devices.values() if d.connected),
            "scanning": self._scanning,
            "dormant_plugins": sorted(self.dormant_plugins),
            "last_scan": [
                {
                    "address": i.address,
                    "name": i.name,
                    "type": i.device_type,
                    "rssi": i.signal_strength,
                }
                for i in self._last_scan
            ],
        }
