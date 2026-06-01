# Colmi R0x SpO2 — SOLVED (BigData blood-oxygen path)

*Reverse-engineered + verified live against R06_8945 on 2026-05-31. This is the
path that actually works; the realtime path does not. Written for the SymbioSync
repo so the next person (or instance) doesn't re-walk the dead end.*

---

## TL;DR

- The **realtime SpO2 path** SymbioSync used for months (request `0x69` type `0x03`,
  parsed off the HR notification channel) **does not work on this ring.**
  Proof: `realtime_spo2` table had **0 rows across 17 days / 1091 sessions** while
  `realtime_heart_rate` had 26,417. It also *destabilized BLE* (pauses HR → ring
  goes silent after `SPO2_STOP` → supervision timeout → the reconnect loop).
- The **working path** is the **BigData blood-oxygen read, data-id `0x2A` (42)** —
  the same BigData channel `fetch_sleep()` already rides. It does **not** pause HR,
  so it does not cause disconnects.
- Replacing the realtime cycle with the BigData read fixes **both** the missing
  SpO2 **and** (hypothesis, pending long-session confirmation) the disconnects.

## The request (verified live)

```
char:   BIG_DATA_WRITE  = DE5BF72A-D711-4E47-AF26-65E3012A5DC7
bytes:  BC 2A 00 00 FF FF
```
This is the "empty/all" form of `LargeDataHandler.addHeader(0x2A, ∅)`:
`[0xBC, dataId, len_u16le, crc16_u16le, ...payload]`, where an empty payload is
encoded as `len=0, crc=0xFFFF` (CRC16.calcCrc16 returns 0xFFFF for empty input).
The form is endianness-immune (symmetric bytes) and needs no CRC. The app normally
sends `addHeader(0x2A, {dayOffset})` with a real CRC, but the empty form returns
all available days and is what we use.

## The response (verified live)

```
char:   BIG_DATA_NOTIFY = DE5BF729-D711-4E47-AF26-65E3012A5DC7
header (6 bytes): BC 2A <len_u16le> <crc16_u16le>
payload: (len / 49) day-records, 49 bytes each:
    rec[0]            = days_ago (0 = today)
    rec[1,3,..,47]    = 24 hourly MAX SpO2 %   (odd offsets)
    rec[2,4,..,48]    = 24 hourly MIN SpO2 %   (even offsets)
  value 0 = no reading that hour
```

Real capture (2026-05-31, ~09:00):
```
bc2a3100 6648 00 6060 6060 6161 6060 6060 6262 6060 6363 6060 6262 0000...
len=0x0031=49, 1 day, days_ago=0:
  00:00 96   01:00 96   02:00 97   03:00 96   04:00 96
  05:00 98   06:00 96   07:00 99   08:00 96   09:00 98
```
0x60=96, 0x61=97, 0x62=98, 0x63=99. Healthy normal curve.

Source of truth: `BloodOxygenRepository.syncAutoBloodOxygen$lambda$1` (data-id 42)
in the QRing APK — `len/49` records, per-record alternating max/min after a
`days_ago` byte. Stored app-side as `maxArray`/`minArray` (one value per hour).

## BigData data-id map (from LargeDataHandler.addHeader calls)

| id (dec/hex) | meaning | request payload |
|---|---|---|
| 39 / 0x27 | **sleep** (already used by SymbioSync) | empty `FF FF` works |
| **42 / 0x2A** | **auto blood oxygen** (hourly max/min per day) | `{dayOffset}` or empty |
| 95 / 0x5F | interval blood oxygen (finer history) | `{day, sub}` |
| 73 / 0x49 | manual (on-demand) SpO2 list `{minute,value}` | (parser only) |
| 40 / 0x28 | manual heart-rate list | — |
| 117 / 0x75 | interval heart rate | `{day, sub}` |
| 119 / 0x77 | interval temperature | `{day, sub}` |
| 71 / 0x47 | blood sugar | `{i}` |
| 72 / 0x48 | (sport/today detail variants) | — |

Framing: `addHeader(id, payload)` → `BC id len_u16le crc16_u16le payload`;
empty payload → `BC id 00 00 FF FF`. CRC16 = CRC-16/MODBUS (init 0xFFFF, poly
0xA001 reflected); returns 0xFFFF for empty input.

## SymbioSync implementation (colmi.py, 2026-05-31)

- `parse_spo2_packets()` — the parser above.
- `fetch_spo2()` — sends `BC 2A 00 00 FF FF`, collects on the BigData queue,
  sets `self._spo2` to the latest hourly reading, logs to `realtime_spo2`.
- `_auto_sync_spo2()` — runs ~3.5s after connect.
- `keepalive` — refreshes via `fetch_spo2()` every `SPO2_REFRESH` (600s). The old
  `_run_spo2_cycle` (realtime, BLE-destabilizing) is **no longer called**.
- requests `sync_spo2` / `get_spo2`; UI "Sync" button on the Blood Oxygen card.
- `_snapshot_spo2` / `current_biometrics(include_spo2)` now route through
  `fetch_spo2()` (returns latest *hourly* value, labeled — not a fresh spot read).

## Also fixed (today-sport units)

Raw `today_sports` (opcode 0x48) fields confirmed against QRing display code:
- **calorie** raw is **milli-kcal** → kcal = `raw // 1000` (QRing shows int kcal).
  `49800 → 49 kcal`. (Was displayed as "49800 kcal".)
- **distance** raw is **meters** (QRing: `getDistance()/1000` = km). UI was wrongly
  dividing by 100 → showed "7 m"; now shows raw meters (`711 m`).
- steps were already correct.

## Still open

- **Confirm the disconnect fix** over one long session (removing the realtime
  cycle should stop the 20s–5min session deaths; not yet observed live).
- **Fresh spot SpO2** (true on-demand "measure now") would use the manual path
  (data-id 73) and likely a trigger via `BloodOxygenSettingReq` opcode 44
  `{2,1}` to enable auto-measurement first. Not needed for dashboard/history.
- **Slow discovery**: the ring needs ~40s of motion to advertise; server-side
  scan window may need to be longer / repeating for clean reconnects.
