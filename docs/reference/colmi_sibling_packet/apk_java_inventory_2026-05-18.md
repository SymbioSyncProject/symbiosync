# QRing APK Java File Inventory — 2026-05-18

**Analyst:** Sibling analyst (decompiled APK static analysis)
**Source trees:**
- `D:\feedback\qring\decompiled\sources` — 3,397 .java files (jadx first pass)
- `D:\feedback\qring\decompiled4\sources` — 4,372 .java files (jadx second pass, richer output)

**Total .java files across both trees:** ~7,769 (with overlap)

---

## Package Structure Overview

| Package | File count | Role | Candidate for BLE/biometrics? |
|---|---|---|---|
| `com.oudmon.ble.*` | ~60 | Vendor BLE SDK: connection, communication, data parsing | **PRIMARY** |
| `com.qcwireless.smart.*` | ~13 (decompiled) / ~200+ (decompiled4) | QRing app UI, ViewModels, activities | **SECONDARY** (app-level sync orchestration) |
| `com.cxxyuek.app.utyi.*` | ~2,500 | Obfuscated app code (46 sub-packages) | Unlikely — no direct BLE SDK references found |
| `com.realsil.sdk.*` | ~30 | RealTek SDK (audio/SPP/MMI constants) | **TERTIARY** (Mmi constants used as command byte values) |
| `com.oudmon.qc_utils.*` | ~5 | Utility library (bytes, date, bluetooth) | Support (ByteUtil, DataTransferUtils, DateUtil) |
| Third-party libs | ~1,500+ | Glide, OkHttp, Protobuf, Firebase, etc. | Not relevant |

---

## `com.oudmon.ble.base.bluetooth.*` — BLE Connection Lifecycle

| File | Role | Key content |
|---|---|---|
| `BleBaseControl.java` | Core BLE connection manager | GATT connect/disconnect, `BluetoothGattCallback`, service discovery, reconnection logic (10 retries, 6 inner-fail loops), 40s connection timeout |
| `BleOperateManager.java` | BLE operation orchestrator (HandlerThread) | Executes `BaseRequest` objects, manages notify listeners (`SparseArray`), broadcasts events via `LocalBroadcastManager`, UUID enable flow |
| `DeviceManager.java` | Device info holder | Device name, address, firmware version |
| `IBleListener.java` | BLE event interface | `bleCharacteristicChanged`, `bleGattConnected`, `bleGattDisconnect`, `bleServiceDiscovered`, `bleNoCallback` |
| `BleAction.java` | Broadcast action constants | `com.swatchdevice.pro.*` action strings |
| `BeanFactory.java` | **Command ID → Response class factory** | Maps command IDs (1–123) to `BaseRspCmd` subclasses (see walkthrough) |
| `QCBluetoothCallbackReceiver.java` | Small-data notification router | `onCharacteristicChange`: CRC check → `QCDataParser.parserAndDispatchReqData` → `parserAndDispatchNotifyData` |
| `QCBluetoothCallbackCloneReceiver.java` | Clone receiver (empty stub) | Receives same broadcasts, no-op |
| `QCBluetoothCallbackBigDataCloneReceiver.java` | Large-data notification router | `onCharacteristicChange` → `LargeDataParser.parseBigLargeData` |
| `QCDataParser.java` | Small-data parser/dispatcher | Strips CRC, looks up command ID, creates `BaseRspCmd` via `BeanFactory`, calls `acceptData` |
| `LargeDataParser.java` | Large-data reassembler | Accumulates fragments across BLE MTU, checks header `0xBC`, dispatches to `LargeDataHandler` response map |
| `SDKInit.java` | SDK initialization | Creates `BleOperateManager` |
| `OnGattEventCallback.java` | GATT event callback interface | `onReceivedData(uuid, data)` |
| `queue/BleDataBean.java` | BLE write queue item | Holds byte array + packet length |
| `queue/BleConsumer.java` | Queue consumer | Writes packets to GATT characteristic |
| `queue/BleThreadManager.java` | Thread-safe queue manager | `addData(BleDataBean)`, `clean()` |
| `spp/*` | Serial Port Profile (RealTek SPP) | Music control, not biometric |

---

## `com.oudmon.ble.base.communication.*` — Protocol Constants & Infrastructure

| File | Role | Key content |
|---|---|---|
| **`Constants.java`** | **UUID and packet constants** | **Service UUID** `6e40fff0-b5a3-f393-e0a9-e50e24dcca9e`, **Notify UUID** `6e400003-...`, **Write UUID** `6e400002-...`, **Descriptor UUID** `00002902-...`, **LargeData Service** `de5bf728-...`, **LargeData Notify** `de5bf729-...`, **LargeData Write** `de5bf72a-...`, **Packet length** `l=16`, **High-bit mask** `m=128` |
| `CommandHandle.java` | Command execution singleton | `executeReqCmd(BaseReqCmd, ICommandResponse)`: writes to `6e400002`, stores callback in `ConcurrentHashMap` keyed by `cmdId & ~128` |
| `ICommandResponse.java` | Response callback interface | `onDataResponse(T extends BaseRspCmd)` |
| `ILargeDataResponse.java` | Large-data response interface | `parseData(int cmdId, byte[] data)` |
| `ILargeDataSleepResponse.java` | Sleep-specific callback | `sleepData(SleepNewProtoResp)` |
| `IIntervalBloodOxygenCallback.java` | Interval SpO2 callback | `readIntervalBloodOxygen(IntervalBloodOxygenEntity)` |
| `JPackageManager.java` | Packet length manager | Default `20` bytes, `setLength()` updates from device |
| `LargeDataHandler.java` | **Large-data command builder & parser** | All BigData operations: sleep, interval HR/SpO2/temp, manual HR/SpO2, contacts, alarms, QR code, GPS (see walkthrough) |
| `CompressUtils.java` | Data compression | Used for large-data payloads |
| `DfuHandle.java` | DFU/OTA handler | Firmware update |

---

## `com.oudmon.ble.base.communication.req.*` — Request (Command) Classes

| File | Command byte | Sub-data | Purpose |
|---|---|---|---|
| `BaseReqCmd.java` | abstract | `getData()`: `[cmdByte, ...subData, CRC]` | Base: cmd byte at [0], sub-data at [1..n-1], CRC at [n-1] |
| `MixtureReq.java` | extends BaseReqCmd | `byte[] b` as sub-data | Setting read/write requests |
| `SetTimeReq.java` | `0x01` | 7 bytes BCD (year, month, day, hour, min, sec, language) | Set device time |
| `BloodOxygenSettingReq.java` | `0x2C` (44) | `[1]` read, `[2, enable, interval]` write | Read/write SpO2 interval setting |
| `HeartRateSettingReq.java` | `0x16` (22, via Mmi) | `[1]` read, `[2, enable, interval]` or `[2, enable, interval, start, low, high]` write | Read/write HR interval setting |
| `HrvSettingReq.java` | `0x38` (56, via Mmi) | `[1]` read, `[2, enable]` write | Read/write HRV enable |
| `HRVReq.java` | `0x39` (57, via Mmi) | `[action_byte]` | HRV data request |
| `PressureReq.java` | `0x37` (55, via Mmi) | `[action_byte]` | Pressure data request |
| `PressureSettingReq.java` | `0x36` (54, via Mmi) | `[1]` read, `[2, enable]` write | Read/write pressure setting |
| `BpSettingReq.java` | `0x0C` (12) | `[1]` read, `[2, enable, startH, startM, endH, endM, interval]` write | Blood pressure setting |
| `ReadHeartRateReq.java` | `0x15` (21, via Mmi) | 4-byte int (timestamp) | Read interval HR history |
| `RealTimeHeartRate.java` | `0x1E` (30) | `[type]` | Realtime HR start/stop |
| `StartHeartRateReq.java` | `0x69` (105, via Mmi) | `[type, param]` | Start HR/SpO2/BP/ECG measurement |
| `StopHeartRateReq.java` | `0x6A` (106, via Mmi) | `[type, param, 0]` | Stop measurement (type: 1=HR, 2=BP, 3=SpO2, 4=fatigue, 5=health, 7=ECG, 8=pressure, 9=sugar, 10=HRV, 11=temp) |
| `ReadPressureReq.java` | `0x14` (20) | 4-byte timestamp + 2 extra bytes | Read BP history |
| `ReadSleepDetailsReq.java` | `0x44` (68) | `[dayOffset, 15, startIndex, endIndex]` | Read sleep detail history |
| `ReadBandSportReq.java` | `0x13` (19) | 4-byte timestamp | Read sport data |
| `ReadTotalSportDataReq.java` | `0x07` | `[daysAgo]` | Read total step/sport summary |
| `ReadDetailSportDataReq.java` | `0x43` (67) | `[dayOffset, 15, startIndex, endIndex, 1]` | Read detailed step/sport history |
| `DeviceSupportReq.java` | `0x3C` (60, via Mmi) | none | Read device capability flags |
| `SimpleKeyReq.java` | any byte | none | Generic single-byte command |
| `FindDeviceReq.java` | — | — | Find phone |
| `BatterySavingReq.java` | — | — | Battery saving mode |
| `CameraReq.java` | — | — | Camera shutter |
| `DndReq.java` | — | — | Do not disturb |
| `TargetSettingReq.java` | — | — | Step goal |
| `SetAlarmReq.java` | — | — | Alarm setting |
| `DisplayTimeReq.java` | — | — | Display time setting |
| `BrightnessSettingsReq.java` | — | — | Screen brightness |
| `WeatherForecastReq.java` | — | — | Weather push |
| `MusicSwitchReq.java` | — | — | Music control |
| `PhoneGpsReq.java` | — | — | Phone GPS data |
| `PhoneSportReq.java` | — | — | Phone sport data |
| `AgpsReq.java` | — | — | A-GPS data |
| `AppRevisionReq.java` | — | — | Firmware version query |
| `BlackListReq.java` | — | — | Notification blacklist |
| `PushMsgUintReq.java` | — | — | Message push setting |
| `RestoreKeyReq.java` | — | — | Factory reset |
| `TestReq.java` | — | — | Test command |
| `BpReadConformReq.java` | — | — | BP read confirm |
| `SugarLipidsSettingReq.java` | — | — | Blood sugar/lipids setting |
| `MenstruationReq.java` | — | — | Menstruation setting |
| `MuslimReq.java` | — | — | Muslim prayer setting |
| `IntellReq.java` | — | — | Intelligent reminder |
| `LoverEventReq.java` | — | — | Lover event |
| `DegreeSwitchReq.java` | — | — | Celsius/Fahrenheit switch |
| `DialIndexReq.java` | — | — | Watch face index |
| `DeviceAvatarReq.java` | — | — | Device avatar |
| `DisplayClockReq.java` | — | — | Display clock style |
| `DisplayOrientationReq.java` | — | — | Display orientation |
| `DisplayStyleReq.java` | — | — | Display style |
| `PalmScreenReq.java` | — | — | Palm screen |
| `TouchControlReq.java` | — | — | Touch control |
| `TimeFormatReq.java` | — | — | 12h/24h format |
| `SetANCSReq.java` | — | — | ANCS setting |
| `BindAncsReq.java` | — | — | ANCS bind |
| `SetMessagePushReq.java` | — | — | Message push enable |
| `SetSitLongReq.java` | — | — | Sedentary reminder |
| `ReadAlarmReq.java` | — | — | Read alarm |
| `ReadDrinkAlarmReq.java` | — | — | Read drink alarm |
| `ReadHeartRateReq.java` | `0x15` (21) | 4-byte int (timestamp) | Read interval HR history |
| `ReadPersonalizationSettingReq.java` | — | — | Read personalization |
| `PhoneStillTime.java` | — | — | Phone still time |

---

## `com.oudmon.ble.base.communication.rsp.*` — Response (Parser) Classes

| File | Command ID | `acceptData` logic | Parsed fields |
|---|---|---|---|
| `BaseRspCmd.java` | abstract | `abstract acceptData(byte[])` | `cmdType`, `status` |
| `MixtureRsp.java` | extends BaseRspCmd | `bArr[0]`: action (1=read, 3=write) → `readSubData` | `action` |
| `SetTimeRsp.java` | 1 | — | — |
| `BatteryRsp.java` | 3 | `bArr[0]`=battery%, `bArr[1]`=charging(1) | `batteryValue`, `isCharging` |
| `RealTimeHeartRateRsp.java` | 30 | `bArr[0]`=HR value | `heart` |
| `StartHeartRateRsp.java` | 105 | `bArr[0]`=type, `bArr[1]`=errCode, `bArr[2]`=value, `bArr[3]`=sbp, `bArr[4]`=dbp | `type`, `errCode`, `value`, `sbp`, `dbp` |
| `StopHeartRateRsp.java` | — | `bArr[0]`=type, `bArr[1]`=errCode, `bArr[2]`=value, `bArr[3]`=sbp, `bArr[4]`=dbp | Same as Start |
| `ReadHeartRateRsp.java` | 21 | Multi-packet: `[0]`=0x00 init (count, range), `[1]`=first data (UTC+values), `[2+]`=continuation | `mHeartRateArray` (288-byte array, 5-min intervals), `mUtcTime`, `range` |
| `HeartRateSettingRsp.java` | 22 | MixtureRsp: `bArr[1]`=enable, `bArr[2]`=interval, `bArr[3]`=startInterval, `bArr[4]`=tooLow, `bArr[5]`=tooHigh | `isEnable`, `heartInterval`, `startInterval`, `tooLowReminder`, `tooHighReminder` |
| `HRVSettingRsp.java` | 56 | MixtureRsp: `bArr[1]`=enable | `isEnable` |
| `HRVRsp.java` | 57 | Multi-packet: `[0]`=0x00 init (count, range), `[1]`=first data (dayOffset+values), `[2+]`=continuation | `hrvArray` (13 bytes per entry), `offset`, `range`, `today` |
| `BloodOxygenSettingRsp.java` | 44 | MixtureRsp: `bArr[1]`=enable, `bArr[2]`=interval | `isEnable`, `interval` |
| `PressureRsp.java` | 55 | Multi-packet: same pattern as HRV | `pressureArray`, `offset`, `range`, `today` |
| `PressureSettingRsp.java` | 54 | MixtureRsp: `bArr[1]`=enable | `isEnable` |
| `ReadBlePressureRsp.java` | 20 | Per-record: 4-byte timestamp + sbp + dbp | `valueList` (BlePressure: timestamp, sbp, dbp) |
| `BpSettingRsp.java` | 12 | — | — |
| `BpDataRsp.java` | 13 | — | — |
| `ReadSleepDetailsRsp.java` | 68 | Multi-packet: `[0]`=0xF0 init, then BCD date + timeIndex + 8 sleep quality bytes | `bleSleepDetailses` (year, month, day, timeIndex, sleepQualities[8]) |
| `SleepNewProtoResp.java` | (large-data) | Parsed by `LargeDataHandler.parseDaySleep` | `st`, `et`, `list` (DetailBean: type, duration), `lunchBreak`, `lunchSt`, `lunchEt`, `lunchList` |
| `ReadDetailSportDataRsp.java` | 67 | Multi-packet: `[0]`=0xF0 init, then BCD date + timeIndex + calorie/steps/distance | `bleStepDetailses` |
| `TotalSportDataRsp.java` | 7 | 2-packet: packet 0 = daysAgo+date+totalSteps+runningSteps+calorie, packet 1 = walkDistance+sportDuration+sleepDuration | `bleStepTotal` |
| `DeviceSupportFunctionRsp.java` | 60 | 9-byte bitmask | ~30 boolean capability flags |
| `DeviceNotifyRsp.java` | 115 | Device-initiated notifications | — |
| `PackageLengthRsp.java` | 47 | Updates `JPackageManager.setLength()` | — |
| `AppRevisionResp.java` | -223 | Firmware version | — |
| `SimpleStatusRsp.java` | 114 | Status byte | — |
| `DeviceAvatarRsp.java` | 50 | — | — |
| `MusicCommandRsp.java` | 29 | — | — |
| `CameraNotifyRsp.java` | 2 | — | — |
| `DisplayTimeRsp.java` | 31 | — | — |
| `DndRsp.java` | 6 | — | — |
| `PalmScreenRsp.java` | 5 | — | — |
| `TimeFormatRsp.java` | 10 | — | — |
| `PhoneNotifyRsp.java` | 17 | — | — |
| `ReadAlarmRsp.java` | 40 | — | — |
| `ReadSitLongRsp.java` | 38 | — | — |
| `ReadMessagePushRsp.java` | 97 | — | — |
| `MuslimRsp.java` | 122 | — | — |
| `MuslimRemindRsp.java` | 82 | — | — |
| `MuslimTargetRsp.java` | 123 | — | — |
| `BloodSugarLipidsSettingRsp.java` | 58 | — | — |
| `TouchControlResp.java` | 59 | — | — |
| `WeatherForecastRsp.java` | 26 | — | — |
| `DegreeSwitchRsp.java` | 25 | — | — |
| `TargetSettingRsp.java` | 33 | — | — |
| `FindPhoneRsp.java` | 34 | — | — |
| `TodaySportDataRsp.java` | 72 | — | — |
| `AppSportRsp.java` | 119 | — | — |
| `HealthEcgRsp.java` | — | — | — |
| `PpgDataRspCmd.java` | — | — | — |
| `QueryDataDistributionRsp.java` | — | — | — |
| `SwitchOTARsp.java` | — | — | — |
| `ReadHeartRateRspBackup.java` | — | — | — |
| `ReadANCSRsp.java` | — | — | — |
| `AgpsRsp.java` | — | — | — |
| `AppGpsRsp.java` | — | — | — |
| `AppSportRsp.java` | — | — | — |

---

## `com.oudmon.ble.base.communication.bigData.bean.*` — BigData Entity Classes

| File | Fields | Purpose |
|---|---|---|
| `BaseBean.java` | `code` | Base response |
| `IntervalHeartRateEntity.java` | `dayIndex`, `interval`, `array` (List<Integer>) | Interval HR history (one value per interval period) |
| `IntervalBloodOxygenEntity.java` | `dayIndex`, `interval`, `array` (List<Integer>) | Interval SpO2 history |
| `IntervalTemperatureEntity.java` | `dayIndex`, `interval`, `array` (List<Float>) | Interval temperature history (values / 100.0) |
| `ManualHeartRate.java` | `index`, `data` (List<DetailBean: m=minute, v=value>) | Manual/on-demand HR history |
| `ManualBloodOxygen.java` | `index`, `data` (List<DetailBean: m=minute, v=value>) | Manual/on-demand SpO2 history |
| `ContactBean.java` | `phoneNumber`, `contactName` | Contact for device |
| `ECardEntity.java` | `type`, `url`, `support`, `deviceError`, `readOrWrite` | QR code/e-card |
| `ClassicBluetooth.java` | `deviceMac`, `deviceName` | Classic BT pairing |
| `EmergencyContactEntity.java` | — | Emergency contact |

---

## `com.oudmon.ble.base.communication.bigData.resp.*` — BigData Callback Interfaces

| File | Method | Purpose |
|---|---|---|
| `IIntervalHeartRateCallback.java` | `readIntervalHeartRate(IntervalHeartRateEntity)` | Interval HR data callback |
| `IIntervalTemperatureCallback.java` | `readIntervalData(IntervalTemperatureEntity)` | Interval temperature callback |
| `ILargeDataBaseResponse.java` | `resp(BaseBean)` | Generic base response |
| `ILargeDataClassicBluetoothResponse.java` | `classicBluetooth(ClassicBluetooth)` | Classic BT callback |
| `ILargeDataManualBloodOxygenResponse.java` | `manualBloodOxygen(ManualBloodOxygen)` | Manual SpO2 callback |
| `ILargeDataManualHeartRateResponse.java` | `manualHeart(ManualHeartRate)` | Manual HR callback |
| `ILargeDataQrCodeResponse.java` | `qrCode(ECardEntity)` | QR code callback |

---

## `com.oudmon.ble.base.communication.entity.*` — Data Entity Classes

| File | Fields | Purpose |
|---|---|---|
| `BleSleepDetails.java` | `year`, `month`, `day`, `timeIndex`, `sleepQualities[8]` | Sleep detail record (old protocol) |
| `BleStepTotal.java` | `daysAgo`, `year`, `month`, `day`, `totalSteps`, `runningSteps`, `calorie`, `walkDistance`, `sportDuration`, `sleepDuration` | Daily step summary |
| `BleStepDetails.java` | `year`, `month`, `day`, `timeIndex`, `calorie`, `walkSteps`, `distance` | Hourly step detail |
| `BleSport.java` | `rateArray` (HR during activity) | Sport activity record |
| `BlePressure.java` | `timestamp`, `sbp`, `dbp` | Blood pressure record |
| `BpDataEntity.java` | — | BP data entity |
| `BpEvent.java` | — | BP event |
| `AlarmEntity.java` | — | Alarm |
| `StartEndTimeEntity.java` | `startHour`, `startMinute`, `endHour`, `endMinute` | Time range |
| `MessagePushBean.java` | `message`, `time` | Push message |
| `RecordEntity.java` | — | Recording |

---

## `com.oudmon.ble.base.communication.utils.*` — Utility Classes

| File | Key methods | Purpose |
|---|---|---|
| `ByteUtil.java` | `byteToInt`, `bytesToInt`, `intToByte`, `byteArrayToString`, `concat`, `hiword`, `loword` | Byte manipulation |
| `BLEDataFormatUtils.java` | `decimalToBCD`, `BCDToDecimal`, `bytes2Int` | BCD encoding/decoding |
| `DataParseUtils.java` | `byteArrayToInt`, `intToByteArray` | Little-endian int conversion |
| `CRC16.java` | `calcCrc16` | CRC16 for large-data packets |

---

## `com.oudmon.ble.base.communication.schedule.*`

| File | Fields | Purpose |
|---|---|---|
| `ScheduleEntity.java` | `a`(content), `b`, `c`, `d`, `e`, `f`(List) | Schedule/alarm |

---

## `com.oudmon.ble.base.communication.dfu_temperature.*`

| File | Fields | Purpose |
|---|---|---|
| `TemperatureEntity.java` | — | Temperature data entity |
| `TemperatureOnceEntity.java` | — | Single temperature reading |
| `TemperatureHandle.java` | — | Temperature command handler |

---

## `com.oudmon.ble.base.communication.file.*`

| File | Purpose |
|---|---|
| `FileHandle.java` | File transfer base |
| `AlbumHandle.java` | Album/image transfer |
| `AvatarHandle.java` | Avatar transfer |
| `EbookHandle.java` | E-book transfer |
| `RecordHandle.java` | Audio recording transfer |
| `DataHelper.java` | Data helper |
| `PlateEntity.java` | Watch face plate |

---

## `com.oudmon.ble.base.communication.sport.*`

| File | Purpose |
|---|---|
| `SportPlusData.java` | Extended sport data |
| `SportPlusEntity.java` | Extended sport entity |
| `SportPlusHandle.java` | Extended sport handler |
| `SportPlusType.java` | Sport type enum |
| `SportLocation.java` | Sport GPS location |

---

## `com.oudmon.ble.base.communication.responseImpl.*`

| File | Purpose |
|---|---|
| `DeviceNotifyListener.java` | Device-initiated notification multiplexer |
| `DeviceSportNotifyListener.java` | Sport notification multiplexer |
| `InnerCameraNotifyListener.java` | Camera notification |
| `MusicCommandListener.java` | Music command notification |
| `PackageLengthListener.java` | Updates `JPackageManager` packet length |

---

## `com.oudmon.ble.base.request.*` — BLE Request Infrastructure

| File | Purpose |
|---|---|
| `BaseRequest.java` | Abstract BLE request (service UUID, characteristic UUID) |
| `WriteRequest.java` | Write to characteristic |
| `LocalWriteRequest.java` | Write with callback |
| `ReadRequest.java` | Read from characteristic |
| `ReadRssiRequest.java` | Read RSSI |
| `EnableNotifyRequest.java` | Enable/disable notifications |

---

## `com.oudmon.ble.base.scan.*` — BLE Scanning

| File | Purpose |
|---|---|
| `BleScannerCompat.java` | Scanner compatibility |
| `BleScannerHelper.java` | Scanner helper |
| `BluetoothScannerImplJB.java` | JB scanner impl |
| `BluetoothScannerImplLollipop.java` | Lollipop+ scanner impl |
| `ScanRecord.java` | Scan record parser |

---

## `com.realsil.sdk.bbpro.params.Mmi.java` — Command Byte Constants

The `Mmi` class provides constants used as command byte values in `MixtureReq` subclasses. Key mappings relevant to SymbioSync:

| Mmi constant | Decimal | Hex | Used by |
|---|---|---|---|
| `AU_MMI_DEV_MIC_VOL_UP` | 21 | 0x15 | `ReadHeartRateReq` |
| `AU_MMI_DEV_MIC_VOL_DOWN` | 22 | 0x16 | `HeartRateSettingReq` |
| `AU_MMI_MIC_SWITCH` | 106 | 0x6A | `StopHeartRateReq` |
| `AU_MMI_OUTPUT_INDICATION_3` | 105 | 0x69 | `StartHeartRateReq` |
| `AU_MMI_AV_EQ_MODE_UP` | 56 | 0x38 | `HrvSettingReq` |
| `AU_MMI_AV_EQ_MODE_DOWN` | 57 | 0x39 | `HRVReq` |
| `AU_MMI_AV_REWIND` | 55 | 0x37 | `PressureReq` |
| `AU_MMI_AV_FASTFORWARD` | 54 | 0x36 | `PressureSettingReq` |
| `AU_MMI_AV_PLAY_PAUSE` | 50 | 0x32 | Used in `ReadPressureReq` |
| `AU_MMI_AV_REWIND_RELEASE` | 60 | 0x3C | `DeviceSupportReq` |
| `AU_MMI_GAMING_MODE_SWITCH` | -128 | 0x80 | Bitmask in `DeviceSupportFunctionRsp` |

---

## `com.qcwireless.smart.*` — QRing App UI (decompiled4)

The decompiled4 tree reveals a full app with ~200+ files. Key areas:

| Package | Files | Role |
|---|---|---|
| `ui.base.bean.request.healthy.*` | `CommitSleepNewProtocolParam`, `HealthyDataDownRequest`, `SleepDetailRequest` | Server sync request models |
| `ui.home.*` | Home fragments, ViewModels | Main dashboard |
| `ui.device.*` | Device settings, firmware | Device management |
| `ui.health.*` | HR, SpO2, sleep, BP, HRV, pressure ViewModels | **Biometric sync orchestration** |
| `ui.sport.*` | Sport activities | Sport tracking |
| `ui.mine.*` | Profile, settings, login | User management |
| `ui.mine.thirdSync.googlefit.*` | `GoogleFitSync` | Google Fit upload (HR, sleep, steps) |

---

## `com.cxxyuek.app.utyi.*` — Obfuscated App Code

~2,500 files across 46 sub-packages (e.g., `auzjuk10`, `awpetw22`, `cputra0`). Search results:

| Term | Files matching | Notes |
|---|---|---|
| `bpm` | 16 | Likely UI display, not protocol |
| `cmd` | 11 | Likely command dispatch wrappers |
| `GATT` | 1 | Single reference |
| `step/Step` | 2 | Step display |
| `Bluetooth`, `UUID`, etc. | 0 | No direct BLE SDK references |

**Conclusion:** The obfuscated package contains UI/business logic that calls the `com.oudmon.ble` SDK via its public API. It does not contain protocol byte definitions or response parsers. All protocol logic is in the `com.oudmon.ble` package.
