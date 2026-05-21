# CH0010 — App Orchestration Strong Hits

> **Chunk type:** app_orchestration_strong_hits  
> **Source tree:** `decompiled4/sources/com/qcwireless/smart/`  
> **DEX origin:** `classes4.dex`  
> **Assigned ledger_ids:** J05028, J05029, J05031, J05049, J05061, J05062, J05064, J05066, J05067, J05070, J05080–J05092, J05095, J05111, J05113, J05114, J05116, J05118, J05139–J05151  
> **Total files:** 35  
> **Analysis date:** 2026-05-19  

---

## 1. Executive Summary

CH0010 covers the **app-level orchestration layer** of the QRing/Colmi companion app — the `MainActivity` that drives the main UI and sync lifecycle, the `QcService` Retrofit interface that defines every cloud API endpoint, device capability beans (`DeviceFunctionSupport`, `DeviceFunctionTouchOnlySupport`, `OneKeySupport`), the `DeviceSetting` configuration bean, and 13 request/response DTOs for health measurement sync (BloodOxygen, BloodPressure, Sleep, HeartRate, Sport, Temperature, GoalSetting).

**Key findings:**

1. **QcService is the complete cloud API contract.** It defines 50+ Retrofit endpoints covering every health-data upload (`commit`) and download (`sync-from-id`/`sync-from-time`) operation. This is the single source of truth for the server API shape.

2. **MainActivity orchestrates a bidirectional sync cycle.** The `doServer()` method (line ~737) implements the full sync flow: `downAll()` → `downUserProfile()` → `downGoalSetting()` → (if BLE connected) `upAll()`. The sync-from-server interval is gated at 43,200 seconds (12 hours).

3. **Device capability beans gate feature availability.** `DeviceFunctionSupport` (21 boolean flags) and `DeviceFunctionTouchOnlySupport` (17 flags) control which health features the app enables for a given device. `OneKeySupport` (mac + 9 flags) is a per-device capability probe for BloodOxygen, BloodPressure, HRV, Temperature, ManualHeart, Pressure, ECard, Location.

4. **DeviceSetting is the full device configuration state.** 55+ fields covering HR detection (`hrDetection`, `hrInterval`, `hrStart`, `hrTooLow`, `hrTooHigh`), HRV (`hrvEnable`), SpO2 (`bo2Detection`), BP (`bpSwitch`, `bpStart`, `bpEnd`, `bpInterval`), temperature (`tempDetection`), sleep tracking, long-sit, drink, do-not-disturb, prayer reminders, screen settings, and wrist sense.

5. **Request/response DTOs reveal the sync protocol structure.** Upload requests carry `uid` + `datas[]` arrays of per-day detail items. Download requests use `uid` + `lastSyncId`/`from` + `size` pagination. The `interval` field in HR and sleep beans indicates time-series data is bucketed at configurable intervals.

6. **Sleep has two protocols.** The original protocol uses `SleepDetailRequest`/`SleepDetailResp` with `indexs[]` + `qualitys[]` arrays. The V1/new protocol uses `CommitSleepNewProtocolParam`/`SleepDetailNewProtocolResp` with structured `SleepList` → `SleepDetail` (d/t pairs), plus `st`/`et`/`lunchSt`/`lunchEt` fields.

7. **Image picker/cropper files (J05139–J05151) are domain-irrelevant.** These 7 files handle avatar image selection and cropping — no health data, BLE, or sync semantics.

---

## 2. File Status Table

| # | Ledger ID | Class | Lines | Domain Hit | Signal | Status |
|---|-----------|-------|-------|------------|--------|--------|
| 1 | J05028 | `MainActivity` | 2737 | **sync_scheduler, ble_connection, hr, sleep, spo2, steps_sport, temperature** | 🔴 CRITICAL | Deep-read complete |
| 2 | J05029 | `MoreDeviceActivity` | ~242 | ble_connection | 🟡 MEDIUM | Deep-read complete |
| 3 | J05031 | `SelectDeviceActivity` | ~62 | ble_connection | 🟢 LOW | Deep-read complete |
| 4 | J05049 | `QcService` | 470 | **sync_scheduler, hr, sleep, spo2, steps_sport, temperature, hrv_regular** | 🔴 CRITICAL | Deep-read complete |
| 5 | J05061 | `DeviceFunctionSupport` | ~230 | **hr, spo2, temperature, ble_connection** | 🔴 CRITICAL | Deep-read complete |
| 6 | J05062 | `DeviceFunctionTouchOnlySupport` | ~200 | **hr, spo2, temperature, ble_connection** | 🟡 MEDIUM | Deep-read complete |
| 7 | J05064 | `DeviceSetting` | ~500 | **hr, hrv_regular, spo2, temperature, sleep, bp** | 🔴 CRITICAL | Deep-read complete |
| 8 | J05066 | `GeneratedJsonAdapter` (DeviceSetting) | ~520 | storage_db | 🟢 LOW | Deep-read complete |
| 9 | J05067 | `OneKeySupport` | ~110 | **hr, spo2, hrv_regular, temperature, bp** | 🔴 CRITICAL | Deep-read complete |
| 10 | J05070 | `GeneratedJsonAdapter` (GoogleFitDataBean) | ~60 | steps_sport | 🟢 LOW | Deep-read complete |
| 11 | J05080 | `BloodOxygenRequest` | 93 | **spo2** | 🔴 CRITICAL | Deep-read complete |
| 12 | J05081 | `BloodPressureRequest` | 96 | **bp** | 🔴 CRITICAL | Deep-read complete |
| 13 | J05082 | `BpDownRequest` | 87 | **bp** | 🟡 MEDIUM | Deep-read complete |
| 14 | J05083 | `CommitSleepNewProtocolParam` | 23 | **sleep** | 🔴 CRITICAL | Deep-read complete |
| 15 | J05085 | `HeartRateIntervalRequest` | 110 | **hr, hrv_regular** | 🔴 CRITICAL | Deep-read complete |
| 16 | J05086 | `SleepDetailRequest` | 114 | **sleep** | 🔴 CRITICAL | Deep-read complete |
| 17 | J05087 | `SleepTypeAndDuration` | 27 | **sleep** | 🟡 MEDIUM | Deep-read complete |
| 18 | J05088 | `Spo2DownRequest` | 87 | **spo2** | 🟡 MEDIUM | Deep-read complete |
| 19 | J05089 | `SportDetailRequest` | 161 | **steps_sport** | 🔴 CRITICAL | Deep-read complete |
| 20 | J05091 | `TemperatureDownloadRequest` | 87 | **temperature** | 🟡 MEDIUM | Deep-read complete |
| 21 | J05092 | `TemperatureRequest` | 84 | **temperature** | 🔴 CRITICAL | Deep-read complete |
| 22 | J05095 | `GoalSettingRequest` | 132 | **steps_sport, sleep** | 🟡 MEDIUM | Deep-read complete |
| 23 | J05111 | `HeartRateResp` | 119 | **hr** | 🔴 CRITICAL | Deep-read complete |
| 24 | J05113 | `SleepDetailNewProtocolResp` | 23 | **sleep** | 🔴 CRITICAL | Deep-read complete |
| 25 | J05114 | `SleepDetailResp` | 103 | **sleep** | 🔴 CRITICAL | Deep-read complete |
| 26 | J05116 | `SportDetailResp` | 146 | **steps_sport** | 🔴 CRITICAL | Deep-read complete |
| 27 | J05118 | `TemperatureDownResp` | 73 | **temperature** | 🔴 CRITICAL | Deep-read complete |
| 28 | J05139 | `BitmapCroppingWorkerTask` | ~150 | none | ⚪ NO_SIGNAL | Skimmed |
| 29 | J05140 | `BitmapLoadingWorkerTask` | ~60 | none | ⚪ NO_SIGNAL | Skimmed |
| 30 | J05141 | `BitmapUtils` | ~600 | none | ⚪ NO_SIGNAL | Skimmed |
| 31 | J05143 | `CropImageActivity` | ~200 | none | ⚪ NO_SIGNAL | Skimmed |
| 32 | J05145 | `CropImageOptions` | ~250 | none | ⚪ NO_SIGNAL | Skimmed |
| 33 | J05146 | `CropImageView` | ~900 | none | ⚪ NO_SIGNAL | Skimmed |
| 34 | J05150 | `ImagePicker` | ~250 | none | ⚪ NO_SIGNAL | Skimmed |
| 35 | J05151 | `Utils` (imagepicker) | 35 | none | ⚪ NO_SIGNAL | Deep-read complete |

---

## 3. Function Dictionary Proposals

### 3.1 QcService — Cloud API Endpoints (J05049)

The `QcService` Retrofit interface defines the complete REST API contract. Below are the health-data-relevant endpoints organized by function.

#### Upload (commit) Endpoints

| API Method | HTTP | Endpoint Path | Request Bean | Response | Domain |
|------------|------|---------------|-------------|----------|--------|
| `upBloodOxygen` | POST | `spo2/commit-list` | `BloodOxygenRequest` | `QcNoDataResponse` | spo2 |
| `upBloodPressure` | POST | `blood-pressure/commit-list` | `BloodPressureRequest` | `QcNoDataResponse` | bp |
| `upIntervalHeart` | POST | `heart-rate-interval/commit` | `HeartRateIntervalRequest` | `QcNoDataResponse` | hr |
| `upSleepDetail` | POST | `sleep/commit` | `SleepDetailRequest` | `QcNoDataResponse` | sleep |
| `upSleepDetailV1` | POST | `sleep/commit/v1` | `CommitSleepNewProtocolParam` | `QcNoDataResponse` | sleep_v1 |
| `upSportDetail` | POST | `sport/commit` | `SportDetailRequest` | `QcNoDataResponse` | sport |
| `upStepDetail` | POST | `step/commit` | `StepDetailRequest` | `QcNoDataResponse` | steps |
| `upTemperature` | POST | `temperature/commit` | `TemperatureRequest` | `QcNoDataResponse` | temperature |
| `goalUpdate` | POST | `goals/update-goals` | `GoalSettingRequest` | `QcNoDataResponse` | goals |

#### Download (sync-from) Endpoints

| API Method | HTTP | Endpoint Path | Request Bean | Response Type | Domain |
|------------|------|---------------|-------------|---------------|--------|
| `downBo2` | POST | `spo2/sync-from-id/v1` | `Spo2DownRequest` | `List<Spo2DownResp>` | spo2 |
| `downBp` (BP) | POST | `blood-pressure/sync-from-id` | `BpDownRequest` | `List<BpDownResp>` | bp |
| `downBp` (SpO2) | POST | `spo2/sync-from-id` | `Spo2DownRequest` | `List<Spo2DownResp>` | spo2 |
| `downHeartRateDetail` | POST | `heart-rate-interval/sync-from-time` | `HealthyDataDownRequest` | `List<HeartRateResp>` | hr |
| `downSleepDetail` | POST | `sleep/sync-from-time` | `HealthyDataDownRequest` | `List<SleepDetailResp>` | sleep |
| `downSleepDetailV1` | POST | `sleep/sync-from-time/v1` | `HealthyDataDownRequest` | `List<SleepDetailNewProtocolResp>` | sleep_v1 |
| `downSportDetail` | POST | `sport/sync-from-id` | `HealthyDataDownRequest` | `List<SportDetailResp>` | sport |
| `downStepDetail` | POST | `step/sync-from-time` | `HealthyDataDownRequest` | `List<StepDetailResp>` | steps |
| `downTemperature` | POST | `temperature/sync-from-id` | `TemperatureDownloadRequest` | `List<TemperatureDownResp>` | temperature |

#### Device & Config Endpoints

| API Method | HTTP | Endpoint Path | Domain |
|------------|------|---------------|--------|
| `getDeviceConfig` | GET | `device/config` | device_config |
| `deviceFeaturesList` | POST | `device/features/list` | device_features |
| `getGoal` | GET | `goals/my` | goals |
| `scanConfig` | GET | `device/scanConfig` | ble_scan |
| `getDeviceFileList` | POST | `device-file/find-list` | firmware |
| `getLastOta` | POST | `app-update/last-ota` | firmware |

**Notable observation:** The `downBp` method name is overloaded — one variant takes `BpDownRequest` for blood-pressure sync, the other takes `Spo2DownRequest` for SpO2 sync. This is a decompilation artifact from Kotlin name mangling; the actual endpoints differ (`blood-pressure/sync-from-id` vs `spo2/sync-from-id`).

---

### 3.2 MainActivity — Sync Orchestration (J05028)

| Method | Semantics | Domain |
|--------|-----------|--------|
| `doServer()` | **Bidirectional sync orchestrator.** Checks `lastSyncFromServerTime` gate (12h). If expired: `downAll()` → `downUserProfile()` → `downGoalSetting()`. If BLE connected: `upAll()`. Also calls `upCollectionData()` if collection timer expired. | sync_scheduler |
| `doCalcStep()` | Loads step/sleep calendar data from local DB via `StepDetailRepository` and `SleepDetailRepository`. | storage_db |
| `deviceScanConfig()` | Coroutine that fetches device scan configuration from server. | ble_connection |
| `initDeviceRequestLocation()` | Sends location request to BLE device via `LargeDataHandler.deviceRequestLocation()`. | ble_connection |
| `notificationUiRefresh(View)` | Tab-switch handler that posts `RefreshEvent`/`HomeStepRefreshEvent`/`CalendarNotifyEvent` to fragments. | ui_orchestration |
| `ReconnectRunnable` | BLE reconnection timer runnable. | ble_connection |

**Sync lifecycle flow (from `doServer()`):**
```
1. if lastCollectionTime < now AND deviceAddress != "" AND fmVersion != "":
     → NetService.upCollectionData()

2. if !loginStatus OR lastSyncFromServerTime >= now:
     → return (skip sync)

3. NetService.downAll()           // download all health data from server
4. NetService.downUserProfile()   // download user profile
5. NetService.downGoalSetting()    // download goal settings

6. if BleOperateManager.isConnected() AND deviceAddress != "":
     → NetService.upAll()         // upload all local health data to server
     → lastSyncFromServerTime = now + 43200  // 12h cooldown
```

---

### 3.3 Device Capability Beans

#### DeviceFunctionSupport (J05061) — 21 boolean flags

| Flag | Domain | Notes |
|------|--------|-------|
| `supportTouch` | ui | Touch screen vs button-only |
| `supportMoslin` | sleep | Muslim prayer mode |
| `supportAPPRevision` | device | App revision support |
| `supportBlePair` | ble_connection | BLE pairing |
| `supportGesture` | ui | Hand gesture control |
| `supportRingMusic` | media | Music control |
| `supportRingVideo` | media | Video control |
| `supportRingEbook` | media | E-book reader |
| `supportCamera` | camera | Remote camera shutter |
| `supportRingCall` | call | Call handling |
| `supportRingGame` | game | Built-in games |
| **`supportHeartMeasure`** | **hr** | **Heart rate measurement** |
| `supportLongSit` | sedentary | Long-sit reminder |
| `supportDrink` | hydration | Drink reminder |
| **`supportSkinTemperature`** | **temperature** | **Skin temperature** |
| **`supportNoSingleTemperature`** | **temperature** | **No single-point temp** |
| `supportNotification` | notification | Push notifications |
| `supportCallReminder` | call | Call reminder |
| **`supportRealTimeHr`** | **hr** | **Real-time HR monitoring** |
| **`supportRealTimeHrRemind`** | **hr** | **HR alert/remind** |
| `supportLoverInteract` | social | Lover interaction |

#### DeviceFunctionTouchOnlySupport (J05062) — 17 flags

Same as above but **without** `supportRealTimeHr`, `supportRealTimeHrRemind`, `supportLoverInteract`, `supportCallReminder`. Used for touch-only devices with reduced feature sets.

#### OneKeySupport (J05067) — Per-device capability probe

| Field | Type | Domain |
|-------|------|--------|
| `mac` | String | Device MAC address |
| `supportBloodOxygen` | boolean | spo2 |
| `supportBloodPressure` | boolean | bp |
| `supportFeature` | boolean | General feature flag |
| `supportTemp` | boolean | temperature |
| `supportManualHeart` | boolean | hr (manual measurement) |
| `supportECard` | boolean | NFC/e-card |
| `supportLocation` | boolean | GPS |
| `supportPressure` | boolean | stress/pressure |
| **`supportHrv`** | **boolean** | **hrv_regular** |

---

### 3.4 DeviceSetting — Configuration Bean (J05064)

Key health-related fields (55+ total):

| Field | Type | Domain | Notes |
|-------|------|--------|-------|
| `hrDetection` | boolean | hr | HR auto-detection on/off |
| `hrInterval` | int | hr | HR measurement interval (minutes) |
| `hrStart` | int | hr | HR monitoring start time |
| `hrTooLow` | int | hr | Low HR threshold |
| `hrTooHigh` | int | hr | High HR threshold |
| **`hrvEnable`** | **boolean** | **hrv_regular** | **HRV measurement enable** |
| **`bo2Detection`** | **boolean** | **spo2** | **SpO2 auto-detection on/off** |
| `bpSwitch` | boolean | bp | Blood pressure switch |
| `bpStart` | int | bp | BP monitoring start time |
| `bpEnd` | int | bp | BP monitoring end time |
| `bpInterval` | int | bp | BP measurement interval |
| **`pressureDetection`** | **boolean** | **stress** | **Stress/pressure detection** |
| **`tempDetection`** | **boolean** | **temperature** | **Temperature auto-detection** |
| `longSitSwitch` | boolean | sedentary | Long-sit reminder switch |
| `longSitStart/End/During/Week` | int | sedentary | Long-sit schedule |
| `drinkSwitch/Week` | boolean+int | hydration | Drink reminder |
| `disturbSwitch/Manual/Start/End` | bool+int | dnd | Do-not-disturb |
| `wristSense` | boolean | ui | Wrist sense (raise to wake) |
| `firmwareVersion` | String | firmware | Current firmware version |
| `alarmList` | List\<AlarmBean\> | alarm | Alarm configuration |
| `lightAllDay/Start/End/Level` | bool+int | screen | Screen brightness |

**Moshi JSON field names** (from GeneratedJsonAdapter, J05066):
`callSwitch`, `messagePushSwitch`, `smsPushSwitch`, `bpSwitch`, `bpStart`, `bpEnd`, `bpInterval`, `hrDetection`, `tempDetection`, `hrInterval`, `hrStart`, `hrTooLow`, `hrTooHigh`, `hrvEnable`, `bo2Detection`, `pressureDetection`, `wristSense`, `wristSenseHand`, `timeFormat`, `weatherFormat`, `metricUnit`, `disturbSwitch`, `disturbManualSwitch`, `disturbStart`, `disturbEnd`, `firmwareVersion`, `screenLight`, `prayRemindSwitch`, `prayStart`, `prayEnd`, `prayDuring`, `prayWeek`, `longSitSwitch`, `longSitStart`, `longSitEnd`, `longSitDuring`, `longSitWeek`, `drinkSwitch`, `drinkWeek`, `drinkArray`, `alarmList`, `avatarScreen`, `avatarWidth`, `avatarHeight`, `batteryWarming`, `gestureSwitch`, `touchSwitch`, `touchSleep`, `screenSetting`, `leftOrRight`, `lightAllDay`, `lightStart`, `lightEnd`, `lightLevel`, `maxLightLevel`, `warmingHeart`, `open`

---

### 3.5 Request DTOs — Upload Protocol

#### BloodOxygenRequest (J05080)
```
BloodOxygenRequest {
  uid: long
  lastSyncId: long
  datas: List<BO2Detail> {
    dateString: String          // date of measurement
    deviceAddress: String      // BLE MAC
    maxValue: List<Integer>    // max SpO2 readings per interval
    minValue: List<Integer>    // min SpO2 readings per interval
  }
}
```

#### BloodPressureRequest (J05081)
```
BloodPressureRequest {
  uid: long
  lastSyncId: long
  datas: List<BpDetail> {
    sbp: int                   // systolic blood pressure
    dbp: int                   // diastolic blood pressure
    time: long                  // timestamp
    deviceId: String
    deviceType: String
  }
}
```

#### HeartRateIntervalRequest (J05085)
```
HeartRateIntervalRequest {
  uid: long
  datas: List<IntervalHeartRateDetail> {
    date: String               // measurement date
    deviceId: String
    deviceType: String
    interval: int              // sampling interval (minutes)
    indexs: List<Integer>      // time offsets within the day
    values: List<Integer>      // HR values (bpm) at each index
  }
}
```

#### SleepDetailRequest (J05086) — Original Protocol
```
SleepDetailRequest {
  uid: long
  deviceId: String
  deviceType: String
  datas: List<SleepDetailItem> {
    date: String
    intervar: int              // interval (minutes)
    indexs: List<Integer>      // time offsets
    qualitys: List<Integer>    // sleep quality per interval
    totalActiveTime: int       // total active time
  }
}
```

#### CommitSleepNewProtocolParam (J05083) — V1 Protocol
```
CommitSleepNewProtocolParam {
  uid: long
  deviceAddress: String
  deviceName: String
  data: List<SleepList> {
    date: String
    st: int                    // sleep start time offset
    et: int                    // sleep end time offset
    detail: List<SleepDetail> {
      d: int                   // sleep stage type
      t: int                   // duration at that stage
    }
  }
}
```

#### SportDetailRequest (J05089)
```
SportDetailRequest {
  uid: long
  datas: List<SportDetailItem> {
    rawType: int               // sport type code
    sportMode: String          // sport mode name
    startTime: long            // start timestamp
    duration: long             // duration in seconds
    step: int                  // step count
    distance: float            // distance (km)
    calorie: float             // calories (kcal)
    heartrates: List<Integer>  // HR values during sport
    mRateAvg: int              // average HR (default 90)
    sportCount: int            // sport count
    deviceId: String
    deviceType: String
  }
}
```

#### TemperatureRequest (J05092)
```
TemperatureRequest {
  uid: long
  deviceAddress: String
  deviceName: String
  data: List<TemperatureDetail> {
    dateStr: String            // measurement date
    content: List<Float>       // temperature readings (°C)
  }
}
```

#### GoalSettingRequest (J05095)
```
GoalSettingRequest {
  uid: long
  weight: int                 // target weight (kg)
  steps: int                  // target steps
  mile: int                   // target distance (miles)
  calorie: int                // target calories
  sportTime: int              // target sport time (minutes)
  deepSleep: int              // target deep sleep (minutes)
  sleep: int                  // target total sleep (minutes)
}
```

---

### 3.6 Response DTOs — Download Protocol

#### HeartRateResp (J05111)
```
HeartRateResp {
  uid: long
  date: String
  deviceId: String
  deviceType: String
  interval: int               // sampling interval
  updateTime: long
  data: HeartDetail {
    indexs: List<Integer>     // time offsets
    values: List<Integer>     // HR values (bpm)
  }
}
```

#### SleepDetailResp (J05114) — Original Protocol
```
SleepDetailResp {
  uid: long
  date: String
  deviceId: String
  deviceType: String
  intervar: int               // interval
  indexs: List<Integer>       // time offsets
  qualitys: List<Integer>     // sleep quality values
  updateTime: long
}
```

#### SleepDetailNewProtocolResp (J05113) — V1 Protocol
```
SleepDetailNewProtocolResp {
  uid: long
  date: String
  deviceAddress: String
  deviceName: String
  st: int                     // sleep start offset
  et: int                     // sleep end offset
  lunchSt: int                // lunch nap start
  lunchEt: int                // lunch nap end
  updateTime: long
  datas: List<SleepDetail> {
    d: int                    // sleep stage type
    t: int                    // duration
  }
}
```

#### SportDetailResp (J05116)
```
SportDetailResp {
  id: long                    // server-assigned ID
  uid: long
  deviceId: String
  deviceType: String
  rawType: int                // sport type code
  sportMode: String
  startTime: long
  duration: float
  step: int
  distance: int
  calorie: int
  heartrates: List<Integer>
  mRateAvg: int               // default 90
  SportCount: int
}
```

#### TemperatureDownResp (J05118)
```
TemperatureDownResp {
  uid: long
  deviceAddress: String
  deviceName: String
  dateStr: String
  temperatures: List<Float>   // temperature readings (°C)
}
```

---

### 3.7 Download Request DTOs — Pagination Pattern

All download requests follow a consistent pattern with `uid` + cursor + page size:

| DTO | Cursor Field | Type | Notes |
|-----|-------------|------|-------|
| `Spo2DownRequest` | `lastSyncId` | long | SpO2 download by last sync ID |
| `BpDownRequest` | `lastSyncId` | long | BP download by last sync ID |
| `TemperatureDownloadRequest` | `from` | long | Temperature download by timestamp |
| `HealthyDataDownRequest` | (implied) | — | Used for HR, sleep, sport, step downloads |

All carry `size: int` for pagination page size.

---

## 4. Cross-Domain Findings

### 4.1 Sync Protocol Architecture

The app uses a **bidirectional sync model** with two distinct flows:

1. **BLE → App → Cloud (Upload):** Device sends health data over BLE → app stores locally → app calls `up*()` API endpoints to commit to server. Upload requests carry full detail arrays (`datas[]`).

2. **Cloud → App (Download):** App calls `down*()` API endpoints with cursor-based pagination (`lastSyncId` or `from` + `size`). Server returns `List<Resp>` items.

3. **Sync gating:** `doServer()` in MainActivity gates sync-from-server at 12-hour intervals and only uploads if BLE is connected.

### 4.2 Sleep Dual-Protocol

The app supports **two sleep data protocols**:

| Aspect | Original (v0) | V1 (new) |
|--------|---------------|----------|
| Upload | `SleepDetailRequest` → `sleep/commit` | `CommitSleepNewProtocolParam` → `sleep/commit/v1` |
| Download | `HealthyDataDownRequest` → `sleep/sync-from-time` | `HealthyDataDownRequest` → `sleep/sync-from-time/v1` |
| Data model | `indexs[]` + `qualitys[]` + `intervar` | `st`/`et` + `SleepList[]` → `SleepDetail(d,t)` |
| Lunch nap | Not supported | `lunchSt`/`lunchEt` |
| Device ID | `deviceId` + `deviceType` | `deviceAddress` + `deviceName` |

### 4.3 HRV Support

HRV is explicitly supported as a **device capability flag** (`OneKeySupport.supportHrv`) and a **device setting** (`DeviceSetting.hrvEnable`). However, there is **no dedicated HRV API endpoint** in QcService. HRV data likely rides on the `heart-rate-interval/commit` and `heart-rate-interval/sync-from-time` endpoints, using the same `HeartRateIntervalRequest`/`HeartRateResp` structure with different interval values.

### 4.4 Device Capability Discovery Flow

The app uses a **three-tier capability system**:

1. **`DeviceFunctionSupport`** — broad feature flags (21 booleans) for the full device class
2. **`DeviceFunctionTouchOnlySupport`** — subset (17 booleans) for touch-only devices
3. **`OneKeySupport`** — per-device MAC-addressed probe (9 booleans) for health-specific capabilities

The `OneKeySupport` bean is the most relevant for health data: it explicitly gates `supportBloodOxygen`, `supportBloodPressure`, `supportHrv`, `supportTemp`, `supportManualHeart`, `supportPressure`.

### 4.5 Temperature Data Model

Temperature uses **float** values (°C), unlike all other health metrics which use integers. The upload (`TemperatureRequest`) and download (`TemperatureDownResp`) both carry `List<Float>` temperature readings per day.

---

## 5. Domain Coverage Matrix

| Domain | Files | API Endpoints | Request Beans | Response Beans | Capability Flags |
|--------|-------|---------------|---------------|----------------|-----------------|
| **hr** | J05028, J05049, J05061, J05062, J05064, J05067, J05085, J05111 | `heart-rate-interval/commit`, `heart-rate-interval/sync-from-time` | `HeartRateIntervalRequest` | `HeartRateResp` | `supportHeartMeasure`, `supportRealTimeHr`, `supportManualHeart` |
| **hrv_regular** | J05049, J05064, J05067 | (rides on HR endpoints) | (same as HR) | (same as HR) | `supportHrv`, `hrvEnable` |
| **spo2** | J05028, J05049, J05061, J05062, J05064, J05067, J05080, J05088 | `spo2/commit-list`, `spo2/sync-from-id`, `spo2/sync-from-id/v1` | `BloodOxygenRequest`, `Spo2DownRequest` | `Spo2DownResp` | `supportBloodOxygen`, `bo2Detection` |
| **bp** | J05049, J05064, J05067, J05081, J05082 | `blood-pressure/commit-list`, `blood-pressure/sync-from-id` | `BloodPressureRequest`, `BpDownRequest` | `BpDownResp` | `supportBloodPressure`, `bpSwitch` |
| **sleep** | J05028, J05049, J05083, J05086, J05087, J05113, J05114 | `sleep/commit`, `sleep/commit/v1`, `sleep/sync-from-time`, `sleep/sync-from-time/v1` | `SleepDetailRequest`, `CommitSleepNewProtocolParam` | `SleepDetailResp`, `SleepDetailNewProtocolResp` | — |
| **steps_sport** | J05028, J05049, J05089, J05095, J05116 | `step/commit`, `step/sync-from-time`, `sport/commit`, `sport/sync-from-id` | `SportDetailRequest`, `StepDetailRequest` | `SportDetailResp`, `StepDetailResp` | — |
| **temperature** | J05028, J05049, J05061, J05062, J05064, J05067, J05091, J05092, J05118 | `temperature/commit`, `temperature/sync-from-id` | `TemperatureRequest`, `TemperatureDownloadRequest` | `TemperatureDownResp` | `supportSkinTemperature`, `supportNoSingleTemperature`, `supportTemp`, `tempDetection` |
| **sync_scheduler** | J05028, J05049 | (orchestration in `doServer()`) | — | — | — |
| **ble_connection** | J05028, J05029, J05031, J05061, J05062 | — | — | — | `supportBlePair` |

---

## 6. Low-Signal / Domain-Irrelevant Files

The following 7 files (J05139–J05151) belong to the image picker/cropper subsystem and carry **no health, BLE, or sync semantics**:

| Ledger ID | Class | Purpose |
|-----------|-------|---------|
| J05139 | `BitmapCroppingWorkerTask` | Background bitmap crop worker |
| J05140 | `BitmapLoadingWorkerTask` | Background bitmap load worker |
| J05141 | `BitmapUtils` | Bitmap utility methods |
| J05143 | `CropImageActivity` | Image cropping activity |
| J05145 | `CropImageOptions` | Crop configuration bean |
| J05146 | `CropImageView` | Custom crop image view |
| J05150 | `ImagePicker` | Image picker launcher |
| J05151 | `Utils` | FileProvider URI helper |

These are included in the chunk due to package proximity but should be excluded from health-data analysis.

---

## 7. Open Questions & Next Steps

1. **HRV data transport:** No dedicated HRV endpoint exists. Need to trace how `hrvEnable` flag translates to actual BLE command flow and whether HRV data uses the `heart-rate-interval` endpoints or a separate channel.

2. **HealthyDataDownRequest:** This request bean is referenced in QcService but not in CH0010. It likely lives in another chunk. Need to locate and analyze its fields (probably `uid` + `from`/`lastSyncId` + `size`).

3. **Sleep d/t encoding:** The `d` field in `SleepDetail`/`CommitSleepNewProtocolParam.SleepDetail` encodes sleep stage type. Need to find the enum mapping (likely: 0=awake, 1=light, 2=deep, 3=REM or similar).

4. **Sport rawType mapping:** The `rawType` integer in sport requests/responses maps to sport types. Need to find the sport type enum.

5. **Spo2DownResp / BpDownResp / StepDetailResp / StepDetailRequest:** These response/request beans are referenced in QcService but not in CH0010. Need to locate in other chunks.

6. **NetService.upAll() / downAll():** The actual implementation of these sync orchestrator methods lives in `NetService` (not in CH0010). Need to trace to understand which specific endpoints are called in sequence.

7. **Collection data:** `upCollectionData()` is called separately from `upAll()`. Need to understand what "collection data" means vs regular health data upload.
