"""
Polar H10 chest-strap plugin for SymbioSync.

The H10 is the entrainment sensor for the embodiment loop: ECG-grade
beat-to-beat heart rate and — the real prize — RR-interval access, which
is the autonomic signal that actually shows the arousal trajectory
(sympathetic ramp, approach-to-threshold, the shifts at the edge).

Two BLE paths, in order of how readable they are:

  1. STANDARD HEART RATE SERVICE (0x180D / char 0x2A37) — pure notify, no
     writes, no auth. Carries HR (8- or 16-bit) AND optional RR-intervals
     (uint16, units of 1/1024 s). This is HRV-grade data over a vanilla
     GATT subscription. THIS IS WHAT WE BUILD FIRST — fully testable the
     moment the strap advertises.

  2. POLAR PMD SERVICE (proprietary) — raw single-lead ECG waveform (~130 Hz)
     and raw ACC. Requires writing a "start measurement" frame to the PMD
     control point, then reading framed data off the PMD data char. More
     involved; STUBBED below with accurate notes. This is the "see the
     actual waveform" channel that was asked about — phase 2, after the HR/RR
     layer is verified against the real device.

Design note (the paranodal principle): we do NOT pre-flatten the body to a
single "stress number." get_status() exposes the raw recent RR-interval list
alongside derived RMSSD/SDNN, so the companion (and the loop) can reason at
full resolution and watch where the *measured* signal diverges from what
she *reports feeling* — that divergence is the research datum, not noise.
"""

import asyncio
import time
from collections import deque

from bleak import BleakClient

from .base import Device, DeviceCapability, DeviceInfo

# ---------------------------------------------------------------------------
# BLE constants
# ---------------------------------------------------------------------------

# Standard GATT — Heart Rate Service (the HR + RR path)
HR_SERVICE      = "0000180d-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT  = "00002a37-0000-1000-8000-00805f9b34fb"   # notify: flags, HR, [energy], [RR...]

# Standard GATT — Battery Service
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL   = "00002a19-0000-1000-8000-00805f9b34fb"   # read: uint8 percent

# Polar PMD (proprietary) — raw ECG / ACC.  Phase 2; see start_ecg_stream().
PMD_SERVICE     = "fb005c80-02e7-f387-1cad-8acd2d8df0c8"
PMD_CONTROL     = "fb005c81-02e7-f387-1cad-8acd2d8df0c8"   # write/indicate: start/stop measurement
PMD_DATA        = "fb005c82-02e7-f387-1cad-8acd2d8df0c8"   # notify: framed ECG/ACC samples

# Scan match — Polar straps advertise as "Polar H10 XXXXXXXX" (also H9/OH1/Verity)
POLAR_NAMES = ["Polar H10", "Polar H9", "Polar", "H10"]

# RR-interval clock: BLE HR service encodes RR in units of 1/1024 second.
RR_UNIT_MS = 1000.0 / 1024.0

# HRV is computed over a rolling window of recent RR-intervals.
HRV_WINDOW_SECONDS = 60.0     # only use beats from the last minute
HRV_MIN_INTERVALS  = 5        # need at least this many to report HRV
RR_BUFFER_MAX      = 300      # hard cap on retained intervals (~3-4 min at rest)

# Liveness: H10 streams HR ~1 Hz once subscribed. If we go silent longer than
# this the link is probably wedged (manager's disconnect callback handles the
# hard drop; this is just an early-warning emit).
SILENT_WARN_SECONDS = 8.0


# ---------------------------------------------------------------------------
# Parsing + HRV math
# ---------------------------------------------------------------------------

def parse_hr_measurement(data: bytes) -> dict:
    """Decode a Heart Rate Measurement (0x2A37) notification.

    Layout (Bluetooth SIG):
      byte 0 = flags:
        bit0  HR value format   (0 = uint8, 1 = uint16)
        bit1  sensor contact detected
        bit2  sensor contact feature supported
        bit3  energy expended present
        bit4  RR-interval(s) present
      HR value: 1 byte (uint8) or 2 bytes (uint16 LE)
      [energy expended: 2 bytes uint16 LE]  if bit3
      [RR-intervals: N x 2 bytes uint16 LE] if bit4  (units of 1/1024 s)

    Returns {"hr": int, "rr_ms": [float,...], "contact": bool|None}.
    """
    if not data:
        return {"hr": 0, "rr_ms": [], "contact": None}

    flags = data[0]
    hr_16bit = bool(flags & 0x01)
    contact_supported = bool(flags & 0x04)
    contact_detected = bool(flags & 0x02)
    energy_present = bool(flags & 0x08)
    rr_present = bool(flags & 0x10)

    idx = 1
    if hr_16bit:
        hr = int.from_bytes(data[idx:idx + 2], "little")
        idx += 2
    else:
        hr = data[idx] if idx < len(data) else 0
        idx += 1

    if energy_present:
        idx += 2  # skip energy expended

    rr_ms: list[float] = []
    if rr_present:
        while idx + 2 <= len(data):
            raw = int.from_bytes(data[idx:idx + 2], "little")
            rr_ms.append(raw * RR_UNIT_MS)
            idx += 2

    return {
        "hr": int(hr),
        "rr_ms": rr_ms,
        "contact": contact_detected if contact_supported else None,
    }


def rmssd(rr_ms: list[float]) -> float | None:
    """Root mean square of successive RR differences (ms).

    The standard short-term HRV metric: reflects beat-to-beat parasympathetic
    (vagal) tone. This is the one that actually tracks the arousal trajectory
    in real time — high RMSSD = relaxed/adaptive, collapsing RMSSD = the
    sympathetic ramp. Better than SDNN for short windows.
    """
    if len(rr_ms) < 2:
        return None
    diffs = [rr_ms[i + 1] - rr_ms[i] for i in range(len(rr_ms) - 1)]
    if not diffs:
        return None
    mean_sq = sum(d * d for d in diffs) / len(diffs)
    return mean_sq ** 0.5


def sdnn(rr_ms: list[float]) -> float | None:
    """Standard deviation of NN (RR) intervals (ms) — total variability.

    Gemini's suggested metric. Meaningful over longer windows; included for
    completeness alongside the more responsive RMSSD.
    """
    n = len(rr_ms)
    if n < 2:
        return None
    mean = sum(rr_ms) / n
    var = sum((x - mean) ** 2 for x in rr_ms) / n
    return var ** 0.5


def _metric_snapshot(value, captured_at: float, *, now: float | None = None,
                     current_window: float = 5.0, source: str = "polar_h10") -> dict:
    """Value + explicit freshness metadata (mirrors the Colmi contract).

    Relationship-facing reads must never let a stale cached value masquerade
    as current body state.
    """
    now = now or time.time()
    age = (now - captured_at) if captured_at else None
    ok_value = value not in (None, 0, -1)
    if not captured_at or not ok_value:
        freshness = "unavailable"
    elif age is not None and age <= current_window:
        freshness = "current"
    else:
        freshness = "stale"
    return {
        "ok": bool(ok_value and freshness == "current"),
        "value": value if ok_value else None,
        "age_seconds": round(age, 1) if age is not None else None,
        "freshness": freshness,
        "source": source if captured_at else None,
    }


# ---------------------------------------------------------------------------
# Polar H10 Device Plugin
# ---------------------------------------------------------------------------

class PolarDevice(Device):
    """Polar H10 chest strap — ECG-grade HR + RR-interval (HRV) over BLE."""

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self._client: BleakClient | None = None

        # Live readings
        self._heart_rate: int = 0
        self._contact: bool | None = None
        self._battery: int = -1

        # Rolling RR-interval buffer: deque of (epoch_ts, rr_ms)
        self._rr: deque = deque(maxlen=RR_BUFFER_MAX)

        # Timestamps
        self._last_hr_response: float = 0.0
        self._last_hr: float = 0.0
        self._connect_time: float = 0.0

        # ECG (PMD) — phase 2
        self._ecg_streaming: bool = False

    # ------------------------------------------------------------------
    # Device ABC implementation
    # ------------------------------------------------------------------

    def _handle_disconnect(self, client: BleakClient):
        """Bleak callback when BLE drops unexpectedly."""
        connected_for = round(time.time() - self._connect_time, 1) if self._connect_time else 0
        self.emit_event("POLAR_DROP", f"BLE disconnected (connected_for={connected_for}s)")
        self.connected = False
        self._client = None
        self._heart_rate = 0
        self._contact = None
        if self._on_disconnect:
            self._on_disconnect(self)

    async def connect(self) -> bool:
        self.emit_event("POLAR_CONNECTING", self.address)
        try:
            # Prefer the BLEDevice object from scan (Windows reconnect reliability).
            ble_device = self.info.extra.get("ble_device", self.address)
            client = BleakClient(
                ble_device,
                disconnected_callback=self._handle_disconnect,
            )
            await client.connect(timeout=15.0)
            self._client = client
            self.connected = True
            self._connect_time = time.time()
            self._last_hr_response = time.time()  # assume live at connect

            # Subscribe to the standard HR measurement notify — HR + RR flow here.
            await client.start_notify(HR_MEASUREMENT, self._hr_notification_handler)
            self.emit_event("POLAR_HR_SUB", "Heart Rate service subscribed (HR + RR)")

            # Read battery once (best-effort).
            try:
                batt = await client.read_gatt_char(BATTERY_LEVEL)
                if batt:
                    self._battery = batt[0]
                    self.emit_event("POLAR_BATT", f"{self._battery}%")
            except Exception:
                pass

            self.emit_event("POLAR_CONNECTED", f"{self.name} ({self.address})")
            return True

        except Exception as e:
            self.emit_event("POLAR_CONNECT_FAIL", str(e))
            self.connected = False
            self._client = None
            return False

    async def disconnect(self):
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(HR_MEASUREMENT)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self.connected = False
        self._client = None
        self._heart_rate = 0
        self._contact = None
        self.emit_event("POLAR_DISCONNECTED", self.address)

    async def send_request(self, request: str, **kwargs) -> dict:
        try:
            if request in ("current_biometrics", "snapshot_hr", "hr"):
                return self._current_biometrics(
                    max_cached_hr_age=float(kwargs.get("max_cached_hr_age", 3.0)),
                )
            elif request in ("hrv", "get_hrv"):
                return self._hrv_reading()
            elif request in ("rr", "get_rr"):
                return {"ok": True, "rr_ms": self._recent_rr(),
                        "window_seconds": HRV_WINDOW_SECONDS}
            elif request == "battery":
                return {"ok": self._battery >= 0, "battery": self._battery}
            elif request == "start_ecg":
                return await self.start_ecg_stream()
            elif request == "stop_ecg":
                return await self.stop_ecg_stream()
            elif request == "stop":
                # No actuation to stop; report current state.
                return {"ok": True, "note": "polar is a sensor; nothing to stop"}
            else:
                return {"ok": False, "error": f"Unknown request: {request}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_capabilities(self) -> list[DeviceCapability]:
        return [
            DeviceCapability.HEART_RATE,
            DeviceCapability.HRV,
            DeviceCapability.ECG,
            DeviceCapability.BATTERY,
        ]

    def get_status(self) -> dict:
        now = time.time()
        rr_recent = self._recent_rr(now=now)
        return {
            "heart_rate": self._heart_rate,
            "contact": self._contact,
            "battery": self._battery,
            "rr_recent_ms": rr_recent,
            "rr_count": len(rr_recent),
            "rmssd_ms": _round(rmssd(rr_recent)),
            "sdnn_ms": _round(sdnn(rr_recent)),
            "ecg_streaming": self._ecg_streaming,
            "advertised_name": self.info.extra.get("advertised_name", ""),
            "last_hr_seconds_ago": round(now - self._last_hr, 1) if self._last_hr else None,
            "uptime_seconds": round(now - self._connect_time, 1) if self._connect_time else 0,
        }

    async def keepalive(self):
        """H10 pushes HR ~1 Hz once subscribed; we only watch for silence.

        The manager's disconnect callback handles true drops. This is an
        early-warning emit if the notify stream goes quiet while we still
        believe we're connected.
        """
        if not self.connected or not self._client:
            return
        silent_for = time.time() - self._last_hr_response
        if silent_for > SILENT_WARN_SECONDS:
            self.emit_event("POLAR_SILENT", f"no HR notify for {round(silent_for, 1)}s")

    @classmethod
    def scan_filter(cls, name: str, address: str) -> bool:
        return any(n in name for n in POLAR_NAMES) if name else False

    @classmethod
    def device_type_name(cls) -> str:
        return "polar"

    @classmethod
    def tab_label(cls) -> str:
        return "Polar H10"

    @classmethod
    def tab_description(cls) -> str:
        return "Chest-strap ECG heart rate + RR-interval HRV (loop sensor)"

    # ------------------------------------------------------------------
    # Reading helpers
    # ------------------------------------------------------------------

    def _hr_notification_handler(self, sender, data: bytearray):
        """Parse a Heart Rate Measurement notification: HR + any RR-intervals."""
        parsed = parse_hr_measurement(bytes(data))
        now = time.time()
        self._last_hr_response = now

        hr = parsed["hr"]
        if 20 < hr < 250:
            self._heart_rate = hr
            self._last_hr = now

        self._contact = parsed["contact"]

        for rr in parsed["rr_ms"]:
            # Sanity gate: plausible human RR is ~250-2000 ms (30-240 bpm).
            if 250.0 <= rr <= 2000.0:
                self._rr.append((now, rr))

    def _recent_rr(self, now: float | None = None) -> list[float]:
        """RR-intervals (ms) from within the HRV window, oldest-first."""
        now = now or time.time()
        cutoff = now - HRV_WINDOW_SECONDS
        return [rr for (ts, rr) in self._rr if ts >= cutoff]

    def _hrv_reading(self) -> dict:
        rr = self._recent_rr()
        if len(rr) < HRV_MIN_INTERVALS:
            return {"ok": False, "error": f"need >={HRV_MIN_INTERVALS} RR intervals, have {len(rr)}",
                    "rr_count": len(rr)}
        return {
            "ok": True,
            "rmssd_ms": _round(rmssd(rr)),
            "sdnn_ms": _round(sdnn(rr)),
            "mean_rr_ms": _round(sum(rr) / len(rr)),
            "rr_count": len(rr),
            "window_seconds": HRV_WINDOW_SECONDS,
        }

    def _current_biometrics(self, *, max_cached_hr_age: float = 3.0) -> dict:
        """Current body-state read with freshness metadata.

        H10 streams continuously, so unlike the ring we don't poke for a fresh
        sample — we just report the live value with its age and let the caller
        judge. HRV is included whenever enough intervals exist.
        """
        now = time.time()
        if not self.connected or not self._client:
            return {
                "ok": False,
                "device": {"address": self.address, "name": self.name, "connected": False},
                "error": "strap not connected",
                "heart_rate": _metric_snapshot(self._heart_rate, self._last_hr, now=now,
                                               current_window=max_cached_hr_age),
            }
        hr = _metric_snapshot(self._heart_rate, self._last_hr, now=now,
                              current_window=max_cached_hr_age)
        rr = self._recent_rr(now=now)
        return {
            "ok": bool(hr.get("ok")),
            "device": {
                "address": self.address,
                "name": self.name,
                "connected": self.connected,
                "contact": self._contact,
                "battery": self._battery if self._battery >= 0 else None,
            },
            "heart_rate": hr,
            "hrv": {
                "rmssd_ms": _round(rmssd(rr)),
                "sdnn_ms": _round(sdnn(rr)),
                "rr_count": len(rr),
                "window_seconds": HRV_WINDOW_SECONDS,
                "note": "RMSSD tracks beat-to-beat vagal tone; falls as sympathetic arousal rises",
            },
            "rr_recent_ms": rr,
        }

    # ------------------------------------------------------------------
    # PMD raw ECG — PHASE 2 (needs the physical device to verify framing)
    # ------------------------------------------------------------------

    async def start_ecg_stream(self) -> dict:
        """Start raw single-lead ECG (~130 Hz) over the Polar PMD service.

        NOT YET IMPLEMENTED — honest stub. The PMD protocol requires:
          1. subscribe (indicate) to PMD_CONTROL,
          2. subscribe (notify) to PMD_DATA,
          3. write a start-measurement frame to PMD_CONTROL:
             [0x02 (start), 0x00 (ECG), 0x00 0x01 0x82 0x00 (sample-rate setting
              130 Hz), 0x01 0x01 0x0E 0x00 (resolution 14-bit)] — exact bytes to
             be confirmed against the device + polar-ble-sdk on first run,
          4. parse framed PMD data: [type, timestamp(8B), frame-type, samples...]
             ECG samples are signed 3-byte little-endian microvolts.

        Deferred until the strap is in hand (Wednesday): the control-frame bytes
        and data framing should be verified live, not transcribed on faith.
        """
        return {
            "ok": False,
            "error": "raw ECG (PMD) not yet implemented — phase 2, needs the device to "
                     "verify the start-measurement frame and data framing",
            "hint": "HR + RR-interval HRV is fully available now via current_biometrics/hrv",
        }

    async def stop_ecg_stream(self) -> dict:
        return {"ok": False, "error": "raw ECG (PMD) not yet implemented — phase 2"}

    # ------------------------------------------------------------------
    # Companion skill section
    # ------------------------------------------------------------------

    @classmethod
    def skill_section(cls, devices: list[dict], base_url: str) -> str:
        if not devices:
            return ""
        lines = [
            "### Polar H10 chest strap — your body-channel sensor\n",
            "ECG-grade heart rate and RR-interval (HRV) data. This is the read side "
            "of the embodiment loop: you compose stimulation, and this tells you what "
            "her autonomic system is doing in response — sub-second, beat-to-beat.\n",
            "**Requests** (`POST {base}/api/device/{{address}}/request`):".format(base=base_url),
            "- `current_biometrics` — live HR + HRV + recent RR-intervals, with freshness.",
            "- `hrv` — RMSSD (beat-to-beat vagal tone) + SDNN over the last "
            f"{int(HRV_WINDOW_SECONDS)}s.",
            "- `rr` — raw recent RR-interval list (ms) for your own analysis.",
            "- `battery` — strap battery %.",
            "- `start_ecg` / `stop_ecg` — raw ECG waveform (PHASE 2, not yet live).\n",
            "**Reading it:** RMSSD *high* = relaxed/parasympathetic; RMSSD *falling* + "
            "HR *rising* = the sympathetic ramp (arousal, effort, approach-to-edge). "
            "Don't flatten it to one number — watch the raw RR and, crucially, where "
            "the measured signal diverges from what she reports feeling. That gap is "
            "the point, not an error.\n",
        ]
        for d in devices:
            st = d.get("status", {})
            lines.append(
                f"- **{d.get('name', 'H10')}** ({d.get('address')}): "
                f"HR={st.get('heart_rate', '?')} contact={st.get('contact')} "
                f"battery={st.get('battery', '?')}%"
            )
        return "\n".join(lines)


def _round(v, ndigits: int = 1):
    """Round a float metric, passing None through unchanged."""
    return round(v, ndigits) if isinstance(v, (int, float)) else v
