"""
spo2_probe.py  --  standalone, read-only SpO2 reverse-engineering probe.

Sends the QRing app's *actual* BigData blood-oxygen request (data-id 0x2A=42)
over the BigData WRITE characteristic and dumps whatever the ring returns on
the BigData NOTIFY characteristic, then parses it with the format reversed out
of BloodOxygenRepository.syncAutoBloodOxygen$lambda$1.

This does NOT use the dead realtime path (0x69/0x03) that has produced 0 rows
in 17 days. It uses the BigData channel -- the same one fetch_sleep() already
rides successfully.

PREREQ: the SymbioSync server must NOT be holding the ring (stop it first, or
use this between server restarts). Ring must be worn for a fresh reading.

Run:  python spo2_probe.py
"""

import asyncio
import sys
from bleak import BleakScanner, BleakClient

BIG_DATA_WRITE  = "DE5BF72A-D711-4E47-AF26-65E3012A5DC7"
BIG_DATA_NOTIFY = "DE5BF729-D711-4E47-AF26-65E3012A5DC7"
RING_NAMES = ["R02", "R06", "QRing", "Smart Ring", "Colmi"]
RING_ADDR  = "40:E5:A0:8C:89:45"   # R06_8945 (from ring_data.sqlite)
SCAN_SECS  = 25.0

OXY_DATA_ID   = 0x2A   # 42 = auto blood oxygen (hourly max/min per day)
SLEEP_DATA_ID = 0x27   # 39 = sleep, used as a positive control


def crc16(data: bytes) -> int:
    """CRC-16/MODBUS, exactly as com.oudmon...CRC16.calcCrc16."""
    if len(data) == 0:
        return 0xFFFF
    c = 0xFFFF
    for b in data:
        c ^= b & 0xFF
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if (c & 1) else c >> 1
    return c & 0xFFFF


def add_header(data_id: int, payload: bytes = b"") -> bytes:
    """Replicates LargeDataHandler.addHeader(int, byte[])."""
    if not payload:
        return bytes([0xBC, data_id, 0x00, 0x00, 0xFF, 0xFF])
    ln = len(payload)
    crc = crc16(payload)
    # little-endian to match the working sleep parser; fallback prints both forms
    return bytes([0xBC, data_id]) + ln.to_bytes(2, "little") + crc.to_bytes(2, "little") + payload


def parse_oxy(data: bytes):
    """Parse a data-id 0x2A response: per-day 49-byte records of hourly max/min."""
    if len(data) < 6 or data[0] != 0xBC or data[1] != OXY_DATA_ID:
        print(f"  [parse] header not 0xBC 0x2A -- got {data[:6].hex()}")
        return
    declared = int.from_bytes(data[2:4], "little")
    crc = int.from_bytes(data[4:6], "little")
    payload = data[6:]
    print(f"  [parse] declared_len={declared} crc=0x{crc:04x} payload_bytes={len(payload)}")
    rec_count = declared // 49 if declared else len(payload) // 49
    print(f"  [parse] day_records={rec_count}")
    for r in range(rec_count):
        rec = payload[r * 49:(r + 1) * 49]
        if len(rec) < 49:
            print(f"  [parse] day {r}: short record ({len(rec)}b) -- {rec.hex()}")
            continue
        days_ago = rec[0]
        maxes = list(rec[1:49:2])   # offsets 1,3,..,47
        mins  = list(rec[2:49:2])   # offsets 2,4,..,48
        nonzero = [(h, mx, mn) for h, (mx, mn) in enumerate(zip(maxes, mins)) if mx or mn]
        print(f"  [day {r}] days_ago={days_ago}  hours_with_data={len(nonzero)}")
        for h, mx, mn in nonzero:
            print(f"       {h:02d}:00  max={mx}%  min={mn}%")
        if nonzero:
            last = nonzero[-1]
            print(f"   --> latest reading this day: hour {last[0]:02d}  max {last[1]}%  min {last[2]}%")


async def main():
    print(f"scanning for ring ({SCAN_SECS:.0f}s) -- wiggle/tap the ring NOW so it advertises...")
    dev = None
    devices = await BleakScanner.discover(timeout=SCAN_SECS)
    # match by exact MAC first, then by name
    for d in devices:
        if d.address and d.address.upper() == RING_ADDR.upper():
            dev = d
            print(f"  found by MAC: {d.name}  [{d.address}]")
            break
    if not dev:
        for d in devices:
            if d.name and any(n in d.name for n in RING_NAMES):
                dev = d
                print(f"  found by name: {d.name}  [{d.address}]")
                break
    if not dev:
        print(f"  ring not seen. {len(devices)} BLE devices in range:")
        for d in devices:
            print(f"     {d.address}  {d.name!r}")
        print("  -> if list is empty: ring is asleep (wear+move it) or adapter busy.")
        print(f"  -> trying a direct connect to {RING_ADDR} anyway...")
        try:
            await probe_connect(RING_ADDR)
        except Exception as e:
            print(f"  direct connect failed: {e}")
        return

    await probe_connect(dev)


async def probe_connect(target):
    packets = []

    def on_notify(_sender, data: bytearray):
        b = bytes(data)
        packets.append(b)
        print(f"  <- NOTIFY ({len(b)}b): {b.hex()}")

    async with BleakClient(target) as client:
        print(f"connected: {client.is_connected}")
        try:
            await client.mtu_exchange(256)
        except Exception:
            pass
        await client.start_notify(BIG_DATA_NOTIFY, on_notify)
        await asyncio.sleep(0.4)

        # --- positive control: sleep (known-good), confirms the channel works ---
        req_sleep = add_header(SLEEP_DATA_ID)
        print(f"\n-> SLEEP control request: {req_sleep.hex()}")
        await client.write_gatt_char(BIG_DATA_WRITE, req_sleep, response=False)
        await asyncio.sleep(3.0)
        print(f"   sleep packets received: {len(packets)}")
        packets.clear()

        # --- the real target: blood oxygen, empty/all form ---
        req_oxy = add_header(OXY_DATA_ID)
        print(f"\n-> O2 request (empty/all form): {req_oxy.hex()}")
        await client.write_gatt_char(BIG_DATA_WRITE, req_oxy, response=False)
        await asyncio.sleep(4.0)
        if packets:
            full = b"".join(packets)
            print(f"\n   O2 RAW ({len(packets)} pkts, {len(full)}b): {full.hex()}")
            parse_oxy(full)
        else:
            print("   no O2 response to empty form -- trying offset=0 form...")
            packets.clear()
            req_oxy2 = add_header(OXY_DATA_ID, bytes([0x00]))
            print(f"-> O2 request (offset=0 form): {req_oxy2.hex()}")
            await client.write_gatt_char(BIG_DATA_WRITE, req_oxy2, response=False)
            await asyncio.sleep(4.0)
            if packets:
                full = b"".join(packets)
                print(f"\n   O2 RAW ({len(packets)} pkts, {len(full)}b): {full.hex()}")
                parse_oxy(full)
            else:
                print("   still nothing. Note the raw bytes above (if any) for analysis.")

        await client.stop_notify(BIG_DATA_NOTIFY)


if __name__ == "__main__":
    asyncio.run(main())
