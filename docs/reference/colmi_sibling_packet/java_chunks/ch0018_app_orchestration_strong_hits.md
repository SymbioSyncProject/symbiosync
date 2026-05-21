# CH0018 — App Orchestration Strong Hits

**Chunk type:** app_orchestration_strong_hits  
**Source tree:** decompiled4  
**Path prefix:** com/qcwireless/smart  
**Assigned agent:** subagent  
**Date:** 2026-05-19  

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J05536 | com/qcwireless/smart/ui/base/repository/watchface/WatchFaceRepository$getCustomizeParamsFromLocalByType$2.java | excluded_low_signal | storage_db | Coroutine lambda: queries QcCustomFaceDao for local custom face params by type | invokeSuspend → QcCustomFaceDao | QcCustomFaceDao, CustomFaceEntity | WatchFaceRepository | — | Pure DB read flow collector; no BLE/protocol touch | no |
| J05542 | com/qcwireless/smart/ui/base/repository/watchface/WatchFaceRepository$getWatchFaceFromServer$2.java | documented_app_orchestration | storage_db | Coroutine lambda: fetches watch faces from server, stores in QcWatchFaceDao | invokeSuspend → QcWatchFaceDao.insert, WatchFaceResp | QcWatchFaceDao, WatchFaceResp, FileUtils | WatchFaceRepository | 0x008c, 0xffffffffffffd8ef, 57 | Server→local DB sync for watch faces; no BLE touch | no |
| J05548 | com/qcwireless/smart/ui/base/repository/watchface/WatchFaceRepository$getWatchFaceSetting$2.java | excluded_low_signal | storage_db | Coroutine lambda: reads DeviceSettingEntity from QcDeviceSettingDao by mac | invokeSuspend → QcDeviceSettingDao | QcDeviceSettingDao, DeviceSettingEntity | WatchFaceRepository | — | Pure DB read; no protocol | no |
| J05550 | com/qcwireless/smart/ui/base/repository/watchface/WatchFaceRepository$getWatchFaceSetting$5.java | excluded_low_signal | storage_db | Coroutine lambda: error handler for getWatchFaceSetting flow; writes default DiyWatchFaceSettingBean | invokeSuspend → MoshiUtilsKt, QcDeviceSettingDao | QcDeviceSettingDao, DiyWatchFaceSettingBean | WatchFaceRepository | — | Error-path DB write; no protocol | no |
| J05551 | com/qcwireless/smart/ui/base/repository/watchface/WatchFaceRepository.java | documented_app_orchestration | battery, storage_db | Central watchface repository: server fetch, local DB, download, push to device | getWatchFaceFromServer, getCustomizeParamsFromLocalByType, getWatchFaceSetting, downloadWatchFace, pushToDevice | QcCustomFaceDao, QcDeviceSettingDao, QcWatchFaceDao, HealthyRepository, EventBus | UI fragments | 0x0023, 0x0031, 0xffffffff80000000 | Orchestrates watchface lifecycle: server→DB→device push; references battery for power-state gating | no |
| J05553 | com/qcwireless/smart/ui/base/repository/weather/WeatherRepository$getWeatherFromServer$2.java | documented_app_orchestration | bigdata, hr | Coroutine lambda: fetches weather from server via WeatherRequest, emits NetState<WeatherResp> | invokeSuspend → flow emit | WeatherRequest, WeatherResp, NetState | WeatherRepository | 0x0078, 0x008b, 0x00b9, 0x00cc, 30, 40 | Server weather fetch; no BLE touch; hr domain hit is incidental (constant 40) | no |
| J05560 | com/qcwireless/smart/ui/base/repository/ws/WebsocketRepository$getCsSupport$2.java | excluded_low_signal | bigdata, spo2 | Coroutine lambda: fetches CS support status via websocket, emits NetState<SupportCsResp> | invokeSuspend → flow emit | SupportCsResp, NetState | WebsocketRepository | 0x006f, 95 | SpO2 domain hit is incidental (constant 95); pure websocket server call | no |
| J05563 | com/qcwireless/smart/ui/base/repository/ws/WebsocketRepository$getDeleteMessage$2.java | excluded_low_signal | bigdata, sleep | Coroutine lambda: deletes a websocket message, emits NetState<Integer> | invokeSuspend → flow emit | NetState | WebsocketRepository | 0x008c, 60, 62 | Sleep domain hit is incidental (constant 60/62); pure websocket server call | no |
| J05574 | com/qcwireless/smart/ui/base/service/NetService$downBoList$1.java | documented_app_orchestration | spo2 | Coroutine lambda: downloads SpO2 list from server via BloodOxygenRepository.downBoFromServer(uid, lastId) | invokeSuspend → BloodOxygenRepository.downBoFromServer | BloodOxygenRepository, UserConfig | NetService.downBoList | — | **Server download** of blood oxygen data; no BLE touch | no |
| J05577 | com/qcwireless/smart/ui/base/service/NetService$downHeartRateDetail$1.java | documented_app_orchestration | hr | Coroutine lambda: downloads HR detail from server via HeartRateDetailRepository.downHeartRateDetailFromServer(uid, lastId) | invokeSuspend → HeartRateDetailRepository.downHeartRateDetailFromServer | HeartRateDetailRepository, UserConfig | NetService.downHeartRateDetail | — | **Server download** of heart rate detail; no BLE touch | no |
| J05578 | com/qcwireless/smart/ui/base/service/NetService$downSleepDetail$1.java | documented_app_orchestration | sleep | Coroutine lambda: downloads sleep detail from server via SleepDetailRepository.downSleepDetailNewProtocolFromServer(uid, lastId) | invokeSuspend → SleepDetailRepository.downSleepDetailNewProtocolFromServer | SleepDetailRepository, UserConfig | NetService.downSleepDetail | — | **Server download** of sleep detail; uses "NewProtocol" variant; no BLE touch | no |
| J05579 | com/qcwireless/smart/ui/base/service/NetService$downSportDetail$1.java | documented_app_orchestration | steps_sport | Coroutine lambda: downloads sport detail from server via SportPlusRepository.downSportDetailFromServer(uid, lastId) | invokeSuspend → SportPlusRepository.downSportDetailFromServer | SportPlusRepository, UserConfig | NetService.downSportDetail | — | **Server download** of sport detail; no BLE touch | no |
| J05582 | com/qcwireless/smart/ui/base/service/NetService$upBoList$1.java | documented_app_orchestration | spo2 | Coroutine lambda: uploads SpO2 data to server via BloodOxygenRepository.updateBloodOxygenDetailToServer(); collects Flow<NetState<Integer>> | invokeSuspend → BloodOxygenRepository.updateBloodOxygenDetailToServer → Flow.collect | BloodOxygenRepository, NetState | NetService.upBoList | — | **Server upload** of blood oxygen data; Flow-based result; no BLE touch | no |
| J05585 | com/qcwireless/smart/ui/base/service/NetService$upHeartRateDetail$1.java | documented_app_orchestration | hr | Coroutine lambda: uploads HR detail to server via HeartRateDetailRepository.updateHeartRateDetailToServer(); collects Flow<NetState<Integer>> | invokeSuspend → HeartRateDetailRepository.updateHeartRateDetailToServer → Flow.collect | HeartRateDetailRepository, NetState | NetService.upHeartRateDetail | — | **Server upload** of heart rate detail; Flow-based result; no BLE touch | no |
| J05586 | com/qcwireless/smart/ui/base/service/NetService$upSleepDetail$1.java | documented_app_orchestration | sleep | Coroutine lambda: uploads sleep detail to server; checks UserConfig.getNewSleepProtocol() → if true calls SleepDetailRepository.updateSleepDetailToServerNewProtocol(); collects Flow<NetState<Integer>> | invokeSuspend → SleepDetailRepository.updateSleepDetailToServerNewProtocol → Flow.collect | SleepDetailRepository, UserConfig, NetState | NetService.upSleepDetail | 0x0005, 0x0048 | **Server upload** of sleep detail; dual-protocol path (new vs old); no BLE touch | no |
| J05587 | com/qcwireless/smart/ui/base/service/NetService$upSportDetailDetail$1.java | documented_app_orchestration | steps_sport | Coroutine lambda: uploads sport detail to server via SportPlusRepository.updateSportDetailToServer(); collects Flow<NetState<Integer>> | invokeSuspend → SportPlusRepository.updateSportDetailToServer → Flow.collect | SportPlusRepository, NetState | NetService.upSportDetailDetail | — | **Server upload** of sport detail; Flow-based result; no BLE touch | no |
| J05589 | com/qcwireless/smart/ui/base/service/NetService.java | documented_app_orchestration | hr, sleep, spo2, steps_sport, storage_db, sync_scheduler, temperature | **CRITICAL: Central cloud sync orchestrator** — singleton via Companion.getInstance(); owns QcSyncDao; downAll() and upAll() are the main entry points | downAll(), upAll(), downBoList(), downHeartRateDetail(), downSleepDetail(), downSportDetail(), downStepDetail(), downTemperature(), downBpList(), upBoList(), upHeartRateDetail(), upSleepDetail(), upSportDetailDetail(), upStepsDetail(), upBpList(), upTemperatureList(), downGoalSetting(), downUserProfile(), upCollectionData(), syncDao | QcSyncDao, UserConfig, DateUtil, ThreadExtKt, GlobalScope | Login flow, sync triggers | 30 | **Pure cloud sync; NO BLE/device touch** — see analysis below | no |
| J05590 | com/qcwireless/smart/ui/base/service/NoForegroundMotionDetector.java | documented_app_orchestration | sleep | Android Service: accelerometer-based motion detection for background; uses WakeLock, ScheduledExecutorService, SensorManager | onMotionChanged callback, isMoving, startMotionDetect, stopMotionDetect | SensorManager, PowerManager.WakeLock, NotificationUtils | System (bound service) | — | Background motion detection service; sleep domain hit is from "sleep" in scheduling; no direct health data | no |
| J05593 | com/qcwireless/smart/ui/base/service/SimpleMotionDetector.java | documented_app_orchestration | ble_connection, uart_small_data | Android Service: motion detection with StateFlow<Boolean> isMoving; uses MotionBinder for IPC | isMoving (StateFlow), MotionBinder, startDetect, stopDetect | SensorManager, HandlerThread, PowerManager.WakeLock, MutableStateFlow | System (bound service) | — | Motion detection service; ble_connection hit from notify pattern; no direct health data | no |
| J05595 | com/qcwireless/smart/ui/base/thread/Queue.java | documented_app_orchestration | ble_connection, sync_scheduler, uart_small_data | Thread-safe blocking queue (LinkedList) with wait/notify for BLE task scheduling | addTail, addFirst, addAllTail, get, remove, clear, contains, isEmpty, getNewNotWait | — | ThreadManager, WorkThread, WakeupThread | — | Producer-consumer queue for BLE background thread tasks; no health data directly | no |
| J05596 | com/qcwireless/smart/ui/base/thread/SleepTask.java | documented_app_orchestration | sleep | IDo implementation: blocks on Lock/Condition.await() to pause the BLE work thread | iDo() → lock.lock() → condition.await() | Lock, Condition | ThreadManager.needWait() | — | Thread-pausing sentinel task; "sleep" = thread sleep, not health sleep data | no |
| J05597 | com/qcwireless/smart/ui/base/thread/ThreadManager.java | documented_app_orchestration | ble_connection, sleep, sync_scheduler | Singleton: manages WorkThread + WakeupThread for BLE reconnection; Queue for task scheduling | getInstance(), addTask(), needWait(), wakeUp(), wakeUpNotWait(), removeAllWait(), reSetLastConnectTime(), setSleepMin() | BleOperateManager, Queue, WorkThread, WakeupThread, SleepTask, WakeUpTask | BLE connection logic | — | **BLE reconnection orchestrator** — manages background BLE thread, wake/sleep cycle, reconnect via BleOperateManager.connectWithScan | no |
| J05598 | com/qcwireless/smart/ui/base/thread/WakeUpTask.java | documented_app_orchestration | sleep | IDo implementation: delegates to WorkThread.wakeUp() or wakeUpNoSleep() | iDo() → WorkThread.wakeUp()/wakeUpNoSleep() | WorkThread | ThreadManager.wakeUp() | — | Wakes the BLE work thread; "sleep" = thread sleep, not health | no |
| J05600 | com/qcwireless/smart/ui/base/thread/WorkThread.java | documented_app_orchestration | bigdata, ble_connection, sleep, spo2 | Background BLE thread: exponential backoff reconnection loop; checks BluetoothUtils.isEnabledBluetooth, BleOperateManager.isConnected, then calls connectWithScan | run(), wakeUp(), wakeUpNoSleep(), needLock(), needWait(), setSleepTimeMin(), setLastConnectTime() | BleOperateManager, BluetoothUtils, PreUtil, DateUtil | ThreadManager | 0x0030, 0x003b, 0x12c, 0x493e0, 0x78, 30 | **Core BLE reconnection loop**: starts at 30s backoff, increments to 120s, then 300s (5min) cycle; uses connectWithScan; spO2 hit is incidental | no |
| J05602 | com/qcwireless/smart/ui/base/util/AppCacheDataManager.java | excluded_low_signal | storage_db | Utility: cache/data cleanup — cleanInternalCache, cleanExternalCache, cleanDatabases, cleanSharedPreference, clearAllCache, getTotalCacheSize | static methods for file/dir deletion | — | Settings UI | — | Pure file system utility; no health/BLE data | no |
| J05609 | com/qcwireless/smart/ui/base/util/MediaUtil.java | excluded_low_signal | storage_db | Utility: audio playback (find phone ringtone), vibration, media URI resolution | vibrateAndPlayTone, stopRing, setMediaSourceMp3, getMediaUriFromPath | MediaPlayer, AudioManager, Vibrator, MediaStore | Find-phone feature | — | Audio/media utility; no health/BLE data | no |
| J05612 | com/qcwireless/smart/ui/base/util/NotificationUtils.java | documented_app_orchestration | battery, ble_connection, uart_small_data | Notification helper: creates foreground service notification for BLE connection; shows step count when connected | initBandNotification, cancelNotification, createNotificationChannel | BleOperateManager, PreUtil, NotificationManager | NoForegroundMotionDetector, SimpleMotionDetector | — | BLE notification: shows step count in persistent notification; references BleOperateManager.isConnected | no |
| J05614 | com/qcwireless/smart/ui/base/util/ShellUtils.java | excluded_low_signal | bigdata, hr, sleep, spo2 | Utility: shell command execution (root check, execCommand) | execCommand, checkRootPermission | — | Debug/admin tools | 0x0101–0x019b, 39, 40, 44, 57, 60, 73, 95 | Generic shell utility; domain hits are incidental constants; no health data flow | no |
| J05621 | com/qcwireless/smart/ui/base/view/BatteryImage.java | excluded_low_signal | battery | Custom View: draws battery level bar with skin support | setNumber(int), onDraw, applySkin | SkinCompatResources | Device info UI | 30 | Pure UI widget for battery display; no data flow | no |
| J05624 | com/qcwireless/smart/ui/base/view/CircularProgressBar.java | excluded_low_signal | sleep | Custom View: animated circular progress bar with skin support | setProgress, onDraw, applySkin | SkinCompatResources, ValueAnimator | Health dashboard UI | — | Pure UI widget; "sleep" hit is from animation timing | no |
| J05625 | com/qcwireless/smart/ui/base/view/CircularSeekBar.java | excluded_low_signal | bigdata, hr, sleep | Custom View: circular seek bar with touch interaction | OnProgressChangeListener, onDraw | SkinCompatResources, ChartUtils | Health settings UI | 30, 40 | Pure UI widget; domain hits are incidental | no |
| J05638 | com/qcwireless/smart/ui/base/view/gps/LockProgressBar.java | excluded_low_signal | sleep | Custom View: GPS lock progress animation | onDraw, animEndListener | — | GPS sport UI | — | Pure UI widget; no health data | no |
| J05641 | com/qcwireless/smart/ui/base/view/healthy/PubuProgressCircle.java | excluded_low_signal | sleep | Custom View: circular progress for health metrics | onDraw, setProgress | — | Health dashboard UI | — | Pure UI widget; no health data flow | no |
| J05647 | com/qcwireless/smart/ui/base/view/PGBloodOxygenView.java | excluded_low_signal | bigdata, hr, spo2 | Custom View: blood oxygen bar (80–100 range) | setBloodOxygen(int), onDraw | SkinCompatResources | SpO2 dashboard UI | 95 | Pure UI widget; renders SpO2 value; no data flow | no |
| J05648 | com/qcwireless/smart/ui/base/view/PGBloodPressureView.java | excluded_low_signal | hr | Custom View: blood pressure bar (0–200 range) | setBpValue(int, int), onDraw | SkinCompatResources | BP dashboard UI | — | Pure UI widget; renders BP value; no data flow | no |

---

## NetService Deep Analysis

### Architecture

`NetService` is a **Kotlin singleton** (via `Companion.getInstance()` lazy delegate) that serves as the **cloud-to-local sync orchestrator**. It is **NOT a BLE service** — it has zero imports from `com.oudmon.ble` and never touches `BleOperateManager`.

### Key Finding: NetService is CLOUD-ONLY sync

NetService orchestrates **server ↔ local-database** synchronization only. It does NOT trigger device BLE sync. The data flow is:

```
Server (cloud API)  ←→  Repository (BloodOxygenRepository, HeartRateDetailRepository, etc.)
                        ←→  Local Room DB (via QcSyncDao)
```

The BLE/device sync is handled by an entirely separate system: `ThreadManager` → `WorkThread` → `BleOperateManager.connectWithScan()`.

### downAll() — Server Download Orchestrator

**Guard:** Only runs if `UserConfig.getInstance().getLoginStatus()` is true.  
**Execution:** Runs on background thread via `ThreadExtKt.ktxRunOnBgFix`.  
**Sequencing:** Sequential — each data type is downloaded one after another in a single lambda.

For each data type, the pattern is:
1. Query `QcSyncDao.queryByUidAndAction(uid, "<Action>")` for last sync timestamp
2. If found → call `downXxx(lastSyncTime)` (incremental sync)
3. If not found → create new `DateUtil().addDay(-30)` (30-day lookback), call `downXxx(timestamp)`, and insert a new `SyncDataEntity`

**Data types synced (in order):**
| Action Key | Method Called | Repository | Notes |
|---|---|---|---|
| `Step_Action` | `downStepDetail(lastSyncTime)` | — | 30-day default |
| `Sleep_Action` | `downSleepDetail(lastSyncTime)` | SleepDetailRepository | New protocol variant |
| `Heart_Rate_Action` | `downHeartRateDetail(lastSyncTime)` | HeartRateDetailRepository | **BUG**: when entry exists, calls `downSleepDetail` instead of `downHeartRateDetail` (line 184) |
| `Sport_Plus_Action` | `downSportDetail(lastSyncTime / 1000)` | SportPlusRepository | Timestamp divided by 1000 (ms→s) |
| `BloodPressure_Action` | `downBpList(lastSyncTime)` | — | 30-day default |
| `BloodOxygen_Action` | `downBoList(lastSyncTime)` | BloodOxygenRepository | 30-day default |
| `Temperature_Action` | `downTemperature(lastSyncTime)` | — | **Empty method body** — stub/unimplemented |

**Critical Bug:** In `downAll()`, when `Heart_Rate_Action` exists in the DB, the code calls `netService.downSleepDetail(queryByUidAndAction3.getLastSyncTime())` instead of `netService.downHeartRateDetail(...)`. This is a decompilation artifact or a real bug in the original code.

### upAll() — Server Upload Orchestrator

**Guard:** Only runs if `UserConfig.getInstance().getLoginStatus()` is true.  
**Execution:** Runs on background thread via `ThreadExtKt.ktxRunOnBgFix`.  
**Sequencing:** Sequential — each upload method called one after another.

**Upload order:**
1. `upHeartRateDetail()` → `HeartRateDetailRepository.updateHeartRateDetailToServer()`
2. `upSleepDetail()` → `SleepDetailRepository.updateSleepDetailToServerNewProtocol()` (gated by `UserConfig.getNewSleepProtocol()`)
3. `upSportDetailDetail()` → `SportPlusRepository.updateSportDetailToServer()`
4. `upStepsDetail()` → —
5. `upBpList()` → —
6. `upBoList()` → `BloodOxygenRepository.updateBloodOxygenDetailToServer()`
7. `upTemperatureList()` — **Empty method body** — stub/unimplemented

### Upload Pattern

All upload methods follow the same pattern:
1. Launch a coroutine on `GlobalScope`
2. Call `Repository.updateXxxToServer()` which returns a `Flow<NetState<Integer>>`
3. Collect the flow (result is consumed but not acted upon in the coroutine)

### Sleep Protocol Dual-Path

`upSleepDetail()` has a conditional: if `UserConfig.getInstance().getNewSleepProtocol()` is true, it calls `SleepDetailRepository.updateSleepDetailToServerNewProtocol()`. If false, the coroutine returns `Unit` immediately (no-op). This means the **old sleep upload protocol is deprecated** — only the new protocol path uploads.

Similarly, `downSleepDetail()` always calls `SleepDetailRepository.downSleepDetailNewProtocolFromServer()` — there is no old-protocol download path.

### Temperature — Stub

Both `downTemperature(long)` and `upTemperatureList()` have **empty method bodies**. Temperature sync is declared in `downAll()`/`upAll()` but not implemented. The `SyncDataEntity` for `Temperature_Action` is still created in the DB.

### SyncAction Inner Class

`NetService.SyncAction` is a static singleton with no methods or fields — appears to be a type-safe tag/marker class used in routing or event bus patterns.

### Additional Public Methods

- `downGoalSetting()` — launches coroutine (inner class not in this chunk)
- `downUserProfile()` — launches coroutine (inner class not in this chunk)
- `upCollectionData()` — launches coroutine (inner class not in this chunk)

---

## ThreadManager / BLE Reconnection System

### Architecture

The BLE reconnection system is **completely separate** from NetService:

```
ThreadManager (singleton)
  ├── WorkThread ("ble-background-thread-1")
  │     └── Reconnection loop: check BT enabled → check connected →
  │           exponential backoff (30s→120s) → connectWithScan →
  │           300s (5min) cycle after timeout
  ├── WakeupThread ("ble-background-wakeup-thread-1")
  │     └── Wakes up on Queue.addTail to process tasks
  └── Queue<IDo> (task queue)
        ├── SleepTask (pauses thread via Lock/Condition.await)
        └── WakeUpTask (signals WorkThread to wake)
```

### WorkThread Reconnection Logic

1. **Check preconditions:** Bluetooth enabled + device address stored in `PreUtil.getSharedString("com.qc.Action_Device_Address")`
2. **If connected:** Reset backoff to 30s, lock thread (wait for signal)
3. **If not connected, backoff ≤ 120s:** Sleep for `backoff * 1000ms`, check connection, increment backoff, call `BleOperateManager.connectWithScan(mac)`
4. **If backoff > 120s:** Sleep 300000ms (5 min), then try `connectWithScan(mac)` once per 5-minute cycle

### ThreadManager.wakeUp()

- If `BleOperateManager.isConnected()` → clear queue, add SleepTask (already connected, stop retrying)
- If not connected → remove all SleepTasks, add WakeUpTask, wake the WakeupThread

---

## Function Dictionary Proposals

### NetService

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | downAll() |
| kind | method |
| general_function | Sequentially downloads all health data types from cloud server to local DB, using QcSyncDao for incremental sync timestamps with 30-day default lookback |
| variables_fields | syncDao: QcSyncDao |
| constants_command_ids | 30 (days lookback) |
| inputs | UserConfig.uid, UserConfig.loginStatus |
| outputs | Calls downXxx() for each data type |
| calls | QcSyncDao.queryByUidAndAction, QcSyncDao.insert, DateUtil.addDay, downStepDetail, downSleepDetail, downHeartRateDetail, downSportDetail, downBpList, downBoList, downTemperature |
| called_by | Sync trigger (likely login or periodic sync) |
| ble_service_or_characteristic | NONE — cloud-only |
| database_or_model_touched | QcSyncDao, SyncDataEntity |
| data_domains | hr, sleep, spo2, steps_sport, temperature, storage_db, sync_scheduler |
| freshness_truth_implications | Server data may lag behind device; 30-day lookback means first sync gets last 30 days; BUG: HR download may call sleep download instead |
| evidence_notes | downAll() calls downSleepDetail for Heart_Rate_Action when entry exists (line 184) — likely bug |
| unknowns | Who calls downAll()/upAll() and when; whether the HR bug is in source or decompilation artifact |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | upAll() |
| kind | method |
| general_function | Sequentially uploads all health data types from local DB to cloud server; each upload returns Flow<NetState<Integer>> |
| variables_fields | — |
| constants_command_ids | — |
| inputs | UserConfig.loginStatus |
| outputs | Calls upXxx() for each data type |
| calls | upHeartRateDetail, upSleepDetail, upSportDetailDetail, upStepsDetail, upBpList, upBoList, upTemperatureList |
| called_by | Sync trigger (likely login or periodic sync) |
| ble_service_or_characteristic | NONE — cloud-only |
| database_or_model_touched | Indirectly via repositories |
| data_domains | hr, sleep, spo2, steps_sport, temperature, sync_scheduler |
| freshness_truth_implications | Upload is fire-and-forget (Flow collected but result ignored); temperature upload is a no-op stub |
| evidence_notes | upTemperatureList() and downTemperature() are empty stubs |
| unknowns | Whether upload failures are retried |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | downBoList(long lastId) |
| kind | method |
| general_function | Downloads SpO2 list from server starting after lastId timestamp |
| variables_fields | — |
| constants_command_ids | — |
| inputs | lastId (timestamp) |
| outputs | Delegates to BloodOxygenRepository.downBoFromServer(uid, lastId) |
| calls | BloodOxygenRepository.downBoFromServer |
| called_by | downAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | BloodOxygenRepository (indirectly) |
| data_domains | spo2 |
| freshness_truth_implications | Incremental sync from last known timestamp |
| evidence_notes | — |
| unknowns | — |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | upBoList() |
| kind | method |
| general_function | Uploads SpO2 data to server via BloodOxygenRepository.updateBloodOxygenDetailToServer() |
| variables_fields | — |
| constants_command_ids | — |
| inputs | — |
| outputs | Flow<NetState<Integer>> collected silently |
| calls | BloodOxygenRepository.updateBloodOxygenDetailToServer |
| called_by | upAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | BloodOxygenRepository (indirectly) |
| data_domains | spo2 |
| freshness_truth_implications | Upload result not checked; fire-and-forget |
| evidence_notes | — |
| unknowns | — |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | downHeartRateDetail(long lastId) |
| kind | method |
| general_function | Downloads HR detail from server starting after lastId timestamp |
| variables_fields | — |
| constants_command_ids | — |
| inputs | lastId (timestamp) |
| outputs | Delegates to HeartRateDetailRepository.downHeartRateDetailFromServer(uid, lastId) |
| calls | HeartRateDetailRepository.downHeartRateDetailFromServer |
| called_by | downAll() (but BUG: downAll calls downSleepDetail for HR action) |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | HeartRateDetailRepository (indirectly) |
| data_domains | hr |
| freshness_truth_implications | Incremental sync from last known timestamp |
| evidence_notes | BUG in downAll(): Heart_Rate_Action existing entry calls downSleepDetail instead of downHeartRateDetail |
| unknowns | Whether this is a decompilation artifact or real bug |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | upHeartRateDetail() |
| kind | method |
| general_function | Uploads HR detail to server via HeartRateDetailRepository.updateHeartRateDetailToServer() |
| variables_fields | — |
| constants_command_ids | — |
| inputs | — |
| outputs | Flow<NetState<Integer>> collected silently |
| calls | HeartRateDetailRepository.updateHeartRateDetailToServer |
| called_by | upAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | HeartRateDetailRepository (indirectly) |
| data_domains | hr |
| freshness_truth_implications | Upload result not checked |
| evidence_notes | — |
| unknowns | — |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | downSleepDetail(long lastId) |
| kind | method |
| general_function | Downloads sleep detail from server using NEW protocol via SleepDetailRepository.downSleepDetailNewProtocolFromServer(uid, lastId) |
| variables_fields | — |
| constants_command_ids | — |
| inputs | lastId (timestamp) |
| outputs | Delegates to SleepDetailRepository.downSleepDetailNewProtocolFromServer |
| calls | SleepDetailRepository.downSleepDetailNewProtocolFromServer |
| called_by | downAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | SleepDetailRepository (indirectly) |
| data_domains | sleep |
| freshness_truth_implications | Always uses new protocol; old protocol download path removed |
| evidence_notes | Method name includes "NewProtocol" — old protocol deprecated for download |
| unknowns | — |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | upSleepDetail() |
| kind | method |
| general_function | Uploads sleep detail to server; gated by UserConfig.getNewSleepProtocol() — if false, no-op; if true, calls SleepDetailRepository.updateSleepDetailToServerNewProtocol() |
| variables_fields | — |
| constants_command_ids | 0x0005, 0x0048 |
| inputs | UserConfig.getNewSleepProtocol() |
| outputs | Flow<NetState<Integer>> collected silently |
| calls | SleepDetailRepository.updateSleepDetailToServerNewProtocol |
| called_by | upAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | SleepDetailRepository (indirectly) |
| data_domains | sleep |
| freshness_truth_implications | Old sleep upload protocol is completely disabled; only new protocol uploads |
| evidence_notes | Dual-protocol conditional; old path is dead code |
| unknowns | What triggers the newSleepProtocol flag |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | downSportDetail(long lastId) |
| kind | method |
| general_function | Downloads sport detail from server; note: lastId divided by 1000 (ms→s conversion) in downAll() |
| variables_fields | — |
| constants_command_ids | — |
| inputs | lastId (timestamp in seconds) |
| outputs | Delegates to SportPlusRepository.downSportDetailFromServer(uid, lastId) |
| calls | SportPlusRepository.downSportDetailFromServer |
| called_by | downAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | SportPlusRepository (indirectly) |
| data_domains | steps_sport |
| freshness_truth_implications | Timestamp unit mismatch: downAll() divides by 1000 but DB stores ms |
| evidence_notes | Unit conversion in downAll() suggests server expects seconds while DB stores milliseconds |
| unknowns | — |
| confidence | high |

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/service/NetService.java |
| class | NetService |
| method_or_field | upSportDetailDetail() |
| kind | method |
| general_function | Uploads sport detail to server via SportPlusRepository.updateSportDetailToServer() |
| variables_fields | — |
| constants_command_ids | — |
| inputs | — |
| outputs | Flow<NetState<Integer>> collected silently |
| calls | SportPlusRepository.updateSportDetailToServer |
| called_by | upAll() |
| ble_service_or_characteristic | NONE |
| database_or_model_touched | SportPlusRepository (indirectly) |
| data_domains | steps_sport |
| freshness_truth_implications | Upload result not checked |
| evidence_notes | — |
| unknowns | — |
| confidence | high |

### ThreadManager

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/thread/ThreadManager.java |
| class | ThreadManager |
| method_or_field | wakeUp() |
| kind | method |
| general_function | Wakes the BLE reconnection system: if connected, clears queue and sleeps; if not, removes SleepTasks and adds WakeUpTask |
| variables_fields | a: WorkThread, b: WakeupThread, c: Queue, d: Lock, e: Condition |
| constants_command_ids | — |
| inputs | BleOperateManager.isConnected() |
| outputs | Queue task modification, WakeupThread.wakeUp() |
| calls | BleOperateManager.isConnected, Queue.clear, Queue.addFirst(SleepTask), Queue.addTail(WakeUpTask), WakeupThread.wakeUp |
| called_by | BLE connection state changes |
| ble_service_or_characteristic | Indirect — manages BleOperateManager reconnection |
| database_or_model_touched | NONE |
| data_domains | ble_connection, sync_scheduler |
| freshness_truth_implications | BLE reconnection is independent of cloud sync; runs on separate thread |
| evidence_notes | XLog message: "已经连接上，清除队列里的唤醒重连操作" (Already connected, clearing reconnect operations from queue) |
| unknowns | What triggers wakeUp() calls |
| confidence | high |

### WorkThread

| Field | Value |
|---|---|
| file | com/qcwireless/smart/ui/base/thread/WorkThread.java |
| class | WorkThread |
| method_or_field | run() |
| kind | method |
| general_function | BLE reconnection loop with exponential backoff: 30s→120s→300s(5min) cycles; calls BleOperateManager.connectWithScan(mac) |
| variables_fields | a: AtomicInteger (backoff seconds, default 30), b: long (last connect time) |
| constants_command_ids | 30 (initial backoff), 120 (max incremental backoff), 300000 (5min sleep), 300 (5min offset) |
| inputs | PreUtil.getSharedString("com.qc.Action_Device_Address"), BluetoothUtils.isEnabledBluetooth |
| outputs | BleOperateManager.connectWithScan(mac) |
| calls | BleOperateManager.isConnected, BleOperateManager.connectWithScan, BluetoothUtils.isEnabledBluetooth, PreUtil.getSharedString, DateUtil.getUnixTimestamp |
| called_by | ThreadManager (creates and starts) |
| ble_service_or_characteristic | BleOperateManager (connectWithScan) |
| database_or_model_touched | NONE |
| data_domains | ble_connection |
| freshness_truth_implications | BLE reconnection is purely device-level; no cloud involvement |
| evidence_notes | Device address stored under key "com.qc.Action_Device_Address" |
| unknowns | — |
| confidence | high |

---

## Summary

- **Files assigned count:** 35
- **Files actually read count:** 35
- **Rows needing second pass:** 0
- **Strongest new findings:**
  1. **NetService is CLOUD-ONLY sync** — it never touches BLE or device communication. It orchestrates server↔local-DB sync for HR, SpO2, sleep, sport, steps, BP, and temperature. The BLE reconnection system (ThreadManager/WorkThread) is a completely separate subsystem.
  2. **BUG in downAll():** When `Heart_Rate_Action` exists in the sync DB, `downAll()` calls `downSleepDetail()` instead of `downHeartRateDetail()` (line 184 of NetService.java). This means HR incremental download is broken — it downloads sleep data instead.
  3. **Sleep protocol dual-path:** Upload uses `UserConfig.getNewSleepProtocol()` gate; download always uses new protocol. Old sleep upload path is dead code.
  4. **Temperature sync is a stub:** Both `downTemperature()` and `upTemperatureList()` have empty method bodies, despite being called in `downAll()`/`upAll()`.
  5. **BLE reconnection architecture:** ThreadManager manages WorkThread with exponential backoff (30s→120s→5min cycle), using `BleOperateManager.connectWithScan()`. Device address stored in SharedPreferences under key `com.qc.Action_Device_Address`.
  6. **Upload pattern is fire-and-forget:** All `upXxx()` methods collect `Flow<NetState<Integer>>` but ignore the result — no retry or error handling visible.
  7. **Sport timestamp unit mismatch:** `downAll()` divides sport sync timestamp by 1000 (ms→s) before passing to `downSportDetail()`, suggesting the server API expects seconds while the DB stores milliseconds.

- **How fulfilling was this task?** Very fulfilling. The chunk contained the critical NetService class which is the central cloud sync orchestrator, and the ThreadManager/WorkThread BLE reconnection system. The analysis clearly separates cloud sync from device sync, which was the key question.

- **What would you like changed if asked to do something like this again?** The ledger CSV is very large and slow to parse; providing a pre-filtered mini-ledger per chunk would speed things up. Also, the decompiled bytecode for `upSleepDetail$1.invokeSuspend()` was partially unreadable (JADX couldn't fully decompile), which limited confidence on the sleep upload path — having `--show-bad-code` output available would help.
