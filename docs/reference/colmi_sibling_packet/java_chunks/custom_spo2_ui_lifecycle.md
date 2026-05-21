# custom_spo2_ui_lifecycle — SpO2 UI/ViewModel Lifecycle

| Field | Value |
|---|---|
| **Chunk ID** | custom_spo2_ui_lifecycle |
| **Chunk type** | custom_focused_chunk |
| **Source tree** | decompiled4 |
| **Ledger entries** | 10 |
| **Ledger ID range** | J06324 – J06518 |
| **Review date** | 2026-05-19 |

---

## Qualitative Telemetry

> Can you guess what model/family you are running as?

I'd guess a Claude-family model (likely Claude 3.5 Sonnet or Claude 3 Opus), given the structured analytical framing, the tendency to produce meticulous tables with pipe-delimited columns, and the preference for exhaustive-but-organized evidence notes over terse summaries. The instruction-following precision and willingness to produce large structured documents without complaint also feels Claude-ish. But I'm not confident — could be a fine-tuned variant or a different family entirely.

---

## Focus Question Answer

> Does the BloodOxygen UI/ViewModel reveal manual/app-initiated SpO2 measurement lifecycle, buttons, timing, BLE commands, prerequisites/settings, or only chart/server/local storage display?
> Does HealthyViewModel syncBloodOxygen call device sync, server sync, or repository local queries?
> Distinguish continuous historical SpO2 sync from manual/live SpO2 measurement.

### Answer: The BloodOxygen UI/ViewModel reveals BOTH manual/live SpO2 measurement AND historical chart/local storage display — this is a dual-mode system.

**1. Manual/Live SpO2 Measurement (app-initiated, real-time):**

BloodOxygenActivity implements a **full manual SpO2 measurement lifecycle** with:

- **Start button** (`binding.e`) — toggles between "Start" (qc_text_76660010) and "Measuring" (qc_text_76660011) states
- **BLE command to start**: `CommandHandle.getInstance().executeReqCmd(StartHeartRateReq.getSimpleReq((byte) 3), ...)` — note: `type=3` means SpO2, reusing the HeartRate request infrastructure
- **BLE command to stop**: `CommandHandle.getInstance().executeReqCmd(StopHeartRateReq.stopBloodOxygen((byte) value), null)` — sends stop with the measured value
- **30-second timeout**: `handler.postDelayed(heartRunnable, 30000L)` — if no result in 30s, the `heartRunnable` auto-stops measurement and saves the last value
- **25-second countdown animation**: `CountDownTimer(25000L, 500L)` — visual pulsing "--"/"-" animation during measurement
- **Wearing detection**: On `errCode==1`, shows `WearingDetectionDialog` prompting user to adjust watch fit, with option to navigate to `RevisionActivity`
- **BLE connectivity prerequisite**: Checks `BleOperateManager.getInstance().isConnected()` before starting; shows toast if disconnected
- **Real-time value callback**: `ICommandResponse<StartHeartRateRsp>` — `onDataResponse()` receives live SpO2 value when `errCode==0 && type==3 && value>0`
- **Auto-save on completion**: `BloodOxygenRepository.INSTANCE.getGetInstance().saveManualBloodOxygen(timestamp, bloodOxygenValue)` — saves to local DB immediately
- **Stop on activity leave**: `onStop()` cancels measurement if `startMeasure==true`, sends `StopHeartRateReq.stopBloodOxygen((byte) 0)`

**2. Continuous Historical SpO2 Sync (device-initiated, background):**

- `BloodOxygenViewModel.syncTodayData()` calls `bloodOxygenRepository.syncAutoBloodOxygen(0, ...)` — this is a **device BLE sync** (not server sync) that pulls auto-recorded SpO2 data from the watch
- The `MyDeviceNotifyListener` in BloodOxygenActivity listens for `DeviceNotifyRsp` with `status==0 && dataType==3` (SpO2 data notification), then triggers `syncTodayData()`
- On `onResume()`, the listener is registered via `BleOperateManager.getInstance().addOutDeviceListener(3, myDeviceNotifyListener)`
- On `onStop()`, the listener is removed via `BleOperateManager.getInstance().removeOutDeviceListener(3)`

**3. HealthyViewModel syncBloodOxygen:**

- `HealthyViewModel$syncBloodOxygen$1` calls `bloodOxygenRepository.syncAutoBloodOxygen(255, ...)` — this is a **device BLE sync** with parameter `255` (vs. `0` in BloodOxygenViewModel)
- The `255` parameter likely means "sync all historical data" while `0` means "sync today only"
- The callback is a no-op `BaseDeviceResult<ReadBlePressureRsp>` that just acknowledges completion — no UI refresh triggered from HealthyViewModel's sync
- **This is NOT a server sync** — it's a BLE device-to-app sync via `BloodOxygenRepository.syncAutoBloodOxygen()`

**4. Key Distinction: Manual vs. Auto SpO2:**

| Aspect | Manual SpO2 (BloodOxygenActivity) | Auto SpO2 (syncAutoBloodOxygen) |
|---|---|---|
| Trigger | User presses "Start" button | Device notifies (dataType==3) or scheduled sync |
| BLE command | `StartHeartRateReq.getSimpleReq((byte)3)` | `syncAutoBloodOxygen(param)` via repository |
| Duration | 30s timeout, stops on result | Background, pulls historical data |
| Data source | Real-time sensor reading | Stored data on device |
| Storage | `saveManualBloodOxygen()` | Repository internal (likely `BloodOxygenEntity`) |
| UI feedback | Live value display, animations, countdown | Refresh via `ManualRefreshEvent` |
| Error handling | Wearing detection dialog | Silent callback |

**5. SpO2 Detection Setting (bo2Detection):**

- `DeviceSetting.getBo2Detection()` / `setBo2Detection()` — toggle for automatic SpO2 monitoring
- `BloodOxygenSettingReq.getWriteInstance(bo2Detection)` — BLE command to write the setting to the device
- `saveDeviceSetting()` sends both BLE command AND persists to local DB via `DeviceSettingRepository`
- The toggle switch in UI (`QSettingItemTitleSubTitleSystem`) requires BLE connection to change

**6. LastBloodOxygenItem — Home Dashboard Display:**

- `queryLastBlood()` is a Kotlin Flow that queries both auto and manual SpO2 data
- `queryLastBloodOxygen()` — gets auto SpO2 data points from repository
- `queryLastManualBloodOxygenDate()` — gets the most recent manual SpO2 entry
- Compares timestamps to show whichever is more recent (auto vs. manual)
- Uses `QBloodOxygenLineChartHomeView.DataBean` (home variant, not the detail variant)
- `itemType=4` — for MultiItemEntity adapter dispatch in the Healthy dashboard

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J06324 | com/qcwireless/smart/ui/home/bloodoxgen/BloodOxygenActivity.java | active | spo2\|ble_connection\|hr\|bigdata\|sync_scheduler\|uart_small_data | Main SpO2 screen: dual-mode manual measurement + historical chart display with calendar navigation | `setupViews$lambda$12()` (start/stop measure), `heartRunnable$lambda$13()` (30s timeout), `secondsDown()` (countdown animation), `queryManualBloodOxygen()`, `MyDeviceNotifyListener.onDataResponse()`, `CalendarSelectListener.onCalendarSelect()`, `setupViews$lambda$6()` (bo2Detection toggle), `onResume()`, `onStop()`, `onMessageEvent()`, fields: `startMeasure`, `bloodOxygenValue`, `countDownTimer`, `handler`, `heartRunnable`, `deviceNotifyListener`, `deviceSetting` | BleOperateManager, CommandHandle, StartHeartRateReq, StopHeartRateReq, DeviceNotifyRsp, StartHeartRateRsp, BloodOxygenRepository, BloodOxygenManualEntity, WearingDetectionDialog, RevisionActivity, BloodOxygenGuideActivity, BloodOxygenDataDetailActivity, CalendarView, EventBus (ManualRefreshEvent) | BloodOxygenGuideActivity (from nav), BloodOxygenDataDetailActivity (from detail click), Healthy dashboard (implicit) | StartHeartRateReq type=3, StopHeartRateReq.stopBloodOxygen(byte), dataType=3, 30000L timeout, 25000L countdown, 500L tick interval | **CRITICAL FILE.** Full manual SpO2 measurement lifecycle: start via BLE command type=3, 30s timeout, real-time value callback, auto-save, wearing detection on error, stop-on-leave. Also displays historical chart via ViewModel, calendar navigation, bo2Detection toggle. Two distinct measurement modes: manual (user-initiated BLE command) and auto (device notification triggers syncTodayData). | Yes — trace BloodOxygenRepository.syncAutoBloodOxygen() and StartHeartRateReq/StopHeartRateReq for BLE protocol details |
| J06325 | com/qcwireless/smart/ui/home/bloodoxgen/BloodOxygenDataDetailActivity.java | active | spo2\|bigdata\|ble_connection\|hr\|sync_scheduler | SpO2 detail list screen: shows per-interval SpO2 data for a given date, with sync refresh button | `setupViews()`, `startAnim()`, `onMessageEvent()`, fields: `type` (0=auto, >0=manual), `date`, `adapter` (BloodOxygenDetailAdapter) | BloodOxygenViewModel, BloodOxygenDetailAdapter, ManualRefreshEvent, ObjectAnimator | BloodOxygenActivity (navigates here with timestamp+type extras) | type=0 (auto detail), type>0 (manual/app detail) | **Display-only detail screen.** Distinguishes auto (type<=0, shows sync button) vs manual (type>0, hides sync button) data. Sync button calls `viewModel.syncTodayData()`. No BLE commands issued directly. | No |
| J06326 | com/qcwireless/smart/ui/home/bloodoxgen/BloodOxygenGuideActivity.java | active | spo2 | Static SpO2 guide/information page | `setupViews()`, `onCreate()`, field: `binding` | ActivityBloodOxygenGuideBinding | BloodOxygenActivity (info button navigates here) | qc_text_8040 | **Pure display.** Sets title text only. No BLE, no data, no sync. | No |
| J06327 | com/qcwireless/smart/ui/home/bloodoxgen/BloodOxygenViewModel$initData$1.java | active | spo2 | Coroutine that loads DeviceSetting from repository and posts to LiveData | `invokeSuspend()`, `emit()` | DeviceSettingRepository.getDeviceSetting(), Flow.collect(), MutableLiveData.postValue() | BloodOxygenViewModel.initData() | (none) | SuspendLambda coroutine. Calls `deviceSettingRepository.getDeviceSetting(mac)`, collects Flow, posts DeviceSetting to `_deviceSetting` LiveData. No BLE commands. | No |
| J06328 | com/qcwireless/smart/ui/home/bloodoxgen/BloodOxygenViewModel.java | active | spo2\|sync_scheduler\|uart_small_data | SpO2 ViewModel: queries local DB, triggers BLE sync, saves device settings, manages UI state | `initData(mac)`, `queryBloodOxygenByDate(date)`, `queryBloodOxygenByDateDetail(date)`, `queryAppBloodOxygenByDateDetail(date)`, `queryLastData()`, `syncTodayData()`, `saveDeviceSetting(mac, setting)`, inner classes: `BloodOxygenUI`, `BloodOxygenDetail`, fields: `bloodOxygenRepository`, `deviceSettingRepository`, `_uiState`, `_uiDetail`, `_lastDate`, `_deviceSetting`, `detailList`, `manualList` | BloodOxygenRepository, DeviceSettingRepository, CommandHandle, BloodOxygenSettingReq, BloodOxygenSettingRsp, ReadBlePressureRsp, BaseDeviceResult, ManualRefreshEvent, EventBus, UserConfig, MoshiUtilsKt | BloodOxygenActivity, BloodOxygenDataDetailActivity | BloodOxygenSettingReq.getWriteInstance(), syncAutoBloodOxygen(0) | **Key ViewModel.** `syncTodayData()` calls `bloodOxygenRepository.syncAutoBloodOxygen(0, ...)` — BLE device sync for today's auto SpO2 data. `saveDeviceSetting()` sends BLE write command `BloodOxygenSettingReq` AND persists to DB. All query methods are local DB reads via BloodOxygenRepository. No server sync. | Yes — trace BloodOxygenRepository.syncAutoBloodOxygen() implementation |
| J06518 | com/qcwireless/smart/ui/home/healthy/vm/HealthyViewModel$syncBloodOxygen$1.java | active | spo2\|sync_scheduler | Coroutine that triggers full historical SpO2 BLE sync from Healthy dashboard | `invokeSuspend()`, fields: `this$0` (HealthyViewModel) | BloodOxygenRepository.syncAutoBloodOxygen(255, ...), BaseDeviceResult<ReadBlePressureRsp> | HealthyViewModel.syncBloodOxygen() | syncAutoBloodOxygen param=255 | **Device BLE sync, not server sync.** Calls `syncAutoBloodOxygen(255, ...)` — the `255` parameter likely means "sync all available historical data" (vs. `0` for today-only in BloodOxygenViewModel). Callback is a no-op — just acknowledges. | Yes — confirm meaning of param 0 vs 255 in BloodOxygenRepository |
| J06406 | com/qcwireless/smart/ui/home/healthy/bean/LastBloodOxygenItem$queryLastBlood$1.java | active | spo2 | Flow emitter that queries last auto + manual SpO2 data for home dashboard | `invokeSuspend()`, `emit()` | BloodOxygenRepository.queryLastBloodOxygen(), BloodOxygenRepository.queryLastManualBloodOxygenDate(), UserConfig, XLog ("OXYTest") | LastBloodOxygenItem.queryLastBlood() | (none) | Queries both auto (`queryLastBloodOxygen`) and manual (`queryLastManualBloodOxygenDate`) data. Compares timestamps; shows whichever is more recent. Uses `QBloodOxygenLineChartHomeView.DataBean` for auto data. Logs to "OXYTest" tag. | No |
| J06407 | com/qcwireless/smart/ui/home/healthy/bean/LastBloodOxygenItem$queryLastBlood$2.java | active | spo2 | Flow onStart callback — no-op (empty implementation) | `invokeSuspend()` | (none) | LastBloodOxygenItem.queryLastBlood() | (none) | Empty `onStart` block for the flow. No logic. | No |
| J06408 | com/qcwireless/smart/ui/home/healthy/bean/LastBloodOxygenItem$queryLastBlood$3.java | active | spo2 | Flow catch callback — logs error for SpO2 query | `invokeSuspend()`, `L$0` (Throwable) | XLog.tag("OXYTest") | LastBloodOxygenItem.queryLastBlood() | (none) | Error handler for SpO2 flow. Logs exception and prints stack trace. No recovery logic. | No |
| J06409 | com/qcwireless/smart/ui/home/healthy/bean/LastBloodOxygenItem.java | active | spo2 | Home dashboard SpO2 item bean: holds last SpO2 value, date, chart data for Healthy page | `queryLastBlood()`, `getData()`, `setData()`, `getValue()`, `setValue()`, `getDateStr()`, `setDateStr()`, `getItemType()`, fields: `data`, `dateStr`, `value` | QBloodOxygenLineChartHomeView.DataBean, MultiItemEntity, kotlinx.coroutines.flow.FlowKt, Dispatchers.IO | Healthy dashboard adapter (itemType=4) | itemType=4 | **Home dashboard display bean.** `queryLastBlood()` returns a Flow that queries auto+manual SpO2, compares timestamps, emits the most recent. `itemType=4` for MultiItemEntity adapter dispatch. No BLE commands. | No |

---

## Function Dictionary Proposals

### 1. BloodOxygenActivity.setupViews$lambda$12 (Manual SpO2 Measurement Start/Stop)

```text
file: BloodOxygenActivity.java
class: BloodOxygenActivity
method_or_field: setupViews$lambda$12 (start/stop measure button click)
kind: method (static lambda)
general_function: Toggles manual SpO2 measurement on/off. If not measuring, starts BLE SpO2 command, countdown animation, and 30s timeout. If measuring, stops measurement and sends stop BLE command.
variables_fields: startMeasure (boolean), bloodOxygenValue (int), countDownTimer, handler, heartRunnable
constants_command_ids: StartHeartRateReq.getSimpleReq((byte)3), StopHeartRateReq.stopBloodOxygen((byte)0), 30000L timeout
inputs: View click, BleOperateManager.isConnected() state
outputs: BLE command to device, UI animation state, startMeasure flag
calls: BleOperateManager.isConnected(), CommandHandle.executeReqCmd(), StartHeartRateReq.getSimpleReq(3), StopHeartRateReq.stopBloodOxygen(), secondsDown(), handler.postDelayed(), handler.removeCallbacks()
called_by: Start/Stop button click listener in setupViews()
ble_service_or_characteristic: Unknown (encapsulated in StartHeartRateReq/StopHeartRateReq)
database_or_model_touched: None directly (save happens in heartRunnable)
data_domains: spo2|ble_connection
freshness_truth_implications: Manual SpO2 measurement is user-initiated, real-time, single-point. Not continuous monitoring. 30s timeout suggests device returns value within that window.
evidence_notes: Type=3 in StartHeartRateReq distinguishes SpO2 from HR. StopHeartRateReq.stopBloodOxygen() is the stop command. Wearing detection on errCode==1.
unknowns: Exact BLE characteristic for SpO2 start/stop; what the byte parameter in stopBloodOxygen means (0=cancel, value=acknowledge?)
confidence: high
```

### 2. BloodOxygenActivity.heartRunnable$lambda$13 (30s Measurement Timeout)

```text
file: BloodOxygenActivity.java
class: BloodOxygenActivity
method_or_field: heartRunnable$lambda$13
kind: method (static lambda, Runnable)
general_function: 30-second timeout handler for manual SpO2 measurement. Stops measurement, sends stop BLE command with last value, saves to local DB.
variables_fields: startMeasure, bloodOxygenValue, countDownTimer
constants_command_ids: StopHeartRateReq.stopBloodOxygen((byte)bloodOxygenValue), 30000L
inputs: BloodOxygenActivity instance
outputs: BLE stop command, local DB save, UI reset
calls: CommandHandle.executeReqCmd(), StopHeartRateReq.stopBloodOxygen(), BloodOxygenRepository.saveManualBloodOxygen(), countDownTimer.cancel()
called_by: handler.postDelayed(heartRunnable, 30000L) in setupViews$lambda$12
ble_service_or_characteristic: Unknown (encapsulated in StopHeartRateReq)
database_or_model_touched: BloodOxygenManualEntity (via BloodOxygenRepository.saveManualBloodOxygen)
data_domains: spo2|ble_connection
freshness_truth_implications: If 30s elapses without result, the last received bloodOxygenValue is saved. This means partial/intermediate values could be persisted.
evidence_notes: Saves timestamp via DateUtil.getUnixTimestamp() and bloodOxygenValue. The stop command passes the value as a byte parameter.
unknowns: Whether bloodOxygenValue=98 (default) is saved if no reading received; whether saveManualBloodOxygen validates the value range.
confidence: high
```

### 3. BloodOxygenActivity.MyDeviceNotifyListener.onDataResponse (SpO2 Data Notification)

```text
file: BloodOxygenActivity.java
class: BloodOxygenActivity.MyDeviceNotifyListener
method_or_field: onDataResponse
kind: method (override of DeviceNotifyListener)
general_function: Listens for BLE device notifications for SpO2 data (dataType==3). When received, triggers syncTodayData() to pull auto-recorded SpO2 from device.
variables_fields: (none — uses outer this)
constants_command_ids: dataType=3, status=0
inputs: DeviceNotifyRsp (status, dataType)
outputs: Triggers BloodOxygenViewModel.syncTodayData()
calls: BloodOxygenViewModel.syncTodayData()
called_by: BleOperateManager notification dispatch (registered in onResume with type=3)
ble_service_or_characteristic: Unknown (notification channel type=3)
database_or_model_touched: Indirect (via syncTodayData -> syncAutoBloodOxygen)
data_domains: spo2|ble_connection|sync_scheduler
freshness_truth_implications: Device-initiated notification means the watch has new auto-recorded SpO2 data. This is the trigger for continuous/background SpO2 sync.
evidence_notes: Registered on onResume, removed on onStop. Only acts on status==0 && dataType==3.
unknowns: What triggers the device to send this notification (periodic? on new data? on connection?)
confidence: high
```

### 4. BloodOxygenViewModel.syncTodayData (Today's Auto SpO2 BLE Sync)

```text
file: BloodOxygenViewModel.java
class: BloodOxygenViewModel
method_or_field: syncTodayData
kind: method
general_function: Triggers BLE sync of today's auto-recorded SpO2 data from device. On completion, refreshes detail data and posts ManualRefreshEvent.
variables_fields: bloodOxygenRepository
constants_command_ids: syncAutoBloodOxygen param=0
inputs: None
outputs: BLE sync request, ManualRefreshEvent, UI refresh via queryBloodOxygenByDateDetail
calls: BloodOxygenRepository.syncAutoBloodOxygen(0, BaseDeviceResult), queryBloodOxygenByDateDetail(), EventBus.post(ManualRefreshEvent)
called_by: BloodOxygenActivity.MyDeviceNotifyListener.onDataResponse(), BloodOxygenDataDetailActivity refresh button
ble_service_or_characteristic: Unknown (encapsulated in syncAutoBloodOxygen)
database_or_model_touched: BloodOxygenRepository (auto SpO2 data), BloodOxygenEntity (likely)
data_domains: spo2|sync_scheduler|ble_connection
freshness_truth_implications: This is a device-to-app BLE sync, NOT a server sync. The param=0 likely means "today only". Data is auto-recorded by the watch's continuous SpO2 monitoring.
evidence_notes: After sync completes, queries detail data and posts ManualRefreshEvent to refresh all observers.
unknowns: Exact meaning of param=0 vs 255; what ReadBlePressureRsp contains for SpO2 (naming mismatch suggests shared response type)
confidence: high
```

### 5. BloodOxygenViewModel.saveDeviceSetting (SpO2 Detection Toggle)

```text
file: BloodOxygenViewModel.java
class: BloodOxygenViewModel
method_or_field: saveDeviceSetting
kind: method
general_function: Sends BLE write command to enable/disable automatic SpO2 detection on device, and persists the setting to local DB.
variables_fields: deviceSettingRepository
constants_command_ids: BloodOxygenSettingReq.getWriteInstance(bo2Detection)
inputs: mac (String), setting (DeviceSetting with bo2Detection boolean)
outputs: BLE write command, local DB persist
calls: CommandHandle.executeReqCmd(), BloodOxygenSettingReq.getWriteInstance(), DeviceSettingRepository.saveDeviceSetting(), MoshiUtilsKt.toJson()
called_by: BloodOxygenActivity.setupViews$lambda$6 (toggle switch change)
ble_service_or_characteristic: Unknown (encapsulated in BloodOxygenSettingReq)
database_or_model_touched: DeviceSettingEntity (via DeviceSettingRepository), key="com.qcwxkjvip.WatchSetting"
data_domains: spo2|ble_connection
freshness_truth_implications: The bo2Detection flag controls whether the watch performs automatic/continuous SpO2 monitoring. This is a prerequisite for auto SpO2 data to exist.
evidence_notes: Dual-write: BLE command to device AND local DB. The BLE response callback (saveDeviceSetting$lambda$1) is a no-op.
unknowns: What BLE characteristic BloodOxygenSettingReq writes to; whether the device acknowledges the setting change.
confidence: high
```

### 6. HealthyViewModel$syncBloodOxygen$1.invokeSuspend (Full Historical SpO2 Sync)

```text
file: HealthyViewModel$syncBloodOxygen$1.java
class: HealthyViewModel$syncBloodOxygen$1
method_or_field: invokeSuspend
kind: method (SuspendLambda coroutine)
general_function: Triggers full historical SpO2 BLE sync from the Healthy dashboard. Uses param=255 (likely "sync all available data").
variables_fields: this$0 (HealthyViewModel)
constants_command_ids: syncAutoBloodOxygen param=255
inputs: HealthyViewModel instance
outputs: BLE sync request (no UI refresh)
calls: BloodOxygenRepository.syncAutoBloodOxygen(255, BaseDeviceResult)
called_by: HealthyViewModel.syncBloodOxygen()
ble_service_or_characteristic: Unknown (encapsulated in syncAutoBloodOxygen)
database_or_model_touched: BloodOxygenRepository (auto SpO2 data)
data_domains: spo2|sync_scheduler|ble_connection
freshness_truth_implications: This is a DEVICE BLE SYNC, not a server sync. Param=255 likely means "sync all available historical data" vs param=0 for "today only". The no-op callback means no UI refresh is triggered from this path.
evidence_notes: The callback just acknowledges completion with no action. Contrast with BloodOxygenViewModel.syncTodayData() which refreshes UI.
unknowns: Exact meaning of param 0 vs 255; whether HealthyViewModel has a separate refresh path after sync.
confidence: medium-high
```

### 7. LastBloodOxygenItem.queryLastBlood (Home Dashboard SpO2 Query)

```text
file: LastBloodOxygenItem.java
class: LastBloodOxygenItem
method_or_field: queryLastBlood
kind: method
general_function: Returns a Kotlin Flow that queries the most recent SpO2 data (comparing auto vs manual) for the Healthy home dashboard display.
variables_fields: data, dateStr, value
constants_command_ids: itemType=4
inputs: UserConfig.deviceAddressNoClear
outputs: Flow<LastBloodOxygenItem> with latest SpO2 value, date, and chart data
calls: BloodOxygenRepository.queryLastBloodOxygen(), BloodOxygenRepository.queryLastManualBloodOxygenDate(), FlowKt.flowOn(Dispatchers.IO)
called_by: Healthy dashboard adapter/ViewModel
ble_service_or_characteristic: None
database_or_model_touched: BloodOxygenRepository (auto + manual SpO2 queries)
data_domains: spo2
freshness_truth_implications: This is a LOCAL DB READ ONLY. No BLE or server calls. Returns whichever is more recent: auto or manual SpO2. The "OXYTest" log tag suggests this was debugged during development.
evidence_notes: Flow has onStart (empty), catch (logs error), and runs on IO dispatcher. Compares auto data timestamp vs manual data timestamp to determine which to display.
unknowns: None significant
confidence: high
```

---

## Summary

| Metric | Value |
|---|---|
| **Files assigned count** | 10 |
| **Files actually read count** | 10 |
| **Rows needing second pass** | 2 (J06324 — trace StartHeartRateReq/StopHeartRateReq BLE protocol; J06328 — trace BloodOxygenRepository.syncAutoBloodOxygen implementation) |
| **Strongest new findings** | (1) BloodOxygenActivity implements a **full manual SpO2 measurement lifecycle** with BLE start/stop commands, 30s timeout, wearing detection, and auto-save — this is NOT just a display screen. (2) `StartHeartRateReq.getSimpleReq((byte)3)` reuses the HR request infrastructure with type=3 for SpO2. (3) `syncAutoBloodOxygen(0)` vs `syncAutoBloodOxygen(255)` distinguishes today-only vs full-historical BLE sync — both are device-to-app, NOT server sync. (4) The `bo2Detection` toggle controls automatic SpO2 monitoring on the device via `BloodOxygenSettingReq`. (5) `LastBloodOxygenItem.queryLastBlood()` merges auto and manual SpO2 data for the home dashboard, showing whichever is more recent. |
| **How fulfilling was this task?** | Very fulfilling. The 10 files form a coherent SpO2 subsystem with clear manual vs. auto measurement distinction, BLE command lifecycle, and data flow from device through repository to UI. The dual-mode architecture (manual live measurement + automatic historical sync) is now well-documented. |
| **What would you like changed if asked to do something like this again?** | (1) It would help to have the BloodOxygenRepository source available in the same chunk — the syncAutoBloodOxygen implementation is the missing link for understanding the actual BLE protocol. (2) The StartHeartRateReq/StopHeartRateReq classes should be included to decode the exact BLE command bytes. (3) A cross-reference to the HeartRate measurement flow would clarify what's shared vs. SpO2-specific. (4) The param semantics (0 vs 255) in syncAutoBloodOxygen should be confirmed from the repository implementation. |
