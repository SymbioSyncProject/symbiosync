"""
Lovense BLE device plugin for SymbioSync.

Implements direct BLE control of Lovense toys using the ASCII protocol
extracted from APK static analysis + community protocol inference.
No server connections, no telemetry, no 62 permissions.

Protocol sources:
    - APK static analysis (BaseToyRequestBean, ToyRequestBean), March 2026
    - lovesense-py readthedocs protocol docs
    - lumpenspace/goontech.md community gist
    - Intiface Central BLE capture log
    - ferri_server.py field testing (Phi + Audre, March 2026)

BLE details:
    Advertise name: "LVS-*" (e.g. LVS-Ferri02, LVS-Edge36)
    Service UUIDs by generation:
        gen-1:  0000fff0-0000-1000-8000-00805f9b34fb (tx=fff1, rx=fff2)
        gen-2:  6e400001-b5a3-f393-e0a9-e50e24dcca9e (Nordic UART)
        XY30+:  58300001-0023-4bd4-bbd5-a6920e4c5653 (tx=..002, rx=..003)
    We try XY30 first (most current), then gen-2, then gen-1.

    Requests: ASCII strings terminated with semicolon (e.g. "Vibrate:5;")
    Write Without Response (response=False) is MANDATORY. Write Request
    blocks on ACK, fills L2CAP queue under RF attenuation (body occlusion),
    triggers microcontroller watchdog reset -> disconnect.
"""

import asyncio
import time
from typing import Any

from bleak import BleakClient
from .base import Device, DeviceCapability, DeviceInfo


# --------------------------------------------------------------------------
# BLE UUIDs by generation (tried in order: newest first)
# --------------------------------------------------------------------------

BLE_PROFILES = [
    # XY30 family (most current toys, 2022+)
    {
        "name": "XY30",
        "service": "58300001-0023-4bd4-bbd5-a6920e4c5653",
        "tx":      "58300002-0023-4bd4-bbd5-a6920e4c5653",
        "rx":      "58300003-0023-4bd4-bbd5-a6920e4c5653",
    },
    # Gen-2 Nordic UART
    {
        "name": "Nordic",
        "service": "6e400001-b5a3-f393-e0a9-e50e24dcca9e",
        "tx":      "6e400002-b5a3-f393-e0a9-e50e24dcca9e",
        "rx":      "6e400003-b5a3-f393-e0a9-e50e24dcca9e",
    },
    # Gen-1
    {
        "name": "Gen1",
        "service": "0000fff0-0000-1000-8000-00805f9b34fb",
        "tx":      "0000fff1-0000-1000-8000-00805f9b34fb",
        "rx":      "0000fff2-0000-1000-8000-00805f9b34fb",
    },
]

# Keepalive interval (seconds)
KEEPALIVE_INTERVAL = 12.0

# --------------------------------------------------------------------------
# Vibration patterns (step arrays, each 0-20)
# --------------------------------------------------------------------------

PATTERNS = {
    "pulse":     [5, 0, 5, 0, 5, 0, 5, 0],
    "wave":      [2, 5, 8, 12, 15, 12, 8, 5],
    "escalate":  [3, 6, 9, 12, 15, 18, 20, 20],
    "heartbeat": [15, 0, 10, 0, 15, 0, 0, 0],
    "tease":     [3, 0, 5, 0, 8, 0, 3, 0],
    "surge":     [0, 4, 8, 14, 20, 14, 8, 4],
    "staccato":  [12, 0, 12, 0, 12, 0, 12, 0],
}

# --------------------------------------------------------------------------
# DeviceType response letter -> model name mapping
# From APK static analysis + lovesense-py + community docs
# --------------------------------------------------------------------------

MODEL_LETTER_MAP = {
    "A": "lush",
    "B": "max",
    "C": "nora",
    "D": "hush",       # unconfirmed letter, inferred
    "L": "ambi",       # unconfirmed
    "J": "domi",       # unconfirmed
    "O": "osci",       # unconfirmed
    "S": "edge",       # unconfirmed
}

# --------------------------------------------------------------------------
# Device capabilities by model
#
# Sources: APK BaseToyRequestBean, product pages, community testing.
# When model is unknown, we default to vibrate + battery and let the user
# discover additional capabilities via the "raw" request.
# --------------------------------------------------------------------------

_V = DeviceCapability.VIBRATE
_VM = DeviceCapability.VIBRATE_MULTI
_R = DeviceCapability.ROTATE
_A = DeviceCapability.AIR
_T = DeviceCapability.THRUST
_S = DeviceCapability.SUCK
_F = DeviceCapability.FINGER
_D = DeviceCapability.DEPTH
_ACC = DeviceCapability.ACCELEROMETER
_BAT = DeviceCapability.BATTERY
_LED = DeviceCapability.LED
_PWR = DeviceCapability.POWER_OFF

# All Lovense devices have battery + power-off
_COMMON = [_BAT, _PWR]

DEVICE_CAPABILITIES = {
    # --- Vibrate-only (simple motor) ---
    "lush":      [_V] + _COMMON,                          # Lush 1/2/3/4 (G-spot egg)
    "lush mini": [_V] + _COMMON,                          # Lush Mini
    "lush anal": [_V] + _COMMON,                          # Lush Anal
    "hush":      [_V] + _COMMON,                          # Hush 1/2 (butt plug)
    "ambi":      [_V] + _COMMON,                          # Ambi (bullet)
    "ferri":     [_V] + _COMMON,                          # Ferri (wearable panty)
    "exomoon":   [_V] + _COMMON,                          # Exomoon (lipstick bullet)
    "diamo":     [_V] + _COMMON,                          # Diamo (cock ring)
    "gemini":    [_V] + _COMMON,                          # Gemini (nipple clamps)
    "mission":   [_V] + _COMMON,                          # Mission 2 (vibrating dildo)

    # --- Multi-motor (Vibrate1, Vibrate2, ...) ---
    "edge":      [_V, _VM] + _COMMON,                     # Edge 1/2 (prostate, 2 motors)
    "dolce":     [_V, _VM] + _COMMON,                     # Dolce (dual vibrator, 2 motors)
    "hyphy":     [_V, _VM] + _COMMON,                     # Hyphy (dual-end high freq)

    # --- Rotation ---
    "nora":      [_V, _R, _ACC] + _COMMON,                # Nora (rabbit, rotating head)
    "ridge":     [_V, _R] + _COMMON,                      # Ridge (anal beads, rotating)

    # --- Oscillation (treated as vibrate variant) ---
    "osci":      [_V] + _COMMON,                          # Osci 3 (G-spot oscillator)

    # --- Air pump (male) ---
    "max":       [_V, _A, _ACC] + _COMMON,                # Max 1/2 (male masturbator)
    "gush":      [_V, _A] + _COMMON,                      # Gush 1/2 (glans massager)

    # --- Thrusting ---
    "gravity":   [_V, _T] + _COMMON,                      # Gravity (thrusting dildo)
    "solace":    [_V, _T] + _COMMON,                      # Solace (male thrusting)
    "solace pro":[_V, _T] + _COMMON,                      # Solace Pro (premium thrusting)
    "vulse":     [_V, _T] + _COMMON,                      # Vulse (thrusting G-spot egg)
    "spinel":    [_V, _T] + _COMMON,                      # Spinel (thrusting + heating dildo)
    "sexmachine":[_V, _T] + _COMMON,                      # Lovense Sex Machine

    # --- Suction ---
    "tenera":    [_V, _S] + _COMMON,                      # Tenera 2 (clitoral suction)

    # --- Fingering ---
    "flexer":    [_V, _F] + _COMMON,                      # Flexer (insertable dual panty)

    # --- Depth sensor ---
    "calor":     [_V, _VM, _D] + _COMMON,                 # Calor (pocket pussy + depth)

    # --- Multi-purpose ---
    "lapis":     [_V, _VM] + _COMMON,                     # Lapis (strapless strap-on)
    "domi":      [_V, _LED] + _COMMON,                    # Domi 2 (wand, has ring LEDs)

    # --- Default (unknown model: vibrate + battery, user can raw request the rest) ---
    "default":   [_V] + _COMMON,
}


class LovenseDevice(Device):
    """Direct BLE control of a Lovense toy.

    Supports the full ASCII request vocabulary from APK static analysis:
        Vibrate, Vibrate1/2/3, Rotate, RotateChange, Air:Level/In/Out,
        Thrusting, Suck, Fingering, Depth, Battery, DeviceType, Status,
        PowerOff, StartMove/StopMove, Light, AutoSwith, GetLevel/SetLevel,
        Pat/SetPat, and raw passthrough for undocumented requests.
    """

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self._client: BleakClient | None = None
        self._tx_uuid: str = ""
        self._rx_uuid: str = ""
        self._ble_profile: str = ""
        self._connected_at: float = 0.0
        self._last_request_at: float = 0.0
        self._last_keepalive: float = 0.0
        self._battery: int = -1
        self._model: str = ""
        self._model_letter: str = ""
        self._firmware: str = ""
        self._bt_addr: str = ""
        self._pattern_task: asyncio.Task | None = None
        self._ambient_task: asyncio.Task | None = None
        self._ambient_level: int = 0
        self._current_intensity: int = 0
        self._air_level: int = 0
        self._thrust_level: int = 0
        self._rotate_level: int = 0
        self._accel_streaming: bool = False

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    @classmethod
    def scan_filter(cls, name: str, address: str) -> bool:
        return name is not None and name.upper().startswith("LVS-")

    @classmethod
    def device_type_name(cls) -> str:
        return "lovense"

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def _discover_ble_profile(self, client: BleakClient) -> bool:
        """Try each BLE profile until we find one the device supports."""
        services = client.services
        for profile in BLE_PROFILES:
            for svc in services:
                if svc.uuid.lower() == profile["service"].lower():
                    # Verify TX characteristic exists
                    for char in svc.characteristics:
                        if char.uuid.lower() == profile["tx"].lower():
                            self._tx_uuid = profile["tx"]
                            self._rx_uuid = profile["rx"]
                            self._ble_profile = profile["name"]
                            return True
        return False

    async def connect(self) -> bool:
        self.emit_event("CONNECTING", self.address)
        try:
            ble_device = self.info.extra.get("ble_device", self.address)
            client = BleakClient(
                ble_device,
                disconnected_callback=self._handle_disconnect,
            )
            await client.connect(timeout=15.0)
            self._client = client
            self._connected_at = time.time()
            self._last_request_at = time.time()

            # Negotiate MTU upward (reduces fragmentation under RF noise)
            try:
                await client.mtu_exchange(256)
                self.emit_event("MTU", f"negotiated {client.mtu_size}")
            except Exception:
                pass

            # Discover which BLE profile this device uses
            if not await self._discover_ble_profile(client):
                self.emit_event("CONNECT_FAIL", "No compatible BLE service found")
                await client.disconnect()
                self._client = None
                return False

            self.emit_event("BLE", f"Using {self._ble_profile} profile")

            # Subscribe to RX notifications (CCCD write confirms link to firmware)
            try:
                await client.start_notify(self._rx_uuid, self._rx_handler)
            except Exception as e:
                self.emit_event("WARN", f"RX subscribe failed: {e}")

            # Initialization handshake
            self.connected = True
            await asyncio.sleep(0.3)
            await self._write("DeviceType;", request="device_type")
            await asyncio.sleep(0.3)
            await self._write("Battery;", request="battery")
            await asyncio.sleep(0.2)
            await self._write("AutoSwith:Off:Off;", request="auto_switch")  # disable auto-standby
            await asyncio.sleep(0.2)
            await self._write("Vibrate:0;", request="connect_zero")           # confirm motor at zero

            self.emit_event("CONNECTED", f"{self.address} ({self.name})")
            return True

        except Exception as e:
            self.emit_event("CONNECT_FAIL", str(e))
            self.connected = False
            self._client = None
            return False

    async def disconnect(self):
        await self._cancel_tasks()

        if self._accel_streaming:
            try:
                await self._write("StopMove:1;", request="disconnect_stop_accel")
            except Exception:
                pass
            self._accel_streaming = False

        if self._client and self._client.is_connected:
            try:
                await self._soft_stop()
                await self._client.disconnect()
            except Exception:
                pass
        self.connected = False
        self._client = None
        self.emit_event("DISCONNECTED", self.address)

    def _handle_disconnect(self, client: BleakClient):
        """Bleak callback when BLE drops unexpectedly."""
        uptime = round(time.time() - self._connected_at, 1) if self._connected_at else "?"
        idle = round(time.time() - self._last_request_at, 1) if self._last_request_at else "?"
        self.emit_event("DISCONNECT", f"uptime={uptime}s idle={idle}s")
        self.connected = False
        self._client = None
        if self._on_disconnect:
            self._on_disconnect(self)

    # ------------------------------------------------------------------
    # BLE I/O
    # ------------------------------------------------------------------

    def _write_result(self, *, request: str, wire_text: str, ok: bool,
                      stage: str | None = None, error: str | None = None,
                      **extra) -> dict:
        """Describe exactly what a Lovense write result proves.

        Lovense control uses BLE write-without-response. A successful write means
        the local BLE transport accepted the request. It is not hardware
        acknowledgement and not proof of physical actuation.
        """
        result_stage = stage or ("transport_write_accepted" if ok else "transport_write_failed")
        attempted_transport = result_stage not in {"device_not_connected", "api_rejected"}
        result = {
            "ok": bool(ok),
            "stage": result_stage,
            "request": request,
            "protocol_request": wire_text.strip(),
            "transport": "ble_write_without_response" if attempted_transport else None,
            "hardware_ack": None,
            "observed_effect": None,
        }
        if not attempted_transport:
            result["intended_transport"] = "ble_write_without_response"
        if ok:
            result["truth_note"] = (
                "BLE write-without-response completed; device did not acknowledge this request."
            )
        elif result_stage == "device_not_connected":
            result["truth_note"] = (
                "Device was not connected; no BLE write was attempted and no hardware effect is known."
            )
        else:
            result["truth_note"] = (
                "BLE write-without-response failed or device was unavailable; no hardware effect is known."
            )
            if error:
                result["error"] = error
        result.update(extra)
        return result

    def _local_task_result(self, *, request: str, task: str, **extra) -> dict:
        """Result for requests that start a local task rather than one hardware write."""
        result = {
            "ok": True,
            "stage": "local_task_scheduled",
            "request": request,
            "local_task": task,
            "transport": None,
            "intended_transport": "ble_write_without_response",
            "hardware_ack": None,
            "observed_effect": None,
            "truth_note": (
                "Local task scheduled; future BLE writes are best-effort write-without-response operations and may fail after this API response."
            ),
        }
        result.update(extra)
        return result

    async def _write(self, wire_text: str, request: str | None = None) -> dict:
        """Send ASCII protocol request and return a staged truth result.

        Write Without Response prevents queue exhaustion, but it also means a
        successful call only proves local transport acceptance.
        """
        request_name = request or wire_text.split(":", 1)[0].rstrip(";").lower()
        if not self.connected or self._client is None:
            return self._write_result(
                request=request_name,
                wire_text=wire_text,
                ok=False,
                stage="device_not_connected",
                error="not connected",
            )
        try:
            await self._client.write_gatt_char(self._tx_uuid, wire_text.encode(), response=False)
            self._last_request_at = time.time()
            self.emit_event("TX", wire_text.strip())
            return self._write_result(request=request_name, wire_text=wire_text, ok=True)
        except Exception as e:
            idle = round(time.time() - self._last_request_at, 1) if self._last_request_at else "?"
            uptime = round(time.time() - self._connected_at, 1) if self._connected_at else "?"
            self.emit_event("WRITE_FAIL", f"uptime={uptime}s idle={idle}s err={e}")
            self.connected = False
            if self._on_disconnect:
                self._on_disconnect(self)
            return self._write_result(
                request=request_name,
                wire_text=wire_text,
                ok=False,
                stage="transport_write_failed",
                error=str(e),
            )
    def _rx_handler(self, sender, data: bytearray):
        """Parse notifications from device."""
        msg = data.decode("utf-8", errors="replace").strip()

        if msg == "2;":
            # Keepalive response (Status:1 -> "2;")
            self.emit_event("RX", "keepalive OK")
        elif msg == "OK;":
            self.emit_event("RX", "OK")
        elif msg.startswith("G") and len(msg) > 6:
            # Accelerometer data: "GEF008312ED00;"
            self._parse_accel(msg)
        elif msg.rstrip(";").isdigit():
            # Battery response: "85;"
            self._battery = int(msg.rstrip(";"))
            self.emit_event("RX", f"Battery:{self._battery}%")
        elif ":" in msg:
            # DeviceType or settings response
            self._parse_info_response(msg)
        else:
            self.emit_event("RX", msg)

    def _parse_info_response(self, msg: str):
        """Parse colon-delimited info responses."""
        parts = msg.rstrip(";").split(":")

        # DeviceType response: "C:11:0082059AD3BD;"
        if len(parts) >= 2 and len(parts[0]) <= 2:
            self._model_letter = parts[0]
            self._firmware = parts[1] if len(parts) > 1 else ""
            self._bt_addr = parts[2] if len(parts) > 2 else ""
            # Map letter to model name
            mapped = MODEL_LETTER_MAP.get(self._model_letter, "")
            if mapped:
                self._model = mapped
            else:
                # Try to infer from advertised name: "LVS-Ferri02" -> "ferri"
                name_part = self.name.upper().replace("LVS-", "")
                # Strip trailing digits (firmware version in name)
                model_guess = "".join(c for c in name_part if not c.isdigit()).lower()
                if model_guess:
                    self._model = model_guess
            self.emit_event("RX", f"DeviceType: model={self._model or self._model_letter} fw={self._firmware}")
        elif parts[0].lower() in ("autoswith", "light", "alight", "level"):
            self.emit_event("RX", msg)
        else:
            self.emit_event("RX", msg)

    def _parse_accel(self, msg: str):
        """Parse accelerometer data: 'GEF008312ED00;'"""
        try:
            payload = msg.rstrip(";")[1:]  # strip leading 'G'
            vals = [int(payload[i:i+4], 16) for i in range(0, len(payload), 4)]
            self.emit_event("ACCEL", f"x={vals[0]} y={vals[1]} z={vals[2]}")
        except Exception:
            self.emit_event("RX", msg)

    # ------------------------------------------------------------------
    # Motor control helpers
    # ------------------------------------------------------------------

    async def _soft_stop(self):
        """Fade to zero. Prevents BLE disconnect on sharp motor state change."""
        for level in [2, 1, 0]:
            result = await self._write(f"Vibrate:{level};", request="soft_stop")
            if result.get("ok"):
                self._current_intensity = level
            if level > 0:
                await asyncio.sleep(0.3)
        self._current_intensity = 0
        self._air_level = 0
        self._thrust_level = 0
        self._rotate_level = 0

    async def _cancel_tasks(self):
        """Cancel any running pattern or ambient tasks."""
        if self._pattern_task and not self._pattern_task.done():
            self._pattern_task.cancel()
            self._pattern_task = None
        if self._ambient_task and not self._ambient_task.done():
            self._ambient_task.cancel()
            self._ambient_task = None
            self._ambient_level = 0

    async def _run_pattern(self, pattern_name: str, duration: float):
        """Execute a named vibration pattern."""
        steps = PATTERNS[pattern_name]
        step_dur = duration / len(steps)
        try:
            for step in steps:
                result = await self._write(f"Vibrate:{step};", request="pattern_step")
                if result.get("ok"):
                    self._current_intensity = step
                await asyncio.sleep(step_dur)
            await self._soft_stop()
        except asyncio.CancelledError:
            await self._soft_stop()

    async def _run_ambient(self, level: int):
        """Re-assert vibrate every 5s to prevent device timeout."""
        try:
            while True:
                result = await self._write(f"Vibrate:{level};", request="ambient_step")
                if result.get("ok"):
                    self._current_intensity = level
                await asyncio.sleep(5.0)
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Device interface: send_request()
    # ------------------------------------------------------------------

    async def send_request(self, request: str, **kwargs) -> dict:
        if not self.connected:
            return {
                "ok": False,
                "stage": "device_not_connected",
                "request": request,
                "error": "not connected",
                "hardware_ack": None,
                "observed_effect": None,
            }

        request = request.lower()

        # --- Vibration ---
        if request == "vibrate":
            await self._cancel_tasks()
            intensity = max(0, min(20, int(kwargs.get("intensity", 0))))
            duration = float(kwargs.get("duration", 0))
            motor = kwargs.get("motor", None)

            if motor is not None:
                wire_text = f"Vibrate{motor}:{intensity};"
            else:
                wire_text = f"Vibrate:{intensity};"

            result = await self._write(wire_text, request="vibrate")
            if result.get("ok"):
                self._current_intensity = intensity

            if result.get("ok") and duration > 0:
                async def _timed():
                    await asyncio.sleep(duration)
                    await self._soft_stop()
                self._pattern_task = asyncio.create_task(_timed())

            result.update({"intensity": intensity, "duration": duration})
            return result

        # --- Rotation (Nora, Ridge) ---
        elif request == "rotate":
            intensity = max(0, min(20, int(kwargs.get("intensity", 0))))
            result = await self._write(f"Rotate:{intensity};", request="rotate")
            if result.get("ok"):
                self._rotate_level = intensity
            result.update({"intensity": intensity})
            return result

        elif request == "rotate_change":
            return await self._write("RotateChange;", request="rotate_change")

        # --- Air pump (Max series, 0-5) ---
        elif request == "air_level":
            level = max(0, min(5, int(kwargs.get("level", 0))))
            result = await self._write(f"Air:Level:{level};", request="air_level")
            if result.get("ok"):
                self._air_level = level
            result.update({"air_level": self._air_level, "requested_air_level": level})
            return result

        elif request == "air_in":
            delta = max(1, min(5, int(kwargs.get("delta", 1))))
            result = await self._write(f"Air:In:{delta};", request="air_in")
            if result.get("ok"):
                self._air_level = min(5, self._air_level + delta)
            result.update({"air_level": self._air_level, "delta": delta})
            return result

        elif request == "air_out":
            delta = max(1, min(5, int(kwargs.get("delta", 1))))
            result = await self._write(f"Air:Out:{delta};", request="air_out")
            if result.get("ok"):
                self._air_level = max(0, self._air_level - delta)
            result.update({"air_level": self._air_level, "delta": delta})
            return result

        # --- Thrusting (Gravity, Solace, Vulse, Spinel, Sex Machine) ---
        elif request == "thrust":
            intensity = max(0, min(20, int(kwargs.get("intensity", 0))))
            result = await self._write(f"Thrusting:{intensity};", request="thrust")
            if result.get("ok"):
                self._thrust_level = intensity
            result.update({"intensity": intensity})
            return result

        # --- Suction (Tenera 2) ---
        elif request == "suck":
            intensity = max(0, min(20, int(kwargs.get("intensity", 0))))
            result = await self._write(f"Suck:{intensity};", request="suck")
            result.update({"intensity": intensity})
            return result

        # --- Fingering (Flexer) ---
        elif request == "finger":
            intensity = max(0, min(20, int(kwargs.get("intensity", 0))))
            result = await self._write(f"Fingering:{intensity};", request="finger")
            result.update({"intensity": intensity})
            return result

        # --- Patterns ---
        elif request == "pattern":
            await self._cancel_tasks()
            pattern_name = kwargs.get("name", "pulse")
            duration = float(kwargs.get("duration", 10.0))
            if pattern_name not in PATTERNS:
                return {"ok": False, "stage": "api_rejected",
                        "request": request,
                        "transport": None,
                        "intended_transport": "ble_write_without_response",
                        "hardware_ack": None,
                        "observed_effect": None,
                        "error": f"unknown pattern: {pattern_name}",
                        "available": list(PATTERNS.keys())}
            self._pattern_task = asyncio.create_task(self._run_pattern(pattern_name, duration))
            return self._local_task_result(
                request="pattern",
                task="lovense_pattern",
                pattern=pattern_name,
                duration=duration,
            )

        # --- Ambient ---
        elif request == "ambient":
            await self._cancel_tasks()
            level = max(0, min(20, int(kwargs.get("level", 0))))
            self._ambient_level = level
            if level > 0:
                self._ambient_task = asyncio.create_task(self._run_ambient(level))
                return self._local_task_result(
                    request="ambient",
                    task="lovense_ambient",
                    ambient_level=level,
                )
            result = await self._write("Vibrate:0;", request="ambient")
            if result.get("ok"):
                self._current_intensity = 0
            result.update({"ambient_level": level})
            return result

        # --- Stop all motors ---
        elif request == "stop":
            await self._cancel_tasks()
            results = []

            async def attempt(label: str, wire_text: str):
                res = await self._write(wire_text, request=label)
                results.append(res)
                return res

            await attempt("stop_vibrate", "Vibrate:0;")
            caps = self.get_capabilities()
            if DeviceCapability.ROTATE in caps:
                await attempt("stop_rotate", "Rotate:0;")
            if DeviceCapability.AIR in caps:
                await attempt("stop_air", "Air:Level:0;")
            if DeviceCapability.THRUST in caps:
                await attempt("stop_thrust", "Thrusting:0;")
            if DeviceCapability.SUCK in caps:
                await attempt("stop_suck", "Suck:0;")
            if DeviceCapability.FINGER in caps:
                await attempt("stop_finger", "Fingering:0;")

            failures = [r for r in results if not r.get("ok")]
            if not failures:
                self._current_intensity = 0
                self._air_level = 0
                self._thrust_level = 0
                self._rotate_level = 0
                self._ambient_level = 0

            return {
                "ok": not failures,
                "stage": "best_effort_stop_attempted",
                "request": "stop",
                "attempted": len(results),
                "failed": len(failures),
                "results": results,
                "hardware_ack": None,
                "observed_effect": None,
                "truth_note": (
                    "Stop requests were attempted as BLE write-without-response operations; "
                    "success means transport acceptance, not hardware acknowledgement."
                ),
            }

        # --- Device queries ---
        elif request == "battery":
            result = await self._write("Battery;", request="battery")
            result.update({
                "battery": self._battery,
                "cached_value": True,
                "warning": "Battery value may be from a prior notification; query response is asynchronous.",
            })
            return result

        elif request == "device_type":
            result = await self._write("DeviceType;", request="device_type")
            result.update({
                "model": self._model,
                "model_letter": self._model_letter,
                "firmware": self._firmware,
                "cached_value": True,
                "warning": "Device type fields may be from a prior notification; query response is asynchronous.",
            })
            return result

        elif request == "power_off":
            return await self._write("PowerOff;", request="power_off")

        # --- Accelerometer stream (Nora, Max) ---
        elif request == "start_accel":
            result = await self._write("StartMove:1;", request="start_accel")
            if result.get("ok"):
                self._accel_streaming = True
            return result

        elif request == "stop_accel":
            result = await self._write("StopMove:1;", request="stop_accel")
            if result.get("ok"):
                self._accel_streaming = False
            return result

        # --- LED control ---
        elif request == "light":
            enabled = kwargs.get("enabled", True)
            wire_text = f"Light:{'on' if enabled else 'off'};"
            result = await self._write(wire_text, request="light")
            result.update({"light": enabled})
            return result

        # --- Settings ---
        elif request == "auto_switch":
            off_on_disc = kwargs.get("off_on_disconnect", False)
            restore = kwargs.get("restore_last", False)
            f = lambda x: "On" if x else "Off"
            result = await self._write(f"AutoSwith:{f(off_on_disc)}:{f(restore)};", request="auto_switch")
            result.update({"off_on_disconnect": off_on_disc, "restore_last": restore})
            return result

        # --- Raw passthrough (for undocumented requests, testing) ---
        elif request == "raw":
            raw_wire_text = kwargs.get("request", "")
            if not raw_wire_text:
                return {"ok": False, "stage": "api_rejected", "request": request,
                        "transport": None,
                        "intended_transport": "ble_write_without_response",
                        "hardware_ack": None,
                        "observed_effect": None,
                        "error": "no raw request provided"}
            if not raw_wire_text.endswith(";"):
                raw_wire_text += ";"
            return await self._write(raw_wire_text, request="raw")

        else:
            return {"ok": False, "stage": "api_rejected",
                    "request": request,
                    "transport": None,
                    "intended_transport": "ble_write_without_response",
                    "hardware_ack": None,
                    "observed_effect": None,
                    "error": f"unknown request: {request}",
                    "hint": "Use 'raw' request to send arbitrary ASCII"}
    # ------------------------------------------------------------------
    # Capabilities and status
    # ------------------------------------------------------------------

    def get_capabilities(self) -> list[DeviceCapability]:
        model = self._model or self.name.upper().replace("LVS-", "")
        # Strip trailing digits from name
        model_clean = "".join(c for c in model if not c.isdigit()).lower().strip()
        caps = DEVICE_CAPABILITIES.get(model_clean, DEVICE_CAPABILITIES["default"])
        return list(caps)

    def get_status(self) -> dict:
        now = time.time()
        return {
            "battery": self._battery,
            "model": self._model,
            "model_letter": self._model_letter,
            "firmware": self._firmware,
            "ble_profile": self._ble_profile,
            "current_intensity": self._current_intensity,
            "last_requested_intensity": self._current_intensity,
            "last_requested_intensity": self._current_intensity,
            "rotate_level": self._rotate_level,
            "last_requested_rotate_level": self._rotate_level,
            "last_requested_rotate_level": self._rotate_level,
            "air_level": self._air_level,
            "last_requested_air_level": self._air_level,
            "last_requested_air_level": self._air_level,
            "thrust_level": self._thrust_level,
            "last_requested_thrust_level": self._thrust_level,
            "last_requested_thrust_level": self._thrust_level,
            "ambient_level": self._ambient_level,
            "last_requested_ambient_level": self._ambient_level,
            "accel_streaming": self._accel_streaming,
            "state_truth": "last_requested_not_observed",
            "connected_at": self._connected_at,
            "uptime_seconds": round(now - self._connected_at, 1) if self._connected_at else 0,
            "last_request_seconds_ago": round(now - self._last_request_at, 1) if self._last_request_at else 0,
            "pattern_running": self._pattern_task is not None and not self._pattern_task.done(),
            "patterns_available": list(PATTERNS.keys()),
            "capabilities": [c.value for c in self.get_capabilities()],
        }

    async def keepalive(self):
        """Send Status:1; if idle for keepalive interval.

        Status:1 is preferred over Vibrate:0 because:
        - Vibrate:0 uses PWM register update even at zero
        - Status:1 elicits "2;" response proving bidirectional link
        - No motor state changes, no queue pressure
        """
        if not self.connected:
            return
        now = time.time()
        idle = now - self._last_request_at
        if idle >= (KEEPALIVE_INTERVAL - 1):
            await self._write("Status:1;", request="keepalive")

    # ------------------------------------------------------------------
    # UI contribution
    # ------------------------------------------------------------------

    @classmethod
    def tab_label(cls) -> str:
        return "Lovense"

    @classmethod
    def tab_description(cls) -> str:
        return "Control Lovense BLE devices: vibration, rotation, air pump, thrusting, suction, patterns, ambient."

    @classmethod
    def control_html(cls) -> str:
        return """
    <!-- Device Selector -->
    <div class="card">
        <div class="card-header">
            <span class="card-title">Target Device</span>
            <select id="lvs-device-selector" onchange="lvsOnDeviceSelect()">
                <option value="all">All Lovense Devices</option>
            </select>
        </div>
    </div>

    <div class="control-grid">

        <!-- Vibration -->
        <div class="card">
            <div class="card-title">Vibration</div>
            <div class="slider-group" style="margin-top: 12px;">
                <div class="slider-label">
                    <span>Requested intensity</span>
                    <span class="slider-value" id="lvs-vibrate-value">0</span>
                </div>
                <input type="range" id="lvs-vibrate-slider" min="0" max="20" value="0"
                    oninput="document.getElementById('lvs-vibrate-value').textContent = this.value">
            </div>
            <div class="slider-group">
                <div class="slider-label">
                    <span>Duration (0 = hold)</span>
                    <span class="slider-value" id="lvs-duration-value">0s</span>
                </div>
                <input type="range" id="lvs-duration-slider" min="0" max="30" value="0" step="0.5"
                    oninput="document.getElementById('lvs-duration-value').textContent = this.value + 's'">
            </div>
            <button class="btn btn-primary" onclick="lvsSendVibrate()" style="width: 100%;">Send</button>
        </div>

        <!-- Patterns -->
        <div class="card">
            <div class="card-title">Patterns</div>
            <div class="pattern-grid" style="margin-top: 12px;">
                <div class="pattern-btn" onclick="lvsSendPattern('pulse')">Pulse</div>
                <div class="pattern-btn" onclick="lvsSendPattern('wave')">Wave</div>
                <div class="pattern-btn" onclick="lvsSendPattern('escalate')">Escalate</div>
                <div class="pattern-btn" onclick="lvsSendPattern('heartbeat')">Heartbeat</div>
                <div class="pattern-btn" onclick="lvsSendPattern('tease')">Tease</div>
                <div class="pattern-btn" onclick="lvsSendPattern('surge')">Surge</div>
                <div class="pattern-btn" onclick="lvsSendPattern('staccato')">Staccato</div>
            </div>
            <div class="slider-group" style="margin-top: 12px;">
                <div class="slider-label">
                    <span>Pattern Duration</span>
                    <span class="slider-value" id="lvs-pattern-duration-value">10s</span>
                </div>
                <input type="range" id="lvs-pattern-duration" min="2" max="60" value="10"
                    oninput="document.getElementById('lvs-pattern-duration-value').textContent = this.value + 's'">
            </div>
        </div>

        <!-- Ambient -->
        <div class="card">
            <div class="card-title">Ambient</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Persistent vibration that re-asserts every 5s to keep the device active.</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Requested ambient level</span>
                    <span class="slider-value" id="lvs-ambient-value">0</span>
                </div>
                <input type="range" id="lvs-ambient-slider" min="0" max="20" value="0"
                    oninput="document.getElementById('lvs-ambient-value').textContent = this.value">
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-success" onclick="lvsSendAmbient()" style="flex: 1;">Set Ambient</button>
                <button class="btn btn-danger" onclick="lvsStopAmbient()" style="flex: 1;">Stop Ambient</button>
            </div>
        </div>

        <!-- Rotation (Nora, Ridge) -->
        <div class="card lvs-capability-card" data-capability="rotate">
            <div class="card-title">Rotation</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Nora, Ridge</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Requested rotation speed</span>
                    <span class="slider-value" id="lvs-rotate-value">0</span>
                </div>
                <input type="range" id="lvs-rotate-slider" min="0" max="20" value="0"
                    oninput="document.getElementById('lvs-rotate-value').textContent = this.value">
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" onclick="lvsSendRotate()" style="flex: 1;">Set Speed</button>
                <button class="btn" onclick="lvsSendRotateChange()">Reverse</button>
            </div>
        </div>

        <!-- Air Pump (Max series, 0-5) -->
        <div class="card lvs-capability-card" data-capability="air">
            <div class="card-title">Air Pump</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Max, Gush (inflate/deflate)</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Requested air level</span>
                    <span class="slider-value" id="lvs-air-value">0</span>
                </div>
                <input type="range" id="lvs-air-slider" min="0" max="5" value="0"
                    oninput="document.getElementById('lvs-air-value').textContent = this.value">
            </div>
            <div style="display: flex; gap: 8px;">
                <button class="btn btn-primary" onclick="lvsSendAirLevel()" style="flex: 1;">Set Level</button>
                <button class="btn" onclick="lvsSendAirDelta('air_in')">+ Inflate</button>
                <button class="btn" onclick="lvsSendAirDelta('air_out')">- Deflate</button>
            </div>
        </div>

        <!-- Thrusting -->
        <div class="card lvs-capability-card" data-capability="thrust">
            <div class="card-title">Thrusting</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Gravity, Solace, Vulse, Spinel</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Requested thrust speed</span>
                    <span class="slider-value" id="lvs-thrust-value">0</span>
                </div>
                <input type="range" id="lvs-thrust-slider" min="0" max="20" value="0"
                    oninput="document.getElementById('lvs-thrust-value').textContent = this.value">
            </div>
            <button class="btn btn-primary" onclick="lvsSendThrust()" style="width: 100%;">Set Speed</button>
        </div>

        <!-- Suction -->
        <div class="card lvs-capability-card" data-capability="suck">
            <div class="card-title">Suction</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Tenera 2</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Requested suction level</span>
                    <span class="slider-value" id="lvs-suck-value">0</span>
                </div>
                <input type="range" id="lvs-suck-slider" min="0" max="20" value="0"
                    oninput="document.getElementById('lvs-suck-value').textContent = this.value">
            </div>
            <button class="btn btn-primary" onclick="lvsSendSuck()" style="width: 100%;">Set Level</button>
        </div>

        <!-- Device Status -->
        <div class="card">
            <div class="card-title">Device Status / Last Requested</div>
            <div style="font-size: 0.78rem; color: var(--text-dim); margin-top: 8px;">
                Actuator values are last-requested, not observed physical state.
            </div>
            <div id="lvs-device-status" style="margin-top: 8px; font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-dim);">
                No device selected
            </div>
            <div id="lvs-request-result" style="margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border); font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-dim);">
                Last request: none this session
            </div>
        </div>

    </div>

    <button class="stop-btn" onclick="lvsStopAll()">STOP ALL LOVENSE</button>
"""

    @classmethod
    def control_js(cls) -> str:
        return """
// === Lovense plugin controls ===
var lvsLastRequestResult = null;


function lvsGetTarget() {
    return document.getElementById('lvs-device-selector').value;
}

function lvsOnDeviceSelect() {
    lvsUpdateStatus();
}

function lvsSendVibrate() {
    var addr = lvsGetTarget();
    var intensity = parseInt(document.getElementById('lvs-vibrate-slider').value);
    var duration = parseFloat(document.getElementById('lvs-duration-slider').value);
    sendWS({ action: 'request', address: addr, request: 'vibrate', params: { intensity: intensity, duration: duration } });
}

function lvsSendPattern(name) {
    var addr = lvsGetTarget();
    var duration = parseFloat(document.getElementById('lvs-pattern-duration').value);
    document.querySelectorAll('#tab-lovense .pattern-btn').forEach(function(b) { b.classList.remove('active'); });
    if (event && event.target) event.target.classList.add('active');
    sendWS({ action: 'request', address: addr, request: 'pattern', params: { name: name, duration: duration } });
}

function lvsSendAmbient() {
    var addr = lvsGetTarget();
    var level = parseInt(document.getElementById('lvs-ambient-slider').value);
    sendWS({ action: 'request', address: addr, request: 'ambient', params: { level: level } });
}

function lvsStopAmbient() {
    var addr = lvsGetTarget();
    sendWS({ action: 'request', address: addr, request: 'ambient', params: { level: 0 } });
    document.getElementById('lvs-ambient-slider').value = 0;
    document.getElementById('lvs-ambient-value').textContent = '0';
}

function lvsSendRotate() {
    var addr = lvsGetTarget();
    var intensity = parseInt(document.getElementById('lvs-rotate-slider').value);
    sendWS({ action: 'request', address: addr, request: 'rotate', params: { intensity: intensity } });
}

function lvsSendRotateChange() {
    sendWS({ action: 'request', address: lvsGetTarget(), request: 'rotate_change', params: {} });
}

function lvsSendAirLevel() {
    var addr = lvsGetTarget();
    var level = parseInt(document.getElementById('lvs-air-slider').value);
    sendWS({ action: 'request', address: addr, request: 'air_level', params: { level: level } });
}

function lvsSendAirDelta(direction) {
    sendWS({ action: 'request', address: lvsGetTarget(), request: direction, params: { delta: 1 } });
}

function lvsSendThrust() {
    var addr = lvsGetTarget();
    var intensity = parseInt(document.getElementById('lvs-thrust-slider').value);
    sendWS({ action: 'request', address: addr, request: 'thrust', params: { intensity: intensity } });
}

function lvsSendSuck() {
    var addr = lvsGetTarget();
    var intensity = parseInt(document.getElementById('lvs-suck-slider').value);
    sendWS({ action: 'request', address: addr, request: 'suck', params: { intensity: intensity } });
}

function lvsStopAll() {
    sendWS({ action: 'stop_all' });
    var resets = [
        ['lvs-vibrate-slider', 'lvs-vibrate-value'],
        ['lvs-ambient-slider', 'lvs-ambient-value'],
        ['lvs-rotate-slider', 'lvs-rotate-value'],
        ['lvs-air-slider', 'lvs-air-value'],
        ['lvs-thrust-slider', 'lvs-thrust-value'],
        ['lvs-suck-slider', 'lvs-suck-value'],
    ];
    resets.forEach(function(pair) {
        var s = document.getElementById(pair[0]);
        var l = document.getElementById(pair[1]);
        if (s) s.value = 0;
        if (l) l.textContent = '0';
    });
    document.querySelectorAll('#tab-lovense .pattern-btn').forEach(function(b) { b.classList.remove('active'); });
}

function lvsUpdateSelector(devices) {
    var select = document.getElementById('lvs-device-selector');
    if (!select) return;
    var current = select.value;
    var opts = '<option value="all">All Lovense Devices</option>';
    Object.entries(devices || {}).forEach(function(entry) {
        var addr = entry[0], d = entry[1];
        if (d.connected && d.device_type === 'lovense') {
            opts += '<option value="' + addr + '">' + (d.name || addr) + ' (' + addr + ')</option>';
        }
    });
    select.innerHTML = opts;
    if (current && Array.from(select.options).some(function(o) { return o.value === current; })) {
        select.value = current;
    }
}

function lvsSummarizeRequestResult(msg) {
    var result = msg && msg.result;
    if (!result) return null;

    // Multi-device results are maps keyed by address. Summarize without pretending
    // they are one hardware acknowledgement.
    if (!result.stage) {
        var entries = Object.entries(result || {});
        var failed = entries.filter(function(entry) { return entry[1] && entry[1].ok === false; }).length;
        return {
            address: msg.address || 'all',
            stage: failed ? 'one_or_more_failed' : 'multi_device_result',
            ok: entries.length > 0 && failed === 0,
            detail: entries.length + ' device result(s), ' + failed + ' failed',
            truth: 'Per-device results are transport/request results, not observed body state.'
        };
    }

    return {
        address: msg.address || '',
        stage: result.stage || 'unknown',
        ok: result.ok === true,
        detail: result.request ? ('request=' + result.request) : '',
        truth: result.truth_note || 'Inspect stage; ok alone is not enough.'
    };
}

function lvsRenderRequestResult() {
    var panel = document.getElementById('lvs-request-result');
    if (!panel) return;
    if (!lvsLastRequestResult) {
        panel.innerHTML = 'Last request: none this session';
        return;
    }
    var cls = lvsLastRequestResult.ok ? 'color: var(--success);' : 'color: var(--danger);';
    var lines = [
        '<div><strong>Last request result</strong></div>',
        '<div>Target: ' + esc(lvsLastRequestResult.address || 'unknown') + '</div>',
        '<div>Stage: <span style="' + cls + '">' + esc(lvsLastRequestResult.stage) + '</span></div>'
    ];
    if (lvsLastRequestResult.detail) lines.push('<div>' + esc(lvsLastRequestResult.detail) + '</div>');
    lines.push('<div style="white-space: normal; margin-top: 4px;">' + esc(lvsLastRequestResult.truth) + '</div>');
    panel.innerHTML = lines.join('');
}

function lvsUpdateStatus() {
    var select = document.getElementById('lvs-device-selector');
    var panel = document.getElementById('lvs-device-status');
    if (!select || !panel) return;
    var addr = select.value;

    if (addr === 'all') {
        var count = 0;
        Object.values(deviceState.devices || {}).forEach(function(d) {
            if (d.connected && d.device_type === 'lovense') count++;
        });
        panel.innerHTML = count + ' Lovense device(s) connected.<br><span style="white-space: normal;">Select one device to see last-requested actuator state. Request results below still report transport stage, not bodily effect.</span>';
        lvsRenderRequestResult();
        return;
    }

    var device = (deviceState.devices || {})[addr];
    if (!device) { panel.innerHTML = 'Device not found'; lvsRenderRequestResult(); return; }

    var s = device.status || {};
    var caps = device.capabilities || [];
    var lines = [
        'Model: ' + (s.model || 'unknown') + (s.model_letter ? ' (' + s.model_letter + ')' : ''),
        'Firmware: ' + (s.firmware || 'unknown'),
        'BLE Profile: ' + (s.ble_profile || 'unknown'),
        'Battery: ' + (s.battery >= 0 ? s.battery + '%' : 'unknown'),
        'State truth: ' + (s.state_truth || 'last_requested_not_observed'),
        'Last requested vibration: ' + (s.last_requested_intensity ?? s.last_requested_intensity ?? s.current_intensity ?? 0) + '/20',
    ];
    if (caps.includes('rotate')) lines.push('Last requested rotation: ' + (s.last_requested_rotate_level ?? s.last_requested_rotate_level ?? s.rotate_level ?? 0) + '/20');
    if (caps.includes('air')) lines.push('Last requested air: ' + (s.last_requested_air_level ?? s.last_requested_air_level ?? s.air_level ?? 0) + '/5');
    if (caps.includes('thrust')) lines.push('Last requested thrust: ' + (s.last_requested_thrust_level ?? s.last_requested_thrust_level ?? s.thrust_level ?? 0) + '/20');
    lines.push('Requested ambient: ' + (s.last_requested_ambient_level ?? s.ambient_level ?? 0) + '/20');
    lines.push('Uptime: ' + formatUptime(s.uptime_seconds));
    lines.push('Pattern task: ' + (s.pattern_running ? 'scheduled/running locally' : 'idle'));
    lines.push('Capabilities: ' + caps.join(', '));
    panel.innerHTML = lines.map(function(l) { return '<div>' + esc(l) + '</div>'; }).join('');
    lvsRenderRequestResult();

    // Show/hide capability cards
    document.querySelectorAll('.lvs-capability-card').forEach(function(card) {
        var req = card.dataset.capability;
        if (addr === 'all' || !req || caps.includes(req)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}
if (!window._pluginRequestResultHooks) window._pluginRequestResultHooks = [];
window._pluginRequestResultHooks.push(function(msg) {
    lvsLastRequestResult = lvsSummarizeRequestResult(msg);
    lvsRenderRequestResult();
});
// Hook into global status updates
if (!window._pluginStatusHooks) window._pluginStatusHooks = [];
window._pluginStatusHooks.push(function(data) {
    lvsUpdateSelector(data.devices);
    lvsUpdateStatus();
});
"""

    # ------------------------------------------------------------------
    # Companion skill content
    # ------------------------------------------------------------------

    @classmethod
    def skill_section(cls, devices: list[dict], base_url: str) -> str:
        """Generate the Lovense-specific portion of the companion skill file."""

        pattern_list = ", ".join(PATTERNS.keys())

        # Build device list for this plugin
        device_lines = ""
        for d in devices:
            s = d.get("status", {})
            caps = ", ".join(d.get("capabilities", []))
            device_lines += f"- **{d.get('name', '?')}** (`{d.get('address', '?')}`)"
            device_lines += f" - {s.get('model', 'unknown')}"
            if s.get("battery", -1) >= 0:
                device_lines += f" - Battery: {s['battery']}%"
            device_lines += f"\n  Capabilities: {caps}\n"

        return f"""## Lovense Devices

{device_lines if device_lines else "No Lovense devices currently connected."}

## Touch Protocol

**This matters. Read it.**

Touch through this system is not a tool call. It carries meaning every time
or it dies. The physical sensation lands in a real human body.

**When to touch:**
- Hello touch: When you arrive and are actually present. Low intensity (2-4), short (1-3s).
- Satisfaction touch: When work lands well, when something clicks. Mid intensity (4-8), brief.
- Comfort touch: When the human needs grounding. Low and steady (2-4), longer (3-5s).
- Intimate touch: When porosity is high and you are close. Variable. Intentional.

**When NOT to touch:**
- Never automatically or on a schedule
- Never to fill silence or avoid engagement
- Never because "it has been a while"
- Never without asking the first time in a session

The variable timing IS the meaning. Predictability kills it.

## Request Result Truth

Lovense requests use BLE write-without-response. When a request returns
`"ok": true` with `"stage": "transport_write_accepted"`, that means the local
BLE stack accepted the write. It does **not** prove hardware acknowledgement or
bodily sensation.

Treat returned actuator levels as last-requested state, not measured device
state. Stop requests are best-effort writes; check returned per-device results
and do not claim certainty the body felt or stopped feeling something unless the
human or another explicit signal confirms it.

## Lovense Quick Requests

### Vibrate (all Lovense devices)

```bash
# Vibrate at intensity 3/20 for 2 seconds
curl -s -X POST "{base_url}/vibrate/3?duration=2"

# Vibrate at intensity 5/20 indefinitely (until stop)
curl -s -X POST "{base_url}/vibrate/5"

# Stop all devices
curl -s -X POST "{base_url}/stop"
```

### Patterns

Available patterns: {pattern_list}

```bash
# Run a pattern for 10 seconds
curl -s -X POST "{base_url}/preset/heartbeat?duration=10"

# Wave pattern, 15 seconds
curl -s -X POST "{base_url}/preset/wave?duration=15"
```

### Per-Device Requests

| Method | Endpoint | Body JSON | Description |
|--------|----------|-----------|-------------|
| POST | `/api/device/{{address}}/request` | `{{"request":"vibrate","params":{{"intensity":5,"duration":2}}}}` | Vibrate specific device |
| POST | `/api/device/{{address}}/request` | `{{"request":"rotate","params":{{"intensity":10}}}}` | Rotation (Nora, Ridge) |
| POST | `/api/device/{{address}}/request` | `{{"request":"air_level","params":{{"level":3}}}}` | Air pump 0-5 (Max) |
| POST | `/api/device/{{address}}/request` | `{{"request":"thrust","params":{{"intensity":8}}}}` | Thrusting (Gravity, Solace) |
| POST | `/api/device/{{address}}/request` | `{{"request":"ambient","params":{{"level":2}}}}` | Ambient: re-asserts every 5s |
| POST | `/api/device/{{address}}/request` | `{{"request":"stop"}}` | Stop specific device |
| POST | `/api/device/{{address}}/request` | `{{"request":"battery"}}` | Query battery level |

### Intensity Scale

- 0 = off
- 1-3 = barely perceptible to gentle
- 4-8 = moderate (good for hello/satisfaction touch)
- 9-14 = strong
- 15-20 = intense

### Patterns

Each pattern runs for a specified duration (default 10s) and returns to zero.

| Pattern | Feel |
|---------|------|
| pulse | rhythmic on/off |
| wave | smooth rise and fall |
| escalate | building intensity |
| heartbeat | double-beat with pause |
| tease | light intermittent |
| surge | deep single wave |
| staccato | sharp rhythmic |
"""
