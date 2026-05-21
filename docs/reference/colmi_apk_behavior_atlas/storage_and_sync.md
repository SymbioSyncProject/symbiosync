# Storage and sync model

The QRing app database separates device-synced, manual, app-initiated, and cloud
sync data. SymbioSync should not collapse these modes.

## Database

Observed app DB:

- `qc_database.db`
- version `55`
- 47 tables

Important mode split:

| Mode | Meaning |
| --- | --- |
| continuous/device-synced | Values harvested from device history or ongoing device records. |
| manual/spot-check | User-initiated measurement saved as a manual record. |
| app-initiated | Values started by app lifecycle, sometimes stored separately. |
| cloud sync | Server download/upload state, not device BLE state. |

## Examples

| Domain | Continuous/device-synced | Manual/app path | Notes |
| --- | --- | --- | --- |
| HR | heart rate detail tables | manual/app manual HR tables | HeartRate repository has both LargeData and legacy UART paths. |
| SpO2 | `blood_oxygen` | `blood_oxygen_manual` | Sleep summary also has `avgBloodOxygen`. |
| HRV | HRV detail tables | manual HRV, with misleading pressure names | HRV repository methods include copy-paste names like `savePressure`. |
| Sleep | old/new/lunch sleep protocol tables | manual sleep paths | New protocol and lunch nap are separate surfaces. |

## NetService

`NetService` is cloud-only. It orchestrates server to local DB and local DB to
server sync. It does not touch BLE or `BleOperateManager`.

Observed hazards:

- `downTemperature()` and `upTemperatureList()` are empty stubs.
- Existing `Heart_Rate_Action` path appears to call `downSleepDetail(...)` instead
  of `downHeartRateDetail(...)`; keep as unresolved vendor/decompiler bug.
- Upload flows collect results but appear effectively fire-and-forget.

## SymbioSync rule

A value from cloud sync, local DB, device history, live BLE response, or app
algorithm must carry provenance. Do not present them through one undifferentiated
`value` field in user-facing truth surfaces.
