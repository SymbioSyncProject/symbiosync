# Measurement lifecycle map

This page summarizes the live/manual and historical/device-sync flows found so far.
For a denser implementation table, see [Command and behavior matrix](command_matrix.md).

## Shared manual/live request family

Manual/live HR, SpO2, HRV, and OneKey all reuse:

```text
StartHeartRateReq.getSimpleReq(type)
StartHeartRateRsp(type, errCode, value, sbp, dbp)
```

Type map:

| Type | APK meaning | Stop command | Notes |
| --- | --- | --- | --- |
| `1` | manual/live heart rate | `StopHeartRateReq.stopHeartRate(value)` | HR UI also polls `RealTimeHeartRate(3)` about every 20s during measurement. |
| `3` | manual/live SpO2 | `StopHeartRateReq.stopBloodOxygen(...)` | 25s countdown, 30s hard timeout, wearing detection on `errCode == 1`. |
| `5` | OneKey composite | `StopHeartRateReq.stopHealthCheck()` | HR/BP from device response; SpO2/score/fatigue are phone-generated. |
| `10` | manual/live HRV | `StopHeartRateReq.stopHrv(value)` | 75s countdown, 80s hard timeout. |

`StartHeartRateRsp` parses:

```text
[0] type
[1] errCode
[2] value
[3] sbp, if present
[4] dbp, if present
```

## Historical/device sync

| Domain | Path | Transport | Notes |
| --- | --- | --- | --- |
| HR | `syncIntervalHeartRateWithCallback` or legacy `ReadHeartRateReq` | LargeData `0x75` or UART legacy | Uses LargeData when `supportRealTimeHr`; otherwise legacy UART. Wrapper weirdness still unresolved. |
| SpO2 | `BloodOxygenRepository.syncAutoBloodOxygen(0/255)` plus SDK interval oxygen | LargeData `0x2A` and/or `0x5F` | Needs reconciliation before implementation. |
| HRV | `HRVReq` / `HRVRsp` | UART cmd `0x39` | Multi-packet 13-byte records. No LargeData HRV found. |
| Sleep | regular and lunch nap sync | LargeData `0x27`, `0x3E` | New-protocol sleep IDs still need mapping. |
| Temperature | interval temperature | LargeData `0x77` | 2-byte little-endian values divided by `100.0f`. |

## Freshness implication

Manual/live flows can produce current-ish device-reported values if a fresh response
is received and parsed. Historical sync flows produce stored device history and
must be labelled as such.
