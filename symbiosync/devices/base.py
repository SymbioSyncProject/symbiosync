"""
Base device interface for SymbioSync.

Every BLE device plugin implements this ABC. The manager treats all devices
uniformly through this interface. Plugin authors only need to implement
the abstract methods.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceCapability(str, Enum):
    """What a device can do. UI uses these to show relevant controls."""
    # Motor / actuation
    VIBRATE = "vibrate"
    VIBRATE_MULTI = "vibrate_multi"   # multiple motors (Vibrate1, Vibrate2...)
    ROTATE = "rotate"                 # rotation motor (Nora, Ridge)
    AIR = "air"                       # air pump inflate/deflate (Max series, 0-5)
    THRUST = "thrust"                 # thrusting mechanism (Gravity, Solace, Vulse, Spinel)
    SUCK = "suck"                     # suction (Tenera 2)
    FINGER = "finger"                 # fingering mechanism (Flexer)
    # Sensors (read-only)
    DEPTH = "depth"                   # depth sensor (Calor)
    ACCELEROMETER = "accelerometer"   # 3-axis accel stream (Nora, Max)
    BATTERY = "battery"
    # Settings
    LED = "led"                       # status LED toggle
    POWER_OFF = "power_off"           # remote power-off
    # Biometric (non-Lovense, e.g. Colmi ring)
    HEART_RATE = "heart_rate"
    SPO2 = "spo2"
    STEPS = "steps"


@dataclass
class DeviceInfo:
    """Static info about a discovered or remembered device."""
    address: str
    name: str
    device_type: str              # "lovense", "colmi", etc.
    signal_strength: int = 0      # RSSI from scan, 0 if unknown
    extra: dict = field(default_factory=dict)  # device-specific metadata


class Device(ABC):
    """Abstract base for all BLE device plugins.

    Lifecycle:
        1. Manager creates device from DeviceInfo (or from saved config)
        2. connect() establishes BLE link
        3. send_command() for control, get_status() for state
        4. keepalive() called periodically by manager
        5. disconnect() on shutdown or user request
        6. on_disconnect callback fires if BLE drops unexpectedly
    """

    def __init__(self, info: DeviceInfo):
        self.info = info
        self.address: str = info.address
        self.name: str = info.name
        self.device_type: str = info.device_type
        self.connected: bool = False
        self._on_event = None      # callback: (device, event_type, detail) -> None
        self._on_disconnect = None  # callback: (device) -> None

    def set_event_callback(self, callback):
        """Manager sets this so device can emit log events."""
        self._on_event = callback

    def set_disconnect_callback(self, callback):
        """Manager sets this to be notified of unexpected disconnects."""
        self._on_disconnect = callback

    def emit_event(self, event_type: str, detail: str = ""):
        """Emit a log event through the manager's logging system."""
        if self._on_event:
            self._on_event(self, event_type, detail)

    @abstractmethod
    async def connect(self) -> bool:
        """Establish BLE connection. Returns True on success."""
        ...

    @abstractmethod
    async def disconnect(self):
        """Gracefully close BLE connection."""
        ...

    @abstractmethod
    async def send_command(self, command: str, **kwargs) -> dict:
        """Send a command to the device.

        Args:
            command: Command name (e.g. "vibrate", "rotate", "battery")
            **kwargs: Command-specific args (e.g. intensity=5, duration=3.0)

        Returns:
            dict with at least {"ok": bool, ...}
        """
        ...

    @abstractmethod
    def get_capabilities(self) -> list[DeviceCapability]:
        """Return list of capabilities this device supports."""
        ...

    @abstractmethod
    def get_status(self) -> dict:
        """Return current device state (battery, uptime, etc.)."""
        ...

    @abstractmethod
    async def keepalive(self):
        """Called periodically by the manager to maintain BLE link."""
        ...

    @classmethod
    @abstractmethod
    def scan_filter(cls, name: str, address: str) -> bool:
        """Return True if this device name/address matches this plugin.

        Used during BLE scan to determine which plugin handles a device.
        Example: LovenseDevice.scan_filter("LVS-Ferri", "AA:BB:...") -> True
        """
        ...

    @classmethod
    @abstractmethod
    def device_type_name(cls) -> str:
        """Return the device type string (e.g. 'lovense', 'colmi')."""
        ...

    # ------------------------------------------------------------------
    # UI contribution: each plugin provides its own tab
    # ------------------------------------------------------------------

    @classmethod
    def tab_label(cls) -> str:
        """Display name for this plugin's tab in the UI.

        Override to customize. Defaults to the device_type_name() capitalized.
        """
        return cls.device_type_name().capitalize()

    @classmethod
    def tab_description(cls) -> str:
        """Short description shown in the Plugins management tab."""
        return f"{cls.tab_label()} device control"

    @classmethod
    def control_html(cls) -> str:
        """Return the HTML fragment for this plugin's control tab.

        This is injected into the UI as a tab panel. It should contain
        cards, sliders, buttons, etc. for controlling this device type.
        Use plugin-namespaced IDs (e.g. 'lovense-vibrate-slider') to
        avoid collisions with other plugins.

        Return empty string for no control tab (sensor-only plugins).
        """
        return ""

    @classmethod
    def control_js(cls) -> str:
        """Return the JavaScript for this plugin's control tab.

        Functions defined here are available globally. Use plugin-namespaced
        function names (e.g. 'lovenseSendVibrate()') to avoid collisions.

        Return empty string if no JS needed.
        """
        return ""

    @classmethod
    @abstractmethod
    def skill_section(cls, devices: list[dict], base_url: str) -> str:
        """Return the plugin-specific section of the companion skill file.

        This is where each plugin defines:
        - What the devices are and what they can do
        - Command reference with examples
        - Etiquette / protocol for interacting with these devices
        - Intensity scales, patterns, or any device-specific semantics

        Args:
            devices: List of device status dicts for connected devices
                     of this plugin type (from to_dict())
            base_url: The SymbioSync server URL (e.g. "http://192.168.1.14:8080")

        Returns:
            Markdown string to be included in the generated SKILL.md
        """
        ...

    def to_dict(self) -> dict:
        """Serialize device state for API responses."""
        return {
            "address": self.address,
            "name": self.name,
            "device_type": self.device_type,
            "connected": self.connected,
            "capabilities": [c.value for c in self.get_capabilities()],
            "status": self.get_status(),
        }
