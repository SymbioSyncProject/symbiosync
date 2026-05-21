# Unresolved questions

These are the current hard stones before implementation claims.

## SpO2 historical reconciliation

Two SpO2-ish LargeData paths are documented:

- app repository path: `BloodOxygenRepository.syncAutoBloodOxygen(0/255)`, reported as cmd `0x2A / 42`, 49-byte records with day offset and hourly min/max arrays.
- SDK interval oxygen path: cmd `0x5F / 95`, single-byte interval samples.

Need determine which path the ring supports, which path the app uses for which UI,
and what SymbioSync should implement.

## Start/Stop exact bytes

The type map is known, but create a clean exact-byte table for:

- `StartHeartRateReq`
- `StopHeartRateReq`
- `RealTimeHeartRate`
- `ReadHeartRateReq`
- `HRVReq`
- setting requests

## Device support mapping

`DeviceSupportFunctionRsp` parses many obfuscated boolean fields. Map them to
semantic capability names by cross-referencing `DeviceFunctionSupport`, `UserConfig`,
and UI branches.

## HR interval wrapper weirdness

One decompiled path appears to call SpO2 interval logic from `syncIntervalHeartRate`.
This may be a decompiler artifact or vendor bug. Confirm via bytecode or packet capture.

## BLE callback and timeout lifecycle

`CommandHandle` registers callbacks by masked command id. Need map where callbacks
are removed, timed out, or overwritten.

## Sleep new protocol

Map new-protocol IDs:

- `0x00b3`
- `0x00b9`
- `0x0175`
- `0x0189`
- `0x018b`
- `0x018c`

## Ledger integration

Completed chunk reports should be reflected back into the master ledger with
terminal statuses and atlas links. Until then, the ledger remains an accounting
backend plus separate reports, not one unified completion table.
