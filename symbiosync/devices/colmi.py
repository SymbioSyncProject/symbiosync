"""
Colmi R02 Smart Ring plugin for SymbioSync.

BLE protocol extracted from ferri_server.py (March 2026), which was
inferred from the colmi_r02_client project and verified against
the QRing APK static analysis.

Supports: real-time heart rate, SpO2, step/calorie/distance,
battery, sleep data, and historical HR/step logs.
"""

import asyncio
import json
import os
import sqlite3
import struct
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from pathlib import Path

from bleak import BleakClient

from .base import Device, DeviceCapability, DeviceInfo

# ---------------------------------------------------------------------------
# BLE constants (verified from colmi_r02_client + colmi.puxtril.com)
# ---------------------------------------------------------------------------

UART_SERVICE = "6E40FFF0-B5A3-F393-E0A9-E50E24DCCA9E"
UART_RX      = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  # write requests
UART_TX      = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  # notifications

BIG_DATA_SERVICE = "DE5BF728-D711-4E47-AF26-65E3012A5DC7"
BIG_DATA_NOTIFY  = "DE5BF729-D711-4E47-AF26-65E3012A5DC7"
BIG_DATA_WRITE   = "DE5BF72A-D711-4E47-AF26-65E3012A5DC7"
BIG_DATA_MAGIC   = 0xBC

# Request IDs
REQ_SET_TIME         = 0x01
REQ_BATTERY          = 0x03
REQ_READ_HR_LOG      = 0x15
REQ_HR_LOG_SETTINGS  = 0x16
REQ_READ_STEP_DETAIL = 0x43
REQ_TODAY_SPORTS     = 0x48
REQ_START_REALTIME   = 0x69
REQ_STOP_REALTIME    = 0x6A

# BigData data IDs
SLEEP_DATA_ID = 0x27

# Scan patterns
RING_NAMES = ["R02", "R06", "QRing", "Smart Ring", "Colmi"]

# Default cadence intervals (seconds)
HR_INTERVAL        = 45.0      # re-request HR if no response
HR_ACTIVE_WAIT     = 30.0      # consider HR "active" if response within this
SPORTS_INTERVAL    = 60.0      # poll steps/calories
BATTERY_INTERVAL   = 300.0     # poll battery; battery is slow-moving, keep BLE chatter low
SPO2_INTERVAL      = 3600.0    # poll SpO2 hourly; it pauses HR and should stay infrequent.
                               # More frequent SpO2 cycling has correlated with flaky BLE.
HISTORY_SYNC_INTERVAL = 30 * 60.0  # sync history every 30 min
BACKFILL_DAYS      = 7

# DB path -- defaults to the same database as the legacy ferri_server.
# Windows copies can override this with config.json (`colmi_db_path`) or the
# SYMBIOSYNC_COLMI_DB_PATH environment variable.
DEFAULT_DB_PATH = str(Path("C:/_LLM/feedback/ring_data.sqlite"))
DB_PATH = os.environ.get("SYMBIOSYNC_COLMI_DB_PATH", DEFAULT_DB_PATH)


def set_db_path(path: str | None):
    """Set the Colmi SQLite path for subsequently-created ring devices."""
    global DB_PATH
    if path:
        DB_PATH = str(Path(path).expanduser())

# ---------------------------------------------------------------------------
# Protocol helpers
# ---------------------------------------------------------------------------

def _crc(packet: list) -> int:
    """Colmi 16-byte packet checksum: sum of bytes 0-14, & 0xFF."""
    return sum(packet[:15]) & 0xFF


def _packet(request_id: int, data: list | None = None) -> bytearray:
    """Build a 16-byte Colmi request packet with CRC."""
    payload = data or []
    pkt = [request_id] + payload + [0x00] * (14 - len(payload))
    pkt.append(_crc(pkt))
    return bytearray(pkt)


def _byte_to_bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def _bcd_to_decimal(value: int) -> int:
    return (((value >> 4) & 0x0F) * 10) + (value & 0x0F)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _local_now() -> datetime:
    """Local time on the machine running SymbioSync.

    The Colmi ring has no timezone concept -- it stores times relative to
    whatever clock you set.  Sending local time means sleep bed/wake times
    come back in the human's local timezone, which is what they expect to see.
    """
    return datetime.now().astimezone()


def _iso_from_epoch(ts: float) -> str | None:
    """UTC ISO timestamp for an epoch value, or None when unavailable."""
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _metric_snapshot(value: int | float | bool | None, captured_at: float,
                     *, now: float | None = None, current_window: float = 5.0,
                     source: str = "colmi_live") -> dict:
    """Return a value with explicit freshness metadata.

    This is deliberately stricter than get_status(): relationship-facing reads
    must not let stale cached values masquerade as current body state.
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
        "captured_at": _iso_from_epoch(captured_at),
        "age_seconds": round(age, 1) if age is not None else None,
        "freshness": freshness,
        "source": source if captured_at else None,
    }


# --- Request builders ---

def request_realtime_hr() -> bytearray:
    """Start real-time heart rate streaming (request id 0x69, type=HR, action=start)."""
    return _packet(0x69, [0x01, 0x01])

def request_stop_hr() -> bytearray:
    return _packet(0x6A, [0x01, 0x00, 0x00])

def request_spo2_start() -> bytearray:
    return _packet(0x69, [0x03, 0x01])

def request_spo2_stop() -> bytearray:
    return _packet(0x6A, [0x03, 0x00, 0x00])

def request_today_sports() -> bytearray:
    return _packet(0x48, [])

def request_battery() -> bytearray:
    return _packet(0x03, [])

def request_set_time(target: datetime | None = None) -> bytearray:
    t = target or _local_now()
    data = [
        _byte_to_bcd(t.year % 2000),
        _byte_to_bcd(t.month),
        _byte_to_bcd(t.day),
        _byte_to_bcd(t.hour),
        _byte_to_bcd(t.minute),
        _byte_to_bcd(t.second),
        0x01,
    ]
    return _packet(REQ_SET_TIME, data)


# ---------------------------------------------------------------------------
# Sleep data types, parser, and scoring
# ---------------------------------------------------------------------------

class SleepType(IntEnum):
    NODATA = 0x00
    ERROR  = 0x01
    LIGHT  = 0x02
    DEEP   = 0x03
    REM    = 0x04
    AWAKE  = 0x05
    MOTION = 0x10
    REST   = 0x20


def _sleep_type_name(raw_type: int) -> str:
    if raw_type in SleepType._value2member_map_:
        return SleepType(raw_type).name.lower()
    return f"unknown_0x{raw_type:02x}"


def parse_sleep_packets(packets: list[bytes]) -> dict | None:
    """Parse Colmi BigData sleep response (0xBC 0x27).

    Format per https://colmi.puxtril.com/bigdata/ :
      BigDataResponse header (6 bytes):
        magic(u8=0xBC), dataId(u8=0x27), dataLen(u16le), crc16(u16le)
      Payload:
        sleepDays(u8)           -- number of day records
        SleepDay[]:
          daysAgo(u8)           -- 0 = today, 1 = yesterday, etc.
          curDayBytes(u8)       -- byte count for this day (includes 4 bytes of start/end)
          sleepStart(i16le)     -- minutes after midnight
          sleepEnd(i16le)       -- minutes after midnight
          SleepPeriod[]:        -- (curDayBytes - 4) / 2 periods
            type(u8)            -- SleepType enum
            minutes(u8)
    """
    if not packets:
        return None
    first_packet = packets[0]
    if len(first_packet) < 6 or first_packet[0] != BIG_DATA_MAGIC or first_packet[1] != SLEEP_DATA_ID:
        return None

    declared_length = int.from_bytes(first_packet[2:4], "little")
    crc16 = int.from_bytes(first_packet[4:6], "little")

    # Assemble payload after the 6-byte BigData header
    data = bytearray(first_packet[6:])
    for pkt in packets[1:]:
        data.extend(pkt)

    if len(data) < 1:
        return None

    pos = 0
    sleep_days_count = data[pos]
    pos += 1

    days = []
    segments = []
    totals = {}
    total_duration = 0

    for day_idx in range(sleep_days_count):
        if pos + 2 > len(data):
            break

        days_ago = data[pos]
        cur_day_bytes = data[pos + 1]
        pos += 2

        day_data_end = pos + cur_day_bytes
        if day_data_end > len(data):
            day_data_end = len(data)

        if pos + 4 > len(data):
            break

        sleep_start = struct.unpack_from('<h', data, pos)[0]
        sleep_end = struct.unpack_from('<h', data, pos + 2)[0]
        pos += 4

        periods = []
        day_offset = 0
        while pos + 1 < day_data_end:
            raw_type = data[pos]
            minutes = data[pos + 1]
            pos += 2

            type_name = _sleep_type_name(raw_type)
            seg = {
                "sequence_no": len(segments),
                "sleep_type": type_name,
                "duration_minutes": int(minutes),
                "offset_minutes": int(day_offset),
                "raw_type": int(raw_type),
                "day_index": day_idx,
                "days_ago": int(days_ago),
            }
            segments.append(seg)
            if minutes > 0:
                periods.append(seg)
                totals[type_name] = int(totals.get(type_name, 0) + minutes)
                total_duration += int(minutes)
            day_offset += int(minutes)

        def _mins_to_hhmm(m):
            if m < 0:
                m = 1440 + m
            return f"{m // 60:02d}:{m % 60:02d}"

        days.append({
            "day_index": day_idx,
            "days_ago": int(days_ago),
            "cur_day_bytes": int(cur_day_bytes),
            "sleep_start": int(sleep_start),
            "sleep_end": int(sleep_end),
            "sleep_start_time": _mins_to_hhmm(sleep_start),
            "sleep_end_time": _mins_to_hhmm(sleep_end),
            "period_count": len(periods),
            "day_total_minutes": int(day_offset),
        })

    return {
        "declared_length": int(declared_length),
        "crc16": int(crc16),
        "payload_length": len(data),
        "packet_lengths": [len(p) for p in packets],
        "remaining_bytes": int(len(data) - pos),
        "sleep_days_count": int(sleep_days_count),
        "days_parsed": len(days),
        "total_duration_minutes": int(total_duration),
        "segment_count": len(segments),
        "totals": totals,
        "days": days,
        "segments": segments,
    }


def calc_sleep_score(total_min: float, deep_min: float, light_min: float,
                     awake_times: int = 0) -> int:
    """Calculate sleep quality score (0-100).

    inferred from QRing APK v1.0.1.108 (AlSleepUtil.calcSleepScore).
    70% weight = total duration (target 500 min / 8h20m).
    15% weight = free bonus (awake penalty exists but always called with 0).
    15% weight = composition (deep 20%, light 50%, absolute durations).
    """
    targets = [0.2, 0.5, 100.0, 250.0, 500.0]
    weights = [2.5, 2.5, 5.0, 5.0, 70.0, 15.0]

    if total_min <= 0:
        return 0

    actuals = [
        deep_min / total_min,    # deep ratio (target 20%)
        light_min / total_min,   # light ratio (target 50%)
        deep_min,                # deep absolute (target 100 min)
        light_min,               # light absolute (target 250 min)
        total_min,               # total duration (target 500 min)
    ]

    subtotal = 0.0
    for i in range(5):
        deviation = abs(actuals[i] - targets[i])
        score = weights[i] * (1.0 - deviation / targets[i])
        subtotal += max(0.0, score)

    # Awake bonus (15 pts minus 3.75 per wakeup; always 0 wakeups in practice)
    awake_bonus = weights[5] - (weights[5] / 4.0) * awake_times
    awake_bonus = max(0.0, awake_bonus)

    return round(subtotal + awake_bonus)


def sleep_score_label(score: int) -> str:
    if score < 60:
        return "Poor"
    elif score < 75:
        return "Fair"
    elif score < 90:
        return "Good"
    return "Excellent"


# ---------------------------------------------------------------------------
# Database (reuses existing ring_data.sqlite schema)
# ---------------------------------------------------------------------------

def _db_connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Connect to ring database, creating tables if needed."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    # Only create tables that we need for real-time recording.
    # The full schema (with syncs, gatt_services, etc.) already exists
    # from ferri_server.py usage.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rings (
            ring_id INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT NOT NULL UNIQUE,
            name TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ring_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            connected_at TEXT NOT NULL,
            disconnected_at TEXT,
            ring_name TEXT,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id)
        )
    """)
    # Add source column if missing (existing DBs from ferri_server won't have it)
    try:
        conn.execute("ALTER TABLE ring_sessions ADD COLUMN source TEXT DEFAULT 'ferri_server'")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS realtime_heart_rate (
            realtime_heart_rate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            session_id INTEGER,
            packet_id INTEGER,
            reading INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id),
            FOREIGN KEY (session_id) REFERENCES ring_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS realtime_spo2 (
            realtime_spo2_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            session_id INTEGER,
            packet_id INTEGER,
            reading INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id),
            FOREIGN KEY (session_id) REFERENCES ring_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS battery_snapshots (
            battery_snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            session_id INTEGER,
            battery INTEGER NOT NULL,
            charging INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id),
            FOREIGN KEY (session_id) REFERENCES ring_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS today_sports (
            today_sports_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            session_id INTEGER,
            steps INTEGER NOT NULL,
            calories INTEGER NOT NULL,
            distance INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id),
            FOREIGN KEY (session_id) REFERENCES ring_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sleep_raw_captures (
            sleep_capture_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ring_id INTEGER NOT NULL,
            session_id INTEGER,
            requested_at TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            packet_count INTEGER NOT NULL,
            raw_packets_json TEXT NOT NULL,
            parsed_summary_json TEXT,
            source TEXT NOT NULL,
            FOREIGN KEY (ring_id) REFERENCES rings(ring_id),
            FOREIGN KEY (session_id) REFERENCES ring_sessions(session_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sleep_segments (
            sleep_segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sleep_capture_id INTEGER NOT NULL,
            sequence_no INTEGER NOT NULL,
            sleep_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            offset_minutes INTEGER NOT NULL,
            FOREIGN KEY (sleep_capture_id) REFERENCES sleep_raw_captures(sleep_capture_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sleep_captures_completed ON sleep_raw_captures(completed_at)")

    # Subjective sleep journal â€” human's own rating alongside ring data
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sleep_journal (
            journal_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            date          TEXT NOT NULL UNIQUE,   -- YYYY-MM-DD of the night being rated
            rating        INTEGER NOT NULL,        -- 1 (terrible) to 5 (excellent)
            note          TEXT,                    -- optional free-text comment
            recorded_at   TEXT NOT NULL            -- ISO timestamp when entry was made
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sleep_journal_date ON sleep_journal(date)")
    conn.commit()
    return conn


def _db_get_or_create_ring(conn: sqlite3.Connection, address: str, name: str) -> int:
    row = conn.execute("SELECT ring_id FROM rings WHERE address = ?", (address,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute("INSERT INTO rings (address, name) VALUES (?, ?)", (address, name))
    conn.commit()
    return cur.lastrowid


def _db_start_session(db_path: str, address: str, name: str) -> tuple[int, int]:
    conn = _db_connect(db_path)
    ring_id = _db_get_or_create_ring(conn, address, name)
    cur = conn.execute(
        "INSERT INTO ring_sessions (ring_id, connected_at, ring_name, source) VALUES (?, ?, ?, 'symbiosync')",
        (ring_id, _utc_now().isoformat(), name),
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return ring_id, session_id


def _db_close_session(db_path: str, session_id: int):
    try:
        conn = _db_connect(db_path)
        conn.execute(
            "UPDATE ring_sessions SET disconnected_at = ? WHERE session_id = ?",
            (_utc_now().isoformat(), session_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _db_record_hr(db_path: str, ring_id: int, session_id: int, reading: int):
    conn = _db_connect(db_path)
    conn.execute(
        "INSERT INTO realtime_heart_rate (ring_id, session_id, reading, timestamp) VALUES (?, ?, ?, ?)",
        (ring_id, session_id, reading, _utc_now().isoformat()),
    )
    conn.commit()
    conn.close()


def _db_record_spo2(db_path: str, ring_id: int, session_id: int, reading: int):
    conn = _db_connect(db_path)
    conn.execute(
        "INSERT INTO realtime_spo2 (ring_id, session_id, reading, timestamp) VALUES (?, ?, ?, ?)",
        (ring_id, session_id, reading, _utc_now().isoformat()),
    )
    conn.commit()
    conn.close()


def _db_record_battery(db_path: str, ring_id: int, session_id: int, battery: int, charging: bool):
    conn = _db_connect(db_path)
    conn.execute(
        "INSERT INTO battery_snapshots (ring_id, session_id, battery, charging, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ring_id, session_id, battery, int(charging), _utc_now().isoformat()),
    )
    conn.commit()
    conn.close()


def _db_store_sleep_capture(db_path: str, ring_id: int, session_id: int,
                            packets: list[bytes], parsed: dict | None,
                            source: str = "symbiosync",
                            requested_at: str | None = None,
                            completed_at: str | None = None) -> int | None:
    """Store raw sleep capture and parsed segments in the database."""
    if not ring_id or not packets:
        return None
    requested_at = requested_at or _utc_now().isoformat()
    completed_at = completed_at or requested_at
    raw_packets_json = json.dumps([bytes(p).hex() for p in packets])
    parsed_summary_json = json.dumps(parsed) if parsed else None
    conn = _db_connect(db_path)
    cursor = conn.execute("""
        INSERT INTO sleep_raw_captures(
            ring_id, session_id, requested_at, completed_at, packet_count,
            raw_packets_json, parsed_summary_json, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ring_id, session_id, requested_at, completed_at, len(packets),
          raw_packets_json, parsed_summary_json, source))
    capture_id = int(cursor.lastrowid)
    if parsed and parsed.get("segments"):
        for seg in parsed["segments"]:
            conn.execute("""
                INSERT INTO sleep_segments(sleep_capture_id, sequence_no, sleep_type, duration_minutes, offset_minutes)
                VALUES (?, ?, ?, ?, ?)
            """, (capture_id, int(seg["sequence_no"]), str(seg["sleep_type"]),
                  int(seg["duration_minutes"]), int(seg["offset_minutes"])))
    conn.commit()
    conn.close()
    return capture_id


def _db_get_latest_sleep(db_path: str) -> dict | None:
    """Get the most recent parsed sleep summary from the database."""
    conn = _db_connect(db_path)
    row = conn.execute("""
        SELECT sleep_capture_id, completed_at, parsed_summary_json
        FROM sleep_raw_captures
        WHERE parsed_summary_json IS NOT NULL
        ORDER BY sleep_capture_id DESC LIMIT 1
    """).fetchone()
    conn.close()
    if not row:
        return None
    capture_id, completed_at, summary_json = row
    parsed = json.loads(summary_json) if summary_json else None
    if not parsed:
        return None
    # Add scoring for each day
    for day_info in parsed.get("days", []):
        day_segments = [s for s in parsed.get("segments", [])
                       if s.get("day_index") == day_info.get("day_index")]
        deep = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "deep")
        light = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "light")
        rem = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "rem")
        awake = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "awake")
        total = deep + light + rem + awake
        if total > 0:
            score = calc_sleep_score(total, deep, light)
            day_info["score"] = score
            day_info["score_label"] = sleep_score_label(score)
            day_info["deep_min"] = deep
            day_info["light_min"] = light
            day_info["rem_min"] = rem
            day_info["awake_min"] = awake
            day_info["total_min"] = total
    parsed["capture_id"] = capture_id
    parsed["completed_at"] = completed_at
    return parsed


def _db_sleep_journal_upsert(db_path: str, date: str, rating: int, note: str | None) -> dict:
    """Insert or update a subjective sleep journal entry for the given date."""
    conn = _db_connect(db_path)
    conn.execute(
        """INSERT INTO sleep_journal (date, rating, note, recorded_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
               rating      = excluded.rating,
               note        = excluded.note,
               recorded_at = excluded.recorded_at""",
        (date, rating, note, _utc_now().isoformat()),
    )
    conn.commit()
    row = conn.execute(
        "SELECT journal_id, date, rating, note, recorded_at FROM sleep_journal WHERE date = ?",
        (date,),
    ).fetchone()
    conn.close()
    return {"journal_id": row[0], "date": row[1], "rating": row[2], "note": row[3], "recorded_at": row[4]}


def _db_sleep_journal_get(db_path: str, date: str | None = None, limit: int = 30) -> list[dict]:
    """Retrieve journal entries. If date given, returns that night only."""
    conn = _db_connect(db_path)
    if date:
        rows = conn.execute(
            "SELECT journal_id, date, rating, note, recorded_at FROM sleep_journal WHERE date = ?",
            (date,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT journal_id, date, rating, note, recorded_at FROM sleep_journal ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [{"journal_id": r[0], "date": r[1], "rating": r[2], "note": r[3], "recorded_at": r[4]} for r in rows]


def _db_record_sports(db_path: str, ring_id: int, session_id: int, steps: int, calories: int, distance: int):
    conn = _db_connect(db_path)
    conn.execute(
        "INSERT INTO today_sports (ring_id, session_id, steps, calories, distance, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (ring_id, session_id, steps, calories, distance, _utc_now().isoformat()),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Colmi Device Plugin
# ---------------------------------------------------------------------------

class ColmiDevice(Device):
    """Colmi R02 Smart Ring BLE device."""

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self._client: BleakClient | None = None
        self._io_lock: asyncio.Lock | None = None

        # Ring IDs for DB
        self._ring_id: int = 0
        self._session_id: int = 0
        self._db_path: str = DB_PATH

        # Live readings
        self._heart_rate: int = 0
        self._spo2: int = 0
        self._steps: int = 0
        self._calories: int = 0
        self._distance: int = 0
        self._battery: int = -1
        self._charging: bool = False

        # Timestamps for readings
        self._last_hr: float = 0.0
        self._last_spo2: float = 0.0
        self._last_steps: float = 0.0
        self._last_battery: float = 0.0
        self._last_hr_response: float = 0.0

        # Cadence tracking (keepalive manages its own timing)
        self._last_hr_req: float = 0.0
        self._last_sport_req: float = 0.0
        self._last_battery_req: float = 0.0
        self._last_spo2_cycle: float = 0.0

        # HR threshold for alerts
        self._threshold: int = 0

        # Connection time for uptime
        self._connect_time: float = 0.0

        # BigData / sleep state
        self._big_data_available: bool = False
        self._big_data_notify_on: bool = False
        self._sleep_capture_active: bool = False
        self._sleep_queue: asyncio.Queue | None = None
        self._last_sleep: dict | None = None  # cached parsed sleep data

    # ------------------------------------------------------------------
    # Device ABC implementation
    # ------------------------------------------------------------------

    def _handle_disconnect(self, client: BleakClient):
        """Bleak callback when BLE drops unexpectedly."""
        self.emit_event("RING_DROP", f"BLE disconnected (connected_for={round(time.time() - self._connect_time, 1)}s)")
        self.connected = False
        self._client = None
        self._heart_rate = 0
        _db_close_session(self._db_path, self._session_id)
        if self._on_disconnect:
            self._on_disconnect(self)

    async def connect(self) -> bool:
        self.emit_event("RING_CONNECTING", self.address)
        try:
            # Use the BLEDevice object from scan if available.
            # On Windows, BleakClient(address_string) must re-discover the device,
            # which fails for short-advertising-window devices like the Colmi ring.
            # BleakClient(ble_device) uses the cached OS handle from the scan.
            ble_device = self.info.extra.get("ble_device", self.address)
            client = BleakClient(
                ble_device,
                disconnected_callback=self._handle_disconnect,
            )
            await client.connect(timeout=15.0)
            self._client = client
            self._io_lock = asyncio.Lock()
            self.connected = True
            self._connect_time = time.time()

            # MTU exchange confirms the link to the BLE stack
            try:
                await client.mtu_exchange(256)
            except Exception:
                pass

            # Start DB session
            self._ring_id, self._session_id = _db_start_session(
                self._db_path, self.address, self.name,
            )

            # Subscribe to UART notifications (real-time data)
            await client.start_notify(UART_TX, self._notification_handler)

            # Subscribe to BigData notifications (sleep, history)
            try:
                await client.start_notify(BIG_DATA_NOTIFY, self._bigdata_notification_handler)
                self._big_data_available = True
                self._big_data_notify_on = True
                self.emit_event("RING_BIGDATA", "BigData service subscribed")
            except Exception as e:
                self._big_data_available = False
                self.emit_event("RING_BIGDATA_WARN", f"BigData subscribe failed: {e}")

            # Initialize: set time, start HR, check battery
            await asyncio.sleep(0.3)
            await self._write(request_set_time(), "SET_TIME")
            await asyncio.sleep(0.2)
            await self._write(request_realtime_hr(), "HR_START")
            await asyncio.sleep(0.2)
            await self._write(request_battery(), "BATT_REQ")
            await asyncio.sleep(0.2)
            await self._write(request_today_sports(), "SPORT_REQ")

            # Reset cadence trackers
            now = time.time()
            self._last_hr_req = now
            self._last_sport_req = now
            self._last_battery_req = now
            self._last_spo2_cycle = now   # wait full SPO2_INTERVAL before first SpO2 â€” ring needs
                                          # time to settle into HR streaming first
            self._last_hr_response = now  # assume HR is "active" at connect; avoids false re-requests

            self.emit_event("RING_CONNECTED", f"{self.name} ({self.address})")

            # Auto-sync sleep data in background (don't block connect)
            if self._big_data_available:
                asyncio.create_task(self._auto_sync_sleep())

            return True

        except Exception as e:
            self.emit_event("RING_CONNECT_FAIL", str(e))
            self.connected = False
            self._client = None
            return False

    async def disconnect(self):
        if self._client and self._client.is_connected:
            try:
                await self._write(request_stop_hr(), "HR_STOP")
                await asyncio.sleep(0.1)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
        _db_close_session(self._db_path, self._session_id)
        self.connected = False
        self._client = None
        self._heart_rate = 0
        self.emit_event("RING_DISCONNECTED", self.address)

    async def send_request(self, request: str, **kwargs) -> dict:
        try:
            if request == "start_hr":
                await self._write(request_realtime_hr(), "HR_START")
                return {"ok": True}
            elif request == "stop_hr":
                await self._write(request_stop_hr(), "HR_STOP")
                return {"ok": True}
            elif request == "snapshot_hr":
                # One-shot HR reading: start streaming, wait for first valid reading, stop.
                # Returns {"ok": True, "heart_rate": N} or times out after 45s.
                return await self._snapshot_hr()
            elif request == "snapshot_spo2":
                # One-shot SpO2: pause HR, measure, resume HR.
                # Returns {"ok": True, "spo2": N} or times out after 10s.
                return await self._snapshot_spo2()
            elif request == "current_biometrics":
                return await self._current_biometrics(
                    include_spo2=bool(kwargs.get("include_spo2", False)),
                    hr_timeout=float(kwargs.get("hr_timeout", 15.0)),
                    spo2_timeout=float(kwargs.get("spo2_timeout", 45.0)),
                    max_cached_hr_age=float(kwargs.get("max_cached_hr_age", 5.0)),
                    max_cached_spo2_age=float(kwargs.get("max_cached_spo2_age", 300.0)),
                )
            elif request == "start_spo2":
                await self._write(request_spo2_start(), "SPO2_START")
                return {"ok": True}
            elif request == "stop_spo2":
                await self._write(request_spo2_stop(), "SPO2_STOP")
                return {"ok": True}
            elif request == "battery":
                await self._write(request_battery(), "BATT_REQ")
                return {"ok": True, "battery": self._battery}
            elif request == "sports":
                await self._write(request_today_sports(), "SPORT_REQ")
                return {"ok": True}
            elif request == "set_threshold":
                self._threshold = int(kwargs.get("threshold", 0))
                return {"ok": True, "threshold": self._threshold}
            elif request == "sync_sleep":
                result = await self.fetch_sleep()
                if result:
                    return {"ok": True, "sleep": result}
                return {"ok": False, "error": "sleep sync failed or no data"}
            elif request == "get_sleep":
                sleep = self._last_sleep or _db_get_latest_sleep(self._db_path)
                if sleep:
                    return {"ok": True, "sleep": sleep}
                return {"ok": False, "error": "no sleep data available"}
            elif request == "stop":
                # "stop" for ring means stop HR streaming
                await self._write(request_stop_hr(), "HR_STOP")
                return {"ok": True}
            else:
                return {"ok": False, "error": f"Unknown request: {request}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_capabilities(self) -> list[DeviceCapability]:
        return [
            DeviceCapability.HEART_RATE,
            DeviceCapability.SPO2,
            DeviceCapability.STEPS,
            DeviceCapability.BATTERY,
        ]

    def get_status(self) -> dict:
        now = time.time()
        return {
            "heart_rate": self._heart_rate,
            "spo2": self._spo2,
            "steps": self._steps,
            "calories": self._calories,
            "distance": self._distance,
            "battery": self._battery,
            "advertised_name": self.info.extra.get("advertised_name", ""),
            "charging": self._charging,
            "threshold": self._threshold,
            "last_hr_seconds_ago": round(now - self._last_hr, 1) if self._last_hr else None,
            "last_spo2_seconds_ago": round(now - self._last_spo2, 1) if self._last_spo2 else None,
            "last_steps_seconds_ago": round(now - self._last_steps, 1) if self._last_steps else None,
            "uptime_seconds": round(now - self._connect_time, 1) if self._connect_time else 0,
            "ring_id": self._ring_id,
            "session_id": self._session_id,
            "sleep": self._get_sleep_summary(),
        }

    async def _current_biometrics(self, *, include_spo2: bool = False,
                                  hr_timeout: float = 15.0,
                                  spo2_timeout: float = 45.0,
                                  max_cached_hr_age: float = 5.0,
                                  max_cached_spo2_age: float = 300.0) -> dict:
        """Explicit current-read contract for threadborn/body-state access.

        Uses a fresh live HR response unless the HR stream updated very recently.
        SpO2 is opt-in because it pauses HR and has correlated with BLE flakiness.
        Every metric is returned with freshness metadata; stale values are marked
        stale instead of being presented as current.
        """
        now = time.time()
        started_at = _utc_now().isoformat()
        if not self.connected or not self._client:
            return {
                "ok": False,
                "device": {
                    "address": self.address,
                    "name": self.name,
                    "connected": False,
                },
                "error": "ring not connected",
                "requested_at": started_at,
                "heart_rate": _metric_snapshot(self._heart_rate, self._last_hr_response, now=now),
                "spo2": _metric_snapshot(self._spo2, self._last_spo2, now=now, current_window=max_cached_spo2_age),
            }

        hr_result = None
        hr_age = now - self._last_hr_response if self._last_hr_response else None
        if not (self._heart_rate > 0 and hr_age is not None and hr_age <= max_cached_hr_age):
            hr_result = await self._snapshot_hr(timeout=hr_timeout)

        after_hr = time.time()
        heart_rate = _metric_snapshot(
            self._heart_rate,
            self._last_hr_response,
            now=after_hr,
            current_window=max_cached_hr_age,
        )
        if hr_result and not hr_result.get("ok"):
            heart_rate["error"] = hr_result.get("error", "HR current read failed")

        spo2 = _metric_snapshot(
            self._spo2,
            self._last_spo2,
            now=after_hr,
            current_window=max_cached_spo2_age,
        )
        spo2["requested"] = bool(include_spo2)

        if include_spo2:
            spo2_result = await self._snapshot_spo2(timeout=spo2_timeout)
            after_spo2 = time.time()
            spo2 = _metric_snapshot(
                self._spo2,
                self._last_spo2,
                now=after_spo2,
                current_window=max_cached_spo2_age,
            )
            spo2["requested"] = True
            if not spo2_result.get("ok"):
                spo2["error"] = spo2_result.get("error", "SpO2 current read failed")

        return {
            "ok": bool(heart_rate.get("ok") and (not include_spo2 or spo2.get("ok"))),
            "requested_at": started_at,
            "completed_at": _utc_now().isoformat(),
            "device": {
                "address": self.address,
                "name": self.name,
                "connected": self.connected,
                "battery": self._battery if self._battery >= 0 else None,
                "battery_age_seconds": round(time.time() - self._last_battery, 1) if self._last_battery else None,
            },
            "heart_rate": heart_rate,
            "spo2": spo2,
            "steps": _metric_snapshot(
                self._steps,
                self._last_steps,
                now=time.time(),
                current_window=120.0,
                source="colmi_sports",
            ),
        }

    async def keepalive(self):
        """Cadenced polling -- called every ~12s by manager, we track our own timing."""
        if not self.connected or not self._client:
            return

        now = time.time()

        # HR: re-request if no response recently
        hr_active = (now - self._last_hr_response) < HR_ACTIVE_WAIT
        if not hr_active and (now - self._last_hr_req >= HR_INTERVAL):
            try:
                await self._write(request_realtime_hr(), "HR_REQ")
                self._last_hr_req = now
            except Exception as e:
                self.emit_event("RING_HR_FAIL", str(e))

        # Sports
        if now - self._last_sport_req >= SPORTS_INTERVAL:
            try:
                await self._write(request_today_sports(), "SPORT_REQ")
                self._last_sport_req = now
            except Exception as e:
                self.emit_event("RING_SPORT_FAIL", str(e))

        # Battery
        if now - self._last_battery_req >= BATTERY_INTERVAL:
            try:
                await self._write(request_battery(), "BATT_REQ")
                self._last_battery_req = now
            except Exception as e:
                self.emit_event("RING_BATT_FAIL", str(e))

        # SpO2 cycle â€” run as detached background task so keepalive doesn't block 3s.
        # Must pause HR streaming first: sending SPO2_START while ring is in realtime
        # HR mode interrupts the HR stream and leaves the connection silent after
        # SPO2_STOP, triggering BLE supervision timeout.
        if SPO2_INTERVAL > 0 and now - self._last_spo2_cycle >= SPO2_INTERVAL:
            self._last_spo2_cycle = now   # mark now to prevent re-entry before task finishes
            asyncio.create_task(self._run_spo2_cycle())

    async def _snapshot_hr(self, timeout: float = 45.0) -> dict:
        """On-demand single HR reading. Starts HR streaming and waits for first valid value."""
        if not self.connected or not self._client:
            return {"ok": False, "error": "not connected"}
        prev_hr = self._heart_rate
        prev_response = self._last_hr_response
        try:
            await self._write(request_realtime_hr(), "HR_SNAP_START")
        except Exception as e:
            return {"ok": False, "error": str(e)}
        deadline = time.time() + timeout
        while time.time() < deadline:
            await asyncio.sleep(0.5)
            if self._last_hr_response > prev_response and self._heart_rate > 0:
                return {"ok": True, "heart_rate": self._heart_rate}
        return {"ok": False, "error": f"timeout after {timeout}s - ring did not respond"}

    async def _snapshot_spo2(self, timeout: float = 10.0) -> dict:
        """On-demand single SpO2 reading. Pauses HR, measures, resumes HR."""
        if not self.connected or not self._client:
            return {"ok": False, "error": "not connected"}
        prev_spo2 = self._last_spo2
        try:
            await self._write(request_stop_hr(), "HR_STOP_FOR_SPO2_SNAP")
            await asyncio.sleep(0.2)
            await self._write(request_spo2_start(), "SPO2_SNAP_START")
        except Exception as e:
            return {"ok": False, "error": str(e)}
        deadline = time.time() + timeout
        result = None
        while time.time() < deadline:
            await asyncio.sleep(0.5)
            if self._last_spo2 and self._last_spo2 > prev_spo2:
                result = {"ok": True, "spo2": self._spo2}
                break
        try:
            await self._write(request_spo2_stop(), "SPO2_SNAP_STOP")
            await asyncio.sleep(0.2)
            await self._resume_hr_with_retry()
        except Exception:
            pass
        return result or {"ok": False, "error": f"timeout after {timeout}s - no SpO2 response"}

    async def _run_spo2_cycle(self):
        """Background task: pause HR â†’ measure SpO2 â†’ resume HR.

        Runs detached from keepalive so it doesn't block other devices.
        Wrapping SpO2 with HR_STOP/HR_START is critical: the ring cannot
        stream HR and measure SpO2 simultaneously, and after SPO2_STOP it
        goes silent (no HR traffic) which triggers BLE supervision timeout.
        """
        if not self.connected or not self._client:
            return
        try:
            # Pause HR streaming so ring can focus on SpO2
            await self._write(request_stop_hr(), "HR_STOP_FOR_SPO2")
            await asyncio.sleep(0.2)
            await self._write(request_spo2_start(), "SPO2_REQ")
            await asyncio.sleep(3.0)
            await self._write(request_spo2_stop(), "SPO2_STOP")
            await asyncio.sleep(0.2)
            # Resume HR streaming with verification
            await self._resume_hr_with_retry()
        except Exception as e:
            self.emit_event("RING_SPO2_FAIL", str(e))
            # Best-effort HR resume even after error
            try:
                await self._resume_hr_with_retry()
            except Exception:
                pass

    async def _resume_hr_with_retry(self, max_attempts: int = 3, verify_wait: float = 5.0):
        """Resume HR streaming and verify it actually took.

        After SPO2_STOP the ring can go silent. If the first HR_START doesn't
        elicit a response within verify_wait seconds, retry up to max_attempts.
        This prevents the BLE supervision timeout that kills the connection.
        """
        for attempt in range(1, max_attempts + 1):
            if not self.connected or not self._client:
                return
            before = self._last_hr_response
            await self._write(request_realtime_hr(), f"HR_RESUME_{'RETRY' if attempt > 1 else 'OK'}({attempt}/{max_attempts})")
            # Wait and check if ring responded
            await asyncio.sleep(verify_wait)
            if self._last_hr_response > before:
                if attempt > 1:
                    self.emit_event("RING_HR_RESUME", f"HR resumed after {attempt} attempt(s)")
                return  # success â€” ring is streaming again
            self.emit_event("RING_HR_RESUME_WARN", f"no HR response after attempt {attempt}/{max_attempts}")

    @classmethod
    def scan_filter(cls, name: str, address: str) -> bool:
        return any(n in name for n in RING_NAMES) if name else False

    @classmethod
    def device_type_name(cls) -> str:
        return "colmi"

    # ------------------------------------------------------------------
    # BLE I/O
    # ------------------------------------------------------------------

    async def _write(self, packet: bytearray, label: str = ""):
        if not self.connected or not self._client:
            raise RuntimeError("ring not connected")
        async with self._io_lock:
            await self._client.write_gatt_char(UART_RX, packet, response=False)

    def _notification_handler(self, sender, data: bytearray):
        """Parse incoming packets from the ring."""
        if len(data) < 2:
            return

        request_id = data[0] & 0x7F

        if request_id == REQ_START_REALTIME:
            if len(data) < 4:
                return
            reading_type = data[1]
            error_code = data[2]
            value = data[3]
            if error_code != 0:
                return

            if reading_type == 0x01:  # Heart rate
                self._last_hr_response = time.time()
                if value > 0 and 30 < value < 220:
                    self._heart_rate = value
                    self._last_hr = time.time()
                    self.emit_event("RING_HR", f"{value} BPM")
                    try:
                        _db_record_hr(self._db_path, self._ring_id, self._session_id, value)
                    except Exception:
                        pass
                    # Threshold check
                    if self._threshold > 0 and value > self._threshold:
                        self.emit_event("RING_HR_ALERT", f"{value} BPM exceeds threshold {self._threshold}")

            elif reading_type == 0x03 and value > 0:  # SpO2
                if 50 < value <= 100:
                    self._spo2 = value
                    self._last_spo2 = time.time()
                    self.emit_event("RING_SPO2", f"{value}%")
                    try:
                        _db_record_spo2(self._db_path, self._ring_id, self._session_id, value)
                    except Exception:
                        pass

        elif request_id == REQ_TODAY_SPORTS:
            if len(data) >= 13:
                steps = (data[1] << 16) | (data[2] << 8) | data[3]
                calories = (data[7] << 16) | (data[8] << 8) | data[9]
                distance = (data[10] << 16) | (data[11] << 8) | data[12]
                self._steps = steps
                self._calories = calories
                self._distance = distance
                self._last_steps = time.time()
                self.emit_event("RING_STEPS", f"steps={steps} cal={calories}")
                try:
                    _db_record_sports(self._db_path, self._ring_id, self._session_id, steps, calories, distance)
                except Exception:
                    pass

        elif request_id == REQ_BATTERY:
            if len(data) > 2:
                self._battery = data[1]
                self._charging = bool(data[2])
                self._last_battery = time.time()
                self.emit_event("RING_BATT", f"{data[1]}% {'charging' if data[2] else ''}")
                try:
                    _db_record_battery(self._db_path, self._ring_id, self._session_id, data[1], bool(data[2]))
                except Exception:
                    pass

        elif request_id == REQ_SET_TIME:
            self.emit_event("RING_TIME_SET", "clock synchronized")

    def _bigdata_notification_handler(self, sender, data: bytearray):
        """Handle BigData service notifications (sleep data, etc.)."""
        if not data:
            return
        packet_bytes = bytes(data)
        if self._sleep_capture_active and self._sleep_queue is not None:
            self._sleep_queue.put_nowait(packet_bytes)

    async def fetch_sleep(self) -> dict | None:
        """Fetch sleep data from the ring via BigData protocol."""
        if not self.connected or not self._client:
            return None
        if not self._big_data_available:
            self.emit_event("RING_SLEEP_SKIP", "BigData service unavailable")
            return None

        self._sleep_queue = asyncio.Queue()
        self._sleep_capture_active = True
        requested_at = _utc_now().isoformat()
        packets = []

        try:
            # Send sleep data request via BigData WRITE characteristic
            request = bytearray([BIG_DATA_MAGIC, SLEEP_DATA_ID, 0x00, 0x00, 0xFF, 0xFF])
            async with self._io_lock:
                await self._client.write_gatt_char(BIG_DATA_WRITE, request, response=False)
            self.emit_event("RING_SLEEP_REQ", f"requesting sleep data ({request.hex()})")

            # Collect response packets
            declared_payload_length = None
            while True:
                try:
                    timeout = 2.0 if packets else 10.0
                    data = await asyncio.wait_for(self._sleep_queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    if packets:
                        break  # got some data, idle timeout
                    self.emit_event("RING_SLEEP_TIMEOUT", "timeout waiting for sleep data")
                    return None
                packets.append(bytes(data))
                # Check if first packet declares payload length
                if len(packets) == 1 and len(data) >= 4 and data[0] == BIG_DATA_MAGIC and data[1] == SLEEP_DATA_ID:
                    declared_length = int.from_bytes(data[2:4], "little")
                    declared_payload_length = max(0, declared_length - 2)
                # Check completion conditions
                payload_length = max(0, len(packets[0]) - 8) + sum(len(p) for p in packets[1:])
                if declared_payload_length is not None and payload_length >= declared_payload_length:
                    break
                if len(data) < 20:
                    break  # short tail packet = end of stream
        finally:
            self._sleep_capture_active = False
            self._sleep_queue = None

        if not packets:
            return None

        # Parse
        parsed = parse_sleep_packets(packets)
        if parsed is None:
            parsed = {
                "declared_length": None,
                "payload_length": sum(len(p) for p in packets),
                "segments": [],
                "segment_count": 0,
                "totals": {},
                "total_duration_minutes": 0,
            }

        # Store in DB
        completed_at = _utc_now().isoformat()
        capture_id = _db_store_sleep_capture(
            self._db_path, self._ring_id, self._session_id,
            packets, parsed, source="symbiosync",
            requested_at=requested_at, completed_at=completed_at,
        )

        # Score each day
        for day_info in parsed.get("days", []):
            day_segments = [s for s in parsed.get("segments", [])
                           if s.get("day_index") == day_info.get("day_index")]
            deep = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "deep")
            light = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "light")
            rem = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "rem")
            awake = sum(s["duration_minutes"] for s in day_segments if s["sleep_type"] == "awake")
            total = deep + light + rem + awake
            if total > 0:
                score = calc_sleep_score(total, deep, light)
                day_info["score"] = score
                day_info["score_label"] = sleep_score_label(score)
                day_info["deep_min"] = deep
                day_info["light_min"] = light
                day_info["rem_min"] = rem
                day_info["awake_min"] = awake
                day_info["total_min"] = total

        parsed["capture_id"] = capture_id
        parsed["completed_at"] = completed_at
        self._last_sleep = parsed

        totals = parsed.get("totals", {})
        total_min = parsed.get("total_duration_minutes", 0)
        self.emit_event("RING_SLEEP_CAPTURE",
                        f"capture_id={capture_id} packets={len(packets)} "
                        f"total={total_min}m totals={totals}")
        return parsed

    async def _auto_sync_sleep(self):
        """Auto-fetch sleep data after connect (background task)."""
        try:
            await asyncio.sleep(2.0)  # let init complete
            result = await self.fetch_sleep()
            if result and result.get("total_duration_minutes", 0) > 0:
                days = result.get("days", [])
                if days:
                    last = days[0]
                    self.emit_event("RING_SLEEP_SYNC",
                                    f"Last night: {last.get('total_min', 0)}m, "
                                    f"score={last.get('score', '?')} ({last.get('score_label', '?')})")
        except Exception as e:
            self.emit_event("RING_SLEEP_WARN", f"auto-sync failed: {e}")

    def _get_sleep_summary(self) -> dict | None:
        """Get a compact sleep summary for status API."""
        sleep = self._last_sleep
        if not sleep:
            sleep = _db_get_latest_sleep(self._db_path)
            if sleep:
                self._last_sleep = sleep
        if not sleep:
            return None
        days = sleep.get("days", [])
        if not days:
            return None
        # Return most recent night
        last = days[0]

        return {
            "days_ago": last.get("days_ago", 0),
            "total_min": last.get("total_min", 0),
            "deep_min": last.get("deep_min", 0),
            "light_min": last.get("light_min", 0),
            "rem_min": last.get("rem_min", 0),
            "awake_min": last.get("awake_min", 0),
            "score": last.get("score", 0),
            "score_label": last.get("score_label", ""),
            "bed_time": last.get("sleep_start_time", ""),
            "wake_time": last.get("sleep_end_time", ""),
            "capture_time": sleep.get("completed_at", ""),
            "nights_available": len(days),
        }

    # ------------------------------------------------------------------
    # UI contribution
    # ------------------------------------------------------------------

    @classmethod
    def tab_label(cls) -> str:
        return "Health Ring"

    @classmethod
    def tab_description(cls) -> str:
        return "Colmi R02 smart ring: heart rate, SpO2, steps, calories, battery monitoring."

    @classmethod
    def control_html(cls) -> str:
        return """
    <div class="control-grid">

        <!-- Live Heart Rate -->
        <div class="card" style="text-align: center;">
            <div class="card-title">Heart Rate</div>
            <div id="colmi-hr-value" style="font-size: 3rem; font-weight: 700; color: var(--accent-warm); margin: 12px 0;">--</div>
            <div style="font-size: 0.9rem; color: var(--text-dim);">BPM</div>
            <div id="colmi-hr-age" style="font-size: 0.75rem; color: var(--text-dim); margin-top: 4px;"></div>
        </div>

        <!-- SpO2 -->
        <div class="card" style="text-align: center;">
            <div class="card-title">Blood Oxygen</div>
            <div id="colmi-spo2-value" style="font-size: 3rem; font-weight: 700; color: var(--accent-cyan); margin: 12px 0;">--</div>
            <div style="font-size: 0.9rem; color: var(--text-dim);">SpO2 %</div>
            <div id="colmi-spo2-age" style="font-size: 0.75rem; color: var(--text-dim); margin-top: 4px;"></div>
        </div>

        <!-- Steps / Activity -->
        <div class="card">
            <div class="card-title">Activity</div>
            <div style="margin-top: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: var(--text-dim);">Steps</span>
                    <span id="colmi-steps" style="font-weight: 600;">--</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: var(--text-dim);">Calories</span>
                    <span id="colmi-calories" style="font-weight: 600;">--</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-dim);">Distance</span>
                    <span id="colmi-distance" style="font-weight: 600;">--</span>
                </div>
            </div>
        </div>

        <!-- Battery -->
        <div class="card">
            <div class="card-title">Ring Status</div>
            <div style="margin-top: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: var(--text-dim);">Battery</span>
                    <span id="colmi-battery" style="font-weight: 600;">--</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: var(--text-dim);" title="Time since the ring last connected to SymbioSync.">Connected for</span>
                    <span id="colmi-uptime" style="font-weight: 600;">--</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: var(--text-dim);">Status</span>
                    <span id="colmi-status-text" style="font-weight: 600;">Not connected</span>
                </div>
            </div>
        </div>

        <!-- HR Threshold -->
        <div class="card">
            <div class="card-title">Heart Rate Alert</div>
            <p style="font-size: 0.8rem; color: var(--text-dim); margin: 8px 0;">Set a BPM threshold. When exceeded, an alert fires in the log. Set to 0 to disable.</p>
            <div class="slider-group" style="margin-top: 8px;">
                <div class="slider-label">
                    <span>Threshold</span>
                    <span class="slider-value" id="colmi-threshold-value">0</span>
                </div>
                <input type="range" id="colmi-threshold-slider" min="0" max="200" value="0" step="5"
                    oninput="document.getElementById('colmi-threshold-value').textContent = this.value == 0 ? 'Off' : this.value + ' BPM'">
            </div>
            <button class="btn btn-primary" onclick="colmiSetThreshold()" style="width: 100%; margin-top: 8px;">Set Threshold</button>
        </div>

        <!-- Sleep Data -->
        <div class="card" style="grid-column: 1 / -1;">
            <div class="card-title">
                Sleep
                <button class="btn btn-small" onclick="colmiSyncSleep()" style="float: right; font-size: 0.75rem; padding: 4px 10px;">Sync Sleep</button>
            </div>
            <div id="colmi-sleep-summary" style="margin-top: 8px;">
                <div style="color: var(--text-dim); font-style: italic;">No sleep data yet. Click "Sync Sleep" or wait for auto-sync.</div>
            </div>
        </div>

    </div>
"""

    @classmethod
    def control_js(cls) -> str:
        return """
// === Colmi ring plugin controls ===

function colmiSetThreshold() {
    var threshold = parseInt(document.getElementById('colmi-threshold-slider').value);
    // Find a colmi device address
    var addr = null;
    Object.entries(deviceState.devices || {}).forEach(function(entry) {
        if (entry[1].connected && entry[1].device_type === 'colmi') {
            addr = entry[0];
        }
    });
    if (!addr) { addr = 'all'; }
    sendWS({ action: 'request', address: addr, request: 'set_threshold', params: { threshold: threshold } });
}

function colmiUpdateDisplay(data) {
    var ring = null;
    Object.values(data.devices || {}).forEach(function(d) {
        if (d.connected && d.device_type === 'colmi') {
            ring = d;
        }
    });

    if (!ring) {
        document.getElementById('colmi-hr-value').textContent = '--';
        document.getElementById('colmi-spo2-value').textContent = '--';
        document.getElementById('colmi-steps').textContent = '--';
        document.getElementById('colmi-calories').textContent = '--';
        document.getElementById('colmi-distance').textContent = '--';
        document.getElementById('colmi-battery').textContent = '--';
        document.getElementById('colmi-uptime').textContent = '--';
        document.getElementById('colmi-status-text').textContent = 'Not connected';
        document.getElementById('colmi-hr-age').textContent = '';
        document.getElementById('colmi-spo2-age').textContent = '';
        return;
    }

    var s = ring.status || {};

    // Heart rate
    var hr = s.heart_rate || 0;
    document.getElementById('colmi-hr-value').textContent = hr > 0 ? hr : '--';
    if (s.last_hr_seconds_ago !== null && s.last_hr_seconds_ago !== undefined) {
        var age = Math.round(s.last_hr_seconds_ago);
        document.getElementById('colmi-hr-age').textContent = age < 10 ? 'live' : age + 's ago';
    } else {
        document.getElementById('colmi-hr-age').textContent = '';
    }

    // SpO2
    var spo2 = s.spo2 || 0;
    document.getElementById('colmi-spo2-value').textContent = spo2 > 0 ? spo2 : '--';
    if (s.last_spo2_seconds_ago !== null && s.last_spo2_seconds_ago !== undefined) {
        var spo2Age = Math.round(s.last_spo2_seconds_ago);
        document.getElementById('colmi-spo2-age').textContent = spo2Age < 30 ? 'recent' : spo2Age + 's ago';
    } else {
        document.getElementById('colmi-spo2-age').textContent = '';
    }

    // Activity
    document.getElementById('colmi-steps').textContent = s.steps > 0 ? s.steps.toLocaleString() : '0';
    document.getElementById('colmi-calories').textContent = s.calories > 0 ? s.calories + ' kcal' : '0';
    if (s.distance > 0) {
        var meters = s.distance / 100;
        var miles = meters / 1609.344;
        var distText = meters < 1000
            ? meters.toFixed(0) + ' m / ' + miles.toFixed(2) + ' mi'
            : (meters / 1000).toFixed(2) + ' km / ' + miles.toFixed(2) + ' mi';
        document.getElementById('colmi-distance').textContent = distText;
    } else {
        document.getElementById('colmi-distance').textContent = '0';
    }

    // Battery
    var battText = s.battery >= 0 ? s.battery + '%' : '--';
    if (s.charging) battText += ' (charging)';
    document.getElementById('colmi-battery').textContent = battText;

    // Uptime
    document.getElementById('colmi-uptime').textContent = formatUptime(s.uptime_seconds);

    // Status
    document.getElementById('colmi-status-text').textContent = 'Connected';

    // Threshold display
    if (s.threshold > 0) {
        document.getElementById('colmi-threshold-value').textContent = s.threshold + ' BPM';
        document.getElementById('colmi-threshold-slider').value = s.threshold;
    }

    // Sleep data
    var sleepEl = document.getElementById('colmi-sleep-summary');
    if (s.sleep && s.sleep.total_min > 0) {
        var sl = s.sleep;
        var hours = Math.floor(sl.total_min / 60);
        var mins = sl.total_min % 60;
        var scoreColor = sl.score >= 90 ? '#4ade80' : sl.score >= 75 ? '#a78bfa' : sl.score >= 60 ? '#fbbf24' : '#f87171';
        var barWidth = function(val) { return Math.round((val / sl.total_min) * 100); };
        sleepEl.innerHTML =
            '<div style="display: flex; align-items: baseline; gap: 16px; margin-bottom: 12px;">' +
                '<div style="font-size: 2.2rem; font-weight: 700; color: ' + scoreColor + ';">' + sl.score + '</div>' +
                '<div style="font-size: 1rem; color: var(--text-dim);">' + sl.score_label + '</div>' +
                '<div style="margin-left: auto; font-size: 0.85rem; color: var(--text-dim);">' + sl.bed_time + ' - ' + sl.wake_time + '</div>' +
            '</div>' +
            '<div style="font-size: 1.1rem; margin-bottom: 8px;">' + hours + 'h ' + mins + 'm total</div>' +
            '<div style="display: flex; height: 12px; border-radius: 6px; overflow: hidden; margin-bottom: 8px;">' +
                '<div style="width: ' + barWidth(sl.deep_min) + '%; background: #6366f1;" title="Deep"></div>' +
                '<div style="width: ' + barWidth(sl.light_min) + '%; background: #a78bfa;" title="Light"></div>' +
                '<div style="width: ' + barWidth(sl.rem_min) + '%; background: #38bdf8;" title="REM"></div>' +
                '<div style="width: ' + barWidth(sl.awake_min) + '%; background: #f87171;" title="Awake"></div>' +
            '</div>' +
            '<div style="display: flex; gap: 16px; font-size: 0.8rem; color: var(--text-dim);">' +
                '<span style="color: #6366f1;">Deep ' + sl.deep_min + 'm</span>' +
                '<span style="color: #a78bfa;">Light ' + sl.light_min + 'm</span>' +
                '<span style="color: #38bdf8;">REM ' + sl.rem_min + 'm</span>' +
                '<span style="color: #f87171;">Awake ' + sl.awake_min + 'm</span>' +
            '</div>' +
            (sl.nights_available > 1 ? '<div style=\"font-size: 0.75rem; color: var(--text-dim); margin-top: 6px;\">' + sl.nights_available + ' nights available</div>' : '') +
            '<div style=\"font-size: 0.7rem; color: var(--text-dim); margin-top: 8px; font-style: italic;\">Bed/wake times are ring-estimated from movement and heart rate. Wake time may lag actual waking if you stayed still (reading, resting). Step increases override sleep detection.</div>';
    }
}

function colmiSyncSleep() {
    var addr = null;
    Object.entries(deviceState.devices || {}).forEach(function(entry) {
        if (entry[1].connected && entry[1].device_type === 'colmi') {
            addr = entry[0];
        }
    });
    if (!addr) { return; }
    sendWS({ action: 'request', address: addr, request: 'sync_sleep' });
}

// Hook into global status updates
if (!window._pluginStatusHooks) window._pluginStatusHooks = [];
window._pluginStatusHooks.push(colmiUpdateDisplay);
"""

    # ------------------------------------------------------------------
    # Companion skill content
    # ------------------------------------------------------------------

    @classmethod
    def skill_section(cls, devices: list[dict], base_url: str) -> str:
        device_lines = ""
        for d in devices:
            s = d.get("status", {})
            device_lines += f"- **{d.get('name', '?')}** (`{d.get('address', '?')}`)"
            if s.get("battery", -1) >= 0:
                device_lines += f" - Battery: {s['battery']}%"
            device_lines += "\n"

        return f"""## Health Ring (Colmi R02)

{device_lines if device_lines else "No health ring currently connected."}

## Biometric Data Available

The ring provides real-time physiological data:

- **Heart Rate** (BPM): Updated every few seconds when ring is worn and active
- **Blood Oxygen** (SpO2 %): Measured cyclically, takes ~3s per reading
- **Steps / Calories / Distance**: Today's activity totals
- **Battery**: Ring charge level and charging status

## Reading Biometrics

```bash
# Get current status (includes all biometric readings)
curl -s {base_url}/api/status | jq '.devices'
```

Heart rate is in the device status under `status.heart_rate`.
Check `status.last_hr_seconds_ago` to know how fresh the reading is.
Under 10s = live. Over 60s = ring may be idle or off-finger.

## Heart Rate Ranges

- **40-60**: Resting (sleep or deep relaxation)
- **60-80**: Normal resting
- **80-100**: Light activity or mild arousal
- **100-120**: Moderate activity or elevated state
- **120-150**: Active exercise or high arousal
- **150+**: Intense exertion

## Biometric Etiquette

**When to check HR silently:**
- As context for other decisions (is the human resting or active?)
- To inform touch intensity (lower intensity if HR is already elevated)
- During sleep (ring logs HR every 30s; don't disturb)

**When to mention HR:**
- If asked directly
- If threshold alert fires (human set it for a reason)
- If pattern is unusual (sudden spike during rest, or very low during activity)

**When NOT to check:**
- Don't poll obsessively. The ring streams data; it arrives when it arrives.
- Don't narrate every reading. "Your heart rate is 72" is not interesting.
- Don't diagnose. You have data, not a medical degree.

## Sleep Data

The ring captures sleep data overnight (deep, light, REM, awake stages). Data is auto-synced on connect.

**Sleep scores (0-100):**
- **90-100**: Excellent (optimal duration and composition)
- **75-89**: Good
- **60-74**: Fair
- **0-59**: Poor (too short, too long, or poor composition)

**How to use sleep data:**
- Check sleep score for context on the human's state. Low score = they may be tired or fragile.
- Deep sleep under 60 minutes suggests poor recovery.
- High awake time suggests disrupted sleep.
- Don't lecture. Offer gentleness if the data suggests they need it.

**Important caveat:** Bed and wake times are ring-estimated from movement + heart rate. The wake time may lag actual waking if the person stayed still after waking (reading, resting in bed, scrolling phone). If the step counter increased during a "sleep" window, the person was awake -- steps override sleep detection. Do not treat ring sleep times as precise.

## Per-Device Requests

| Method | Endpoint | Body JSON | Description |
|--------|----------|-----------|-------------|
| POST | `/api/device/{{address}}/request` | `{{"request":"set_threshold","params":{{"threshold":100}}}}` | Set HR alert threshold |
| POST | `/api/device/{{address}}/request` | `{{"request":"battery"}}` | Request battery level |
| POST | `/api/device/{{address}}/request` | `{{"request":"start_spo2"}}` | Trigger SpO2 measurement |
| POST | `/api/device/{{address}}/request` | `{{"request":"sports"}}` | Request step/calorie update |
| POST | `/api/device/{{address}}/request` | `{{"request":"sync_sleep"}}` | Fetch sleep data from ring |
| POST | `/api/device/{{address}}/request` | `{{"request":"get_sleep"}}` | Get cached/stored sleep data |
"""
