# Command and behavior matrix

This matrix is the quick implementation reference for known Colmi / QRing APK
behavior. It summarizes current evidence without claiming that unresolved paths
are complete.

## UART small-data commands

UART uses the `6e40xxxx` characteristic family and 16-byte `BaseReqCmd` frames.
`CommandHandle` registers callbacks by `cmd & 0x7F`.

| Command / class | Cmd | Mode | Request shape | Response / parser | Known caller / flow | SymbioSync guidance | Confidence |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| `StartHeartRateReq` type 1 | `0x69` / 105 | manual/live HR | `StartHeartRateReq.getSimpleReq((byte)1)` | `StartHeartRateRsp`: type, errCode, value, optional sbp/dbp | HR activity manual measurement | Current-ish only when fresh response is parsed. Record as device-reported manual/live HR. | high |
| `StartHeartRateReq` type 3 | `0x69` / 105 | manual/live SpO2 | `StartHeartRateReq.getSimpleReq((byte)3)` | `StartHeartRateRsp`: type 3, errCode, value | BloodOxygenActivity manual measurement | Good next live SpO2 basis, but preserve timeout/freshness and wearing error semantics. | high |
| `StartHeartRateReq` type 5 | `0x69` / 105 | OneKey composite | `StartHeartRateReq.getSimpleReq((byte)5)` | `StartHeartRateRsp`: HR/BP fields only appear device-derived | OneKeyCheckViewModel / Activity | Do not expose as normal health feature. OneKey SpO2/score/fatigue are synthetic in APK UI. | high |
| `StartHeartRateReq` type 10 | `0x69` / 105 | manual/live HRV | `StartHeartRateReq.getSimpleReq((byte)10)` | `StartHeartRateRsp`: type 10, errCode, value | HrvActivity manual measurement | Record as manual/live HRV, separate from historical `HRVReq`. | high |
| `StopHeartRateReq.stopHeartRate(value)` | `0x6A` / 106 | stop HR | type 1 plus measured value | no clear response requirement | HR activity timeout/stop | Stop is a request, not proof the device stopped or body state changed. | high |
| `StopHeartRateReq.stopBloodOxygen(...)` | `0x6A` / 106 | stop SpO2 | type 3 | no clear response requirement | BloodOxygenActivity timeout/stop | Stop is best-effort unless response/effect is separately observed. | high |
| `StopHeartRateReq.stopHealthCheck()` | `0x6A` / 106 | stop OneKey | type 5 | no clear response requirement | OneKeyCheckViewModel.stopOnKey() | Keep OneKey experimental/synthetic-labelled. | high |
| `StopHeartRateReq.stopHrv(value)` | `0x6A` / 106 | stop HRV | type 10 plus measured value | no clear response requirement | HrvActivity timeout/stop | Stop request should be logged separately from measurement result. | high |
| `RealTimeHeartRate` | likely `0x1E` / 30 response | live HR poll/notify | `RealTimeHeartRate(3)` during HR manual measurement | `RealTimeHeartRateRsp.acceptData`: value at payload byte 0 / raw data[1] | HR activity runnable every ~20s | Check current SymbioSync parser: `0x1E` and `0x69` have different value offsets. | medium-high |
| `ReadHeartRateReq` | `0x15` / 21 | legacy historical HR | day/offset request | `ReadHeartRateRsp` interval array | HeartRateDetailRepository fallback if no realtime HR support | Historical device data, not current. | medium-high |
| `HRVReq` | `0x39` / 57 | historical HRV | one-byte day offset | `HRVRsp`, multi-packet 13-byte records | HRVRepository history/today sync | HRV historical path is UART-only in current evidence. | high |
| `DeviceSupportFunctionRsp` | `0x3C` / 60 | capability query | support request class not fully matrixed here | bitfield bytes `[1..9]` into many booleans | feature gating / UserConfig / DeviceFunctionSupport | Implement conservatively: expose unmapped flags until semantic names are proven. | medium |
| `HeartRateSettingReq` | `0x16` / 22 | HR setting | enable/interval/start/limits | `HeartRateSettingRsp` | HeartActivityViewModel.saveDeviceSetting | Settings write accepted is not proof settings applied unless response parsed. | medium |
| `BloodOxygenSettingReq` | `0x2C` / 44 | SpO2 setting | `getWriteInstance(bo2Detection)` | `BloodOxygenSettingRsp` | BloodOxygenViewModel.saveDeviceSetting | Controls automatic SpO2 monitoring flag in vendor UI. | medium-high |
| `HrvSettingReq` | `0x38` / 56 | HRV setting | enable flag | `HRVSettingRsp` | HrvActivityViewModel.saveDeviceSetting | Setting support depends on capability mapping. | medium |

## LargeData commands

LargeData uses the `de5bf7xx` characteristic family and `0xBC` frames with CRC-16.
Treat these as stored/historical device data unless proven otherwise.

| Command / flow | Cmd | Mode | Request shape | Response / parser | Known caller / flow | SymbioSync guidance | Confidence |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| interval HR | `0x75` / 117 | historical interval HR | `[dayIndex, packetIndex]` | offset 6 day, 7 interval, 8 packet count, 9 packet index, 10+ u8 values | HeartRateDetailRepository when `supportRealTimeHr` | Good historical HR path after parser/firmware validation. Not current. | medium-high |
| interval SpO2 | `0x5F` / 95 | historical interval SpO2 | `[dayIndex, packetIndex]` | same single-byte parser shape as interval HR | LargeDataHandler SDK path | Needs reconciliation with `0x2A` before implementation. | medium |
| BloodOxygenRepository auto SpO2 | `0x2A` / 42 | historical/auto SpO2 | repository report says 49-byte records | day offset plus hourly min/max arrays | BloodOxygenRepository.syncAutoBloodOxygen(0/255) | Run 4 target: reconcile with `0x5F`. | medium |
| regular sleep | `0x27` / 39 | historical sleep | sleep request/list | sleep day records and detail pairs | SleepDetailRepository / LargeDataHandler | Existing SymbioSync sleep support must keep old/new type-code distinctions visible. | medium-high |
| lunch nap sleep | `0x3E` / 62 | historical nap sleep | requested alongside regular sleep | lunch sleep parser with cumulative offsets | LargeDataHandler.syncSleepList | Not implemented fully; do not silently merge with night sleep without provenance. | medium |
| interval temperature | `0x77` / 119 | historical temperature | `[dayIndex, packetIndex]` | 2-byte little-endian values / 100.0f | Temperature sync paths | Historical skin/device temperature, not core body temperature unless proven. | medium |
| manual HR list | `0x28` / 40 | stored manual HR history | offset selector | triplets: time/index plus value | HeartRateDetailRepository.syncManualHeartRate | Stored manual history, not current. | medium |
| manual SpO2 list | `0x49` / 73 | stored manual SpO2 history | unclear/incomplete in current evidence | likely similar triplets | LargeDataHandler reports callbacks | Needs direct reconciliation before implementation. | low-medium |

## UI lifecycle timings

| Domain | Start | Stop | Countdown / timeout | Save path | Error behavior | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| HR | `StartHeartRateReq` type 1 | `stopHeartRate(value)` | 25s countdown, 30s hard timeout | `saveManualHeartRate` | wearing detection style similar to siblings | `RealTimeHeartRate(3)` poll every ~20s during measurement. |
| SpO2 | `StartHeartRateReq` type 3 | `stopBloodOxygen(...)` | 25s countdown, 30s hard timeout | `saveManualBloodOxygen` | `errCode == 1` wearing dialog | Separate from historical SpO2 sync. |
| HRV | `StartHeartRateReq` type 10 | `stopHrv(value)` | 75s countdown, 80s hard timeout | misleading `saveManualPressure` path | wearing detection / stop-on-leave | Manual/live HRV is separate from `HRVReq` historical path. |
| OneKey | `StartHeartRateReq` type 5 | `stopHealthCheck()` | 30s window | `LastOneKeyBean` | composite UI result | HR/BP device-derived; SpO2/score/fatigue synthetic. |

## Implementation warning

The same displayed vendor screen may combine values with different provenance.
SymbioSync should not expose a domain value without `mode`, `source`, `transport`,
`stage`, and `freshness` metadata.
