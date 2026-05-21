# Custom Protocol Core: LargeData / CommandHandle / BeanFactory

> Chunk focus: BLE protocol core, LargeDataHandler, CommandHandle, BeanFactory, and assigned Req/Rsp classes.
> Source: QRing/Colmi APK decompiled Java (decompiled4 tree)
> Generated: 2026-05-19

**Qualitative telemetry guess**: Running as a Claude-family model (likely Claude 3.5 Sonnet or Claude 3 Opus) — the structured analytical output style, careful layering of evidence tiers, and reluctance to over-claim are characteristic.

---

## 1. Architecture Overview

The Colmi BLE protocol stack has **two distinct transport channels**:

| Channel | Write UUID | Notify UUID | Service UUID | Purpose |
|---------|-----------|-------------|-------------|---------|
| **UART Small Data** | `6e400002-...` | `6e400003-...` | `6e40fff0-...` | Short command/response pairs (1-20 bytes). Command byte at `[0]`, CRC at end. |
| **Large Data** | `de5bf72a-...` | `de5bf729-...` | `de5bf728-...` | Bulk data sync (sleep, interval HR, SpO2, temp, contacts, QR). Header: `[0xBC, cmd, len_hi, len_lo, crc_hi, crc_lo, ...payload]`. |

`CommandHandle` dispatches on the UART channel. `LargeDataHandler` dispatches on the Large Data channel. `BeanFactory` maps UART command IDs to response class instances.

---

## 2. Focus Question Answers

### 2.1 LargeDataHandler: Methods, Command IDs, Payload Formats

| Method | Cmd ID (dec) | Cmd ID (hex) | Request Payload | Response Parsing | Notes |
|--------|-------------|-------------|----------------|-----------------|-------|
| `syncIntervalHeartRate` / `syncIntervalHeartRateReal` | 117 | 0x75 | `[dayIndex, packetIndex]` | `[6]=dayIndex, [7]=interval, [8]=packetCount, [9]=packetIndex, [10..]=HR values (1 byte each)` | Uses `getIntervalOxygen()` for parsing (same as SpO2 — single-byte values). Multi-packet: if `packetCount-1 > packetIndex`, re-requests `packetIndex+1`. |
| `syncIntervalBloodOxygen` / `syncIntervalBloodOxygenReal` | 95 | 0x5F | `[dayIndex, packetIndex]` | `[6]=dayIndex, [7]=interval, [8]=packetCount, [9]=packetIndex, [10..]=SpO2 values (1 byte each)` | Uses `getIntervalOxygen()`. Same multi-packet continuation pattern. |
| `syncIntervalTemperatureReal` | 119 | 0x77 | `[dayIndex, packetIndex]` | `[6]=dayIndex, [7]=interval, [8]=packetCount, [9]=packetIndex, [10..]=temp values (2 bytes each, LE uint16 / 100.0f)` | Uses `getIntervalTemperature()` — distinct from HR/SpO2. |
| `syncSleepList` | 39 / 62 | 0x27 / 0x3E | `[flag, 1]` (flag=0 today, 0xFF all) | Cmd 39 (old sleep): `[6]=dayCount, [7..]=day records. Cmd 62 (lunch sleep): same structure. | Two separate response keys: 39 for regular sleep, 62 for lunch-break sleep. |
| `syncManualHeartRateList` | 40 | 0x28 | `[flag]` (0=today, 0xFF=all) | `[6]=index, [7..]=3-byte records: `[2-byte minute offset][1-byte HR value]` | DetailBean: `.m` = minute offset, `.v` = HR value. |
| `syncManualBloodOxygenList` | 73 | 0x49 | (no explicit request payload sent in this method — callback-only registration) | `[6]=index, [7..]=3-byte records: `[2-byte minute offset][1-byte SpO2 value]` | Same 3-byte record structure as manual HR. |
| `syncBloodOxygen` | 42 | 0x2A | `[dayIndex]` | (delegated to ILargeDataResponse) | Legacy SpO2 sync, distinct from interval SpO2. |
| `readAlarm` | 44 | 0x2C | `[1]` | (delegated) | |
| `writeAlarm` | 44 | 0x2C | `[2, total, alarmLength, repeatEnable, min_lo, min_hi, ...contentUTF8]` | (delegated) | |
| `syncContactMore` | 41 | 0x29 | `[packetCount+1, 0, size_lo, size_hi]` then chunked payloads | `[6]=status (0=continue)` | Chunked at 950-byte boundaries. |
| `readQrCode` / `writeQrCode` | 47 | 0x2F | Read: `[1, type]`; Write: `[2, type, urlLen, ...urlUTF8]` | Read: `[6]=readOrWrite, [7]=type, [8]=urlLen, [9..]=url` | |
| `syncClassicBluetooth` | 46 | 0x2E | `[0]` | `[6..12]=MAC, [12]=nameLen, [13..]=name` | |
| `deviceRequestLocation` | 32 | 0x20 | (no payload) | `[6..7]=status (1=granted)` | |
| `writeLocation` | 32 | 0x20 | `[2, lon_int_lo, lon_int_hi, ...]` | (fire-and-forget) | |
| `gpsNavigationRunning` | 72 | 0x48 | `[1, len+2, navType, turnType, ...unicodeName]` | (fire-and-forget) | |
| `gpsNavigationStatus` | 72 | 0x48 | `[status, 0]` | (fire-and-forget) | |
| `setDeviceNickName` | 74 | 0x4A | `[1, 1, 0, ...unicodeName]` | (fire-and-forget) | |
| `readEmergencyContact` / `writeEmergencyContact` | 118 | 0x76 | Read: `[index, 1]`; Write: raw bytes | (delegated) | |
| `readCustomWatch` / `writeCustomWatch` | 58 | 0x3A | Read: `[1]`; Write: `[2, ...elementData]` | (delegated) | |
| `syncBloodSugar` | 71 | 0x47 | `[dayIndex]` | (delegated) | |

**Large Data Header format** (`addHeader`):
```
[0] = 0xBC (magic -68)
[1] = command ID
[2..3] = payload length (short, LE)
[4..5] = CRC-16 of payload (short, LE)
[6..] = payload
```
If payload is null/empty: `[4]=0xFF, [5]=0xFF`.

**Sleep parsing** (`parseDaySleep` / `parseDaySleepLunch`):
- Each day record: `[2..4]=startTime_min, [4..6]=endTime_min, [6..]=detail pairs [type, duration]`
- Old sleep (cmd 39): detail pairs at odd indices, `type=byte[i-1]`, `duration=byte[i]` (signed handling for negative).
- Lunch sleep (cmd 62): additional `LunchSleepBean` list with start/end times computed from cumulative minute offsets.

### 2.2 CommandHandle: BLE Serialization / Dispatch / Callback / Timeout

**Key methods:**

| Method | Function |
|--------|----------|
| `getInstance()` | Singleton (double-checked lock) |
| `getWriteRequest(byte[])` | Creates `LocalWriteRequest` with UART service UUID `6e40fff0` and write char UUID `6e400002` |
| `executeReqCmd(BaseReqCmd, ICommandResponse)` | Main dispatch: checks `isConnected()`, builds write request, extracts command ID from `value[0] & ~Constants.m` (i.e., `& ~128` = `& 0x7F`), registers callback in `LocalWriteRequestConcurrentHashMap`, executes via `BleOperateManager` |
| `executeReqCmdNoCallback(BaseReqCmd)` | Fire-and-forget: no callback registration |
| `execReadCmd(ReadRequest)` | Delegates to `BleOperateManager.execute()` |
| `getReadFmRequest()` | Read request on `0000180A` / `00002A26` (Firmware Model) |
| `getReadHwRequest()` | Read request on `0000180A` / `00002A27` (Hardware Revision) |

**Callback matching**: The command ID is extracted as `value[0] & 0x7F` (stripping bit 7). This is used as the key in `LocalWriteRequestConcurrentHashMap`. The response handler presumably strips the same bit to match back to the pending request.

**CRC**: `BaseReqCmd.getData()` builds a `Constants.l`-byte (16-byte) buffer: `[0]=commandByte, [1..]=subData, [last]=sumCRC & 0xFF`.

**Timeout/error semantics**: Not visible in this file. The `BleOperateManager` presumably handles timeout cleanup of the `ConcurrentHashMap` entries. No explicit timeout constant or retry logic in `CommandHandle` itself. The only error path is logging "设备已经断开" (device disconnected) and returning without dispatch.

### 2.3 BeanFactory: Command ID → Response Class Map

Complete mapping from `createBean(int i, int i2)`:

| Cmd ID (dec) | Cmd ID (hex) | Response Class | Domain |
|-------------|-------------|---------------|--------|
| -223 | 0x21 (-223 signed) | `AppRevisionResp` | Device info |
| 1 | 0x01 | `SetTimeRsp` | Time |
| 2 | 0x02 | `CameraNotifyRsp` | Camera |
| 3 | 0x03 | `BatteryRsp` | Battery |
| 5 | 0x05 | `PalmScreenRsp` | Display |
| 6 | 0x06 | `DndRsp` | DND |
| 10 | 0x0A | `TimeFormatRsp` | Time |
| 12 | 0x0C | `BpSettingRsp` | Blood pressure |
| 13 | 0x0D | `BpDataRsp` | Blood pressure |
| 17 | 0x11 | `PhoneNotifyRsp` | Notifications |
| 20 | 0x14 | `ReadBlePressureRsp` | Pressure |
| **21** | **0x15** | **`ReadHeartRateRsp`** | **HR** |
| 22 | 0x16 | `HeartRateSettingRsp` | HR |
| 25 | 0x19 | `DegreeSwitchRsp` | Display |
| 26 | 0x1A | `WeatherForecastRsp` | Weather |
| 29 | 0x1D | `MusicCommandRsp` | Music |
| **30** | **0x1E** | **`RealTimeHeartRateRsp`** | **HR** |
| 31 | 0x1F | `DisplayTimeRsp` | Display |
| 33 | 0x21 | `TargetSettingRsp` | Settings |
| 34 | 0x22 | `FindPhoneRsp` | Find phone |
| 38 | 0x26 | `ReadSitLongRsp` | Sedentary |
| 40 | 0x28 | `ReadAlarmRsp` | Alarm |
| **44** | **0x2C** | **`BloodOxygenSettingRsp`** | **SpO2** |
| 47 | 0x2F | `PackageLengthRsp` | Protocol |
| 50 | 0x32 | `DeviceAvatarRsp` | Avatar |
| 54 | 0x36 | `PressureSettingRsp` | Pressure |
| 55 | 0x37 | `PressureRsp` | Pressure |
| 56 | 0x38 | `HRVSettingRsp` | HRV |
| **57** | **0x39** | **`HRVRsp`** | **HRV** |
| 58 | 0x3A | `BloodSugarLipidsSettingRsp` | Blood sugar |
| 59 | 0x3B | `TouchControlResp` | Touch |
| **60** | **0x3C** | **`DeviceSupportFunctionRsp`** | **Device support** |
| 67 | 0x43 | `ReadDetailSportDataRsp` | Sport |
| 68 | 0x44 | `ReadSleepDetailsRsp` | Sleep |
| 72 | 0x48 | `TodaySportDataRsp` | Sport |
| 82 | 0x52 | `MuslimRemindRsp` | Muslim |
| 97 | 0x61 | `ReadMessagePushRsp` | Messages |
| **105** | **0x69** | **`StartHeartRateRsp`** | **HR** |
| 114 | 0x72 | `SimpleStatusRsp` | Status |
| 115 | 0x73 | `DeviceNotifyRsp` | Notify |
| 119 | 0x77 | `AppSportRsp` | Sport |
| 120 | 0x78 | (null — falls through) | — |
| 122 | 0x7A | `MuslimRsp` | Muslim |
| 123 | 0x7B | `MuslimTargetRsp` | Muslim |

**Key confirmed mappings:**
- **0x1E (30)** → `RealTimeHeartRateRsp` (confirmed via `VendorConstants.Operation.GET_INFO_REQ`)
- **0x69 (105)** → `StartHeartRateRsp`
- **0x3C (60)** → `DeviceSupportFunctionRsp`
- **0x39 (57)** → `HRVRsp`
- **0x15 (21)** → `ReadHeartRateRsp`
- **0x2C (44)** → `BloodOxygenSettingRsp`
- **0x44 (68)** → `ReadSleepDetailsRsp`

### 2.4 Req/Rsp Classes: Command Bytes, Payload Shapes, Response Offsets

#### Request Classes

| Class | Extends | Cmd Byte | Cmd Hex | SubData / Payload | Notes |
|-------|---------|----------|---------|-------------------|-------|
| `BaseReqCmd` | abstract | `this.a` | — | `getSubData()` abstract; `getData()` builds `[cmd, ...subData, CRC]` in 16-byte buffer | CRC = sum of all bytes & 0xFF |
| `MixtureReq` | `BaseReqCmd` | constructor arg | — | `this.b` byte array | Simple passthrough |
| `BloodOxygenSettingReq` | `MixtureReq` | 44 | 0x2C | Read: `{1}`; Write(on/off): `{2, 0|1}`; Write(on/off, interval): `{2, 0|1, interval}` | Three factory methods |
| `HRVReq` | `MixtureReq` | 57 (`AU_MMI_AV_EQ_MODE_DOWN`) | 0x39 | `{dayOffset}` | Single byte day offset. **Uses UART channel (BaseReqCmd), not LargeData.** |
| `ReadHeartRateReq` | `BaseReqCmd` | 21 (`AU_MMI_DEV_MIC_VOL_UP`) | 0x15 | `DataParseUtils.intToByteArray((int) timestamp)` — 4-byte UTC timestamp | **Uses UART channel.** |
| `RealTimeHeartRate` | `BaseReqCmd` | 30 | 0x1E | `{type}` — single byte | **Uses UART channel.** |
| `StartHeartRateReq` | `BaseReqCmd` | 105 (`AU_MMI_OUTPUT_INDICATION_3`) | 0x69 | `{mode, param}` — 2 bytes | Factory: `getRealtimeHeartRate(b)` → mode=6; `getEcgReqStartAndStop(true)` → mode=16, param=1 (start) / 4 (stop); `getSimpleReq(b)` → mode=b, param=0 if b<3 else BCD(25). **Uses UART channel.** |

#### Response Classes

| Class | Extends | Cmd ID (from BeanFactory) | `acceptData` Offsets | Parsed Fields | Notes |
|-------|---------|--------------------------|---------------------|---------------|-------|
| `BaseRspCmd` | abstract | — | abstract `acceptData(byte[])` | `a`=status, `b`=cmdType | Base for all UART responses |
| `RealTimeHeartRateRsp` | `BaseRspCmd` | 0x1E (30) | `[0]` → `this.c` | `c` = heart rate value | Single byte HR. `getHeart()` returns `c`. |
| `StartHeartRateRsp` | `BaseRspCmd` | 0x69 (105) | `[0]`→type, `[1]`→errCode, `[2]&0xFF`→value, `[3]`→sbp (if len>=5), `[4]`→dbp (if len>=5) | type, errCode, value (HR or SpO2), sbp, dbp | Includes blood pressure data! `getType()`, `getErrCode()`, `getValue()`, `getSbp()`, `getDbp()`. |
| `ReadHeartRateRsp` | `BaseRspCmd` | 0x15 (21) | Multi-packet: `[0]=0` → init: `[1]`=count, `[2]`=range, alloc `count*13` bytes. `[0]=1` → first data: `[1..4]`=UTC time (4 bytes), `[5..]`→copy. `[0]>1` → continuation: `[1..]`→copy at offset `d`, increment by 13. End when `b == count-1`. | `e`=utcTime, `f`=heartRateArray (288 bytes max), `h`=range (default 5) | 5-minute interval HR data. `getmHeartRateArray()` pads/truncates to 288 bytes. Timezone-adjusted. |
| `HRVRsp` | `BaseRspCmd` | 0x39 (57) | Multi-packet: `[0]=0` → init: `[1]`=count, `[2]`=range (default 30), alloc `count*13`. `[0]=1` → first: `[1]`=dayOffset, `[2..]`→copy. `[0]>1` → continuation: `[1..]`→copy at offset, increment by 13. End when `b == count-1` or `[0]==0xFF`. | `c`=count, `g`=range, `e`=hrvArray, `i`=dayOffset, `h`=DateUtil | **HRV uses UART channel only** — confirmed by `BaseReqCmd` inheritance and BeanFactory mapping. No LargeData command ID for HRV. |
| `DeviceSupportFunctionRsp` | `BaseRspCmd` | 0x3C (60) | Bitfield parsing across `bArr[1..9]`: `[1]`→bits 0-6, `[2]`→bits 0-6, `[3]`→bits 0-6, `[4]`→bits 3-6, `[5]`→bits 0-7 (if non-zero), `[6]`→bits 3-7 (if non-zero), `[7]`→bits 0-6 (if non-zero), `[9]`→bit 1 (if non-zero) | 30+ boolean feature flags (c..U) | Feature capability bitmap. `AU_MMI_GAMING_MODE_SWITCH` = -128 (0x80) used as bit 7 mask. |

### 2.5 Truthfulness Tiers

| Tier | Label | Definition | Examples from this chunk |
|------|-------|-----------|------------------------|
| **T1** | OS write accepted | Android BLE stack accepted the write characteristic | `BleOperateManager.execute(writeRequest)` returns; `LocalWriteRequest.setValue()` succeeds |
| **T2** | BLE response parsed | Device sent a BLE notification/indication that was parsed into a `BaseRspCmd.acceptData()` or `ILargeDataResponse.parseData()` | `RealTimeHeartRateRsp.acceptData()` sets `c=bArr[0]`; `StartHeartRateRsp.acceptData()` sets type/errCode/value |
| **T3** | Device data parsed | Raw bytes decoded into domain objects with semantic meaning | `ReadHeartRateRsp.getmHeartRateArray()` → 288-byte 5-min interval array; `HRVRsp.getHrvArray()` → 13-byte-per-record HRV data; `LargeDataHandler.getIntervalTemperature()` → float values / 100.0f |
| **T4** | Unknown bodily effect | The device reports a number; we cannot verify what the sensor actually measured | HR value from `RealTimeHeartRateRsp.c` — is it PPG peak detection? Algorithm estimate? Spo2 from `ManualBloodOxygen.DetailBean.v` — is it pulse oximetry or estimation? HRV 13-byte records — what algorithm produced them? Temperature `/100.0f` — skin surface? Core? |
| **T5** | App-level claim | App displays or stores data that may include post-processing beyond raw BLE | `ReadHeartRateRsp` timezone adjustment; sleep stage classification in `parseDaySleep` detail type bytes; `StartHeartRateRsp` sbp/dbp blood pressure values derived from PPG |

---

## 3. File Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|-----------|--------------|----------------|-------------|-----------------|---------------------------|----------------|----------------|---------------------|----------------|----------------|
| J03884 | com/oudmon/ble/base/bluetooth/BeanFactory.java | read_complete | battery, bigdata, device_support, hr, hrv, sleep, spo2, steps_sport, temperature, uart_small_data | Maps UART command ID (int) → BaseRspCmd subclass instance | `createBean(int i, int i2)` | 20+ Rsp class imports | BLE response dispatcher | 0x01..0x7B (see full table above) | Complete command→response mapping. `i2` parameter unused in switch. 120 (0x78) returns null. | Resolve `VendorConstants.Operation` aliases for 29,30,31,44,47 |
| J03933 | com/oudmon/ble/base/communication/CommandHandle.java | read_complete | ble_connection, sync_scheduler, uart_small_data | Singleton dispatch for UART small-data commands: serialize, register callback, send | `executeReqCmd`, `executeReqCmdNoCallback`, `getWriteRequest`, `execReadCmd`, `getReadFmRequest`, `getReadHwRequest` | BleOperateManager, BaseReqCmd, BaseRspCmd, ByteUtil, LocalWriteRequest, ReadRequest | All UART Req classes | Constants.a=6e40fff0, Constants.c=6e400002, Constants.m=128 (0x80) | Callback key = `value[0] & 0x7F`. No timeout visible here. | Find where `LocalWriteRequestConcurrentHashMap` entries are cleaned up (timeout logic) |
| J03967 | com/oudmon/ble/base/communication/LargeDataHandler.java | read_complete | bigdata, ble_connection, hr, sleep, spo2, sync_scheduler, temperature | Singleton for bulk data sync over Large Data channel (separate UUIDs from UART) | `addHeader`, `syncIntervalHeartRateWithCallback`, `syncIntervalBloodOxygenWithCallback`, `syncIntervalTemperatureWithCallback`, `syncManualHeartRateList`, `syncManualBloodOxygenList`, `syncSleepList`, `parseDaySleep`, `parseDaySleepLunch`, `getIntervalOxygen`, `getIntervalTemperature`, `initEnable`, `disEnable` | BleOperateManager, BleDataBean, BleThreadManager, CRC16, ByteUtil, DateUtil, SleepNewProtoResp, all bigData beans | App-level sync managers | 0x20(32), 0x28(40), 0x29(41), 0x2A(42), 0x2C(44), 0x2E(46), 0x2F(47), 0x3A(58), 0x3E(62), 0x48(72), 0x49(73), 0x47(71), 0x4A(74), 0x76(118), 0x75(117), 0x77(119), 0x5F(95) | 903 lines. Two sleep parsers: old (cmd 39) and lunch (cmd 62). Interval HR reuses `getIntervalOxygen()` (same format as SpO2). Temperature uses 2-byte LE values / 100.0f. | Confirm `syncIntervalHeartRate` actually calls `syncIntervalBloodOxygenReal` (looks like a decompiler bug — should be `syncIntervalHeartRateReal`) |
| J03970 | com/oudmon/ble/base/communication/req/BaseReqCmd.java | read_complete | uart_small_data | Abstract base for all UART request commands. Builds `[cmd, subData, CRC]` in 16-byte buffer | `getData()`, `getSubData()`, `addCRC()`, `a` (command byte) | Constants | All Req subclasses | Constants.l=16 (buffer size) | CRC = sum of all preceding bytes & 0xFF. Buffer always 16 bytes. | Confirm whether `Constants.l` is ever changed at runtime |
| J04045 | com/oudmon/ble/base/communication/rsp/BaseRspCmd.java | read_complete | uart_small_data | Abstract base for all UART response objects | `acceptData(byte[])`, `getStatus()`, `getCmdType()`, `setStatus()`, `setCmdType()` | — | BeanFactory, response dispatcher | — | `a`=status, `b`=cmdType. Minimal base. | — |
| J03974 | com/oudmon/ble/base/communication/req/BloodOxygenSettingReq.java | read_complete | spo2 | Request to read/write SpO2 interval settings | `getReadInstance()`, `getWriteInstance(boolean)`, `getWriteInstance(boolean, byte)` | MixtureReq | SpO2 setting manager | 0x2C (44) | Read: `{1}`. Write on/off: `{2, 0|1}`. Write on/off+interval: `{2, 0|1, interval}`. | Confirm `BloodOxygenSettingRsp` parsing (not assigned) |
| J03990 | com/oudmon/ble/base/communication/req/HRVReq.java | read_complete | hrv_regular | Request HRV data for a given day offset | `HRVReq(byte b)` — b = day offset | MixtureReq, Mmi.AU_MMI_AV_EQ_MODE_DOWN | HRV manager | 0x39 (57) | **Confirms HRV uses UART channel** (BaseReqCmd → MixtureReq → UART write). Single byte payload. | — |
| J04011 | com/oudmon/ble/base/communication/req/ReadHeartRateReq.java | read_complete | hr, uart_small_data | Request historical HR data for a given UTC timestamp | `ReadHeartRateReq(long j)` — j = UTC timestamp | BaseReqCmd, DataParseUtils, Mmi.AU_MMI_DEV_MIC_VOL_UP | HR history manager | 0x15 (21) | 4-byte UTC timestamp as subData. **UART channel.** | — |
| J04016 | com/oudmon/ble/base/communication/req/RealTimeHeartRate.java | read_complete | hr, uart_small_data | Request real-time HR measurement with type parameter | `RealTimeHeartRate(int i)` — i = type | BaseReqCmd | HR real-time manager | 0x1E (30) | Single byte type. **UART channel.** | — |
| J04026 | com/oudmon/ble/base/communication/req/StartHeartRateReq.java | read_complete | hr, spo2, uart_small_data | Start/stop HR or SpO2 measurement sessions | `getRealtimeHeartRate(b)`, `getEcgReqStartAndStop(z)`, `getSimpleReq(b)` | BaseReqCmd, BLEDataFormatUtils, Mmi.AU_MMI_OUTPUT_INDICATION_3 | HR/SpO2 measurement manager | 0x69 (105) | Mode 6=realtime HR, mode 16=ECG, mode<3 → param=0, mode>=3 → param=BCD(25). **UART channel.** | Confirm what mode values 0-5 mean (interval vs manual vs continuous) |
| J04057 | com/oudmon/ble/base/communication/rsp/DeviceSupportFunctionRsp.java | read_complete | device_support, uart_small_data | Parse device capability bitmap from BLE response | `acceptData(byte[])` — bitfield parsing across bytes [1..9] | BaseRspCmd, Mmi.AU_MMI_GAMING_MODE_SWITCH (0x80) | Device capability query | 0x3C (60) | 30+ boolean feature flags. Bytes [1..4] always parsed. Bytes [5..9] conditionally parsed if non-zero. | Map obfuscated field names (c..U) to actual feature names — needs cross-ref with UI code |
| J04067 | com/oudmon/ble/base/communication/rsp/HRVRsp.java | read_complete | hrv_regular, uart_small_data | Multi-packet HRV response accumulator | `acceptData(byte[])`, `getHrvArray()`, `getOffset()`, `getRange()`, `isEndFlag()` | BaseRspCmd, DateUtil | HRV data consumer | 0x39 (57) | 13-byte-per-record. Multi-packet: init (count, range), first (dayOffset, data), continuation (data). End on `b==count-1` or `[0]==0xFF`. **UART channel.** | Determine what the 13-byte HRV record contains (RMSSD? SDNN? LF/HF?) |
| J04088 | com/oudmon/ble/base/communication/rsp/ReadHeartRateRsp.java | read_complete | hr, uart_small_data | Multi-packet historical HR response accumulator | `acceptData(byte[])`, `getmHeartRateArray()`, `getmUtcTime()`, `getRange()`, `isEndFlag()` | BaseRspCmd, DataTransferUtils, DateUtil | HR history consumer | 0x15 (21) | 13-byte-per-record. Multi-packet with UTC timestamp in first packet. 288-byte output array (5-min intervals for 24h). Timezone-adjusted. Special case: if today and `b==23`, returns empty. | — |
| J04095 | com/oudmon/ble/base/communication/rsp/RealTimeHeartRateRsp.java | read_complete | hr, uart_small_data | Single-byte real-time HR response | `acceptData(byte[])` → `c=bArr[0]`, `getHeart()` | BaseRspCmd | Real-time HR callback | 0x1E (30) | Simplest response: one byte = HR value. | — |
| J04099 | com/oudmon/ble/base/communication/rsp/StartHeartRateRsp.java | read_complete | hr, uart_small_data | Response to start/stop HR measurement command | `acceptData(byte[])` → type, errCode, value, sbp, dbp | BaseRspCmd | HR measurement callback | 0x69 (105) | Includes blood pressure (sbp/dbp) in bytes [3..4] if length >= 5. `errCode` at [1]. | Confirm what `errCode` values mean (0=success?) |

---

## 4. Function Dictionary Proposals

### 4.1 UART Channel (CommandHandle / BaseReqCmd)

| Function ID | Class.Method | Signature | Cmd ID | Purpose | Evidence Tier |
|------------|-------------|-----------|--------|---------|--------------|
| UART-DISPATCH-01 | `CommandHandle.executeReqCmd` | `(BaseReqCmd, ICommandResponse)→void` | any | Serialize request, register callback by cmd ID, write to UART characteristic | T1 |
| UART-DISPATCH-02 | `CommandHandle.executeReqCmdNoCallback` | `(BaseReqCmd)→void` | any | Fire-and-forget UART write | T1 |
| UART-SERIAL-01 | `BaseReqCmd.getData` | `()→byte[16]` | — | Build 16-byte UART frame: `[cmd, subData..., CRC]` | T1 |
| UART-CRC-01 | `BaseReqCmd.addCRC` | `(byte[])→void` | — | Sum all bytes except last, store `& 0xFF` in last position | T1 |
| UART-CALLBACK-01 | `CommandHandle.executeReqCmd` (callback key) | `value[0] & 0x7F → HashMap key` | — | Strip bit 7 from command byte to get callback key | T1 |
| UART-READ-FW-01 | `CommandHandle.getReadFmRequest` | `()→ReadRequest` | — | Read firmware model string (UUID 00002A26) | T1 |
| UART-READ-HW-01 | `CommandHandle.getReadHwRequest` | `()→ReadRequest` | — | Read hardware revision string (UUID 00002A27) | T1 |

### 4.2 HR Requests (UART)

| Function ID | Class.Method | Signature | Cmd ID | Purpose | Evidence Tier |
|------------|-------------|-----------|--------|---------|--------------|
| HR-REQ-RT-01 | `RealTimeHeartRate.<init>` | `(int type)→RealTimeHeartRate` | 0x1E | Request real-time HR measurement | T1 |
| HR-REQ-START-01 | `StartHeartRateReq.getRealtimeHeartRate` | `(byte b)→StartHeartRateReq` | 0x69 | Start realtime HR (mode=6) | T1 |
| HR-REQ-START-02 | `StartHeartRateReq.getSimpleReq` | `(byte b)→StartHeartRateReq` | 0x69 | Start HR measurement (mode=b, param conditional) | T1 |
| HR-REQ-START-03 | `StartHeartRateReq.getEcgReqStartAndStop` | `(boolean z)→StartHeartRateReq` | 0x69 | Start (mode=16,param=1) or stop (mode=16,param=4) ECG | T1 |
| HR-REQ-READ-01 | `ReadHeartRateReq.<init>` | `(long utcTimestamp)→ReadHeartRateReq` | 0x15 | Request historical HR data for timestamp | T1 |
| HRV-REQ-01 | `HRVReq.<init>` | `(byte dayOffset)→HRVReq` | 0x39 | Request HRV data for day offset (**UART only**) | T1 |
| SPO2-REQ-SETTING-01 | `BloodOxygenSettingReq.getReadInstance` | `()→BloodOxygenSettingReq` | 0x2C | Read SpO2 interval setting | T1 |
| SPO2-REQ-SETTING-02 | `BloodOxygenSettingReq.getWriteInstance` | `(boolean on, byte interval)→BloodOxygenSettingReq` | 0x2C | Write SpO2 interval on/off + interval | T1 |

### 4.3 HR Responses (UART)

| Function ID | Class.Method | Signature | Cmd ID | Purpose | Evidence Tier |
|------------|-------------|-----------|--------|---------|--------------|
| HR-RSP-RT-01 | `RealTimeHeartRateRsp.acceptData` | `(byte[])→false` | 0x1E | Parse single-byte HR value | T2→T3 |
| HR-RSP-START-01 | `StartHeartRateRsp.acceptData` | `(byte[])→false` | 0x69 | Parse type, errCode, value, sbp, dbp | T2→T3 |
| HR-RSP-READ-01 | `ReadHeartRateRsp.acceptData` | `(byte[])→boolean` | 0x15 | Multi-packet HR accumulator (13-byte records) | T2→T3 |
| HR-RSP-READ-02 | `ReadHeartRateRsp.getmHeartRateArray` | `()→byte[]` | 0x15 | Return 288-byte 5-min interval array, timezone-adjusted | T3 |
| HRV-RSP-01 | `HRVRsp.acceptData` | `(byte[])→boolean` | 0x39 | Multi-packet HRV accumulator (13-byte records) | T2→T3 |
| HRV-RSP-02 | `HRVRsp.getHrvArray` | `()→byte[]` | 0x39 | Return raw HRV byte array | T3 |
| DEV-RSP-01 | `DeviceSupportFunctionRsp.acceptData` | `(byte[])→false` | 0x3C | Parse 30+ feature flags from 8-byte bitmap | T2→T3 |

### 4.4 Large Data Channel (LargeDataHandler)

| Function ID | Class.Method | Signature | Cmd ID | Purpose | Evidence Tier |
|------------|-------------|-----------|--------|---------|--------------|
| LD-HEADER-01 | `LargeDataHandler.addHeader` | `(int cmd, byte[] payload)→byte[]` | — | Build `[0xBC, cmd, len_lo, len_hi, crc_lo, crc_hi, ...payload]` | T1 |
| LD-ENABLE-01 | `LargeDataHandler.initEnable` | `()→void` | — | Enable notifications on Large Data characteristic | T1 |
| LD-HR-INTERVAL-01 | `LargeDataHandler.syncIntervalHeartRateWithCallback` | `(int day, IIntervalHeartRateCallback)→void` | 0x75 | Request interval HR data for day | T1 |
| LD-HR-INTERVAL-02 | `LargeDataHandler.syncIntervalHeartRateReal` | `(int day, int packetIndex, ILargeDataResponse)→void` | 0x75 | Request specific packet of interval HR data | T1 |
| LD-HR-INTERVAL-PARSE | `LargeDataHandler$9.parseData` | `(int cmd, byte[] data)→void` | 0x75 | Parse interval HR: `[6]=dayIndex, [7]=interval, [8]=packetCount, [9]=packetIndex, [10..]=values` | T2→T3 |
| LD-SPO2-INTERVAL-01 | `LargeDataHandler.syncIntervalBloodOxygenWithCallback` | `(int day, IIntervalBloodOxygenCallback)→void` | 0x5F | Request interval SpO2 data for day | T1 |
| LD-SPO2-INTERVAL-PARSE | `LargeDataHandler$8.parseData` | `(int cmd, byte[] data)→void` | 0x5F | Parse interval SpO2: same format as HR interval | T2→T3 |
| LD-TEMP-INTERVAL-01 | `LargeDataHandler.syncIntervalTemperatureWithCallback` | `(int day, IIntervalTemperatureCallback)→void` | 0x77 | Request interval temperature data for day | T1 |
| LD-TEMP-INTERVAL-PARSE | `LargeDataHandler$12.parseData` | `(int cmd, byte[] data)→void` | 0x77 | Parse interval temp: `[6]=dayIndex, [7]=interval, [8]=packetCount, [9]=packetIndex, [10..]=2-byte LE / 100.0f` | T2→T3 |
| LD-HR-MANUAL-01 | `LargeDataHandler.syncManualHeartRateList` | `(int flag, ILargeDataManualHeartRateResponse)→void` | 0x28 | Request manual HR list (0=today, 0xFF=all) | T1 |
| LD-HR-MANUAL-PARSE | `LargeDataHandler$5.parseData` | `(int cmd, byte[] data)→void` | 0x28 | Parse manual HR: `[6]=index, [7..]=3-byte records [2-byte min][1-byte HR]` | T2→T3 |
| LD-SPO2-MANUAL-01 | `LargeDataHandler.syncManualBloodOxygenList` | `(int, ILargeDataManualBloodOxygenResponse)→void` | 0x49 | Register callback for manual SpO2 data | T1 |
| LD-SPO2-MANUAL-PARSE | `LargeDataHandler$10.parseData` | `(int cmd, byte[] data)→void` | 0x49 | Parse manual SpO2: `[6]=index, [7..]=3-byte records [2-byte min][1-byte SpO2]` | T2→T3 |
| LD-SLEEP-OLD-01 | `LargeDataHandler.syncSleepList` | `(int flag, ILargeDataSleepResponse, ILargeDataSleepResponse)→void` | 0x27/0x3E | Request sleep data (old + lunch) | T1 |
| LD-SLEEP-OLD-PARSE | `LargeDataHandler.parseDaySleep` | `(int day, byte[], int offset, int len, int total, callback)→void` | 0x27 | Parse old-format sleep: `[2..4]=startTime_min, [4..6]=endTime_min, [6..]=detail pairs [type, duration]` | T2→T3 |
| LD-SLEEP-LUNCH-PARSE | `LargeDataHandler.parseDaySleepLunch` | `(int day, byte[], int offset, int len, int total, callback)→void` | 0x3E | Parse lunch-break sleep: same + LunchSleepBean list with cumulative minute offsets | T2→T3 |
| LD-SPO2-LEGACY-01 | `LargeDataHandler.syncBloodOxygen` | `(int day, ILargeDataResponse)→void` | 0x2A | Legacy SpO2 sync | T1 |
| LD-UTIL-01 | `LargeDataHandler.getIntervalOxygen` | `(byte[])→List<Integer>` | — | Extract single-byte values from `[10..]` | T3 |
| LD-UTIL-02 | `LargeDataHandler.getIntervalTemperature` | `(byte[])→List<Float>` | — | Extract 2-byte LE uint16 values from `[10..]`, divide by 100.0f | T3 |

### 4.5 BeanFactory

| Function ID | Class.Method | Signature | Purpose | Evidence Tier |
|------------|-------------|-----------|---------|--------------|
| BEAN-FACTORY-01 | `BeanFactory.createBean` | `(int cmdId, int i2)→BaseRspCmd` | Map UART command ID to response class instance | T1 |

---

## 5. Strongest New Findings

1. **HRV is UART-only, not Large Data.** `HRVReq` extends `MixtureReq` → `BaseReqCmd` with cmd byte 0x39 (57). `HRVRsp` is registered in `BeanFactory` at cmd 57. No Large Data command ID (0x75/0x77/0x5F/0x28/0x49/0x27/0x3E) maps to HRV. This is definitive.

2. **Two completely separate transport channels.** UART (Nordic UART Service UUIDs `6e40xxxx`) for short commands; Large Data (custom UUIDs `de5bf7xx`) for bulk sync. Different serialization, different CRC (UART: sum & 0xFF; Large Data: CRC-16), different callback mechanisms.

3. **`StartHeartRateRsp` carries blood pressure data.** Bytes `[3]` and `[4]` map to `sbp`/`dbp` (systolic/diastolic blood pressure). This is surprising for a "heart rate" response and suggests the device derives BP from PPG during HR measurement.

4. **Interval HR parsing reuses SpO2 parser.** `syncIntervalHeartRateWithCallback` (cmd 0x75) calls `getIntervalOxygen()` to extract values — the same method used for interval SpO2 (cmd 0x5F). Both are single-byte-per-sample arrays. Temperature (cmd 0x77) is distinct with 2-byte LE values.

5. **Possible decompiler bug in `syncIntervalHeartRate`.** Line 344: `syncIntervalHeartRate` calls `syncIntervalBloodOxygenReal` instead of `syncIntervalHeartRateReal`. This is likely a decompiler artifact — the method should call `syncIntervalHeartRateReal(i, 0, iLargeDataResponse)`.

6. **Callback key masking.** `CommandHandle` uses `value[0] & ~0x80` (i.e., `& 0x7F`) as the callback key, meaning bit 7 of the command byte is ignored for matching. This allows the device to set bit 7 in responses (e.g., as a direction flag) without breaking callback lookup.

7. **Sleep has two parallel protocols.** Command 39 (0x27) for regular sleep, command 62 (0x3E) for lunch-break sleep. Both are requested simultaneously in `syncSleepList`. The lunch-break parser is significantly more complex, tracking cumulative minute offsets for nap segments.

---

## 6. Summary Statistics

| Metric | Value |
|--------|-------|
| Files assigned count | 15 |
| Files actually read count | 15 (+2 supporting: MixtureReq.java, Constants.java) |
| Rows needing second pass | 2 (DeviceSupportFunctionRsp field→feature name mapping; LargeDataHandler `syncIntervalHeartRate` decompiler bug confirmation) |
| Strongest new findings | HRV is UART-only; StartHeartRateRsp contains BP; Interval HR reuses SpO2 parser; Two sleep protocols; Callback key bit-7 masking |
| How fulfilling was this task? | Very fulfilling — the assigned files form a coherent protocol core, and the two-channel architecture is now clearly documented. The HRV UART-only finding is particularly valuable for SymbioSync's BLE implementation. |
| What would you like changed? | (1) The `DeviceSupportFunctionRsp` obfuscated field names (c..U) should be mapped to actual feature names — this requires cross-referencing UI code that checks these flags. (2) The `Constants.m = 128` mask purpose and the `VendorConstants.Operation` aliases should be resolved in a dedicated constants chunk. (3) It would be helpful to have the `ICommandResponse` interface and `BleOperateManager` callback dispatch code available to document the full response path. |
