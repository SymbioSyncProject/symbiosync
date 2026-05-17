# Colmi / QRing protocol inventory

This is the ledger for Colmi / QRing protocol work. Fill it before changing
current HR, SpO2, or other biometric-adjacent behavior.

The dangerous failure mode is not "we failed to read a value." The dangerous
failure mode is a bridge that sounds more certain than it is.

## Rules for inventory work

- Do not propose implementation changes while filling the ledger.
- Do not collapse live/manual/history/cached reads into one bucket.
- Quote or cite the source artifact for every claim.
- Mark unknowns as `unknown`; do not infer silently.
- Track freshness implications separately from parser mechanics.
- Treat vendor UI behavior as evidence, not truth. The vendor app may also be
  presenting cached values as current.
- Prefer one boring row per artifact over a clever summary.

## Source artifact ledger

| Artifact / class / file | Source kind | Chinese / vendor terms | Related request id(s) | Payload shape | Response / parser fields | Lifecycle / timing / retry behavior | Live, manual, history, or cache? | Freshness implication | SymbioSync parity | Confidence | Source quote / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `symbiosync/devices/colmi.py` `request_realtime_hr()` | current implementation | n/a | `0x69` | `[0x69, 0x01, 0x01, ...]` | notify handler treats `data[1] == 0x01`, `data[2] == 0`, `data[3]` as BPM | Starts stream on connect; keepalive re-requests when no recent response; snapshot starts stream and waits for first response | presumed live stream | current only if a notification timestamp is inside the freshness window | implemented, but repeated identical values need protocol review | medium | Existing behavior, not independent protocol proof. |
| `symbiosync/devices/colmi.py` `request_spo2_start()` / `request_spo2_stop()` | current implementation | n/a | `0x69` | `[0x69, 0x03, start/stop, ...]` | notify handler treats `data[1] == 0x03`, `data[3]` as SpO2 | SpO2 pauses HR, measures, stops, resumes HR; frequent cycling has correlated with flaky BLE | presumed manual/live measurement | current only if notification timestamp is inside SpO2 window | implemented with caution; protocol still needs external confirmation | medium-low | Existing behavior and field observation. |

## Request / response matrix

| Request name | Request id | Start / stop / read | Payload bytes | Notify characteristic | Expected response bytes | Parser | Success condition | Failure / timeout behavior | Freshness boundary | Open questions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Realtime HR | `0x69` | start stream | unknown beyond current implementation | UART notify | unknown | current implementation reads `data[3]` | new response timestamp and plausible BPM | timeout if no newer response | default current window: 5s | Does repeated same BPM represent new measurement, cached stream value, or parser error? |
| Realtime SpO2 | `0x69` | start/stop measurement | unknown beyond current implementation | UART notify | unknown | current implementation reads `data[3]` | new response timestamp and plausible SpO2 | timeout if no newer response | default current window: 300s when requested | Does SpO2 require HR stop? What exact lifecycle does vendor app use? |

## Field anomalies to preserve

| Date / context | Observation | Why it matters | Current handling | Follow-up |
| --- | --- | --- | --- | --- |
| 2026-05-16/17 local testing | Thousands of repeated HR `97` rows accumulated in `data/ring_data.sqlite`. | Repeated identical biometric-adjacent values may be cached, mis-parsed, or stale. They must not be treated as reliable body-state history without protocol proof. | Rows with reading `97` were quarantined into `suspect_realtime_heart_rate` by `scripts/quarantine_colmi_hr_readings.py`, preserving a DB backup. | Identify whether `97` can be a legitimate repeated live value or indicates protocol/parser/lifecycle error. |

## Implementation parity checklist

- [ ] Inventory vendor/decompiled HR request classes.
- [ ] Inventory vendor/decompiled SpO2 request classes.
- [ ] Inventory notification parser paths for HR and SpO2.
- [ ] Inventory app lifecycle around manual/on-demand measurement.
- [ ] Compare vendor retry/timeout behavior to SymbioSync keepalive and snapshot behavior.
- [ ] Decide whether repeated identical values require explicit suspicion flags.
- [ ] Update UI/API copy so status never presents cached/stale body-state as current.
- [ ] Add tests for freshness semantics before public claims about live biometric state.

## Terms

- **Current**: received inside the endpoint's stated freshness window.
- **Stale**: value exists but is older than the freshness window or lacks capture-time proof.
- **Unavailable**: no valid value is known.
- **Live stream**: notification path that appears to push new measurements over time.
- **Manual measurement**: explicit start/read operation intended to produce a fresh value.
- **History read**: stored device history; useful, but not current body state.
- **Cached value**: previously observed value retained by app, device, or bridge.
