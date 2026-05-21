# Protocol transports

The APK uses at least two distinct BLE transports. SymbioSync should preserve
this split internally instead of flattening all Colmi traffic into one parser.
For command-level details, see [Command and behavior matrix](command_matrix.md).

## UART small-data transport

UUID family observed in APK constants:

- service: `6e40fff0-...`
- write characteristic: `6e400002-...`
- notify characteristic: `6e400003-...`

Frame shape:

```text
16-byte BaseReqCmd buffer
[0] command byte
[1..] subdata / parameters
[last] sum CRC & 0xFF
```

Callback matching in `CommandHandle`:

```text
key = value[0] & 0x7F
```

The high bit is stripped for callback lookup.

Known UART uses:

- `StartHeartRateReq` / `StartHeartRateRsp` for manual/live HR, SpO2, HRV, OneKey.
- `StopHeartRateReq` for stopping HR, SpO2, HRV, OneKey, and other vendor modes.
- `HRVReq` / `HRVRsp` for historical/detail HRV, cmd `0x39`.
- `ReadHeartRateReq` for legacy historical HR.
- settings requests such as `HeartRateSettingReq`, `BloodOxygenSettingReq`, `HrvSettingReq`.
- `DeviceSupportFunctionRsp`, cmd `0x3C`, for capability bitfields.

## Large Data transport

UUID family observed in APK constants:

- service/notify/write family: `de5bf7xx`

Frame header:

```text
[0] = 0xBC
[1] = command id
[2..3] = payload length
[4..5] = CRC-16
[6..] = payload
```

Known LargeData uses:

- interval HR: `0x75 / 117`
- interval SpO2: `0x5F / 95`
- app-level blood oxygen repository path: `0x2A / 42`, still needs reconciliation with `0x5F`
- regular sleep: `0x27 / 39`
- lunch nap sleep: `0x3E / 62`
- interval temperature: `0x77 / 119`
- manual HR list and related stored-series reads

LargeData values are historical or stored device series unless proven otherwise.
They must not be exposed as current body-state without freshness/provenance.

## Truth boundary

Transport acceptance is not hardware acknowledgement. A parsed response is not
proof of bodily effect. A displayed app value is not necessarily measured.
SymbioSync should expose stage/provenance instead of collapsing these layers.
