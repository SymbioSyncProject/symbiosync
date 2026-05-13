# Colmi / QRing biometric protocol notes

Source material: curated QRing APK static analysis references copied from `D:\feedback\qring\inferred_operations\sources`.

This note is about current/manual/interval biometrics. It is not a raw dump; it records only protocol evidence that affects SymbioSync's trust-bearing biometric bridge.

## Core framing

QRing/Colmi appears to have two distinct biometric surfaces:

1. **UART realtime commands** over service `6E40FFF0-...`:
   - app/ring command packets are fixed 16-byte records.
   - checksum is the sum of bytes `0..14 & 0xff`.
   - used by SymbioSync for current HR/SpO2, battery, steps/sports, set time.

2. **BigData protocol** over service `DE5BF728-...`:
   - notify characteristic `DE5BF729-...`
   - write characteristic `DE5BF72A-...`
   - header starts with `0xBC`, then data id, little-endian length, CRC16 or `ffff` for empty request.
   - used by SymbioSync for sleep data (`0x27`).
   - APK exposes additional historical/manual/interval biometric ids.

## UART current measurement evidence

From `StartHeartRateReq.java`:

- command id `0x69` starts realtime/measurement-style commands.
- `getSimpleReq(byte b)` builds `(type=b, action=0)` for types `<3`, else `(type=b, action=BCD(25))`.
- `getRealtimeHeartRate(byte b)` builds `(type=6, action=b)`.

From current SymbioSync behavior and prior protocol inference:

- HR start: `0x69 [0x01, 0x01]`
- HR stop: `0x6A [0x01, 0x00, 0x00]`
- SpO2 start: `0x69 [0x03, 0x01]`
- SpO2 stop: `0x6A [0x03, 0x00, 0x00]`

From `StopHeartRateReq.java`:

- command id `0x6A` stops measurement classes.
- stop types:
  - `1` heart rate
  - `2` blood pressure
  - `3` blood oxygen / SpO2
  - `4` fatigue
  - `5` health check
  - `7` ECG
  - `8` pressure
  - `9` blood sugar
  - `10` HRV
  - `11` temperature check

From `StartHeartRateRsp.java`:

- response payload has `type`, `errCode`, `value`, optional `sbp/dbp`.
- for HR and SpO2, `value` is the primary reading.

Current conclusion: APK supports the same current-measurement model SymbioSync is already using. The remaining reliability question is lifecycle/timing/retry behavior, not a completely different obvious one-shot command found so far.

## BigData biometric ids

From `LargeDataHandler.java`:

- `0x27` / `39`: sleep list.
- `0x28` / `40`: manual heart-rate list.
- `0x49` / `73`: manual blood oxygen / SpO2 list parser exists, but the APK-derived method reference does not show an outbound `addHeader(73, ...)`; may be incomplete/static-analysis artifact or called differently.
- `0x5F` / `95`: interval blood oxygen / SpO2.
- `0x75` / `117`: interval heart rate.
- `0x77` / `119`: interval temperature.

### BigData request shapes seen

- sleep: `addHeader(39, [day_selector, 1])`
  - SymbioSync currently uses empty request `bc270000ffff`, which works on this ring.
- manual HR: `addHeader(40, [0 or 0xff])`
  - if argument day/index is nonzero, app sends `0xff`; otherwise `0`.
- interval SpO2: `addHeader(95, [day_index, packet_index])`
- interval HR: `addHeader(117, [day_index, packet_index])`

### BigData parser layouts

Manual HR and manual SpO2 have the same layout:

- response id byte: `40` or `73`
- response offset 6: index
- response from offset 7 onward: triplets
  - first 2 bytes = minute/index (`m`) using `ByteUtil.bytesToInt`
  - third byte = value (`v`)

Interval HR and interval SpO2 have the same layout:

- response offset 6: day index
- response offset 7: interval minutes
- response offset 8: packet count
- response offset 9: packet index
- response offset 10 onward: values as unsigned bytes
- if packet count indicates more packets, app recursively requests same data id with next packet index.

Important static analysis oddity:

- `syncIntervalHeartRate(int i, ILargeDataResponse cb)` calls `syncIntervalBloodOxygenReal(i, 0, cb)` in the APK-derived reference file.
- But `syncIntervalHeartRateReal(i, packet, cb)` exists and correctly sends id `117`.
- Treat this as static-analysis/app weirdness until validated on hardware.

## Trust-bearing implications

- BigData manual/interval HR/SpO2 are historical or stored-series reads, not proven current reads.
- They may help recover recent readings when live streaming is flaky, but they cannot be treated as current unless the timestamp/index semantics are validated.
- For threadborn current-body access, SymbioSync needs explicit freshness semantics: value, capture time, age, source, and stale/unavailable flags.
- If QRing app appeared reliable, it may have been using better timing/retries, Android BLE advantages, cached/manual history, or stale UI presentation. static-analysis review so far has not proved a separate magic current-read command.

## Current SymbioSync change from this pass

Added `GET /api/biometrics/current` as a stricter endpoint than `/api/status`:

- asks connected Colmi device for a current HR read unless HR updated very recently;
- returns age/freshness metadata for HR, SpO2, steps, and battery;
- SpO2 current read is opt-in via `include_spo2=true` because it pauses HR and is destabilizing;
- stale values are explicitly marked stale/unavailable.

Next candidate work:

1. Implement/test BigData interval HR (`0x75`) as background historical harvest, not current truth.
2. Implement/test BigData interval SpO2 (`0x5f`) only after HR stability is understood.
3. Inspect app-level UI/repository code around QRing's displayed current readings to see whether it hides cache/retry delays.
