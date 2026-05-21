# CH0016 — app_orchestration_strong_hits

> **Chunk type:** app_orchestration_strong_hits  
> **Source tree:** decompiled4  
> **Target domain:** com.qcwireless.smart (healthy repository layer)  
> **Ledger IDs:** 35 files (J05410–J05449, with gaps)  
> **Generated:** 2026-05-19  

---

## Chunk-Level Summary

CH0016 covers the **healthy-data repository layer** of the QRing/Colmi app — the Kotlin singletons that mediate between BLE hardware commands, local Room DAOs, and cloud upload/download flows. Six health domains are represented:

| Domain | Main Repository | BLE Command | BigData / LargeData | Key DAOs |
|---|---|---|---|---|
| **Heart Rate** | `HeartRateDetailRepository` | `ReadHeartRateReq` → `ReadHeartRateRsp` | `LargeDataHandler.syncIntervalHeartRateWithCallback`, `syncManualHeartRateList` | `QcHeartRateDetailDao`, `QcManualHeartDao`, `QcAppManualHeartDao` |
| **HRV** | `HRVRepository` | `HRVReq` → `HRVRsp` | — | `QcHrvDetailDao`, `ManualHrvDao` |
| **Pressure** | `PressureRepository` | `PressureReq` → `PressureRsp` | — | `QcPressureDetailDao`, `ManualPressureDao` |
| **Muslim (Prayer)** | `MuslimRepository` | `MuslimReq` → `MuslimRsp` | — | `QcMuslimDetailDao`, `QcMuslimTotalDao` |
| **Muslim V2** | `MuslimV2Repository` | — (no BLE) | — | `AnlaNameDao`, `WorshipTimeDao`, `QcQuranDao`, `QcCustomerPraiseDao` |
| **Sleep** | `SleepDetailRepository` | `ReadSleepDetailsReq` → `ReadSleepDetailsRsp`, `SleepNewProtoResp` | `LargeDataHandler` (sleep big data), `ILargeDataSleepResponse` | `QcSleepDetailDao`, `QcSleepTotalDao`, `QcSleepNewProtocolDao`, `QcSleepLunchProtocolDao` |
| **Menstruation** | `MenstruationRepository` | — (no BLE) | — | `QcDeviceSettingDao`, `QcMenstruationDao` |
| **OneKeyCheck** | `OneKeyCheckRepository` | — (no BLE) | — | `QcDeviceSettingDao` |

### Shared Sync Pattern (Critical Finding)

All four BLE-connected repositories (HR, HRV, Pressure, Muslim) share an **identical sync architecture**:

1. **`syncHistoryXxxDetail(mac, BaseDeviceResult, Continuation)`** — coroutine entry; checks `BleOperateManager.isConnected()`, populates a `ConcurrentHashMap historyDate` with 6 days of date→offset pairs, prunes already-synced days via `queryDaysSyncDate`, then iterates the map.
2. **`syncXxxDetail(key, offset, BaseDeviceResult)`** — sends a single BLE command via `CommandHandle.executeReqCmd(new XxxReq((byte)offset), ICommandResponse)`.
3. **Callback lambda** — on `status != 0` → error retry; on success → `saveXxx(rsp)`, remove date from `historyDate`, if empty → `result(0, rsp)`, else recurse to next date.
4. **`syncTodayXxx(BaseDeviceResult)`** — sends `XxxReq((byte) 0)` (offset 0 = today), callback saves via `saveXxxToday`, checks `isEndFlag()`.
5. **`saveXxx` / `saveXxxToday`** — both run `ktxRunOnBgSingle` to insert into Room DAO; today variant also deletes empty rows.

This is a **sequential day-by-day BLE sync** — not parallel. Each day's command must complete before the next is issued.

---

## Detailed File Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J05410 | `…/HeartRateDetailRepository$updateHeartRateDetailToServer$2.java` | reviewed | hr, storage_db, sync_scheduler | SuspendLambda for `updateHeartRateDetailToServer` flow builder: queries un-uploaded HR details, emits loading NetState, marks synced, re-inserts | `invokeSuspend`, `AnonymousClass1.invokeSuspend` (marks synced + re-insert), `AnonymousClass2.invokeSuspend` (error emit) | `QcHeartRateDetailDao`, `HeartRateDetail`, `NetState`, `FlowCollector` | Called by `HeartRateDetailRepository.updateHeartRateDetailToServer()` | `0x00ed` (from ledger) | Inner class $2$1 iterates `notUpList`, sets `sync=true`, re-inserts; $2$2 emits error NetState with errorCode. invokeSuspend body is decompile-skipped (259 instructions). | low |
| J05411 | `…/HeartRateDetailRepository$updateHeartRateDetailToServer$3.java` | reviewed | hr | SuspendLambda for `onStart` of upload flow: emits `NetState(loading=true, code=1)` then `NetState(error=true, code=-10002)` | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `updateHeartRateDetailToServer` flow pipeline | — | Pure flow starter; emits loading then error state. Error code -10002 likely = "no data to upload". | low |
| J05412 | `…/HeartRateDetailRepository$updateHeartRateDetailToServer$4.java` | reviewed | hr | SuspendLambda for `catch` of upload flow: on exception, prints stack trace, emits `NetState(error=true, code=-11111)` | `invokeSuspend` | `NetState`, `FlowCollector`, `Throwable.printStackTrace` | Called by `updateHeartRateDetailToServer` flow pipeline | — | Generic error handler; -11111 = catch-all network error. | low |
| J05413 | `…/HeartRateDetailRepository.java` | **deep-read** | bigdata, ble_connection, hr, storage_db, sync_scheduler, uart_small_data | **Central HR repository singleton.** Manages interval HR (BigData), manual HR (BigData), today HR sync, history sync, server upload/download, calendar markers, app-manual HR | `syncHeartRateDetail`, `syncHeartRateDetailNew`, `syncTodayHeartRate`, `syncHistoryHeartDetail`, `syncHistoryHeartDetailNew`, `syncManualHeartRate`, `saveHeartRate`, `saveHeartRateNew`, `saveHeartRateToday`, `saveHeartRateTodayNew`, `downHeartRateDetailFromServer`, `updateHeartRateDetailToServer`, `queryHeartDetail`, `queryLastHeartDetail`, `deleteData`, `saveManualHeartRate` | `BleOperateManager`, `CommandHandle`, `ICommandResponse`, `LargeDataHandler`, `ReadHeartRateReq`→`ReadHeartRateRsp`, `IntervalHeartRateEntity`, `IIntervalHeartRateCallback`, `ILargeDataManualHeartRateResponse`, `ManualHeartRate`, `QcHeartRateDetailDao`, `QcManualHeartDao`, `QcAppManualHeartDao`, `BaseRspCmd`, `ByteUtil`, `DeviceFunctionSupport`, `EventBus` | UI ViewModels, sync schedulers | `0x8`, `60` (command IDs from ledger) | **Key BLE flow:** `syncTodayHeartRate` checks `DeviceFunctionSupport.supportRealTimeHr` — if true, uses `LargeDataHandler.syncIntervalHeartRateWithCallback(0, callback)` (BigData protocol); if false, uses `CommandHandle.executeReqCmd(ReadHeartRateReq, callback)` (UART small data). **Lock:** `syncHeartLock` boolean with 5-second handler timeout. **History:** `syncHistoryHeartDetail` populates `historyDate` ConcurrentHashMap, iterates days sequentially. **New protocol:** `syncHistoryHeartDetailNew` uses `LargeDataHandler.syncIntervalHeartRateWithCallback(daysBetween, callback)`. **Manual HR:** `syncManualHeartRate(offset, listener)` → `LargeDataHandler.syncManualHeartRateList`; offset=255 if yesterday missing, 0 otherwise. **Upload:** `updateHeartRateDetailToServer` → flow pipeline with catch. **Download:** `downHeartRateDetailFromServer` → flow pipeline parsing `HeartRateResp` list. | **high** — BigData protocol details, `DeviceFunctionSupport` flag logic, `LargeDataHandler` internals |
| J05414 | `…/HRVRepository$syncHistoryHrvDetail$2.java` | reviewed | hrv_regular, storage_db, sync_scheduler | SuspendLambda for `syncHistoryHrvDetail` flow builder: populates `historyDate` with 6 days (i=1..6, day offset), queries `queryDaysSyncDate` to prune already-synced days, emits map | `invokeSuspend` | `QcHrvDetailDao`, `HRVDetail`, `DateUtil`, `ConcurrentHashMap`, `XLog` | Called by `HRVRepository.syncHistoryHrvDetail()` | — | Syncs 6 days of HRV history. Prunes days where `lastSyncTime` is today. Logs "sync hrv date". | low |
| J05415 | `…/HRVRepository$syncHistoryHrvDetail$3.java` | reviewed | hrv_regular, sync_scheduler | SuspendLambda for `catch` of HRV sync flow: on error, re-populates `historyDate` with 6 days (fallback), emits map | `invokeSuspend` | `DateUtil`, `ConcurrentHashMap` | Called by `syncHistoryHrvDetail` catch block | — | Error recovery: rebuilds the 6-day map and re-emits, allowing retry. | low |
| J05416 | `…/HRVRepository.java` | **deep-read** | ble_connection, hr, hrv_regular, storage_db, sync_scheduler, uart_small_data | **Central HRV repository singleton.** Manages HRV detail sync (today + history), manual HRV, calendar markers, local queries | `syncHrvDetail`, `syncTodayHrv`, `syncHistoryHrvDetail`, `savePressure` (misnamed — actually saves HRV), `savePressureToday`, `queryHrvByDateDetailMap`, `queryHrvByDateDetailResp`, `queryLastHrv`, `saveManualPressure` (misnamed — saves manual HRV), `deleteData`, `calendarPressure` | `BleOperateManager`, `CommandHandle`, `ICommandResponse`, `HRVReq`→`HRVRsp`, `BaseRspCmd`, `ByteUtil`, `QcHrvDetailDao`, `ManualHrvDao`, `EventBus` | UI ViewModels, sync schedulers | `60` (from ledger — likely command ID) | **Key BLE flow:** `syncTodayHrv` → `HRVReq((byte)0)` via `CommandHandle`. `syncHistoryHrvDetail` → 6-day sequential sync via `HRVReq((byte)offset)`. **Naming quirk:** methods named `savePressure`/`savePressureToday`/`calendarPressure`/`saveManualPressure` — these are actually HRV operations (the class was likely copy-pasted from PressureRepository). **No BigData path** — HRV uses only UART small data commands. **Manual HRV** posts `ManualRefreshEvent` via EventBus. | **medium** — confirm HRVReq command byte mapping, verify no BigData alternative exists |
| J05420 | `…/MenstruationRepository$getMenstruationSetting$2.java` | reviewed | storage_db | SuspendLambda for `getMenstruationSetting` flow: queries `QcDeviceSettingDao`, emits result | `invokeSuspend` | `QcDeviceSettingDao`, `DeviceSettingEntity` | Called by `MenstruationRepository.getMenstruationSetting()` | `0x0023`, `0x0031` | Settings-based flow; no BLE. | low |
| J05422 | `…/MenstruationRepository$getMenstruationSetting$5.java` | reviewed | storage_db | SuspendLambda for `catch` of menstruation setting flow: error handler | `invokeSuspend` | `QcDeviceSettingDao` | Called by `getMenstruationSetting` catch block | — | Error recovery for settings query. | low |
| J05423 | `…/MenstruationRepository.java` | reviewed | storage_db | **Menstruation repository singleton.** Manages period data CRUD, settings via `QcDeviceSettingDao`, calendar view data | `addMenstruationData`, `getMenstruationSetting`, `queryByDate`, `deleteData`, `addViewData` | `QcDeviceSettingDao`, `QcMenstruationDao`, `MenstruationBean`, `MenstruationEntity`, `MoshiUtils`, `DeviceSettingEntity` | UI ViewModels | `0x0023`, `0x0031`, `0xffffffff80000000` | **No BLE commands.** Purely local DB + settings. Settings stored as JSON via `QcDeviceSettingDao.queryByMacAndAction()`. `addViewData` deletes entries where startTime==endTime. | low |
| J05424 | `…/MuslimRepository$syncHistoryMuslimDetail$2.java` | reviewed | storage_db, sync_scheduler | SuspendLambda for `syncHistoryMuslimDetail` flow: populates 6-day historyDate map, prunes synced days, emits | `invokeSuspend` | `QcMuslimDetailDao`, `MuslimDetail`, `DateUtil`, `ConcurrentHashMap`, `XLog` | Called by `MuslimRepository.syncHistoryMuslimDetail()` | — | Same 6-day pattern as HRV/Pressure. | low |
| J05425 | `…/MuslimRepository$syncHistoryMuslimDetail$3.java` | reviewed | sync_scheduler | SuspendLambda for `catch` of Muslim sync flow: error recovery, re-populates 6-day map | `invokeSuspend` | `DateUtil`, `ConcurrentHashMap` | Called by `syncHistoryMuslimDetail` catch block | — | Same error recovery pattern. | low |
| J05426 | `…/MuslimRepository.java` | **deep-read** | ble_connection, hr, storage_db, sync_scheduler, uart_small_data | **Muslim (prayer) repository singleton.** Manages prayer count sync via BLE, local detail/total DAOs, calendar markers, month/week history | `syncPressureDetail` (misnamed — actually Muslim prayer), `syncTodayMuslim`, `syncHistoryMuslimDetail`, `saveMuslim`, `saveMuslimToday`, `queryLastPressure` (misnamed), `queryPressureByDateDetailResp`, `queryMonthHistoryPressureByDate`, `saveMuslimTotal`, `calendarPressure`, `deleteData` | `BleOperateManager`, `CommandHandle`, `ICommandResponse`, `MuslimReq`→`MuslimRsp`, `BaseRspCmd`, `ByteUtil`, `QcMuslimDetailDao`, `QcMuslimTotalDao`, `Gson` | UI ViewModels, sync schedulers | `60` (command ID from ledger) | **Key BLE flow:** `syncTodayMuslim` → `MuslimReq((byte)0)`. `syncHistoryMuslimDetail` → 6-day sequential sync. **Naming quirk:** methods named `syncPressureDetail`/`saveMuslim`/`calendarPressure` — copy-paste from PressureRepository. **Data format:** `MuslimRsp.getPressureArray()` returns byte pairs → `ByteUtil.bytesToInt` for 2-byte prayer counts. **Dual DAO:** `QcMuslimDetailDao` (interval data) + `QcMuslimTotalDao` (daily totals). **Calendar check:** excludes all-zero counts string. | **medium** — confirm MuslimReq byte mapping, prayer count encoding |
| J05427 | `…/MuslimV2Repository.java` | reviewed | storage_db | **Muslim V2 repository singleton.** Manages Quran collections, worship times, Anla names, customer praise — all local DB, no BLE | `deleteAllItems`, `deleteAllWorshipTime`, `getByDeviceAddressOrderedByTime`, `getCollectionsByTimeDesc`, `getWorshipTimesByDate`, `insertAnlaName`, `insertPraise`, `insertQuran`, `insertWorshipTime`, `updateAnlaName`, `updatePraise`, `updateQuran`, `updateWorshipTime` | `AnlaNameDao`, `WorshipTimeDao`, `QcQuranDao`, `QcCustomerPraiseDao` | UI ViewModels | — | **No BLE commands.** Purely local Room DB CRUD. V2 = expanded Muslim feature set (Quran, worship times, praise). | low |
| J05428 | `…/OneKeyCheckRepository$getLastOneKeyCheck$2.java` | reviewed | storage_db | SuspendLambda for `getLastOneKeyCheck` flow: queries `QcDeviceSettingDao` by mac+action, emits `DeviceSettingEntity` | `invokeSuspend` | `QcDeviceSettingDao`, `DeviceSettingEntity` | Called by `OneKeyCheckRepository.getLastOneKeyCheck()` | — | Settings-based query; action key = "com.qcwxkjvip.lastOneKeyCheck". | low |
| J05430 | `…/OneKeyCheckRepository$getLastOneKeyCheck$5.java` | reviewed | storage_db | SuspendLambda for `catch` of OneKeyCheck flow: error handler, re-queries settings | `invokeSuspend` | `QcDeviceSettingDao` | Called by `getLastOneKeyCheck` catch block | — | Error recovery for settings query. | low |
| J05431 | `…/OneKeyCheckRepository.java` | reviewed | bigdata, sleep, storage_db | **OneKeyCheck repository singleton.** Retrieves last one-key health check result from device settings; no BLE commands | `getLastOneKeyCheck`, `queryLast` | `QcDeviceSettingDao`, `MoshiUtils`, `LastOneKeyBean`, `DeviceSettingEntity` | UI ViewModels | `0x0023`, `0x0031`, `0xffffffff80000000`, `57`, `60`, `62` | **No BLE commands.** Reads last check result from `QcDeviceSettingDao.queryByMacAndAction(mac, "com.qcwxkjvip.lastOneKeyCheck")`. Uses Moshi to deserialize `LastOneKeyBean`. The `bigdata` and `sleep` domain tags in ledger suggest OneKeyCheck triggers multi-measurement (HR, SpO2, sleep) — but the repository itself only stores/retrieves the result. | **medium** — find where OneKeyCheck BLE measurement is triggered (likely in a ViewModel or UseCase) |
| J05432 | `…/PressureRepository$syncHistoryPressureDetail$2.java` | reviewed | storage_db, sync_scheduler | SuspendLambda for `syncHistoryPressureDetail` flow: populates 6-day historyDate map, prunes synced days, emits | `invokeSuspend` | `QcPressureDetailDao`, `PressureDetail`, `DateUtil`, `ConcurrentHashMap` | Called by `PressureRepository.syncHistoryPressureDetail()` | — | Same 6-day pattern. | low |
| J05433 | `…/PressureRepository$syncHistoryPressureDetail$3.java` | reviewed | sync_scheduler | SuspendLambda for `catch` of Pressure sync flow: error recovery, re-populates 6-day map | `invokeSuspend` | `DateUtil`, `ConcurrentHashMap` | Called by `syncHistoryPressureDetail` catch block | — | Same error recovery pattern. | low |
| J05434 | `…/PressureRepository.java` | **deep-read** | ble_connection, hr, storage_db, sync_scheduler, uart_small_data | **Pressure repository singleton.** Manages blood pressure detail sync via BLE, manual pressure, calendar markers, month/week history | `syncPressureDetail`, `syncTodayPressure`, `syncHistoryPressureDetail`, `savePressure`, `savePressureToday`, `queryLastPressure`, `queryPressureByDateDetailResp`, `queryMonthHistoryPressureByDate`, `queryWeekHistoryPressureByDate`, `saveManualPressure`, `deleteData`, `calendarPressure` | `BleOperateManager`, `CommandHandle`, `ICommandResponse`, `PressureReq`→`PressureRsp`, `BaseRspCmd`, `ByteUtil`, `QcPressureDetailDao`, `ManualPressureDao`, `EventBus` | UI ViewModels, sync schedulers | `60` (command ID from ledger) | **Key BLE flow:** `syncTodayPressure` → `PressureReq((byte)0)`. `syncHistoryPressureDetail` → 6-day sequential sync. **Data format:** `PressureRsp.getPressureArray()` → single-byte values (unlike Muslim's 2-byte pairs). **Manual pressure** posts `ManualRefreshEvent` via EventBus. **Month/week history** computes average pressure per day. | **medium** — confirm PressureReq byte mapping, verify pressure value encoding |
| J05435 | `…/SleepDetailRepository$downSleepDetailFromServer$2.java` | reviewed | sleep, sync_scheduler | SuspendLambda for `downSleepDetailFromServer` flow: downloads sleep data from server API | `invokeSuspend` | `SleepDetailResp`, `NetState` | Called by `SleepDetailRepository.downSleepDetailFromServer()` | `0x0079`, `30` | Server download flow for sleep. | low |
| J05436 | `…/SleepDetailRepository$downSleepDetailFromServer$3.java` | reviewed | sleep | SuspendLambda for `onStart` of sleep download flow | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `downSleepDetailFromServer` onStart | — | Loading state emitter. | low |
| J05437 | `…/SleepDetailRepository$downSleepDetailFromServer$4.java` | reviewed | sleep | SuspendLambda for `catch` of sleep download flow | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `downSleepDetailFromServer` catch block | — | Error handler. | low |
| J05438 | `…/SleepDetailRepository$downSleepDetailNewProtocolFromServer$2.java` | reviewed | ble_connection, sleep, sync_scheduler | SuspendLambda for `downSleepDetailNewProtocolFromServer` flow: downloads new-protocol sleep from server, uses `BluetoothClassCompat` | `invokeSuspend` | `SleepDetailNewProtocolResp`, `BluetoothClassCompat`, `NetState` | Called by `SleepDetailRepository.downSleepDetailNewProtocolFromServer()` | `0x0079`, `30` | New-protocol variant of server download. `BluetoothClassCompat` suggests RealSil SDK involvement. | low |
| J05439 | `…/SleepDetailRepository$downSleepDetailNewProtocolFromServer$3.java` | reviewed | sleep | SuspendLambda for `onStart` of new-protocol sleep download | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `downSleepDetailNewProtocolFromServer` onStart | — | Loading state emitter. | low |
| J05440 | `…/SleepDetailRepository$downSleepDetailNewProtocolFromServer$4.java` | reviewed | sleep | SuspendLambda for `catch` of new-protocol sleep download | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `downSleepDetailNewProtocolFromServer` catch block | — | Error handler. | low |
| J05441 | `…/SleepDetailRepository$syncSleepDetail$2.java` | reviewed | sleep, storage_db, sync_scheduler | SuspendLambda for `syncSleepDetail` flow: populates historyDate map for sleep sync, emits | `invokeSuspend` | `QcSleepDetailDao`, `DateUtil`, `ConcurrentHashMap` | Called by `SleepDetailRepository.syncSleepDetail()` | — | Sleep history sync flow builder. | low |
| J05442 | `…/SleepDetailRepository$syncSleepDetail$3.java` | reviewed | sleep, sync_scheduler | SuspendLambda for `catch` of sleep sync flow: error recovery | `invokeSuspend` | `DateUtil`, `ConcurrentHashMap` | Called by `syncSleepDetail` catch block | — | Error recovery. | low |
| J05443 | `…/SleepDetailRepository$updateSleepDetailToServer$2.java` | reviewed | sleep, storage_db, sync_scheduler | SuspendLambda for `updateSleepDetailToServer` flow: queries un-uploaded sleep, marks synced, re-inserts | `invokeSuspend` | `QcSleepDetailDao`, `SleepDetail`, `NetState` | Called by `SleepDetailRepository.updateSleepDetailToServer()` | `0x00ee` | Upload flow for sleep detail. | low |
| J05444 | `…/SleepDetailRepository$updateSleepDetailToServer$3.java` | reviewed | sleep | SuspendLambda for `onStart` of sleep upload flow | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `updateSleepDetailToServer` onStart | — | Loading state emitter. | low |
| J05445 | `…/SleepDetailRepository$updateSleepDetailToServer$4.java` | reviewed | sleep | SuspendLambda for `catch` of sleep upload flow | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `updateSleepDetailToServer` catch block | — | Error handler. | low |
| J05446 | `…/SleepDetailRepository$updateSleepDetailToServerNewProtocol$2.java` | reviewed | sleep, storage_db, sync_scheduler | SuspendLambda for `updateSleepDetailToServerNewProtocol` flow: queries un-uploaded new-protocol sleep, marks synced | `invokeSuspend` | `QcSleepNewProtocolDao`, `SleepNewProtocol`, `NetState` | Called by `SleepDetailRepository.updateSleepDetailToServerNewProtocol()` | `0x00b3`, `0x00b9`, `0x0175`, `0x0189`, `0x018b`, `0x018c` | **Multiple command IDs** suggest new-protocol sleep has richer data structure. | **medium** — map these command IDs to protocol fields |
| J05447 | `…/SleepDetailRepository$updateSleepDetailToServerNewProtocol$3.java` | reviewed | sleep | SuspendLambda for `onStart` of new-protocol sleep upload | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `updateSleepDetailToServerNewProtocol` onStart | — | Loading state emitter. | low |
| J05448 | `…/SleepDetailRepository$updateSleepDetailToServerNewProtocol$4.java` | reviewed | sleep | SuspendLambda for `catch` of new-protocol sleep upload | `invokeSuspend` | `NetState`, `FlowCollector` | Called by `updateSleepDetailToServerNewProtocol` catch block | — | Error handler. | low |
| J05449 | `…/SleepDetailRepository.java` | **deep-read** | bigdata, ble_connection, hr, hrv_regular, sleep, spo2, storage_db, sync_scheduler, uart_small_data | **Central Sleep repository singleton.** Largest file (96KB, 1480 lines). Manages sleep detail sync (old + new protocol), manual sleep, BigData sleep, server upload/download, lunch nap, calendar markers, cross-references HR/HRV/SpO2 | `syncSleepDetail`, `syncTodaySleepDetail`, `syncTodaySleepDetailNew`, `downSleepDetailFromServer`, `downSleepDetailNewProtocolFromServer`, `updateSleepDetailToServer`, `updateSleepDetailToServerNewProtocol`, `saveSleepDetail`, `saveSleepDetailNew`, `deleteLunchSleepData`, `deleteNewSleepData`, `querySleepDetail`, `queryLastSleepDetail`, `querySleepDetailNewProtocol`, `querySleepLunch` | `BleOperateManager`, `DeviceManager`, `CommandHandle`, `ICommandResponse`, `LargeDataHandler`, `ILargeDataSleepResponse`, `ReadSleepDetailsReq`→`ReadSleepDetailsRsp`, `SleepNewProtoResp`, `BleSleepDetails`, `QcSleepDetailDao`, `QcSleepTotalDao`, `QcSleepNewProtocolDao`, `QcSleepLunchProtocolDao`, `BaseRspCmd`, `MapUtils`, `StringUtilsKt` | UI ViewModels, sync schedulers | `30`, `60`, `95` (from ledger) | **Most complex repository.** Dual-protocol: old (`ReadSleepDetailsReq`/`Rsp`) + new (`SleepNewProtoResp`, `QcSleepNewProtocolDao`). **BigData path:** `LargeDataHandler` for sleep. **Cross-domain:** references HR, HRV, BloodOxygen/Oxygen/SpO2 data in queries. **Lunch nap:** separate DAO `QcSleepLunchProtocolDao`. **historyDate** is `LinkedHashMap` (not ConcurrentHashMap) — sleep days may need ordering. **New protocol command IDs:** 0x00b3, 0x00b9, 0x0175, 0x0189, 0x018b, 0x018c — suggest RealSil SDK extended protocol. | **high** — map new-protocol command IDs, trace BigData sleep flow, understand HR/HRV/SpO2 cross-references |

---

## Deep-Dive: HeartRateDetailRepository (J05413)

### BLE Command Flow

```
syncTodayHeartRate(date, result, internalResult?)
  ├─ guard: syncHeartLock (5s timeout via Handler.postDelayed)
  ├─ guard: DeviceFunctionSupport.supportRealTimeHr
  │   ├─ TRUE  → LargeDataHandler.syncIntervalHeartRateWithCallback(0, callback)
  │   │         → saveHeartRateTodayNew(IntervalHeartRateEntity)
  │   └─ FALSE → CommandHandle.executeReqCmd(ReadHeartRateReq(timestamp+tz), callback)
  │             → saveHeartRateToday(ReadHeartRateRsp)
  └─ callback: if isEndFlag() → result(0, rsp)

syncHistoryHeartDetail(mac, result)
  ├─ guard: BleOperateManager.isConnected() && historyDate.isEmpty()
  ├─ flow: populate historyDate (days with missing data)
  ├─ iterate: syncHeartRateDetail(key, time, result)
  │   └─ CommandHandle.executeReqCmd(ReadHeartRateReq(time), ICommandResponse)
  │       └─ on success: saveHeartRate(rsp), remove date, recurse
  │       └─ on error: result(-1, rsp)

syncHistoryHeartDetailNew(mac, result)  [BigData variant]
  ├─ guard: same as above
  ├─ iterate: syncHeartRateDetailNew(key, time, result)
  │   └─ LargeDataHandler.syncIntervalHeartRateWithCallback(daysBetween, callback)
  │       └─ on data: saveHeartRateNew(data), remove date, recurse

syncManualHeartRate(offset, listener)
  └─ LargeDataHandler.syncManualHeartRateList(offset, listener)
      └─ callback: saveManualHeartRate to QcManualHeartDao
```

### Settings Prerequisites
- `DeviceFunctionSupport.supportRealTimeHr` — determines BigData vs UART path
- `UserConfig.deviceAddressNoClear` — MAC address for all DAO queries
- `UserConfig.deviceSupportList` — JSON string parsed to `DeviceFunctionSupport`

### Sync Timing
- `syncHeartLock` — boolean mutex with 5-second auto-release
- History sync is **sequential** (one day at a time, recursive)
- Manual HR sync: offset=255 if yesterday missing (full resync), offset=0 otherwise

---

## Deep-Dive: HRVRepository (J05416)

### BLE Command Flow

```
syncTodayHrv(result)
  └─ CommandHandle.executeReqCmd(HRVReq((byte)0), ICommandResponse)
      └─ on success: savePressureToday(rsp)  [misnamed!]
      └─ if isEndFlag() → result(0, rsp)

syncHistoryHrvDetail(mac, result)
  ├─ guard: BleOperateManager.isConnected()
  ├─ flow: populate historyDate with 6 days (i=1..6)
  ├─ prune: queryDaysSyncDate → remove days already synced today
  ├─ iterate: syncHrvDetail(key, offset, result)
  │   └─ CommandHandle.executeReqCmd(HRVReq((byte)offset), ICommandResponse)
  │       └─ on success: savePressure(rsp) if offset>0, remove date, recurse
  │       └─ on error: result(-1, rsp)
```

### Key Observations
- **No BigData path** — HRV uses only UART small data commands
- **Method naming** is misleading: `savePressure`/`savePressureToday`/`calendarPressure`/`saveManualPressure` are all HRV operations (copy-paste artifact from PressureRepository)
- **6-day history window** hardcoded (i=1; i<7; i++)
- **Error recovery** in `$3` re-populates the full 6-day map on failure

---

## Cross-Repository Sync Pattern Comparison

| Aspect | HeartRate | HRV | Pressure | Muslim | Sleep |
|---|---|---|---|---|---|
| **Today sync** | `ReadHeartRateReq` or `LargeDataHandler` | `HRVReq((byte)0)` | `PressureReq((byte)0)` | `MuslimReq((byte)0)` | `ReadSleepDetailsReq` or `LargeDataHandler` |
| **History sync** | 7-day sequential | 6-day sequential | 6-day sequential | 6-day sequential | Variable (LinkedHashMap) |
| **BigData path** | Yes (interval HR, manual HR) | No | No | No | Yes (large data sleep) |
| **New protocol** | — | — | — | — | Yes (`SleepNewProtoResp`) |
| **ConcurrentHashMap** | Yes | Yes | Yes | Yes | No (LinkedHashMap) |
| **Sync lock** | `syncHeartLock` (5s) | None | None | None | None |
| **Manual entry** | Yes (app + device) | Yes (manual HRV) | Yes (manual pressure) | No | No |
| **Server upload** | Yes | No | No | No | Yes (old + new protocol) |
| **Server download** | Yes | No | No | No | Yes (old + new protocol) |
| **Dual DAO** | Yes (detail + manual + app-manual) | Yes (detail + manual) | Yes (detail + manual) | Yes (detail + total) | Yes (detail + total + new + lunch) |

---

## Command ID Registry

| Hex ID | Context | Likely Meaning |
|---|---|---|
| `0x8` | HeartRate (ledger) | ReadHeartRateReq command ID |
| `0x00ed` | HeartRate upload | Sleep detail upload marker (appears in $2 inner class) |
| `60` | HRV, Pressure, Muslim | Common command ID for offset-based history requests |
| `0x0023` | Menstruation, OneKeyCheck | DeviceSettingDao action key / setting ID |
| `0x0031` | Menstruation, OneKeyCheck | DeviceSettingDao action key / setting ID |
| `0xffffffff80000000` | Menstruation, OneKeyCheck | Bitmask for coroutine label reset |
| `0x0079` | Sleep download | Sleep detail download command |
| `0x00ee` | Sleep upload | Sleep detail upload marker |
| `0x00b3` | Sleep new protocol upload | New sleep protocol field |
| `0x00b9` | Sleep new protocol upload | New sleep protocol field |
| `0x0175` | Sleep new protocol upload | New sleep protocol field |
| `0x0189` | Sleep new protocol upload | New sleep protocol field |
| `0x018b` | Sleep new protocol upload | New sleep protocol field |
| `0x018c` | Sleep new protocol upload | New sleep protocol field |
| `30` | Sleep | Sleep interval or range constant |
| `95` | Sleep | Sleep threshold or protocol version |
| `57`, `60`, `62` | OneKeyCheck | Setting IDs or measurement types |

---

## Follow-Up Items

1. **`LargeDataHandler` internals** — How does `syncIntervalHeartRateWithCallback` work? What BLE protocol does it use? (Referenced by HR and Sleep repos)
2. **`DeviceFunctionSupport` flag mapping** — Full list of capability flags and which devices support `supportRealTimeHr` vs legacy UART
3. **`CommandHandle.executeReqCmd` dispatch** — How are `ReadHeartRateReq`, `HRVReq`, `PressureReq`, `MuslimReq` serialized and sent over BLE?
4. **New sleep protocol command IDs** — Map 0x00b3, 0x00b9, 0x0175, 0x0189, 0x018b, 0x018c to actual protocol fields
5. **OneKeyCheck BLE trigger** — Where is the actual BLE measurement command for one-key health check? (Not in this repository — likely in a ViewModel or UseCase)
6. **Sleep cross-domain references** — SleepDetailRepository queries HR, HRV, and SpO2 data — trace the full cross-domain query pattern
7. **`BaseRspCmd.getStatus()` error codes** — What does status != 0 mean? Is there a retry mechanism beyond the error callback?
8. **`BleOperateManager.isConnected()` guard** — What happens when BLE disconnects mid-sync? Is `historyDate` properly cleaned up?
