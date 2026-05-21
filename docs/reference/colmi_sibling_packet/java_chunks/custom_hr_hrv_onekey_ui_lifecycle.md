# HR / HRV / OneKey Health Check — Manual Measurement UI Lifecycle

> **Chunk type:** custom_ui_lifecycle  
> **Source tree:** `decompiled4/sources/com/qcwireless/smart/ui/home/`  
> **DEX origin:** `classes4.dex`  
> **Assigned ledger_ids:** J06551, J06552, J06553, J06557, J06558, J06660, J06661, J06662 + adjacent Activity files  
> **Total files:** 10  
> **Analysis date:** 2026-05-19  

---

## 0. Telemetry Answer

**Can you guess what model/family you are running as?**  
This is a **QRing / Colmi sibling wearable companion app** (package `com.qcwireless.smart`, APK name `app_QRingRelease`). The BLE command layer uses the `com.oudmon.ble.base` SDK (RealSil/Realsil BLE stack). The device family includes smart rings and wristbands that support heart rate, HRV, SpO₂, blood pressure estimation, and composite "OneKey" health checks. The app's `DeviceFunctionSupport` and `OneKeySupport` beans gate features per device model. The `UserConfig.INSTANCE.getInstance().getIsBindBand()` check distinguishes wristband (band) vs ring form factors for wearing-detection UX.

---

## 1. Heart Rate (HR) — Manual Measurement Lifecycle

### 1.1 Focus Question: How does the user-initiated manual HR measurement flow from UI tap to BLE command, through timeout, to local DB persistence?

**Answer:**

1. **User taps the "Start" button** in `HeartActivity`. This triggers `setupViews$lambda$14` (the click listener on the start/stop button `binding.b`).

2. **BLE connectivity check:** If `BleOperateManager.getInstance().isConnected()` returns false, a toast "Device not connected" (`R.string.qc_text_75`) is shown and the method returns.

3. **UI state transition to "measuring":**
   - `binding.C.setText("--")` — HR value display resets to dashes
   - `binding.H.setText("")` — timestamp display cleared
   - Heart icon animation starts (`ScaleAnimation` 1.0→1.3, 1500ms, infinite repeat)
   - If `startMeasure == false`, set `startMeasure = true`
   - Button text changes to stop label (`R.string.qc_text_76660011`)
   - HR value text gets `AlphaAnimation` (0→1, 500ms, 60 repeats)
   - `secondsDown()` starts a `CountDownTimer(25000L, 500L)` — 25-second countdown with 500ms tick interval, alternating `"--"` / `"-"` display

4. **BLE command sent:** `CommandHandle.getInstance().executeReqCmd(StartHeartRateReq.getSimpleReq((byte) 1), callback)` — type byte `1` = manual HR measurement

5. **30-second hard timeout:** `handler.postDelayed(heartRunnable, 30000L)` — the `heartRunnable` (lambda 15) fires after 30s if no successful response arrives

6. **Response handling** (inside the `ICommandResponse<StartHeartRateRsp>` callback):
   - **errCode == 0, type == 1, value > 0:** Success! Update `heartValue`, display the value, cancel countdown, stop alpha animation. Then schedule `heartRunnable` via `handler.postDelayed(heartRunnable, 1000L)` — a 1-second delay to finalize.
   - **errCode == 1:** Wearing detection failure. If `isBindBand` → toast "Wearing detection" (`R.string.qc_text_6666064`). Otherwise → show `WearingDetectionDialog` with confirm/cancel, confirm navigates to `RevisionActivity`.
   - **errCode == 0 or 2 (no value):** Clean up — stop animations, cancel countdown, reset button text, remove handler callbacks.

7. **Timeout finalization** (`heartRunnable$lambda$15`):
   - `startMeasure = false`
   - Button text → start label (`R.string.qc_text_76660010`)
   - Display final `heartValue`
   - Clear animations, cancel countdown
   - **Send stop command:** `StopHeartRateReq.stopHeartRate((byte) heartValue)` — sends the measured HR value back to the device
   - **Save timestamp:** `binding.H.setText(dateUtil.getY_M_D_H_M_S())`
   - **Persist to local DB:** `HeartRateDetailRepository.saveManualHeartRate(dateUtil.getUnixTimestamp(), heartValue)`

8. **Stop button (re-tap while measuring):** If `startMeasure == true`, the same button tap toggles it off:
   - `startMeasure = false`, button text → start label
   - Remove handler callbacks, clear animations, cancel countdown
   - `StopHeartRateReq.stopHeartRate((byte) 0)` — stop with value 0 (no measurement taken)

### 1.2 Automatic HR Sync Path

`HeartActivityViewModel.syncTodayData()` is called when:
- The `MyDeviceNotifyListener` receives a device notification with `status == 0 && dataType == 1`
- Or on activity initialization

The sync path has two branches:
- **If `DeviceFunctionList.manualHeart == true`:** Uses `HeartRateDetailRepository.syncManualHeartRate(0, ILargeDataManualHeartRateResponse)` — large-data manual HR sync protocol
- **Otherwise (or null DeviceFunctionList):** Uses `HeartRateDetailRepository.syncTodayHeartRate(DateUtil, BaseDeviceResult<ReadHeartRateRsp>)` — standard interval-based HR sync

After sync completes, `queryHeartRateByDateDetail(new DateUtil())` refreshes the UI and `EventBus.post(ManualRefreshEvent)` triggers dependent observers.

### 1.3 HR Detection Toggle

`setupViews$lambda$10` handles the `QSettingItemTitleSubTitleSystem` switch for HR detection:
- If BLE disconnected → revert switch, show toast
- If connected → update `deviceSetting.setHrDetection(z)`, then `viewModel.saveDeviceSetting(mac, setting)` which:
  1. Sends `HeartRateSettingReq.getWriteInstance(hrDetection, hrInterval, hrStart, hrTooLow, hrTooHigh)` to device
  2. Saves `DeviceSettingEntity(mac, "com.qcwxkjvip.WatchSetting", json)` to local DB

### 1.4 Real-Time HR Polling

`MyRunnable` (the `callback` field) runs every 20 seconds during measurement:
- `CommandHandle.getInstance().executeReqCmdNoCallback(new RealTimeHeartRate(3))` — requests real-time HR with parameter 3
- `handler.postDelayed(callback, 20000L)` — reschedules itself

---

## 2. Heart Rate Variability (HRV) — Manual Measurement Lifecycle

### 2.1 Focus Question: How does the HRV manual measurement differ from HR in timeout duration, BLE command type, and data persistence?

**Answer:**

1. **User taps "Start" button** in `HrvActivity`. This triggers `setupViews$lambda$12`.

2. **BLE connectivity check:** Same pattern — toast if disconnected.

3. **UI state transition to "measuring":**
   - `binding.G.setText("--")` — HRV value display resets
   - `binding.K.setText("")` — timestamp cleared
   - Heart icon animation starts (same `ScaleAnimation`)
   - HRV value text gets `AlphaAnimation` (same pattern)
   - If `startMeasure == false`, set `startMeasure = true`
   - `secondsDown()` starts a `CountDownTimer(75000L, 500L)` — **75-second countdown** (vs HR's 25s)
   - Button text → stop label

4. **BLE command sent:** `CommandHandle.getInstance().executeReqCmd(StartHeartRateReq.getSimpleReq((byte) 10), callback)` — type byte **`10`** = manual HRV measurement

5. **80-second hard timeout:** `handler.postDelayed(heartRunnable, 80000L)` — 80s (vs HR's 30s). The extra 5s beyond the countdown provides a grace period.

6. **Response handling** (inside `ICommandResponse<StartHeartRateRsp>`):
   - **errCode == 0, type == 10, value > 0:** Success! Set `hrvValue`, display it, cancel countdown, clear alpha animation, remove handler callbacks, then `handler.postDelayed(heartRunnable, 1000L)` — 1s delay to finalize.
   - **errCode == 1:** Same wearing detection dialog pattern as HR.
   - **Other errors:** Clean up animations, countdown, reset button.

7. **Timeout finalization** (`heartRunnable$lambda$13`):
   - `startMeasure = false`
   - Button text → start label
   - Display final `hrvValue`
   - Clear animations, cancel countdown
   - **Send stop command:** `StopHeartRateReq.stopHrv((byte) hrvValue)` — HRV-specific stop command
   - **Save timestamp:** `binding.K.setText(dateUtil.getY_M_D_H_M_S())`
   - **Persist to local DB:** `HRVRepository.saveManualPressure(dateUtil.getUnixTimestamp(), hrvValue)`

8. **Stop button (re-tap while measuring):** Same pattern as HR:
   - `StopHeartRateReq.stopHrv((byte) 0)` — stop with value 0

9. **onStop() lifecycle:** If activity stops while measuring, it cancels the measurement:
   - `startMeasure = false`, remove handler callbacks, cancel countdown
   - `StopHeartRateReq.stopHrv((byte) 0)` — ensures device stops measuring

### 2.2 HRV Data Display

The HRV UI shows:
- **Line chart** (`QHrvLineChartView`) with time-series data
- **Statistics:** Average HRV (`totalHrv / totalIndex`), Min HRV, Max HRV
- **HRV distribution buckets:** 0-30 (very low), 31-60 (low), 61-101 (normal), 102+ (high) — displayed as percentages
- **Manual measurement list** via `ManualHrvDetailAdapter` with `HRVManualEntity` data

### 2.3 HRV Enable Toggle

`setupViews$lambda$9` handles the HRV enable switch:
- If BLE disconnected → revert switch, show toast
- If connected → `deviceSetting.setHrvEnable(z)`, then `viewModel.saveDeviceSetting(mac, setting)` which:
  1. Sends `HrvSettingReq(hrvEnable)` to device
  2. Saves `DeviceSettingEntity` to local DB

### 2.4 Automatic HRV Sync

`HrvActivityViewModel.syncTodayData()` calls `hrvRepository.syncTodayHrv(BaseDeviceResult<HRVRsp>)`, then refreshes via `queryPressureByDate(new DateUtil())` and posts `ManualRefreshEvent`.

---

## 3. OneKey Health Check — Composite Measurement Lifecycle

### 3.1 Focus Question: How does the OneKey composite check orchestrate multiple measurements, handle the countdown, and assemble the multi-valued result?

**Answer:**

1. **User taps "Start" button** in `OneKeyCheckActivity`. This triggers the click listener on `binding.b` (setupViews$lambda$2).

2. **BLE connectivity check:** Same pattern — toast if disconnected, also sets `startOneKey = false`.

3. **UI state transition to "measuring":**
   - `ViewKt.visible(binding.x)` — countdown text visible
   - `mCountDown = 30` — reset countdown to 30 seconds
   - `mHandler.removeCallbacks(runnable)` then `mHandler.post(runnable)` — start the countdown runnable
   - `getViewModel().startOnKey()` — sends BLE command
   - `startOneKey = true`
   - `startAnimator()` — starts a `translationY` animation on the heart icon (0 → 140dp → 0, 5000ms, 10 repeats)
   - `ViewKt.visible(binding.i)` — heart icon visible
   - `ViewKt.gone(binding.b)` — start button hidden

4. **BLE commands sent** (in `OneKeyCheckViewModel.startOnKey()`):
   - `CommandHandle.getInstance().executeReqCmd(StartHeartRateReq.getSimpleReq((byte) 5), oneKeyCallback)` — type byte **`5`** = OneKey health check
   - `BleOperateManager.getInstance().addNotifyListener(105, oneKeyCallback)` — registers for notification type 105

5. **30-second countdown** (`CountDownRunnable`):
   - Every 1 second: `mCountDown--`, display `"<countdown>s"` in `binding.x`
   - If app goes to background: cancel measurement, show toast, stop animator, reset countdown, call `stopOnKey()`
   - When `mCountDown <= 0`: **Finalize the measurement**

6. **Response handling** (via `OneKeyResp` inner class observing `OneKeyUI`):
   - **error <= 0:** Store `lastData = oneKeyUI.getResp()` — the `StartHeartRateRsp` object
   - **error > 0:** Show toast "Measurement failed" (`R.string.qc_text_312`), cancel countdown, stop animator, reset, call `stopOnKey()`, set `startOneKey = false`

7. **Timeout finalization** (when `mCountDown <= 0` in `CountDownRunnable`):
   - `ViewKt.visible(binding.b)` — show start button
   - `mHandler.removeCallbacks(runnable)`
   - `ViewKt.invisible(binding.x)` — hide countdown
   - `stopAnimator()`
   - `mCountDown = 30` — reset
   - `ViewKt.gone(binding.i)` — hide heart icon
   - `getViewModel().stopOnKey()` — sends stop command

8. **Result assembly** (if `lastData.getValue() > 0`):
   - **HR:** `lastData.getValue()` → displayed in `binding.v`
   - **BP:** `lastData.getSbp()` + "/" + `lastData.getDbp()` → displayed in `binding.p`
   - **SpO₂:** Randomly selected from `{96, 97, 98, 99}` → displayed in `binding.m`
   - **Fatigue:** `createFatigueValue()` — time-of-day-based random value (40-100 range, morning 80-100, afternoon 40-80, night 40-60) → displayed in `binding.s` as "tired" or "energetic" string
   - **Wellness score:** `Random.nextInt(4) + 96` → value 96-99, displayed in `binding.x` as formatted string (`R.string.qc_text_335`)

9. **Persist to local DB:**
   - `lastBean.setLastTime(timestamp)`, `.setHr()`, `.setSbp()`, `.setDbp()`, `.setBo()`, `.setFatigue()`, `.setScore()`
   - `viewModel.saveLastOneKeyCheck(lastBean)` → `DeviceSettingRepository.saveDeviceSetting(DeviceSettingEntity(mac, "com.qcwxkjvip.lastOneKeyCheck", json))`

10. **Stop command** (in `OneKeyCheckViewModel.stopOnKey()`):
    - `CommandHandle.getInstance().executeReqCmd(StopHeartRateReq.stopHealthCheck(), oneKeyCallback)`
    - `BleOperateManager.getInstance().removeNotifyListener(105)`

11. **onDestroy() lifecycle:** If `startOneKey == true`, calls `stopOnKey()` and removes handler callbacks.

### 3.2 OneKey Support Items

`OneKeyCheckViewModel.querySupportItems()` launches a coroutine (currently a no-op stub — the `invokeSuspend` just returns `Unit`). In `setupViews()`, the `OneKeySupport` bean is deserialized from `UserConfig.getOneKeySupport()` and used to show/hide:
- `supportBloodOxygen` → `binding.d` visible
- `supportBloodPressure` → `binding.f` visible
- `supportFeature` → `binding.e` visible

### 3.3 Last OneKey Check Display

`OneKeyCheckViewModel.getLastOneKeyCheck(mac)` launches a coroutine that:
1. Calls `oneKeyCheckRepository.getLastOneKeyCheck(mac)` — returns a `Flow<LastOneKeyBean>`
2. Emits to `_lastState` as `OneKeyLastBean(lastOneKeyBean)`
3. The UI observer populates the display fields from the stored `LastOneKeyBean` fields

### 3.4 Fatigue Value Generation

`createFatigueValue()` is a **pseudo-random algorithm** based on time of day:
- If >30 minutes since last check: generate new value
  - **5am-11am (morning):** `Random.nextInt(20) + 80` → 80-99 (energetic)
  - **11am-2pm (midday):** 70% chance of 80-99, 30% chance of 40-59
  - **2pm-10pm (afternoon/evening):** 50/50 chance of 40-59 or 80-99
  - **10pm-5am (night):** `Random.nextInt(20) + 40` → 40-59 (tired)
- If <30 minutes: return last stored fatigue value
- **Critical observation:** The SpO₂ and wellness score values are also **randomly generated on the phone side**, not measured by the device. Only HR and BP come from the BLE response.

---

## 4. Comprehensive Status Table

| # | Ledger ID | Class | Relative Path | Terminal Status | Data Domains | General Function | Relevant Methods | Key Calls | Command IDs | Evidence Notes | Needs Followup |
|---|-----------|-------|---------------|-----------------|--------------|------------------|------------------|-----------|-------------|----------------|----------------|
| 1 | J06553 | `HeartActivityViewModel` | `ui/home/heart/HeartActivityViewModel.java` | Deep-read complete | hr, hrv_regular, storage_db | HR ViewModel: syncs today's HR data, saves device settings, queries detail lists | `initData()`, `syncTodayData()`, `saveDeviceSetting()`, `showHeartRateDetail()`, `queryHeartRateByDateDetail()`, `queryAppHeartRateByDateDetail()`, `m862getAge()` | `HeartRateDetailRepository.syncTodayHeartRate()`, `syncManualHeartRate()`, `HeartRateSettingReq.getWriteInstance()`, `DeviceSettingRepository.saveDeviceSetting()` | StartHeartRateReq type=1, HeartRateSettingReq, ReadHeartRateRsp | Three sync branches: manualHeart vs standard vs null DeviceFunctionList. `m862getAge()` launches coroutine via `getAge$1` inner class | No |
| 2 | J06552 | `HeartActivityViewModel$initData$1` | `ui/home/heart/HeartActivityViewModel$initData$1.java` | Deep-read complete | storage_db | Coroutine that loads DeviceSetting from DB and posts to `_deviceSetting` LiveData | `invokeSuspend()` | `deviceSettingRepository.getDeviceSetting(mac)`, Flow.collect → `_deviceSetting.postValue()` | N/A | Two-suspend-point coroutine (labels 0→1→2). Emits DeviceSetting flow to LiveData | No |
| 3 | J06551 | `HeartActivityViewModel$getAge$1` | `ui/home/heart/HeartActivityViewModel$getAge$1.java` | Deep-read complete | hr | Coroutine that fetches user profile age and posts to `_age` LiveData | `invokeSuspend()` | `userProfileRepository.getUserProfile()`, Flow.collect → `_age.postValue()` | N/A | Used for HR zone calculation (maxHeart = 220 - age) | No |
| 4 | J06558 | `HrvActivityViewModel` | `ui/home/heart/HrvActivityViewModel.java` | Deep-read complete | hrv_regular, storage_db | HRV ViewModel: syncs today's HRV data, saves HRV device settings, queries pressure by date | `initData()`, `syncTodayData()`, `saveDeviceSetting()`, `queryPressureByDate()`, `queryLastData()` | `HRVRepository.syncTodayHrv()`, `HrvSettingReq(hrvEnable)`, `DeviceSettingRepository.saveDeviceSetting()` | HrvSettingReq, HRVRsp | Uses `HRVRepository` (not HeartRateDetailRepository). `syncTodayData()` uses `BaseDeviceResult<HRVRsp>` | No |
| 5 | J06557 | `HrvActivityViewModel$initData$1` | `ui/home/heart/HrvActivityViewModel$initData$1.java` | Deep-read complete | storage_db | Coroutine that loads DeviceSetting from DB and posts to `_deviceSetting` LiveData | `invokeSuspend()` | `DeviceSettingRepository.getDeviceSetting(mac)`, Flow.collect → `_deviceSetting.postValue()` | N/A | Same pattern as HR's initData$1 but uses static `DeviceSettingRepository.INSTANCE` | No |
| 6 | J06662 | `OneKeyCheckViewModel` | `ui/home/onekey/OneKeyCheckViewModel.java` | Deep-read complete | hr, spo2, bp, hrv_regular, storage_db | OneKey ViewModel: starts/stops composite health check, saves last result, queries support items | `startOnKey()`, `stopOnKey()`, `saveLastOneKeyCheck()`, `getLastOneKeyCheck()`, `querySupportItems()` | `StartHeartRateReq.getSimpleReq((byte)5)`, `StopHeartRateReq.stopHealthCheck()`, `BleOperateManager.addNotifyListener(105)`, `DeviceSettingRepository.saveDeviceSetting()` | StartHeartRateReq type=5, StopHeartRateReq.stopHealthCheck, notify type=105 | `OneKeyResp` inner class implements `ICommandResponse<StartHeartRateRsp>`. Saves to key `com.qcwxkjvip.lastOneKeyCheck` | No |
| 7 | J06660 | `OneKeyCheckViewModel$getLastOneKeyCheck$1` | `ui/home/onekey/OneKeyCheckViewModel$getLastOneKeyCheck$1.java` | Deep-read complete | storage_db | Coroutine that loads last OneKey check from repository and posts to `_lastState` LiveData | `invokeSuspend()` | `oneKeyCheckRepository.getLastOneKeyCheck(mac)`, Flow.collect → `_lastState.postValue(OneKeyLastBean)` | N/A | Wraps nullable `LastOneKeyBean` in `OneKeyLastBean` data class | No |
| 8 | J06661 | `OneKeyCheckViewModel$querySupportItems$1` | `ui/home/onekey/OneKeyCheckViewModel$querySupportItems$1.java` | Deep-read complete | none | Stub coroutine — `invokeSuspend()` just returns Unit immediately | `invokeSuspend()` | None | N/A | Likely a placeholder or the real logic was inlined/removed by obfuscation | Yes — what was this supposed to do? |
| 9 | — | `HeartActivity` | `ui/home/heart/HeartActivity.java` | Deep-read complete | hr, ble_connection | HR Activity UI: manual measurement start/stop, countdown, wearing detection, calendar, HR detail chart | `setupViews$lambda$14` (start), `heartRunnable$lambda$15` (timeout), `setupViews$lambda$10` (HR toggle), `secondsDown()`, `queryManualHeart()` | `StartHeartRateReq.getSimpleReq((byte)1)`, `StopHeartRateReq.stopHeartRate()`, `RealTimeHeartRate(3)`, `HeartRateDetailRepository.saveManualHeartRate()` | StartHeartRate type=1, StopHeartRate, RealTimeHeartRate | 30s handler timeout, 25s countdown animation. `MyRunnable` polls real-time HR every 20s. `MyDeviceNotifyListener` triggers syncTodayData on dataType==1 | No |
| 10 | — | `HrvActivity` | `ui/home/heart/HrvActivity.java` | Deep-read complete | hrv_regular, ble_connection | HRV Activity UI: manual measurement start/stop, countdown, wearing detection, HRV distribution chart | `setupViews$lambda$12` (start), `heartRunnable$lambda$13` (timeout), `setupViews$lambda$9` (HRV toggle), `secondsDown()`, `queryManualPressure()` | `StartHeartRateReq.getSimpleReq((byte)10)`, `StopHeartRateReq.stopHrv()`, `HRVRepository.saveManualPressure()` | StartHeartRate type=10, StopHeartRateReq.stopHrv | 80s handler timeout, 75s countdown. onStop() cancels measurement. HRV distribution: 0-30, 31-60, 61-101, 102+ | No |
| 11 | — | `OneKeyCheckActivity` | `ui/home/onekey/OneKeyCheckActivity.java` | Deep-read complete | hr, spo2, bp, ble_connection | OneKey Activity UI: composite measurement with countdown, result assembly, fatigue/score generation | `setupViews$lambda$2` (start), `CountDownRunnable.run()` (countdown/finalize), `createFatigueValue()`, `startAnimator()`, `stopAnimator()` | `getViewModel().startOnKey()`, `stopOnKey()`, `saveLastOneKeyCheck()`, `OneKeySupport` deserialization | StartHeartRate type=5, notify type=105 | 30s countdown. SpO₂ = random from {96,97,98,99}. Score = random 96-99. Fatigue = time-of-day random. **Only HR and BP come from device** | No |

---

## 5. Function Dictionary Proposals

### 5.1 HeartActivity — Manual HR Start

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `HeartActivity.startManualHR` | `setupViews$lambda$14` | `(HeartActivity, View) → void` | Checks BLE connection, starts HR measurement animation, sends `StartHeartRateReq((byte)1)`, schedules 30s timeout via `handler.postDelayed(heartRunnable, 30000L)`, starts 25s `CountDownTimer` with "--"/"-" animation |
| `HeartActivity.finalizeManualHR` | `heartRunnable$lambda$15` | `(HeartActivity) → void` | Sets `startMeasure=false`, displays final HR value, sends `StopHeartRateReq.stopHeartRate((byte)heartValue)`, saves `HeartRateDetailRepository.saveManualHeartRate(timestamp, heartValue)`, updates timestamp display |
| `HeartActivity.stopManualHR` | `setupViews$lambda$14` (else branch) | `(HeartActivity) → void` | Sets `startMeasure=false`, sends `StopHeartRateReq.stopHeartRate((byte)0)`, clears animations, cancels countdown |
| `HeartActivity.toggleHRDetection` | `setupViews$lambda$10` | `(HeartActivity, CompoundButton, boolean) → void` | Checks BLE, updates `deviceSetting.hrDetection`, sends `HeartRateSettingReq`, saves `DeviceSettingEntity` |
| `HeartActivity.onHRDeviceNotify` | `MyDeviceNotifyListener.onDataResponse` | `(DeviceNotifyRsp) → void` | If `status==0 && dataType==1`, calls `viewModel.syncTodayData()` |
| `HeartActivity.pollRealTimeHR` | `MyRunnable.run` | `() → void` | Sends `RealTimeHeartRate(3)`, reschedules itself after 20s |

### 5.2 HrvActivity — Manual HRV Start

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `HrvActivity.startManualHRV` | `setupViews$lambda$12` | `(HrvActivity, View) → void` | Checks BLE, starts HRV animation, sends `StartHeartRateReq((byte)10)`, schedules 80s timeout via `handler.postDelayed(heartRunnable, 80000L)`, starts 75s `CountDownTimer` |
| `HrvActivity.finalizeManualHRV` | `heartRunnable$lambda$13` | `(HrvActivity) → void` | Sets `startMeasure=false`, displays final HRV value, sends `StopHeartRateReq.stopHrv((byte)hrvValue)`, saves `HRVRepository.saveManualPressure(timestamp, hrvValue)`, updates timestamp display |
| `HrvActivity.stopManualHRV` | `setupViews$lambda$12` (else branch) | `(HrvActivity) → void` | Sets `startMeasure=false`, sends `StopHeartRateReq.stopHrv((byte)0)`, clears animations, cancels countdown |
| `HrvActivity.toggleHRVEnable` | `setupViews$lambda$9` | `(HrvActivity, CompoundButton, boolean) → void` | Checks BLE, updates `deviceSetting.hrvEnable`, sends `HrvSettingReq`, saves `DeviceSettingEntity` |
| `HrvActivity.cancelOnStop` | `onStop()` | `() → void` | If measuring: `startMeasure=false`, remove callbacks, cancel countdown, send `StopHeartRateReq.stopHrv((byte)0)` |

### 5.3 OneKeyCheckActivity — Composite Health Check

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `OneKeyCheckActivity.startOneKeyCheck` | `setupViews$lambda$2` | `(View) → void` | Checks BLE, starts 30s countdown via `CountDownRunnable`, calls `viewModel.startOnKey()`, starts translationY animator, hides start button |
| `OneKeyCheckActivity.finalizeOneKeyCheck` | `CountDownRunnable.run` (mCountDown ≤ 0 branch) | `() → void` | Shows start button, removes callbacks, stops animator, resets countdown, calls `viewModel.stopOnKey()`, assembles result (HR, BP, SpO₂, fatigue, score), saves to DB |
| `OneKeyCheckActivity.cancelOneKeyCheck` | `CountDownRunnable.run` (app backgrounded branch) | `() → void` | Shows start button, toast, removes callbacks, stops animator, resets countdown, calls `viewModel.stopOnKey()` |
| `OneKeyCheckActivity.createFatigueValue` | `createFatigueValue()` | `() → int` | Time-of-day pseudo-random: morning 80-99, midday 70/30 split, afternoon 50/50, night 40-59. Caches for 30 minutes |
| `OneKeyCheckActivity.startAnimator` | `startAnimator()` | `() → void` | Creates `ObjectAnimator.translationY(0, 140dp, 0)` with 10 repeats, 5000ms, plays in `AnimatorSet` |
| `OneKeyCheckActivity.stopAnimator` | `stopAnimator()` | `() → void` | Calls `animatorSet.end()` |

### 5.4 OneKeyCheckViewModel — BLE Commands

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `OneKeyCheckViewModel.startOneKey` | `startOnKey()` | `() → void` | Sends `StartHeartRateReq.getSimpleReq((byte)5)` with `oneKeyCallback`, registers `addNotifyListener(105, oneKeyCallback)` |
| `OneKeyCheckViewModel.stopOneKey` | `stopOnKey()` | `() → void` | Sends `StopHeartRateReq.stopHealthCheck()` with `oneKeyCallback`, removes `removeNotifyListener(105)` |
| `OneKeyCheckViewModel.saveLastOneKeyCheck` | `saveLastOneKeyCheck()` | `(LastOneKeyBean) → void` | Saves `DeviceSettingEntity(mac, "com.qcwxkjvip.lastOneKeyCheck", json)` via `DeviceSettingRepository` |
| `OneKeyCheckViewModel.onOneKeyResponse` | `OneKeyResp.onDataResponse` | `(StartHeartRateRsp) → void` | Posts `OneKeyUI(errCode, resp)` to `_uiState` LiveData |

### 5.5 HeartActivityViewModel — Sync & Settings

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `HeartActivityViewModel.syncTodayHR` | `syncTodayData()` | `() → void` | Branches: manualHeart → `syncManualHeartRate(0, ILargeDataManualHeartRateResponse)`, else → `syncTodayHeartRate(DateUtil, BaseDeviceResult<ReadHeartRateRsp>)`. Both refresh UI and post `ManualRefreshEvent` |
| `HeartActivityViewModel.saveHRDeviceSetting` | `saveDeviceSetting()` | `(String mac, DeviceSetting) → void` | Sends `HeartRateSettingReq.getWriteInstance(hrDetection, hrInterval, hrStart, hrTooLow, hrTooHigh)`, saves `DeviceSettingEntity(mac, "com.qcwxkjvip.WatchSetting", json)` |
| `HeartActivityViewModel.loadDeviceSetting` | `initData$1.invokeSuspend` | `() → void` | Coroutine: `deviceSettingRepository.getDeviceSetting(mac)` → Flow → `_deviceSetting.postValue()` |

### 5.6 HrvActivityViewModel — Sync & Settings

| Proposed Function Name | Source Location | Signature | Behavior |
|------------------------|----------------|-----------|----------|
| `HrvActivityViewModel.syncTodayHRV` | `syncTodayData()` | `() → void` | Calls `hrvRepository.syncTodayHrv(BaseDeviceResult<HRVRsp>)`, then refreshes UI and posts `ManualRefreshEvent` |
| `HrvActivityViewModel.saveHRVDeviceSetting` | `saveDeviceSetting()` | `(String mac, DeviceSetting) → void` | Sends `HrvSettingReq(hrvEnable)`, saves `DeviceSettingEntity(mac, "com.qcwxkjvip.WatchSetting", json)` |

---

## 6. Cross-Cutting Observations

### 6.1 Shared BLE Command Infrastructure

All three measurement types reuse the same `StartHeartRateRsp` response object, differentiated by the `type` field:

| Measurement | Start Type Byte | Stop Command | Response Type Check | Notify Type |
|-------------|----------------|-------------|--------------------|-------------|
| Heart Rate | `(byte) 1` | `StopHeartRateReq.stopHeartRate((byte) value)` | `type == 1` | `dataType == 1` (DeviceNotifyRsp) |
| HRV | `(byte) 10` | `StopHeartRateReq.stopHrv((byte) value)` | `type == 10` | N/A |
| OneKey | `(byte) 5` | `StopHeartRateReq.stopHealthCheck()` | `errCode <= 0` | `type == 105` (BleNotifyListener) |

### 6.2 Error Code Protocol

| errCode | Meaning | HR Action | HRV Action | OneKey Action |
|---------|---------|-----------|------------|----------------|
| 0 | Success | Display value, finalize | Display value, finalize | Store `lastData` |
| 1 | Wearing detection | Show `WearingDetectionDialog` (or toast if band) | Same | N/A (handled differently) |
| 2 | Other error | Clean up, no value | Clean up, no value | N/A |

### 6.3 Timeout Comparison

| Measurement | Countdown Duration | Hard Timeout | Countdown Class | Finalization Delay |
|-------------|-------------------|--------------|-----------------|-------------------|
| HR | 25,000ms (500ms tick) | 30,000ms | `CountDownTimer` | 1,000ms after success |
| HRV | 75,000ms (500ms tick) | 80,000ms | `CountDownTimer` | 1,000ms after success |
| OneKey | 30 × 1,000ms = 30s | 30s (same as countdown) | `CountDownRunnable` (Handler-based) | Immediate on countdown=0 |

### 6.4 Local DB Persistence

| Measurement | Repository | Save Method | DB Key | Data Saved |
|-------------|-----------|-------------|--------|------------|
| HR | `HeartRateDetailRepository` | `saveManualHeartRate(timestamp, heartValue)` | Per-record (not settings) | Unix timestamp + HR value |
| HRV | `HRVRepository` | `saveManualPressure(timestamp, hrvValue)` | Per-record | Unix timestamp + HRV value |
| OneKey | `DeviceSettingRepository` | `saveDeviceSetting(DeviceSettingEntity)` | `com.qcwxkjvip.lastOneKeyCheck` | Full `LastOneKeyBean` JSON (hr, sbp, dbp, bo, fatigue, score, lastTime) |

### 6.5 OneKey SpO₂ and Score Are Fabricated

**Critical finding:** The OneKey health check's SpO₂ value is randomly selected from `{96, 97, 98, 99}` and the wellness score is `Random.nextInt(4) + 96` (range 96-99). The fatigue value is a time-of-day-based pseudo-random number. Only HR (`getValue()`) and blood pressure (`getSbp()`, `getDbp()`) come from the actual BLE device response. This means the "OneKey" composite check presents a mix of real and synthetic data to the user without clear visual distinction.

---

## 7. Summary Metrics

| Metric | Value |
|--------|-------|
| Files assigned | 10 (3 ViewModels + 3 inner classes + 1 querySupportItems + 3 Activities) |
| Files actually read | 10 |
| Rows needing second pass | 1 (`OneKeyCheckViewModel$querySupportItems$1` — stub coroutine, purpose unclear) |
| Strongest new findings | (1) All three measurement types share `StartHeartRateRsp` with type discrimination; (2) OneKey SpO₂/score/fatigue are **randomly generated on the phone**, not from device; (3) HR uses a 20s real-time polling loop (`RealTimeHeartRate(3)`) during measurement; (4) HRV has a 75s/80s timeout vs HR's 25s/30s; (5) Stop commands carry the measured value back to the device for HR and HRV |
| How fulfilling was this task? | Very fulfilling — the three measurement lifecycles are cleanly parallel in structure but have meaningful differences in timeout, command type, and especially the OneKey's synthetic data generation. The cross-cutting analysis reveals the shared BLE infrastructure clearly. |
| What would you like changed if asked to do something like this again? | (1) The decompiled Java is extremely verbose due to null-safety checks — a Kotlin source reconstruction would be more readable; (2) Having the `StartHeartRateRsp` and `StopHeartRateReq` class definitions available would clarify the full BLE protocol; (3) The `OneKeyCheckRepository` implementation was not in the assigned files — reading it would clarify the `getLastOneKeyCheck` storage mechanism; (4) A companion SpO₂ lifecycle document would make cross-referencing easier. |
