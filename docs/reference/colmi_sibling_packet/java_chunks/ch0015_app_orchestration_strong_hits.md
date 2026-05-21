# CH0015 — App Orchestration Strong Hits (Repository Entities & Healthy Repositories)

**Chunk ID:** CH0015  
**Chunk type:** app_orchestration_strong_hits  
**Source tree:** decompiled4 (`com/qcwireless/smart`)  
**Focus question:** SpO2 domain: entity classes, BloodOxygenRepository fields/flows, measurement modes (continuous/manual/app), device/server sync dependencies. Also covers sibling healthy repositories (BP, sugar, ECG, HR detail) and entity classes for sleep, steps, sport, sync, targets, user.  
**Qualitative telemetry guess:** I'm likely running as a Claude-family model (Claude 3.5 Sonnet or similar), given the multi-step analytical structure, tool-use patterns, and preference for structured tabular output.

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J05359 | com/qcwireless/smart/ui/base/repository/entity/SleepDetail.java | documented_storage | sleep, sync_scheduler | Room entity for per-night sleep detail; PK (device_address, date_str) | deviceAddress, dateStr, intervar, index_str, quality, sync, lastSyncTime | @Entity, @ColumnInfo, Room | QcSleepDetailDao | — | Table `sleep_detail`; interval field misspelled as "intervar"; quality is JSON string; index_str is sleep-stage index array | no |
| J05360 | com/qcwireless/smart/ui/base/repository/entity/SleepLunchProtocol.java | documented_storage | sleep, storage_db, sync_scheduler | Room entity for lunch-nap sleep protocol; PK (device_address, date_str); has upload tracking | deviceAddress, dateStr, detail, lunchSt, lunchEt, sync, lastSyncTime, isUploadServer, uploadServerUnixTime, lunchList | @Entity, QcSleepLunchProtocolDao, updateFromDatabase(dao) | QcSleepLunchProtocolDao | — | Table `sleep_lunch_protocol`; lunchSt/lunchEt = lunch nap start/end; dataEquals() compares only data fields; updateFromDatabase() syncs upload status from existing DB row | no |
| J05361 | com/qcwireless/smart/ui/base/repository/entity/SleepNewProtocol.java | documented_storage | sleep, storage_db, sync_scheduler | Room entity for new sleep protocol; PK (device_address, date_str); has upload tracking | deviceAddress, dateStr, detail, st, et, sync, lastSyncTime, lunchList, isUploadServer, uploadServerUnixTime | @Entity, QcSleepNewProtocolDao, updateFromDatabase(dao) | QcSleepNewProtocolDao | — | Table `sleep_new_protocol`; st/et = sleep start/end; mirrors SleepLunchProtocol but without lunch-specific fields; updateFromDatabase() pattern identical to SleepLunchProtocol | no |
| J05362 | com/qcwireless/smart/ui/base/repository/entity/SleepTotalHistory.java | documented_spO2_cross_domain | hr, hrv_regular, sleep, spo2 | Room entity for daily sleep summary; PK (device_address, date_str); **includes avgBloodOxygen** | deviceAddress, dateStr, totalSleep, deepSleep, lightSleep, rapidSleep, awake, startTime, endTime, lunchStart, lunchEnd, unixTime, **avgHeart**, **avgBloodOxygen**, **avgHrv**, bedtime | @Entity, @ColumnInfo | QcSleepTotalDao | — | Table `sleep_total`; **KEY SpO2 CROSS-DOMAIN**: avgBloodOxygen stored alongside avgHeart and avgHrv in sleep summary — sleep session provides averaged SpO2 reading; rapidSleep = REM sleep | no |
| J05364 | com/qcwireless/smart/ui/base/repository/entity/SportPlusDetail.java | documented_storage | steps_sport, sync_scheduler | Room entity for sport/exercise session records; PK (device_address, start_time, sport_type) | deviceAddress, dateStr, startTime, sportType, duration, distance, calories, steps, rateValue, avgRate, sync | @Entity, @ColumnInfo | QcSportPlusDetailDao | — | Table `sport_plus_detail`; rateValue is JSON string of HR samples during exercise; avgRate is average HR; sportType is int enum | no |
| J05365 | com/qcwireless/smart/ui/base/repository/entity/StepDetail.java | documented_storage | sync_scheduler | Room entity for per-day step detail; PK (device_address, date_str) | deviceAddress, dateStr, intervar, totalActiveTime, index_str, counts, miles, calories, sync, lastSyncTime | @Entity, @ColumnInfo | QcStepDetailDao | — | Table `step_detail`; counts/miles/calories are JSON strings; intervar = interval in minutes; totalActiveTime = active minutes | no |
| J05366 | com/qcwireless/smart/ui/base/repository/entity/StepTotal.java | documented_storage | storage_db | Room entity for daily step totals; PK (device_address, date_str); has upload tracking | deviceAddress, dateStr, step, distance, carolie, unixTime, isUploadServer, uploadServerUnixTime | @Entity, QcStepTotalDao, updateFromDatabase(dao), dataEquals() | QcStepTotalDao | — | Table `step_total`; "carolie" is misspelling of "calorie"; dataEquals() compares step/distance/calore only; updateFromDatabase() syncs upload status | no |
| J05367 | com/qcwireless/smart/ui/base/repository/entity/SyncDataEntity.java | documented_sync | sync_scheduler | Room entity for sync watermark tracking; PK (uid, data_action) | uid, action, lastSyncTime | @Entity, @ColumnInfo | QcSyncDataDao | — | Table `sync_entity`; action is a string key (e.g. "blood_oxygen"); lastSyncTime is the server-side watermark for incremental sync; minimal entity (44 lines) | no |
| J05368 | com/qcwireless/smart/ui/base/repository/entity/TargetEntity.java | documented_storage | bigdata, sleep, steps_sport | Room entity for user goals/targets; PK (device_address) | deviceAddress, goalSteps, goalCalorie, goalDistance, goalSportTime, goalSleepTime, sleepStart, sleepEnd, sleepDuration | @Entity, UserConfig, Companion.getDeFault() | QcTargetDao | — | Table `target_entity`; defaults: 10000 steps, 200 cal, 5km, 1.5hr sport, 8hr sleep; sleepStart=1320 (22:00), sleepEnd=540 (09:00), sleepDuration=660 (11hr) | no |
| J05369 | com/qcwireless/smart/ui/base/repository/entity/UserEntity.java | documented_storage | sleep, steps_sport | Room entity for user profile; PK (uid) | title (=uid), email, nickName, gender, weight, weightLbs, height, birthday, avatarUrl, localAvatarUrl, goalSteps, goalCalorie, goalDistance, goalSportTime, goalSleepTime, registerDate, update | @Entity, UserConfig, DateUtil, Companion | QcUserDao | — | Table `user`; title field is actually uid (JADX rename artifact); getAge() computed from birthday; default gender=1 (male), weight=60kg, height=175cm; goal fields duplicated from TargetEntity | no |
| J05373 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$downBoFromServer$2.java | documented_spO2_sync | spo2, sync_scheduler | **SuspendLambda** — Flow builder for SpO2 download from server; captures $uid and $lastSyncId | invokeSuspend(), $uid, $lastSyncId, AnonymousClass1 (inner coroutine) | SuspendLambda, FlowCollector, Spo2DownResp, NetState | BloodOxygenRepository.downBoFromServer() | — | Inner class AnonymousClass1 emits NetState<List<Spo2DownResp>>; this is the flow producer that calls the server API; $2 = flow {} builder | no |
| J05374 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$downBoFromServer$3.java | documented_spO2_sync | spo2 | **SuspendLambda** — onStart handler for SpO2 download flow; emits loading state | invokeSuspend() | SuspendLambda, FlowCollector, NetState | BloodOxygenRepository.downBoFromServer() | — | Emits NetState.loading() before the actual API call; $3 = onStart {} block | no |
| J05375 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$downBoFromServer$4.java | documented_spO2_sync | spo2 | **SuspendLambda** — catch handler for SpO2 download flow; error recovery | invokeSuspend() | SuspendLambda, FlowCollector, NetState | BloodOxygenRepository.downBoFromServer() | — | Emits NetState with error code on failure; $4 = catch {} block | no |
| J05376 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$updateBloodOxygenDetailToServer$2.java | documented_spO2_sync | spo2 | **SuspendLambda** — Flow builder for SpO2 upload to server; reads un-uploaded records from DAO | invokeSuspend(), this$0, AnonymousClass1 | SuspendLambda, FlowCollector, QcBloodOxygenDao, NetState | BloodOxygenRepository.updateBloodOxygenDetailToServer() | — | Inner class reads DAO for un-uploaded records, maps to upload request; $2 = flow {} builder | no |
| J05377 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$updateBloodOxygenDetailToServer$3.java | documented_spO2_sync | spo2 | **SuspendLambda** — onStart handler for SpO2 upload flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | BloodOxygenRepository.updateBloodOxygenDetailToServer() | — | Emits loading state; $3 = onStart {} block | no |
| J05378 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository$updateBloodOxygenDetailToServer$4.java | documented_spO2_sync | spo2 | **SuspendLambda** — catch handler for SpO2 upload flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | BloodOxygenRepository.updateBloodOxygenDetailToServer() | — | Error recovery; $4 = catch {} block | no |
| J05379 | com/qcwireless/smart/ui/base/repository/healthy/BloodOxygenRepository.java | **documented_spO2_core** | bigdata, spo2, storage_db, sync_scheduler | **PRIMARY SpO2 REPOSITORY** — singleton; manages continuous + manual SpO2 data; BLE sync, server upload/download, chart queries | bloodOxygenDao, bloodOxygenManualDao, syncAutoBloodOxygen(), downBoFromServer(), updateBloodOxygenDetailToServer(), queryBloodOxygenByDate(), queryBloodOxygenByDateDetail(), queryBloodOxygenByDateResultMap(), queryByDateRange(), queryLastBloodOxygen(), queryLastBloodOxygenDate(), queryLastManualBloodOxygenDate(), queryManualBloodOxygen(), queryManualBloodOxygenAll(), queryManualByDateRange(), saveManualBloodOxygen(), deleteData(), calendarBloodOxygen(), updateUploadStatus(), updateManualUploadStatus() | ILargeDataResponse, LargeDataHandler, ReadBlePressureRsp, ByteUtil, QcBloodOxygenDao, ManualBloodOxygenDao, BloodOxygenEntity, BloodOxygenManualEntity, Spo2DownResp, MoshiUtils, EventBus, ManualRefreshEvent | ViewModel/UseCase layer | cmd_id: 42 (0x2A) in syncAutoBloodOxygen; packet_size: 49 bytes per record | **CRITICAL FILE**: 510 lines; two DAOs (continuous + manual); syncAutoBloodOxygen uses LargeDataHandler.syncBloodOxygen(offset, callback); BLE packet: cmd=42, 49-byte records, day_offset at byte[0], even bytes=maxArray, odd bytes=minArray; BloodOxygenEntity constructor: (deviceAddress, dateStr, maxArray_json, minArray_json, zeroTime, isFromServer, unixTime, sync, uploadCount, 384, null) — 384 is likely a constant/version code | no |
| J05380 | com/qcwireless/smart/ui/base/repository/healthy/BloodPressureRepository$downBpFromServer$2.java | documented_sync | sync_scheduler | SuspendLambda — Flow builder for BP download from server; captures $uid and $lastSyncId | invokeSuspend(), $uid, $lastSyncId, AnonymousClass1 | SuspendLambda, FlowCollector, BpDownResp, NetState, BaseConnectionManager | BloodPressureRepository.downBpFromServer() | STATE_DATA_PREPARED constant in debug metadata | Mirror of SpO2 download pattern but for blood pressure; $2 = flow {} builder | no |
| J05383 | com/qcwireless/smart/ui/base/repository/healthy/BloodPressureRepository$syncAutoBp$1$1.java | documented_ble | ble_connection, storage_db, sync_scheduler | SuspendLambda — Coroutine for auto BP sync from BLE device; processes BpDataRsp | invokeSuspend(), $it (BpDataRsp), this$0 | SuspendLambda, BpDataRsp, BpDataEntity, BloodPressureEntity, QcBloodPressureDao, CalcBloodPressureByHeart, GattError | BloodPressureRepository.syncAutoBp() | — | Processes BpDataRsp from BLE; uses CalcBloodPressureByHeart for BP estimation; GattError imported for error handling; stores BloodPressureEntity via DAO | no |
| J05387 | com/qcwireless/smart/ui/base/repository/healthy/BloodPressureRepository.java | documented_ble | storage_db, sync_scheduler, uart_small_data | **BP Repository** — singleton; manages continuous + manual BP data; BLE command-based sync (UART), server sync | bloodPressureDao, bloodPressureManualDao, syncAutoBp(), downBpFromServer(), updateBloodPressureDetailToServer(), queryBloodPressureByDate(), saveManualBloodPressure(), calendarBloodPressure(), updateUploadStatus(), updateManualUploadStatus() | CommandHandle, ICommandResponse, BpReadConformReq, ReadPressureReq, SimpleKeyReq, BaseRspCmd, BpDataRsp, ReadBlePressureRsp, ManualBloodPressureDao, QcBloodPressureDao | ViewModel/UseCase layer | cmd_ids: 0x006f, 0x0098, 0x7e8 | 421 lines; BP uses UART small-data commands (not LargeDataHandler like SpO2); command-based protocol with BpReadConformReq, ReadPressureReq, SimpleKeyReq; three distinct BLE command IDs | no |
| J05388 | com/qcwireless/smart/ui/base/repository/healthy/BloodSugarRepository.java | documented_storage | bigdata, storage_db, sync_scheduler | **Blood Sugar Repository** — singleton; manages continuous + app-manual + continuous-app sugar data; three DAOs | bloodSugarDao, qcAppManualSugarDao, qcAppManualSugarContinuousDao, syncAutoBloodSugar(), downBsFromServer(), updateBloodSugarDetailToServer(), queryBloodSugarByDate(), saveManualBloodSugar(), saveAppManualBloodSugar(), saveAppContinuousBloodSugar(), queryManualBloodSugar(), queryAppManualBloodSugar(), queryAppContinuousBloodSugar(), calendarBloodSugar(), updateUploadStatus() | ILargeDataResponse, LargeDataHandler, ReadBlePressureRsp, ByteUtil, QcBloodSugarDao, QcAppManualSugarDao, QcAppManualSugarContinuousDao | ViewModel/UseCase layer | — | 418 lines; **three measurement modes**: (1) continuous/device-auto via LargeDataHandler, (2) app-manual spot-check, (3) app-continuous; mirrors SpO2 pattern but with additional app-initiated modes | no |
| J05389 | com/qcwireless/smart/ui/base/repository/healthy/EcgRepository.java | documented_storage | storage_db | **ECG Repository** — singleton; simple CRUD for ECG records | ecgDao, queryLastEcg(mac), queryEcgByUnixTime(mac, unixTime), queryEcgByType(mac, type), queryAllEcg(mac), deleteByDeviceAndDate(mac, unixTime) | QcEcgDao, QcEcgEntity | ViewModel/UseCase layer | — | 79 lines; minimal repository — no BLE sync, no server upload; query-only + delete; type field distinguishes ECG measurement types | no |
| J05390 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository$aiChatGPT$2.java | documented_ai | bigdata, spo2 | SuspendLambda — Flow builder for AI chat (GPT) integration; captures $uid and $messages | invokeSuspend(), $uid, $messages, AnonymousClass1 | SuspendLambda, FlowCollector, AiChatBean, NetState | HealthyRepository.aiChatGPT() | 0x0082, 0xffffffffffffd499, 95 | AI health chat feature; streams token responses; 4 debug labels (94, 94, 96, 100 line numbers in HealthyRepository.kt); spo2 tag likely due to co-location | no |
| J05393 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository$getFirmwareInfo$2.java | documented_storage | storage_db | SuspendLambda — Flow builder for firmware info; queries DeviceSettingEntity by mac + "com.qcwxkjvip.DFUInfo" | invokeSuspend(), this$0, $mac | SuspendLambda, FlowCollector, QcDeviceSettingDao, DeviceSettingEntity | HealthyRepository.getFirmwareInfo() | — | Queries device_setting table with action="com.qcwxkjvip.DFUInfo"; 36-line source | no |
| J05395 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository$getFirmwareInfo$5.java | documented_storage | storage_db | SuspendLambda — catch handler for firmware info flow; on error, inserts default DFUInformationBean | invokeSuspend(), this$0, $mac | SuspendLambda, FlowCollector, QcDeviceSettingDao, DeviceSettingEntity, DFUInformationBean, MoshiUtilsKt | HealthyRepository.getFirmwareInfo() | VendorConstants.Operation.SET_APT_NR_ON_OFF | On error: inserts DeviceSettingEntity(mac, "com.qcwxkjvip.DFUInfo", toJson(default DFUInformationBean)) then emits empty DFUInformationBean; fallback pattern | no |
| J05396 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository$getLocalWatchFaceVersion$2.java | documented_storage | storage_db | SuspendLambda — Flow builder for watch face version; queries DeviceSettingEntity by mac + "com.qcwxkjvip.WatchFaceMarketVersion" | invokeSuspend(), this$0, $mac | SuspendLambda, FlowCollector, QcDeviceSettingDao, DeviceSettingEntity | HealthyRepository.getLocalWatchFaceVersion() | — | Queries device_setting table with action="com.qcwxkjvip.WatchFaceMarketVersion"; mirrors getFirmwareInfo$2 pattern | no |
| J05398 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository$getLocalWatchFaceVersion$5.java | documented_storage | storage_db | SuspendLambda — catch handler for watch face version flow; on error, inserts default with hwVersion + "0" | invokeSuspend(), this$0, $mac | SuspendLambda, FlowCollector, QcDeviceSettingDao, DeviceSettingEntity, WatchFaceVersionBean, UserConfig | HealthyRepository.getLocalWatchFaceVersion() | — | On error: inserts DeviceSettingEntity(mac, "com.qcwxkjvip.WatchFaceMarketVersion", toJson(WatchFaceVersionBean(hwVersion, "0"))); fallback pattern identical to getFirmwareInfo$5 | no |
| J05402 | com/qcwireless/smart/ui/base/repository/healthy/HealthyRepository.java | documented_app_orchestration | storage_db | **Healthy Repository** — singleton; device settings, firmware info, watch face version, AI chat | qcDeviceSettingDao, aiChatGPT(), getFirmwareInfo(), getLocalWatchFaceVersion(), saveDeviceSetting(), queryDeviceSetting() | QcDeviceSettingDao, DeviceSettingEntity, AiChatBean, DFUInformationBean, WatchFaceVersionBean, NetState | ViewModel/UseCase layer | 0x0023, 0x0031, 0xffffffff80000000 | 352 lines; **not a health-data repository** despite name — manages device settings and AI chat; firmware/watchface use DeviceSettingEntity as key-value store with action strings as keys | no |
| J05403 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$downHeartRateDetailFromServer$2.java | documented_sync | hr, sync_scheduler | SuspendLambda — Flow builder for HR detail download from server; captures $uid and $lastSyncId | invokeSuspend(), $uid, $lastSyncId, AnonymousClass1 | SuspendLambda, FlowCollector, HeartRateResp, NetState | HeartRateDetailRepository.downHeartRateDetailFromServer() | — | Mirror of SpO2 download pattern but for HR; $2 = flow {} builder | no |
| J05404 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$downHeartRateDetailFromServer$3.java | documented_sync | hr | SuspendLambda — onStart handler for HR download flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | HeartRateDetailRepository.downHeartRateDetailFromServer() | — | Emits loading state; $3 = onStart {} block | no |
| J05405 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$downHeartRateDetailFromServer$4.java | documented_sync | hr | SuspendLambda — catch handler for HR download flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | HeartRateDetailRepository.downHeartRateDetailFromServer() | — | Error recovery; $4 = catch {} block | no |
| J05406 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$syncHistoryHeartDetail$2.java | documented_sync | hr, storage_db, sync_scheduler | SuspendLambda — Flow builder for HR history sync; reads from QcHeartRateDetailDao, groups by date | invokeSuspend(), $deviceAddress | SuspendLambda, FlowCollector, QcHeartRateDetailDao, HeartRateDetail, ConcurrentHashMap | HeartRateDetailRepository.syncHistoryHeartDetail() | — | Reads unsynced HR data from DAO, groups by date into Map<String, Integer>; uses ConcurrentHashMap for thread safety; 420-line source ref | no |
| J05407 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$syncHistoryHeartDetail$3.java | documented_sync | hr, sync_scheduler | SuspendLambda — onStart handler for HR history sync flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | HeartRateDetailRepository.syncHistoryHeartDetail() | — | Emits loading state; $3 = onStart {} block | no |
| J05408 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$syncHistoryHeartDetailNew$2.java | documented_sync | hr, storage_db, sync_scheduler | SuspendLambda — Flow builder for "new" HR history sync; reads from QcHeartRateDetailDao | invokeSuspend(), $deviceAddress | SuspendLambda, FlowCollector, QcHeartRateDetailDao, HeartRateDetail | HeartRateDetailRepository.syncHistoryHeartDetailNew() | — | Variant of syncHistoryHeartDetail$2; "New" variant likely uses different grouping or date range logic; same DAO access pattern | no |
| J05409 | com/qcwireless/smart/ui/base/repository/healthy/HeartRateDetailRepository$syncHistoryHeartDetailNew$3.java | documented_sync | hr, sync_scheduler | SuspendLambda — onStart handler for "new" HR history sync flow | invokeSuspend() | SuspendLambda, FlowCollector, NetState | HeartRateDetailRepository.syncHistoryHeartDetailNew() | — | Emits loading state; $3 = onStart {} block | no |

---

## SpO2 Domain Deep Analysis

### BloodOxygenRepository — Architectural Summary

BloodOxygenRepository is the **central SpO2 data orchestrator** in the QRing app. It implements a singleton pattern via `Companion.getINSTANCE()` with lazy initialization, and manages **two distinct data channels**:

1. **Continuous/Auto SpO2** (`QcBloodOxygenDao` → `blood_oxygen` table)
   - Data originates from BLE device via `LargeDataHandler.syncBloodOxygen(offset, callback)`
   - BLE protocol: command ID 42 (0x2A), 49-byte records
   - Each record: day_offset (byte[0]), then alternating min/max SpO2 values at even/odd byte positions
   - Stored as `BloodOxygenEntity` with `maxArray` and `minArray` as JSON-serialized integer lists
   - Time resolution: hourly (3600-second intervals in chart queries)

2. **Manual SpO2** (`ManualBloodOxygenDao` → `blood_oxygen_manual` table)
   - User-initiated spot-check measurements
   - Stored as `BloodOxygenManualEntity` with single bloodOxygen value + manualTime timestamp
   - Fires `ManualRefreshEvent` via EventBus after save

### Measurement Modes

| Mode | Trigger | DAO | Entity | Table | Sync Direction |
|---|---|---|---|---|---|
| **Continuous (auto)** | BLE device periodic scan | QcBloodOxygenDao | BloodOxygenEntity | blood_oxygen | Device → App → Server |
| **Manual** | User tap in app | ManualBloodOxygenDao | BloodOxygenManualEntity | blood_oxygen_manual | App → Server |
| **App-initiated** | Not in this chunk (see BloodOxygenAppEntity in other chunks) | — | — | — | — |

### SpO2 BLE Protocol Details (from syncAutoBloodOxygen)

```
Command: LargeDataHandler.syncBloodOxygen(offset, ILargeDataResponse)
Response callback: parseData(int cmd, byte[] data)
  - cmd == 42 → SpO2 data packet
  - record_count = ByteUtil.bytesToInt(data[2:4]) / 49
  - For each record i (0..record_count-1):
    - record_bytes = data[i*49+6 : (i+1)*49+6]
    - day_offset = -record_bytes[0]  (negative = days ago)
    - Even-indexed bytes → maxArray (max SpO2 per hour)
    - Odd-indexed bytes → minArray (min SpO2 per hour)
  - If record_count == 0: delete existing BloodOxygenEntity for today
```

### SpO2 Server Sync Flow

```
Download: downBoFromServer(uid, lastSyncId)
  → flow { API.getSpo2List(uid, lastSyncId) }
  → onStart { emit(loading) }
  → catch { emit(error) }
  → collect { for each Spo2DownResp: insert BloodOxygenEntity(isFromServer=true) }

Upload: updateBloodOxygenDetailToServer()
  → flow { read un-uploaded from DAO → API.upload() }
  → onStart { emit(loading) }
  → catch { emit(error) }
  → on success: updateUploadStatus(dateStr, isUpload=true, uploadServerUnixTime)
```

### SpO2 Cross-Domain: SleepTotalHistory.avgBloodOxygen

The `SleepTotalHistory` entity (table `sleep_total`) stores `avgBloodOxygen` alongside `avgHeart` and `avgHrv`. This means the **sleep session provides an averaged SpO2 reading** — the device likely computes average SpO2 during sleep and stores it in the sleep summary. This is a critical cross-domain linkage: SpO2 data flows into the sleep domain.

### BloodOxygenEntity Constructor Signature

```java
BloodOxygenEntity(
  String deviceAddress,
  String dateStr,           // "yyyy-MM-dd"
  String maxArray,          // JSON: [max_spO2_hour0, max_spO2_hour1, ...]
  String minArray,          // JSON: [min_spO2_hour0, min_spO2_hour1, ...]
  long zeroTime,            // midnight timestamp
  boolean isFromServer,     // true if downloaded from server
  int unixTime,             // record creation timestamp
  boolean sync,             // sync status
  int uploadCount,          // 0 = not uploaded
  int unknown_384,          // constant 384 — possibly version or data-type code
  Object null_param         // always null — likely Room auto-generated
)
```

---

## Function Dictionary Proposals

### BloodOxygenRepository Methods

| Proposed Function Name | Source Method | Category | Signature | Description |
|---|---|---|---|---|
| `spo2_ble_sync_auto` | `syncAutoBloodOxygen` | BLE | `(offset: int, result: BaseDeviceResult<ReadBlePressureRsp>) → void` | Initiates BLE large-data transfer for continuous SpO2; uses LargeDataHandler; parses 49-byte records with cmd=42 |
| `spo2_server_download` | `downBoFromServer` | Sync | `(uid: long, lastSyncId: long) → Flow<NetState<List<Spo2DownResp>>>` | Downloads SpO2 records from server; flow with loading/error states; inserts as BloodOxygenEntity(isFromServer=true) |
| `spo2_server_upload` | `updateBloodOxygenDetailToServer` | Sync | `() → Flow<NetState<Integer>>` | Uploads un-synced SpO2 records to server; reads from DAO, posts to API, updates upload status |
| `spo2_query_by_date` | `queryBloodOxygenByDate` | Storage | `(mac: String, date: DateUtil) → List<DataBean>` | Queries continuous SpO2 for a date; deserializes maxArray/minArray JSON; returns hourly data beans (seconds, min, max) |
| `spo2_query_by_date_detail` | `queryBloodOxygenByDateDetail` | Storage | `(mac: String, date: DateUtil) → List<BloodOxyDetailBean>` | Same as above but filters out zero-value hours and sorts descending by seconds |
| `spo2_query_result_map` | `queryBloodOxygenByDateResultMap` | Storage | `(mac: String, date: String) → Map<Integer, DataBean>` | Returns SpO2 data as map keyed by seconds offset (i*3600) |
| `spo2_query_date_range` | `queryByDateRange` | Storage | `(startDate: String, endDate: String) → List<BloodOxygenEntity>` | Range query for continuous SpO2; uses current device address |
| `spo2_query_last` | `queryLastBloodOxygen` | Storage | `(mac: String) → List<HomeDataBean>` | Gets most recent SpO2 record (by date desc); for home screen widget |
| `spo2_manual_save` | `saveManualBloodOxygen` | Storage | `(manualTime: int, bloodOxygen: int) → void` | Saves user-initiated SpO2 measurement; runs on background thread; fires ManualRefreshEvent |
| `spo2_manual_query` | `queryManualBloodOxygen` | Storage | `(date: DateUtil) → List<BloodOxygenManualEntity>` | Queries manual SpO2 records for a date |
| `spo2_upload_status_update` | `updateUploadStatus` | Sync | `(dateStr: String, isUpload: boolean, uploadServerUnixTime: int) → int` | Updates server upload status for continuous SpO2 record |
| `spo2_manual_upload_status_update` | `updateManualUploadStatus` | Sync | `(dateStr: String, isUpload: boolean, uploadServerUnixTime: int) → int` | Updates server upload status for manual SpO2 record |
| `spo2_calendar_mark` | `calendarBloodOxygen` | Storage | `(year: int, month: int) → Map<String, Calendar>` | Returns calendar dates with SpO2 data for month view |
| `spo2_delete_data` | `deleteData` | Storage | `() → void` | Deletes all manual SpO2 data for current device + today |

### BloodPressureRepository Methods (sibling)

| Proposed Function Name | Source Method | Category | Signature | Description |
|---|---|---|---|---|
| `bp_ble_sync_auto` | `syncAutoBp` | BLE | `(result: BaseDeviceResult<BpDataRsp>) → void` | BLE sync for BP; uses BpDataRsp; estimates BP via CalcBloodPressureByHeart |
| `bp_server_download` | `downBpFromServer` | Sync | `(uid, lastSyncId) → Flow<NetState<List<BpDownResp>>>` | Downloads BP from server |
| `bp_server_upload` | `updateBloodPressureDetailToServer` | Sync | `() → Flow<NetState<Integer>>` | Uploads un-synced BP records |
| `bp_manual_save` | `saveManualBloodPressure` | Storage | `(sbp, dbp, manualTime) → void` | Saves manual BP measurement |

### BloodSugarRepository Methods (sibling)

| Proposed Function Name | Source Method | Category | Signature | Description |
|---|---|---|---|---|
| `bs_ble_sync_auto` | `syncAutoBloodSugar` | BLE | `(offset, result) → void` | BLE sync for blood sugar; uses LargeDataHandler (same pattern as SpO2) |
| `bs_app_manual_save` | `saveAppManualBloodSugar` | Storage | `(sugar, manualTime) → void` | Saves app-initiated manual sugar measurement |
| `bs_app_continuous_save` | `saveAppContinuousBloodSugar` | Storage | `(date, hour, minSugar, maxSugar) → void` | Saves app-initiated continuous sugar measurement |

### HealthyRepository Methods (device settings)

| Proposed Function Name | Source Method | Category | Signature | Description |
|---|---|---|---|---|
| `device_firmware_info` | `getFirmwareInfo` | Storage | `(mac: String) → Flow<DFUInformationBean>` | Gets firmware info from device_setting table; fallback inserts default |
| `device_watchface_version` | `getLocalWatchFaceVersion` | Storage | `(mac: String) → Flow<WatchFaceVersionBean>` | Gets watch face version from device_setting table; fallback inserts default |
| `ai_health_chat` | `aiChatGPT` | BigData | `(uid: String, messages: List<AiChatBean>) → Flow<NetState<AiChatBean>>` | AI chat integration for health queries |

---

## Entity Schema Summary

### SpO2-Related Tables

| Table | Entity | PK | Key Columns | Measurement Mode |
|---|---|---|---|---|
| `blood_oxygen` | BloodOxygenEntity | (device_address, date_str) | max_array (JSON), min_array (JSON), unix_time, sync, last_sync_time, isUploadServer, upload_server_unit_time | **Continuous (auto)** |
| `blood_oxygen_manual` | BloodOxygenManualEntity | (mac, timestamp) | blood_oxygen, date_str, isUploadServer, upload_server_unit_time | **Manual** |
| `sleep_total` | SleepTotalHistory | (device_address, date_str) | avg_blood_oxygen, avg_heart, avg_hrv, total_sleep, deep_sleep, light_sleep, rapid_sleep, awake, start_time, end_time, bedtime | **Sleep-averaged** |

### Sleep Tables

| Table | Entity | PK | Key Columns | Notes |
|---|---|---|---|---|
| `sleep_detail` | SleepDetail | (device_address, date_str) | interval, index_str, quality, sync, last_sync_time | Per-night detail; quality=JSON |
| `sleep_lunch_protocol` | SleepLunchProtocol | (device_address, date_str) | detail, lunch_st, lunch_et, lunch_list, sync, last_sync_time, isUploadServer | Lunch nap protocol |
| `sleep_new_protocol` | SleepNewProtocol | (device_address, date_str) | detail, st, et, lunch_list, sync, last_sync_time, isUploadServer | New sleep protocol (no lunch-specific) |
| `sleep_total` | SleepTotalHistory | (device_address, date_str) | total_sleep, deep_sleep, light_sleep, rapid_sleep, awake, avg_heart, avg_blood_oxygen, avg_hrv, bedtime | Daily sleep summary with SpO2 cross-domain |

### Steps/Sport Tables

| Table | Entity | PK | Key Columns | Notes |
|---|---|---|---|---|
| `step_detail` | StepDetail | (device_address, date_str) | interval, total_active_time, index_str, counts, miles, calories, sync, last_sync_time | Per-day step detail; counts/miles/calories=JSON |
| `step_total` | StepTotal | (device_address, date_str) | step, distance, carolie, unix_time, isUploadServer | Daily step totals; "carolie" misspelling |
| `sport_plus_detail` | SportPlusDetail | (device_address, start_time, sport_type) | duration, distance, calories, steps, rate_value, avg_rate, sync | Exercise session records |

### Utility Tables

| Table | Entity | PK | Key Columns | Notes |
|---|---|---|---|---|
| `sync_entity` | SyncDataEntity | (uid, data_action) | action, last_sync_time | Sync watermark tracking |
| `target_entity` | TargetEntity | (device_address) | goal_steps, goal_calorie, goal_distance, goal_sport_time, goal_sleep_time, sleep_start, sleep_end, sleep_duration | User goals; defaults from Companion.getDeFault() |
| `user` | UserEntity | (uid) | email, nickName, gender, weight, height, birthday, goal_*, register_date | User profile; title field = uid (JADX artifact) |

---

## Key Architectural Patterns

### Repository Singleton Pattern
All repositories use the same pattern:
```kotlin
companion object {
    val INSTANCE by lazy(LazyThreadSafetyMode.SYNCHRONIZED) { Repository() }
}
```
JADX decompiles this to `Lazy<Repository>` field + `Companion.getGetInstance()`.

### Flow-Based Server Sync Pattern
All server sync operations use the same 3-stage Flow:
1. `$2` class: `flow { ... }` — actual API call
2. `$3` class: `onStart { emit(NetState.loading()) }` — loading state
3. `$4` class: `catch { emit(NetState.error()) }` — error recovery

### BLE Sync: LargeDataHandler vs CommandHandle
- **SpO2, Blood Sugar**: Use `LargeDataHandler` (bulk data transfer, 49-byte records)
- **Blood Pressure**: Uses `CommandHandle` (UART small-data commands, individual request/response)

### Upload Status Tracking
Entities with server upload tracking share a common pattern:
- `isUploadServer: boolean` — whether record has been uploaded
- `uploadServerUnixTime: int` — timestamp of successful upload
- `updateFromDatabase(dao)` — syncs upload status from existing DB row before re-upload
- `dataEquals(other)` — compares only data fields (not upload status) to determine if re-upload needed

---

## Observations & Gaps

1. **SpO2 app-initiated mode** is not present in this chunk — the `BloodOxygenAppEntity` / `app_blood_oxygen` table likely exists in other chunks (similar to `AppBloodSugarEntity` in BloodSugarRepository)
2. **384 constant** in BloodOxygenEntity constructor is unexplained — could be a data-type version code, packet size hint, or magic number
3. **ReadBlePressureRsp** is shared between SpO2 and BP repositories despite the name suggesting BP-only — this is likely a generic BLE response class
4. **SleepTotalHistory.avgBloodOxygen** provides the only SpO2 cross-domain linkage in this chunk — sleep-averaged SpO2 is stored separately from hourly continuous data
5. **HealthyRepository** is misnamed — it manages device settings and AI chat, not health data
6. **BloodSugarRepository** has three measurement modes (continuous, app-manual, app-continuous) while SpO2 only has two visible here — SpO2 may gain a third mode in other chunks
