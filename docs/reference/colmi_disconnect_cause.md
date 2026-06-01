# Colmi disconnect loop — CAUSE FOUND (scanning destabilizes the link)

*Diagnosed 2026-05-31 from live logs on bubba. The "ring drops every few minutes"
problem that outlived the SpO2 fix. Strong evidence + known mechanism; the cure is
the same "pause scanning" feature audre asked for. Confirmation pending a held
session.*

---

## Symptom

With a healthy ring connection, sessions drop every ~4–12 minutes and auto-reconnect.
Today's durations (new code, SpO2 realtime cycle already removed):
```
716s, 46s, 22s, 234s, 338s, 313s, 453s, 88s ...
```
Wildly variable — which already argues against a fixed-interval command being the killer.

## Evidence — drops follow scan bursts

Pulling the 3–4 events immediately before each `RING_DROP` from the log:
```
DROP(338s): ... RECONNECT Scanning... / RECONNECT Scanning...        -> DROP
DROP(453s): ... Scanning... / RING_STEPS / Scanning... / Scanning... -> DROP
DROP(88s):  ... Scanning... / Scanning... / RING_STEPS / Scanning... -> DROP
DROP(716s): RECONNECT Scanning... / Scanning... / Scanning...        -> DROP
```
Nearly every drop is immediately preceded by a burst of `RECONNECT Scanning for N device(s)...`.

## Mechanism

The reconnect loop (`manager._reconnect_loop`) scans every ~15s (5s `BleakScanner.discover`
+ 10s sleep, manager.py ~L489) for any **remembered + enabled + not-connected** device.
On Windows / cheap BT adapters (here: RZ717), **active BLE scanning while holding a
connection destabilizes that connection** — a well-known limitation. So the loop hunting
for an *absent* device knocks the *connected* ring off the air.

In this case the absent device was the **Ferri (Lovense, not worn)**. It stayed
`enabled: True` in config, so the loop scanned for it every 15s indefinitely, and each
scan burst risked dropping the ring.

This is why removing the realtime-SpO2 cycle did NOT fix the disconnects: SpO2 was never
the cause. The scanning was.

## The fix (mostly already built)

The reconnect loop ALREADY honors an `enabled` flag (manager.py L427:
`if info.get("enabled", True)`), and there's already a `toggle_enabled` WS action
(server.py L365) → `manager.set_device_enabled(addr, enabled)`. So:

1. **Pause (disable) absent devices.** Set the Ferri's `enabled: False`. The loop stops
   scanning for it. Once the ring is connected and nothing else needs scanning, the loop
   hits `if not dropped and not remembered_not_connected: sleep(10)` (L432) and **goes
   silent** — no scans, nothing to knock the ring off. *This is the cure.*
   - The only missing piece is a **UI toggle** wired to the existing `toggle_enabled`
     action. The backend is done.

2. **Robustness improvement (recommended):** even for *un-paused* absent devices, the loop
   should **back off hard while any device is connected** — e.g. scan at most every
   2–5 min for absent devices when something is connected, instead of every 15s. That way
   a forgotten-to-pause device can't silently shred a good connection. (Today it sleeps
   30s only if a *target* device became active; a connected non-target ring doesn't slow it.)

## Experiment (armed 2026-05-31 ~11:24)

Paused the Ferri live via the WS `toggle_enabled` action (no restart). Scan count
immediately dropped from "2 device(s)" to "1 device(s)" (Ferri excluded). Prediction:
once the ring reconnects with the Ferri paused, scanning stops entirely and the ring
**holds** instead of dropping every few minutes. PENDING a held session to confirm.

> NOTE: a paused device will NOT auto-connect until re-enabled. To use the Ferri again,
> flip it back on (toggle_enabled / the future UI toggle).

## Also: the "restart never works" bug

`/api/restart` → `manager.stop()` (which `disconnect_all()` → removes every device from
`self.devices`) → `manager.start()`. Result: the device list goes to **0**, the dashboard
empties, and repopulation depends on the ring re-advertising (slow; ring needs ~40s of
motion). Restart isn't broken so much as **destructive + silent**. Fixes:
- keep remembered devices listed as "reconnecting" instead of vanishing,
- emit a status message ("manager restarted — wake the ring to reconnect"),
- (and the global status line audre asked for is the channel for that message).
