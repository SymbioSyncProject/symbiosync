# CH0009 — app_orchestration_strong_hits

| Field | Value |
|---|---|
| **Chunk ID** | CH0009 |
| **Chunk type** | app_orchestration_strong_hits |
| **Source tree** | decompiled4 |
| **Ledger entries** | 35 |
| **Ledger ID range** | J04145 – J05026 |
| **Review date** | 2026-05-19 |

---

## Focus Question Answer

> Does this base/dialog/event/DI area reveal app-level orchestration or only UI/event/domain glue? Does KoinModuleKt wire repositories/services for HR/SpO2/HRV/sleep sync orchestration?

**Answer: YES — this chunk reveals genuine app-level orchestration, not just UI glue.**

KoinModuleKt is the **central DI wiring hub** for the entire QRing app. It defines two Koin modules:

1. **`repositoryModule`** — registers 30+ singleton repositories via Koin `single { }`, including:
   - `HeartRateDetailRepository` — HR data orchestration
   - `BloodOxygenRepository` — SpO2 data orchestration
   - `HRVRepository` — HRV data orchestration
   - `SleepDetailRepository` — sleep data orchestration
   - `StepDetailRepository`, `StepHistoryRepository`, `SportPlusRepository` — steps/sport
   - `TemperatureRepository`, `BloodPressureRepository`, `BloodSugarRepository`
   - `HealthyRepository` — aggregate health data
   - `DeviceSettingRepository`, `DeviceBindRepository` — device config
   - `OTARepository`, `WatchFaceRepository`, `MessagePushRepository`
   - `ContactsRepository`, `MusicRepository`, `EbookRepository`
   - `MenstruationRepository`, `PressureRepository`, `MuslimRepository`, `MuslimV2Repository`
   - `OneKeyCheckRepository`, `FeedbackRepository`, `FindPwdRepository`
   - `RegisterRepository`, `LoginRepository`, `UserProfileRepository`
   - `WebsocketRepository`, `FriendsRepository`, `LoverRepository`

2. **`viewModelModule`** — registers 50+ ViewModels via Koin `viewModel { }`, each injecting the relevant repositories. Key health-sync ViewModels include:
   - `HealthyViewModel` — injects HealthyRepository, StepDetailRepository, SleepDetailRepository, HeartRateDetailRepository, SportPlusRepository, BloodOxygenRepository, TemperatureRepository, HRVRepository, BloodPressureRepository, BloodSugarRepository, PressureRepository, MuslimRepository, MuslimV2Repository, FriendsRepository, WatchFaceRepository, UserProfileRepository
   - `HeartActivityViewModel` — injects HeartRateDetailRepository, UserProfileRepository, DeviceSettingRepository
   - `HrvActivityViewModel` — injects HRVRepository
   - `BloodOxygenViewModel` — injects BloodOxygenRepository, DeviceSettingRepository
   - `DaySleepFragmentViewModel` / `WeekSleepFragmentViewModel` / `MonthSleepFragmentViewModel` — all inject SleepDetailRepository
   - `TemperatureViewModel` — injects TemperatureRepository

The `appModule` property returns `listOf(repositoryModule, viewModelModule)`, and QCApplication.onCreate() calls `startKoin { modules(KoinModuleKt.getAppModule()) }`, confirming this is the **live DI graph**.

**However**, the repositories themselves are registered as parameterless `new XxRepository()` singletons — the actual BLE sync orchestration logic (command dispatch, data parsing, database writes) lives **inside** those repository classes, not in KoinModuleKt. KoinModuleKt is the **wiring manifest**, not the orchestration engine. The real sync orchestration must be traced into the repository implementations (which are in other chunks).

The event bus classes (12 event files) and lifecycle class (QcLifeCycle) provide the **signaling layer** that triggers sync flows, while UserConfig/UserConfigDAO provide the **persistent configuration** that controls which data domains are active.

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J04145 | com/qcwireless/smart/base/di/KoinModuleKt.java | active | bigdata\|hr\|hrv_regular\|sleep\|spo2\|steps_sport\|temperature | Central Koin DI module; wires all repositories and ViewModels for the app | `getViewModelModule()`, `getRepositoryModule()`, `getAppModule()`, static fields `a` (viewModelModule), `b` (repositoryModule), `c` (appModule list) | 30+ repo imports, 50+ VM imports, org.koin.* | QCApplication.init() calls `startKoin { modules(KoinModuleKt.getAppModule()) }` | 30\|39\|40\|44\|57\|60\|62 | Definitive DI wiring hub. Registers all health repos as singletons and all VMs with repo injection. | Yes — trace into repository implementations for actual sync logic |
| J04147 | com/qcwireless/smart/base/dialog/adapter/EasyAdapter.java | active | ble_connection\|uart_small_data | Abstract RecyclerView adapter base with single/multi-select support | `whenBindViewHolder()`, `clearSelected()`, `getMultiSelectedPosition()`, `OnItemClickListener`, `OnItemSingleSelectListener`, `OnItemMultiSelectListener` | RecyclerView, ViewHolder | BottomRemindDialog.ModeAdapter, BottomListDialog.ModeAdapter | notify:8 | Generic UI adapter; no domain logic. | No |
| J04153 | com/qcwireless/smart/base/dialog/BottomDeviceHeartRemindValueDialog.java | active | bigdata\|ble_connection\|hr | Heart rate remind value picker dialog (wheel selector for HR thresholds) | `initData()`, `SelectSecondListener.showSecond()`, fields: `d` (display list), `e` (value list), `k` (isHigh boolean) | WheelView, ArrayWheelAdapter, GattError constants | Heart settings UI flow | 30\|40, Gatt:5\|GATT:4\|40:2 | Two modes: high (100-150 bpm) and low (40-50 bpm) thresholds. Uses GattError constants as numeric values (133, 129). | No |
| J04157 | com/qcwireless/smart/base/dialog/BottomListDialog.java | active | ble_connection\|uart_small_data | Generic bottom-sheet list dialog with Builder pattern | `Builder.create()`, `DialogItemClickListener`, `ModeAdapter` | EasyAdapter, RecyclerView | Device settings/selection flows | notify:2 | Pure UI dialog; no domain logic. | No |
| J04158 | com/qcwireless/smart/base/dialog/BottomRemindDialog.java | active | ble_connection\|uart_small_data | Reminder/alarm creation dialog with time wheel, week repeat, and label | `ModeAdapter`, `MyTextWatcher`, `RemindDialogListener`, fields: `n` (hour), `o` (minute), `p` (label), `q` (mode) | EasyAdapter, WheelView, WeekRepeat | Alarm/reminder creation flows | notify:2, 30\|60 | UI dialog for creating reminders; week-repeat selection and time picking. | No |
| J04166 | com/qcwireless/smart/base/dialog/HeartWarningDialog.java | active | hr | Heart rate warning threshold picker dialog (wheel selector) | `initData()`, `SelectTimeListener.onSelect()`, fields: `h` (selected value), `i` (index), `d` (display list) | WheelView, ArrayWheelAdapter | Heart rate warning settings | 30, heart:7 | UI dialog for selecting HR warning threshold values. | No |
| J04174 | com/qcwireless/smart/base/event/BatteryIsChargingEvent.java | active | battery | EventBus event signaling battery charging state change | (none — empty class) | MessageEvent | Battery monitoring flow | Battery:2 | Marker event; no payload. | No |
| J04175 | com/qcwireless/smart/base/event/BatteryLowEvent.java | active | battery | EventBus event signaling low battery | (none — empty class) | MessageEvent | QcLifeCycle posts this on resume; battery monitoring flow | Battery:2 | Marker event; no payload. Posted by QcLifeCycle.onActivityResumed(). | No |
| J04176 | com/qcwireless/smart/base/event/BluetoothEvent.java | active | ble_connection | EventBus event signaling BLE connection state change | `connect` (boolean), `getConnect()` | MessageEvent | BLE connection flow | Bluetooth:3 | Carries boolean `connect` flag. | No |
| J04177 | com/qcwireless/smart/base/event/BluetoothInitDeviceEvent.java | active | ble_connection | EventBus event signaling BLE device initialization | (none — empty class) | MessageEvent | BLE init flow | Bluetooth:2 | Marker event; no payload. | No |
| J04178 | com/qcwireless/smart/base/event/BluetoothSppEvent.java | active | ble_connection | EventBus event signaling SPP (serial port profile) connection state | `connect` (boolean), `getConnect()` | MessageEvent | SPP/UART data flow | Bluetooth:3 | Carries boolean `connect` flag. | No |
| J04179 | com/qcwireless/smart/base/event/BluetoothSyncEvent.java | active | ble_connection\|sync_scheduler | EventBus event signaling BLE sync trigger | (none — empty class) | MessageEvent | BLE sync orchestration flow | Bluetooth:2\|Sync:2 | Marker event; no payload. Signals sync should start. | No |
| J04184 | com/qcwireless/smart/base/event/DataSyncEvent.java | active | sync_scheduler | EventBus event signaling data sync status | `status` (boolean), `getStatus()` | MessageEvent | Data sync flow | Sync:3 | Carries boolean `status` (sync in-progress vs. complete). | No |
| J04190 | com/qcwireless/smart/base/event/DeviceHeartChangeEvent.java | active | hr | EventBus event carrying real-time heart rate value from device | `heart` (int), `getHeart()` | MessageEvent | Real-time HR display flow | heart:4 | Carries integer heart rate value. Key for live HR updates. | No |
| J04192 | com/qcwireless/smart/base/event/DeviceSyncEvent.java | active | sync_scheduler | EventBus event signaling device sync trigger | (none — empty class) | MessageEvent | Device sync flow | Sync:2 | Marker event; no payload. | No |
| J04193 | com/qcwireless/smart/base/event/DeviceSyncTodayStepsAndDetailEvent.java | active | sync_scheduler | EventBus event signaling today's steps+detail sync completion | (none — empty class) | MessageEvent | Steps sync flow | Sync:2 | Marker event; no payload. | No |
| J04194 | com/qcwireless/smart/base/event/DeviceSyncTodayStepsEvent.java | active | sync_scheduler | EventBus event signaling today's steps sync completion | (none — empty class) | MessageEvent | Steps sync flow | Sync:2 | Marker event; no payload. | No |
| J04195 | com/qcwireless/smart/base/event/DeviceToAppSyncEvent.java | active | sync_scheduler | EventBus event signaling device-to-app sync with type discriminator | `type` (int), `getType()`, `setType()` | MessageEvent | Device-to-app data sync flow | Sync:3 | Carries mutable `type` int — likely maps to data domain (HR, SpO2, sleep, etc.). **Key sync routing event.** | Yes — map `type` values to data domains |
| J04237 | com/qcwireless/smart/base/event/TodayDataSyncEvent.java | active | sync_scheduler | EventBus event signaling today's data sync status | `status` (boolean), `getStatus()` | MessageEvent | Today data sync flow | Sync:3 | Carries boolean `status`. Similar to DataSyncEvent but scoped to "today". | No |
| J04259 | com/qcwireless/smart/base/ktx/SystemServiceExtKt.java | active | battery\|bigdata\|spo2 | Kotlin extension functions for Android system service access | `getBatteryManager()`, `getConnectivityManager()`, `getTelephonyManager()`, `getAlarmManager()`, `getPowerManager()`, `getSensorManager()`, `getWifiManager()`, `getInputMethodManager()`, etc. (27 extension functions) | ContextCompat.getSystemService | Used throughout app for system service access | 73, Battery:8\|73:2\|battery:1 | Utility class; no domain logic. Provides type-safe system service getters. | No |
| J04263 | com/qcwireless/smart/base/ktx/ThreadExtKt$ktxRunOnBgSingleAnother$1.java | active | bigdata\|hr | SuspendLambda coroutine for background thread execution with job join | `invokeSuspend()`, `$job` field | kotlinx.coroutines (Job, CoroutineScope, SuspendLambda) | ThreadExtKt.ktxRunOnBgSingleAnother | 117:1 | Coroutine helper; joins a job before running. No domain logic. | No |
| J04269 | com/qcwireless/smart/base/lifecycle/QcLifeCycle.java | active | battery\|ble_connection\|sleep\|uart_small_data | Application ActivityLifecycleCallbacks — manages foreground/background transitions, BLE reconnect, battery query | `onActivityResumed()` — queries battery via `SimpleKeyReq((byte)3)`, posts `BatteryLowEvent`, triggers BLE reconnect via `DeviceReconnect`, `onActivityPaused()` — sets `ThreadManager.setSleepMin()`, `isForeground()` (Companion), `isBand()` | BleOperateManager, CommandHandle, SimpleKeyReq, BatteryRsp, EventBus, DeviceReconnect, ThreadManager, UserConfig | QCApplication (registers as lifecycle callback) | Battery:7\|BleOperateManager:5\|CommandHandle:2\|BaseRspCmd:2\|battery:2\|Sleep:1 | **Key orchestration file.** On resume: queries battery, posts BatteryLowEvent, triggers BLE reconnect if disconnected. On pause: sets thread sleep mode. Uses `SimpleKeyReq((byte)3)` for battery command. | Yes — trace DeviceReconnect and ThreadManager for full reconnect/sleep flow |
| J04270 | com/qcwireless/smart/base/permission/PermissionUtilKt.java | active | ble_connection | Kotlin utility for Android permission checks and requests | `hasBluetooth()`, `hasLocationPermission()`, `hasContactPermission()`, `hasCameraPermission()`, `hasSMSPermission()`, `hasCallPhonePermission()`, `hasBgLocationPermission()`, `requestAllPermission()`, `requestBluetooth()`, `requestLocation()` | XXPermissions library | Used throughout app for runtime permission gating | Bluetooth:4 | Utility class; no domain logic. Wraps XXPermissions library. | No |
| J04273 | com/qcwireless/smart/base/pref/UserConfig.java | active | battery\|bigdata\|ble_connection\|hr\|hrv_regular\|sleep\|spo2\|sync_scheduler\|temperature | Central user/device configuration singleton — 270+ fields covering all data domains | `hrvSupport`, `bloodOxygenSupport`, `heartRateInterval`, `temperature`, `supportSkinTemperature`, `newSleepProtocol`, `tpSleep`, `batteryLow`, `batteryWarmingOpen`, `lastSyncFromServerTime`, `lastSyncTodaySteps`, `lastTenMinSyncTime`, `deviceSupportList`, `deviceSupportListTouchOnly`, `bindDevice`, `isBindBand`, `deviceAddress`, `deviceName`, `loginStatus`, `userToken`, `uid`, `googleFit`, `chinaOnly`, `ringTouchOnly`, `ringLightDND`, `save()`, `getInstance()` | PreUtil, QCApplication, DateUtil | Referenced by nearly every class in the app for config state | Battery:28\|Sync:24\|Temperature:20\|Sleep:16\|battery:13\|Bluetooth:9\|Oxygen:8\|HeartRate:4\|heartRate:4\|heart:4\|hrv:4\|Hrv:4\|BloodOxygen:4\|bloodOxygen:4\|temperature:4\|73:2\|sync:1 | **Critical config hub.** Controls which data domains are active (hrvSupport, bloodOxygenSupport, temperature, etc.), sync timing (lastSyncFromServerTime, lastSyncTodaySteps, lastTenMinSyncTime), device support lists, and BLE connection state. | Yes — map all `deviceSupportList` values to feature flags |
| J04274 | com/qcwireless/smart/base/pref/UserConfigDAO.java | active | battery\|ble_connection\|hr\|hrv_regular\|sleep\|spo2\|sync_scheduler\|temperature | SharedPreferences DAO for UserConfig — read/save/clear operations | `readUserConfig()`, `saveUserConfig()`, `clear()`, preference key constants: `Action_hrvSupport`, `Action_bloodOxygenSupport`, `Action_heartRateIntervalSupport`, `Action_temperature`, `Action_newSleepProtocol`, `Action_batteryLow`, `Action_batteryWarmingOpen`, `Action_lastSyncFromServerTime`, `Action_lastSyncTodaySteps`, `Action_lastTenMinSyncTime`, `Action_Support_Function_list`, `Action_deviceSupportListTouchOnly` | SharedPreferences, PreUtil | UserConfig.save() / UserConfig.read() | Battery:19\|Sync:15\|Temperature:13\|Sleep:8\|battery:6\|Bluetooth:5\|Oxygen:5\|HeartRate:3\|Hrv:3\|BloodOxygen:3\|heartRate:2\|heart:2\|hrv:2\|bloodOxygen:2\|sleep:2\|temperature:2 | **Key persistence layer.** Maps all UserConfig fields to SharedPreferences keys. Preference key names reveal the canonical field naming convention. | No |
| J04282 | com/qcwireless/smart/base/utils/FileUtils.java | active | storage_db | File I/O utilities — read/write/copy files, URI path resolution | `readFile()`, `writeFile()`, `copyFile()`, `saveBitmap()`, `getSaveFile()`, `getSaveDir()`, `UriUtil` inner class with `getDataColumn()`, `getImagePath()`, `getRealPathApi19Above()` | ContentResolver, MediaStore, DocumentsContract | Used for file export/import, image saving, database file ops | 0x0063\|0x006d\|0x0077\|0x2000, database:1 | File utility; touches storage_db domain. Constants suggest protocol-related file operations. | No |
| J04283 | com/qcwireless/smart/base/utils/GetFilePathFromUri.java | active | storage_db | URI-to-filepath converter for Android content/document URIs | `getPath()`, `copyFile()`, `copyStream()` | ContentResolver, DocumentsContract, MediaStore | File picker/import flows | database:1 | Utility class; no domain logic. | No |
| J04288 | com/qcwireless/smart/base/utils/QcDateUtil.java | active | steps_sport | Date formatting utility for app-wide date display | `localDateFormat()`, `localDateNoYearFormat()`, `localDateNoDayFormat()`, `localDateYMDHMSFormat()`, `localDateYMDHMSFormatSport()`, `localDateFormatSport()`, `sportIsToday()`, `initStringArray()`, `monthShorthandList` | DateUtil, LanguageUtil, GlobalKt | Used for date display in sport/sleep/HR views | Sport:4\|sport:2 | Date formatting utility; no domain logic. | No |
| J04289 | com/qcwireless/smart/base/utils/ShellUtils.java | active | bigdata\|hr\|sleep\|spo2 | Shell command execution utility with root check | `execCommand()`, `checkRootPermission()`, `CommandResult` inner class | java.io.Process, BufferedReader | Debug/development tool | 0x0101\|0x0106\|0x010a\|0x010e\|0x0112\|0x012f\|0x0133\|0x0137\|0x013c\|0x0143\|0x0145\|0x0148\|0x0157\|0x015b\|0x015f\|0x0164\|0x016b\|0x0172\|0x0174\|0x017b\|0x0185\|0x0189\|0x018d\|0x0192\|0x019b\|39\|40\|44\|57\|60\|73\|95 | **Notable: contains many BLE protocol command IDs** (0x0101-0x019b range) plus numeric constants (39, 40, 44, 57, 60, 73, 95). These may be embedded in the decompiled output as switch case labels or constant arrays. | Yes — map the 0x01xx command IDs to BLE protocol operations |
| J04291 | com/qcwireless/smart/base/utils/TelephonyHelper.java | active | sync_scheduler | Phone call state monitoring utility | `CallStateListener` (interface), `onCallEnded()`, `onCallIdle()`, `onCallStateChanged()`, `listen()`, `stopListen()`, `previousState` | TelephonyManager, TelephonyCallback, PhoneStateListener | Call notification/push flow | sync:1 | Monitors phone call state for call notification push to device. | No |
| J05019 | com/qcwireless/smart/QCApplication.java | active | ble_connection\|uart_small_data | Main Application class — initializes Koin DI, BLE stack, receivers, Glide, OkDownload, skin engine | `onCreate()` → `initSkin()`, `init()`, `initReceiver()`, `initService()`, `initOkDownLoad()`, `initFindPhone()`, `initRTKSPP()`, `pingHwServer()`, `initGlide()`, `init()` → `startKoin { modules(KoinModuleKt.getAppModule()) }`, `defaultScan()`, `defaultScanBand()`, `defaultScanDevice()`, `findPhoneRspIOdmOpResponse`, `mediaRunnable` | BleOperateManager, BleBaseControl, BleAction, KoinModuleKt, BluetoothReceiver, MyBluetoothReceiver, UserConfig, PreUtil, SkinCompatManager, Glide, OkDownload | Android framework (Application entry point) | Bluetooth:7\|BleOperateManager:6\|BaseRspCmd:2 | **Top-level orchestration entry point.** Initializes entire app stack including Koin DI, BLE, receivers. Scan config keys: R01-R06, R11, VK-5098, MERLIN, Hello Ring, RING1, boAtring, Y25, H59. | No |
| J05020 | com/qcwireless/smart/QJavaApplication.java | active | sleep\|sync_scheduler | Java-side Application singleton — manages device scan keys, support CS list, and app state | `getInstance()`, `getDeviceKeys()`, `getKeysMap()`, `putDeviceScanKeys()`, `putScanKeysMap()`, `getListSupportCS()`, `cleanListCache()`, `filterKeysSize()`, `getAppLogPath()`, `getCurrDial()`, `getGpsType()` | PreUtil, DateUtil, SupportCsResp | QCApplication.init() | Sleep:2\|sync:1 | Manages BLE scan filter keys and device support CS list. Singleton pattern. | No |
| J05023 | com/qcwireless/smart/ui/activity/LoadingActivity.java | active | bigdata\|hr\|temperature | Splash/loading screen — routes to MainActivity or LoginGuideActivity | `onResume$lambda$0()` — checks `UserConfig.getLoginStatus()`, routes to MainActivity; checks `UserConfig.getUserToLoginFirst()`, routes to LoginGuideActivity | UserConfig, Intent, MainActivity, LoginGuideActivity | App launch flow | 106\|117\|119, 117:2\|119:2 | Routing activity; no domain logic. | No |
| J05024 | com/qcwireless/smart/ui/ui/activity/LoginGuideActivity.java | active | bigdata\|hr | Login/register guide screen — routes to LoginActivity or RegisterActivity | `setupViews()`, `onMessageEvent()` (EventBus subscriber for LoginSuccessEvent) | UserConfig, LoginActivity, RegisterActivity, LoginSuccessEvent, EventBus | App login flow | 117\|57, 117:2 | UI routing activity; no domain logic. | No |
| J05026 | com/qcwireless/smart/ui/activity/MainActivity$initDeviceRequestLocation$1$1.java | active | bigdata | Coroutine lambda for requesting device location and writing to BLE | `invokeSuspend()` — calls `DeviceSettingRepository.getDeviceLocation()`, collects Flow, calls `LargeDataHandler.writeLocation(lon, lat, address)` | DeviceSettingRepository, LargeDataHandler, UserConfig, PermissionUtilKt, MyLocationBean | MainActivity.initDeviceRequestLocation() | LargeDataHandler:2 | **BLE write orchestration.** Fetches location from server, writes to device via LargeDataHandler. Shows repository→BLE data flow pattern. | Yes — trace LargeDataHandler for full BLE write protocol |

---

## Function Dictionary Proposals

### 1. `koin_wire_repositoryModule`
- **Source file**: `com/qcwireless/smart/base/di/KoinModuleKt.java`
- **Domain**: DI / orchestration
- **Signature**: `Module getRepositoryModule()` → Koin Module
- **Behavior**: Registers 30+ singleton repositories via Koin `single { }` including HeartRateDetailRepository, BloodOxygenRepository, HRVRepository, SleepDetailRepository, TemperatureRepository, StepDetailRepository, SportPlusRepository, HealthyRepository, DeviceSettingRepository, DeviceBindRepository, OTARepository, WatchFaceRepository, MessagePushRepository, BloodPressureRepository, BloodSugarRepository, PressureRepository, MenstruationRepository, MuslimRepository, MuslimV2Repository, OneKeyCheckRepository, FeedbackRepository, ContactsRepository, MusicRepository, EbookRepository, RegisterRepository, LoginRepository, UserProfileRepository, FindPwdRepository, WebsocketRepository, FriendsRepository, LoverRepository
- **Key constants**: None (all repos instantiated with parameterless constructors)
- **Calls**: `ModuleKt.module()`, `module.declareDefinition()`
- **Called by**: `KoinModuleKt.getAppModule()`, which is called by `QCApplication.init()` via `startKoin { modules(...) }`

### 2. `koin_wire_viewModelModule`
- **Source file**: `com/qcwireless/smart/base/di/KoinModuleKt.java`
- **Domain**: DI / orchestration
- **Signature**: `Module getViewModelModule()` → Koin Module
- **Behavior**: Registers 50+ ViewModels via Koin `viewModel { }`, each injecting relevant repositories. Key health VMs:
  - `HealthyViewModel(HealthyRepository, StepDetailRepository, SleepDetailRepository, HeartRateDetailRepository, SportPlusRepository, WatchFaceRepository, BloodPressureRepository, BloodOxygenRepository, TemperatureRepository, BloodSugarRepository, PressureRepository, HRVRepository, MuslimRepository, MuslimV2Repository, FriendsRepository, UserProfileRepository)`
  - `HeartActivityViewModel(HeartRateDetailRepository, UserProfileRepository, DeviceSettingRepository)`
  - `HrvActivityViewModel(HRVRepository)`
  - `BloodOxygenViewModel(BloodOxygenRepository, DeviceSettingRepository)`
  - `DaySleepFragmentViewModel(SleepDetailRepository)`
  - `WeekSleepFragmentViewModel(SleepDetailRepository)`
  - `MonthSleepFragmentViewModel(SleepDetailRepository)`
  - `TemperatureViewModel(TemperatureRepository)`
- **Calls**: `ModuleKt.module()`, `ModuleExtKt.setIsViewModel()`
- **Called by**: `KoinModuleKt.getAppModule()`

### 3. `qclifecycle_onActivityResumed`
- **Source file**: `com/qcwireless/smart/base/lifecycle/QcLifeCycle.java`
- **Domain**: BLE connection / battery / lifecycle
- **Signature**: `void onActivityResumed(Activity activity)`
- **Behavior**: Increments foreground counter. When transitioning from background to foreground (mCount==1):
  1. If BLE connected: sends `SimpleKeyReq((byte)3)` to query battery, posts `BatteryLowEvent` via EventBus
  2. If BLE disconnected: sets reconnect MAC from UserConfig, calls `DeviceReconnect.connectWithScanValidation()`, wakes ThreadManager, resets updating flag
- **Key constants**: `SimpleKeyReq((byte) 3)` — battery query command
- **Calls**: `BleOperateManager.isConnected()`, `CommandHandle.executeReqCmd()`, `EventBus.post()`, `DeviceReconnect.connectWithScanValidation()`, `ThreadManager.wakeUpNotWait()`
- **Called by**: Android framework (ActivityLifecycleCallbacks)

### 4. `qclifecycle_onActivityPaused`
- **Source file**: `com/qcwireless/smart/base/lifecycle/QcLifeCycle.java`
- **Domain**: BLE connection / lifecycle
- **Signature**: `void onActivityPaused(Activity activity)`
- **Behavior**: Decrements foreground counter. When transitioning to background (mCount==0): sets `isForeground=false`, calls `ThreadManager.setSleepMin()` to reduce thread activity
- **Calls**: `ThreadManager.setSleepMin()`
- **Called by**: Android framework (ActivityLifecycleCallbacks)

### 5. `userconfig_getInstance`
- **Source file**: `com/qcwireless/smart/base/pref/UserConfig.java`
- **Domain**: Configuration / all health domains
- **Signature**: `UserConfig getInstance(Context)` / `UserConfig getInstance()` (singleton)
- **Behavior**: Returns singleton UserConfig instance. On first access, initializes from SharedPreferences via UserConfigDAO. Contains 270+ fields controlling all data domains:
  - HR: `heartRateInterval`, `hrvSupport`
  - SpO2: `bloodOxygenSupport`
  - Sleep: `newSleepProtocol`, `tpSleep`
  - Temperature: `temperature`, `supportSkinTemperature`, `noSingleTemperature`
  - Battery: `batteryLow`, `batteryWarmingOpen`
  - Sync: `lastSyncFromServerTime`, `lastSyncTodaySteps`, `lastTenMinSyncTime`
  - Device: `deviceSupportList`, `deviceSupportListTouchOnly`, `bindDevice`, `isBindBand`, `deviceAddress`, `ringTouchOnly`
- **Calls**: `UserConfigDAO.readUserConfig()`, `UserConfigDAO.saveUserConfig()`
- **Called by**: Nearly every class in the app

### 6. `userconfigdao_readUserConfig`
- **Source file**: `com/qcwireless/smart/base/pref/UserConfigDAO.java`
- **Domain**: Persistence / all health domains
- **Signature**: `void readUserConfig(UserConfig)`
- **Behavior**: Reads all UserConfig fields from SharedPreferences named "UserConfig_Preferences_Qc_1.0". Key preference keys:
  - HR: `Action_heartRateIntervalSupport`, `Action_hrvSupport`
  - SpO2: `Action_bloodOxygenSupport`
  - Sleep: `Action_newSleepProtocol`, `Action_tp_sleep`
  - Temperature: `Action_temperature`, `Action_supportSkinTemperature`, `Action_noSingleTemperature`
  - Battery: `Action_batteryLow`, `Action_batteryWarmingOpen`
  - Sync: `Action_lastSyncFromServerTime`, `Action_lastSyncTodaySteps`, `Action_lastTenMinSyncTime`
  - Device: `Action_Support_Function_list`, `Action_deviceSupportListTouchOnly`, `Action_bindDevice`
- **Calls**: `PreUtil.getSharedPreferences()`
- **Called by**: `UserConfig.getInstance()`

### 7. `userconfigdao_saveUserConfig`
- **Source file**: `com/qcwireless/smart/base/pref/UserConfigDAO.java`
- **Domain**: Persistence / all health domains
- **Signature**: `void saveUserConfig(UserConfig)`
- **Behavior**: Writes all UserConfig fields to SharedPreferences. Mirror of readUserConfig.
- **Calls**: `PreUtil.getSharedEditor()`
- **Called by**: `UserConfig.save()`

### 8. `qcapplication_onCreate`
- **Source file**: `com/qcwireless/smart/QCApplication.java`
- **Domain**: App initialization / BLE / DI
- **Signature**: `void onCreate()`
- **Behavior**: Application entry point. Initializes:
  1. UserConfig singleton
  2. XLog logging
  3. Skin engine (`initSkin()`)
  4. Koin DI with `KoinModuleKt.getAppModule()` (`init()`)
  5. BLE receiver (`initReceiver()`) — registers BluetoothReceiver, SystemLocaleChangeReceiver
  6. BLE service stub (`initService()` — empty)
  7. OkDownload (`initOkDownLoad()`)
  8. Find phone BLE listener (`initFindPhone()`) — adds notify listener for command ID 34
  9. RTK SPP (`initRTKSPP()`)
  10. Server ping (`pingHwServer()`)
  11. Glide image loading (`initGlide()`)
  12. LogToFile
- **Key constants**: BLE notify listener ID `34` (find phone response)
- **Calls**: `startKoin()`, `KoinModuleKt.getAppModule()`, `BleOperateManager.addNotifyListener()`, `BleBaseControl.setmContext()`
- **Called by**: Android framework

### 9. `deviceToAppSyncEvent_type`
- **Source file**: `com/qcwireless/smart/base/event/DeviceToAppSyncEvent.java`
- **Domain**: Sync orchestration
- **Signature**: `int getType()` / `void setType(int)`
- **Behavior**: EventBus event carrying a mutable `type` integer that discriminates which data domain is being synced from device to app. Likely maps to domain-specific sync handlers.
- **Calls**: None
- **Called by**: Sync orchestration code (outside this chunk)

### 10. `deviceHeartChangeEvent_heart`
- **Source file**: `com/qcwireless/smart/base/event/DeviceHeartChangeEvent.java`
- **Domain**: HR
- **Signature**: `int getHeart()`
- **Behavior**: EventBus event carrying real-time heart rate value from device. Used for live HR display updates.
- **Calls**: None
- **Called by**: BLE response handlers, HR display fragments

### 11. `mainactivity_initDeviceRequestLocation`
- **Source file**: `com/qcwireless/smart/ui/activity/MainActivity$initDeviceRequestLocation$1$1.java`
- **Domain**: BLE connection / location
- **Signature**: `Object invokeSuspend(Object)` (SuspendLambda)
- **Behavior**: Coroutine that:
  1. Calls `DeviceSettingRepository.getDeviceLocation(deviceAddressNoClear)` — gets location from server
  2. Collects the Flow result
  3. Truncates address string if >100 bytes
  4. If location permission granted, calls `LargeDataHandler.writeLocation(longitude, latitude, address)` — writes location to BLE device
- **Calls**: `DeviceSettingRepository.getDeviceLocation()`, `LargeDataHandler.writeLocation()`, `PermissionUtilKt.hasLocationPermission()`
- **Called by**: `MainActivity.initDeviceRequestLocation()`

### 12. `qcapplication_defaultScan`
- **Source file**: `com/qcwireless/smart/QCApplication.java`
- **Domain**: BLE connection / device support
- **Signature**: `void defaultScan()` / `void defaultScanBand()` / `void defaultScanDevice()`
- **Behavior**: Sets BLE scan filter keys in SharedPreferences:
  - `defaultScan()`: R01,R02,R03,VK-5098,MERLIN,Hello Ring,RING1,boAtring,R04,R05,R06,R11
  - `defaultScanBand()`: Y25,H59
  - `defaultScanDevice()`: all of the above combined
- **Key constants**: Device model codes: R01-R06, R11, VK-5098, MERLIN, Hello Ring, RING1, boAtring, Y25, H59
- **Calls**: `PreUtil.putString()`, `QJavaApplication.putDeviceScanKeys()`, `QJavaApplication.putScanKeysMap()`
- **Called by**: Device type detection flows

---

## Event Bus Taxonomy

All 12 event classes extend `MessageEvent` and are dispatched via `EventBus.getDefault().post()`:

| Event | Payload | Domain | Purpose |
|---|---|---|---|
| BatteryIsChargingEvent | none | battery | Battery charging state changed |
| BatteryLowEvent | none | battery | Low battery warning |
| BluetoothEvent | boolean connect | ble_connection | BLE connection state |
| BluetoothInitDeviceEvent | none | ble_connection | BLE device initialized |
| BluetoothSppEvent | boolean connect | ble_connection | SPP connection state |
| BluetoothSyncEvent | none | ble_connection + sync | BLE sync trigger |
| DataSyncEvent | boolean status | sync_scheduler | Data sync in-progress/complete |
| DeviceHeartChangeEvent | int heart | hr | Real-time HR value from device |
| DeviceSyncEvent | none | sync_scheduler | Device sync trigger |
| DeviceSyncTodayStepsAndDetailEvent | none | sync_scheduler | Steps+detail sync complete |
| DeviceSyncTodayStepsEvent | none | sync_scheduler | Steps sync complete |
| DeviceToAppSyncEvent | int type (mutable) | sync_scheduler | **Domain-routed sync event** |
| TodayDataSyncEvent | boolean status | sync_scheduler | Today data sync status |

---

## Key Findings

1. **KoinModuleKt is the definitive DI wiring manifest** — it registers all health data repositories (HR, SpO2, HRV, Sleep, Temperature, Steps, Sport, BloodPressure, BloodSugar, Pressure) as singletons and injects them into the corresponding ViewModels.

2. **Repository implementations are parameterless singletons** — the actual BLE sync orchestration logic (command dispatch, data parsing, database writes) lives inside the repository classes themselves, not in the DI module. These repositories must be traced in other chunks.

3. **QcLifeCycle is a key orchestration trigger** — on app resume, it queries battery via BLE command `SimpleKeyReq((byte)3)` and triggers BLE reconnect if disconnected. This is the primary foreground/background state machine.

4. **UserConfig is the central feature flag store** — fields like `hrvSupport`, `bloodOxygenSupport`, `temperature`, `newSleepProtocol`, `deviceSupportList` control which data domains are active. These flags are likely set during device capability negotiation after BLE connection.

5. **DeviceToAppSyncEvent.type is the sync routing mechanism** — the mutable `int type` field likely maps to specific data domains (HR=0x30, SpO2=0x39, etc.) and is used to route sync responses to the correct repository/handler.

6. **ShellUtils contains embedded BLE protocol command IDs** — the 0x0101-0x019b range constants in the ledger suggest this file may contain switch-case logic for BLE command routing, though the decompiled output is heavily obfuscated by JADX.

7. **QCApplication.init() wires the complete app stack** — Koin DI, BLE receivers, BLE base control, scan config, find-phone listener (command ID 34), RTK SPP, and server connectivity check.

8. **EventBus is the inter-component communication backbone** — all sync triggers, BLE state changes, and data updates flow through EventBus events extending MessageEvent.

---

## Assumptions

- `DeviceToAppSyncEvent.type` integer values map to BLE protocol command IDs or data domain identifiers — this mapping needs verification from sync handler code in other chunks.
- `SimpleKeyReq((byte)3)` is the battery query command — confirmed by the response being cast to `BatteryRsp`.
- The `0x01xx` constants in ShellUtils are BLE protocol command IDs embedded in switch-case logic — the decompiled output is too obfuscated to confirm directly.
- `UserConfig.deviceSupportList` and `deviceSupportListTouchOnly` are comma-separated strings of feature flags — the exact format needs verification from their setter code.
- The `LargeDataHandler.writeLocation()` method writes location data to the BLE device via the large data transfer protocol — this is the reverse-direction BLE write pattern (app→device).
