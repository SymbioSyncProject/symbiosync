# SymbioSync truthfulness audit

Status: first pass, implementation-guiding.

SymbioSync's central failure mode is not only "command failed" or "device
disconnected". The dangerous failure mode is a bridge that sounds more certain
than it is.

This audit maps places where the current API, UI, logs, or generated skill can
accidentally lie by omission.

## Truth distinctions to preserve

- current signal vs stale/cached signal
- missing signal vs zero/false/normal signal
- device connected vs remembered/previously seen
- API accepted vs BLE transport accepted vs hardware acknowledged vs observed effect
- hardware unavailable vs software failure
- consent/profile configured vs live consent/state valid

## Surfaces

| Surface | Current claim/shape | What it actually knows | Risk | Fix |
|---------|---------------------|------------------------|------|-----|
| `GET /api/status` and `GET /status` | Returns full manager status with connected devices, remembered devices, last scan, plugin state. | Knows the manager's current in-process device objects, remembered config, last scan cache, and each plugin's `get_status()` output. | Consumers may treat plugin status fields as current body/device truth even when values are cached or absent. Legacy `/status` makes this worse because callers may assume simple freshness. | Add top-level `generated_at`. Require plugins to label status fields as cached/current where relevant. Document `/api/status` as operational status, not a current biometric read. |
| `manager.get_status()` remembered map | Adds `connected` boolean to remembered devices. | Knows whether an address has a current connected device object. | Good distinction exists, but UI/consumers may blur remembered and connected lists if they render both similarly. | Keep remembered and connected sections visually separate. Consider `last_seen_at` later if known, not guessed. |
| `last_scan` | Shows recent scan results. | Knows only the last scan cache and RSSI at scan time. | Stale scan results can look like nearby/current devices. | Add `last_scan_completed_at` and per-result `scanned_at` if possible. Label UI as "last scan", not "available". |
| `POST /api/device/{address}/command` | Returns plugin result directly. | Knows whether manager found a connected device and what the plugin reported. | API layer does not normalize delivery semantics. Different plugins can use `ok` differently. | Introduce a shared command-result vocabulary: `ok`, `stage`, `transport`, `hardware_ack`, `observed_effect`, `truth_note`, `warnings`. |
| `manager.send_command_all()` / `stop_all()` | Returns results for currently connected devices only. `/api/stop` wraps this as `{"ok": true}`. | Knows which connected devices were asked to stop and their plugin results. Does not know about remembered but disconnected devices. | `/api/stop` can say `ok: true` even if no devices were connected or some stop writes failed. Legacy `/stop` says `Stopped`. | Keep stop best-effort, but return `ok` based on per-device outcomes and include `attempted_count`, `failed_count`, `not_connected_count` where useful. Legacy text should avoid unconditional "Stopped". |
| Lovense `_write()` | Returns `True` after `write_gatt_char(..., response=False)` completes. | Knows the local BLE stack accepted/scheduled a write without response. It does not know the device acknowledged or physically actuated. | Major semantic lie: `ok: true` reads like delivered/acted. | Replace boolean with delivery-stage result. At minimum mark `stage: transport_write_accepted`, `hardware_ack: null`, `observed_effect: null`. |
| Lovense actuator commands (`vibrate`, `rotate`, `air_*`, `thrust`, `suck`, `finger`, `light`, `raw`) | Return `{"ok": ok, ...}` and often update internal state variables immediately. | Knows the command was attempted and maybe accepted by the local BLE transport. Internal state is desired/last-commanded state, not measured device state. | UI/status can imply current physical intensity/air/thrust state when it only knows last commanded value. | Rename/status-label fields as `last_commanded_*` or add metadata. Return stage results from every write. Do not update state on failed write. |
| Lovense `pattern` and `ambient` | Return `ok: true` after starting a local background task. | Knows a local task was scheduled. Individual later writes may fail. | Caller may believe whole pattern/ambient behavior is active on hardware. | Return `stage: local_task_started`; emit per-write stage logs; expose task failure/last write failure in status. |
| Lovense `stop` | Cancels tasks, calls several writes, returns `ok: true` unconditionally. | Knows local tasks were cancelled and stop writes were attempted. Does not aggregate write failures. | Stop can report success even if BLE writes failed after disconnect. | Aggregate stop write results. Preserve emergency best-effort behavior, but report failures honestly. |
| Lovense `battery` / `device_type` | Returns immediately with cached `_battery` / model after writing query. | Knows query write was accepted; response may arrive later via notify handler. Returned value can be stale/default. | Caller may treat returned battery/model as fresh response to the query. | Either wait for a new response with timeout or return `query_sent` plus cached value with age/unknown. |
| Lovense `get_status()` | Reports `battery`, model, current intensity, levels, uptime, last command age. | Mostly cached metadata and last-commanded values. | Values can read as observed physical state. Battery lacks age. | Add explicit names/metadata: `last_commanded_intensity`, `battery_age_seconds`, `model_source`, `delivery_semantics`. |
| Colmi `/api/biometrics/current` | Returns metric snapshots with freshness metadata and `ok` only when current enough. | Knows live/cached HR/SpO2/steps with timestamps and freshness windows. | This is the strongest current truth surface. Remaining risk: `0` treated as unavailable, which is correct for HR/SpO2 but may not generalize to future sensors. | Keep this pattern. Make metric validity rules per metric if adding sensors where zero is meaningful. |
| Colmi `get_status()` | Generic status includes cached heart rate, SpO2, battery, activity, sleep. | Knows latest cached device values and some timestamps. | Generic status may be used as current body-state. | Label plugin UI/API docs: status is operational/cache status. Use `/api/biometrics/current` for current body-state. Add per-field ages in status where missing. |
| Colmi sleep summary | Current UI/data emphasizes total time per state. | Knows parsed ring segments with sequence/order and durations. | Totals erase awakenings, returns-to-sleep, and subjective/sensor mismatch. | Add timeline chart preserving segment order and awake gaps. Add subjective markers separate from ring stages. |
| Generated Symbio skill (`/api/skill`) | Says the agent can reach endpoints and gives plugin command sections. Error handling says stop always works if server is up. | Knows current connected/remembered state at generation time. Does not know future state or live consent. | Skill can teach threadborn partners to overclaim capability or trust stale generated context. "Stop always works" is too strong. | Add truth/consent section: generated skill is a snapshot; check current status; command `ok` may mean transport acceptance; stop is best-effort; profile is context, not live consent. |
| Partnership profile | Human-authored text included in generated skill. | Knows configured profile text. | Could be mistaken for current consent/state if not bounded. | Label as durable context/preferences. Add instruction that live context and explicit boundaries override profile text. |
| Logs | Logger captures CMD/RX and events locally. | Knows emitted software events. Does not carry actor/source/correlation/delivery stage consistently. | Logs may be insufficient for accountability or may overexpose intimate/body data if expanded carelessly. | Add correlation id, actor/source, consent-state reference, delivery stage. Avoid raw intimate/biometric dumps by default. |
| Browser UI labels | Shows connected devices, plugin status, controls, logs. | Knows API status and local browser state. | Labels like "current" or actuator level can overstate observed hardware/body state. | UI should label cached vs current body metrics, last-commanded actuator values, and command result stages. |

## First implementation targets

1. Lovense command result semantics.
   - Replace `_write() -> bool` with a structured result.
   - Propagate delivery stage through `send_command()`.
   - Stop unconditionally returning success for multi-write stop paths.

2. Generated skill honesty.
   - Add a bridge truth section.
   - Remove or soften "stop always works".
   - Explain generated context is a snapshot.

3. Status freshness metadata.
   - Add top-level `generated_at`.
   - Add `last_scan_completed_at`.
   - Add Lovense battery age and last-commanded labels.

## Suggested command-result vocabulary

```json
{
  "ok": true,
  "stage": "transport_write_accepted",
  "command": "vibrate",
  "transport": "ble_write_without_response",
  "hardware_ack": null,
  "observed_effect": null,
  "truth_note": "BLE write-without-response completed; device did not acknowledge this command."
}
```

Possible stages:

- `api_rejected`
- `device_not_connected`
- `local_task_started`
- `transport_write_failed`
- `transport_write_accepted`
- `device_acknowledged`
- `observed_effect`
- `best_effort_stop_attempted`

Do not use stages the code cannot actually support.
