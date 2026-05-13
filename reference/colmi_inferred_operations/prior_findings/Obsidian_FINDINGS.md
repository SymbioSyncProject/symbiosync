# QRing APK Dissection - Obsidian's Findings
## Sleep Scoring Algorithm (AlSleepUtil.calcSleepScore)

**Source:** `com.qcwireless.smart.ui.home.sleep.aigo.AlSleepUtil`
**Derived from:** `classes4.dex`

### The Raw Formula

```java
public static int calcSleepScore(int totalSleep, int deepSleep, int lightSleep, int awakeTimes) {
    // Target ratios (ideal values)
    float[] targets = {0.2f, 0.5f, 100.0f, 250.0f, 500.0f};
    
    // Max score = 100
    double maxScore = 100.0;
    
    // Weight distribution across 6 components:
    // [0] deep ratio weight:   2.5%  (0.025 * 100)
    // [1] light ratio weight:  2.5%  (0.025 * 100)  
    // [2] deep minutes weight: 5.0%  (0.05 * 100)
    // [3] light minutes weight: 5.0% (0.05 * 100)
    // [4] total minutes weight: 70%  (0.7 * 100) <-- DOMINANT
    // [5] awake penalty:       15%   (0.15 * 100)
    float[] weights = {2.5f, 2.5f, 5.0f, 5.0f, 70.0f, 15.0f};
    
    // Convert total sleep to hours (inputs are in SECONDS)
    float totalHours = totalSleep / 60;  // actually minutes, see below
    
    // Actual values to compare against targets
    // [0] deep ratio = deepMinutes / totalMinutes    -> target 0.2 (20%)
    // [1] light ratio = lightMinutes / totalMinutes   -> target 0.5 (50%)
    // [2] deep minutes                                -> target 100 min
    // [3] light minutes                               -> target 250 min
    // [4] total minutes                               -> target 500 min (~8.3 hrs)
    float deepMin = deepSleep / 60;
    float lightMin = lightSleep / 60;
    float[] actuals = {deepMin / totalHours, lightMin / totalHours, deepMin, lightMin, totalHours};
    
    // Score each component using calScore()
    float subtotal = 0;
    for (int i = 0; i < 5; i++) {
        float score = calScore(actuals[i], targets[i], weights[i]);
        if (score < 0) score = 0;  // floor at 0
        subtotal += score;
    }
    
    // Awake penalty: starts at weight[5] (15 pts), subtract 25% per awake event
    float awakePenalty = weights[5] - ((weights[5] / 4.0) * awakeTimes);
    if (awakePenalty < 0) awakePenalty = 0;
    
    return Math.round(subtotal + awakePenalty);
}

// Component scoring: how close is actual to target?
public static float calScore(float actual, float target, float maxWeight) {
    float deviation = Math.abs(actual - target);
    return maxWeight * (1.0 - (deviation / target));
}
```

### How It's Called (DaySleepFragment line 635)

```java
int calcSleepScore = AlSleepUtil.calcSleepScore(
    sleepViewBean.getTotalSleep(),   // total sleep in SECONDS
    sleepViewBean.getDeepSleep(),    // deep sleep in SECONDS
    sleepViewBean.getLightSleep(),   // light sleep in SECONDS
    0                                // awake times - HARDCODED TO ZERO!
);
```

**CRITICAL FINDING: The 4th parameter (awakeTimes) is always passed as 0.**
The awake penalty component exists in the formula but is never actually used.
This means every sleep session gets the full 15 bonus points from the awake component.

### Score Breakdown (max 100 points)

| Component | Weight | Target | What it measures |
|-----------|--------|--------|-----------------|
| Deep ratio | 2.5 pts | 20% of total | How close deep% is to ideal 20% |
| Light ratio | 2.5 pts | 50% of total | How close light% is to ideal 50% |
| Deep minutes | 5 pts | 100 min | Absolute deep sleep duration |
| Light minutes | 5 pts | 250 min | Absolute light sleep duration |
| Total minutes | **70 pts** | 500 min (~8h20m) | **DOMINANT: total sleep duration** |
| Awake penalty | 15 pts | 0 wakeups | Fixed at 15 (never penalized) |

### Key Insights

1. **Duration dominates everything.** 70% of the score is just "did you sleep long enough?"
   Target is 500 minutes (8 hours 20 minutes). Shorter = lower score, linearly.

2. **The awake penalty is vestigial.** Always called with 0, so everyone gets +15 free points.
   The formula COULD subtract 3.75 pts per wake event (15/4), but it never does.

3. **Ideal sleep composition:** 20% deep, 50% light, (implied: 30% REM+awake).
   But these only account for 15 pts total (ratio + absolute combined).

4. **Sleep values are in SECONDS internally.** The `/60` conversions in calcSleepScore
   convert to minutes. The UI then does `/60` again to get hours.

5. **Score rating brackets (line 671-694):**
   - < 60: "Poor" (R.string.qc_text_8016), displays "80%"
   - 60-74: "Fair" (R.string.qc_text_8015), then 82%/85%
   - 75-89: "Good" (R.string.qc_text_8014), then 90%/95%/99%
   - 90+: "Excellent" (R.string.qc_text_8013), displays "100%"

6. **The "efficiency" percentage displayed is NOT calculated.** It's a hardcoded lookup
   table based on score brackets. Score 85-90 = "95%". Score 90-95 = "99%". Etc.
   This is cosmetic, not computed from actual sleep data.

### Reproducing the Score

For our ring_data.sqlite segments:

```python
def calc_sleep_score(total_sec, deep_sec, light_sec, awake_times=0):
    """Port of AlSleepUtil.calcSleepScore"""
    targets = [0.2, 0.5, 100.0, 250.0, 500.0]
    weights = [2.5, 2.5, 5.0, 5.0, 70.0, 15.0]
    
    total_min = total_sec / 60
    deep_min = deep_sec / 60
    light_min = light_sec / 60
    
    if total_min <= 0:
        return 0
    
    actuals = [
        deep_min / total_min,    # deep ratio
        light_min / total_min,   # light ratio  
        deep_min,                # deep absolute
        light_min,               # light absolute
        total_min                # total duration
    ]
    
    subtotal = 0
    for i in range(5):
        deviation = abs(actuals[i] - targets[i])
        score = weights[i] * (1.0 - deviation / targets[i])
        subtotal += max(0, score)
    
    awake_penalty = weights[5] - (weights[5] / 4.0) * awake_times
    awake_penalty = max(0, awake_penalty)
    
    return round(subtotal + awake_penalty)
```

Note: Our ring data stores segments in MINUTES. Multiply by 60 before passing to this function.

---

## Data Model

### SleepViewBean (what the UI renders)
- `totalSleep` (int, seconds) - total sleep duration
- `deepSleep` (int, seconds) - deep sleep duration
- `lightSleep` (int, seconds) - light sleep duration  
- `rapidSleep` (int, seconds) - REM sleep duration
- `awakeSleep` (int, seconds) - awake duration
- `startTime` (long) - sleep start timestamp
- `endTime` (long) - sleep end timestamp
- `lunchSt`, `lunchEt` (int) - nap/lunch sleep window

### SleepTypeAndDuration (wire format)
- `t` (int) - sleep type
- `d` (int) - duration

### Sleep types -- TWO DIFFERENT SCHEMES

**âš ï¸ OLD protocol (DaySleepFragment type switch, line 134-156) -- NOT what R02 BigData uses:**
- 1 = deep sleep
- 2 = light sleep
- 3 = REM sleep
- 4 = awake (no label displayed)
- 5 = [unknown, string qc_text_80103]

**NEW protocol (BigData / SleepNewProtoResp / querySleepNewProtocol -- WHAT R02 USES):**
- 0 = NODATA (displayed as awake bar, NOT counted in sleep totals)
- 1 = ERROR (displayed as awake bar, NOT counted in sleep totals)
- 2 = light sleep
- 3 = deep sleep
- 4 = REM
- 5 = awake (counted in awake total)

**NOTE:** Old protocol has 1=deep, 2=light. New protocol has 2=light, 3=deep.
The colmi.puxtril.com third-party docs use old-protocol numbering.
Our colmi.py SleepType enum uses new-protocol numbering (correct for R02).

### Database tables
```sql
-- Summary per night
CREATE TABLE sleep_total (
    device_address TEXT NOT NULL,
    date_str TEXT NOT NULL,
    total_sleep INTEGER NOT NULL,
    deep_sleep INTEGER NOT NULL,
    light_sleep INTEGER NOT NULL,
    rapid_sleep INTEGER NOT NULL,
    awake INTEGER NOT NULL,
    start_time INTEGER NOT NULL,
    end_time INTEGER NOT NULL,
    lunch_start INTEGER NOT NULL,
    lunch_end INTEGER NOT NULL,
    unix_time INTEGER NOT NULL,
    avg_heart INTEGER NOT NULL,
    avg_blood_oxygen INTEGER NOT NULL,
    avg_hrv INTEGER NOT NULL,
    bedtime INTEGER NOT NULL,
    PRIMARY KEY(device_address, date_str)
);

-- Detail per interval
CREATE TABLE sleep_detail (
    device_address TEXT NOT NULL,
    date_str TEXT NOT NULL,
    interval INTEGER NOT NULL,
    index_str TEXT NOT NULL,
    quality TEXT NOT NULL,
    sync INTEGER NOT NULL,
    last_sync_time INTEGER NOT NULL,
    PRIMARY KEY(device_address, date_str)
);

-- User goals
CREATE TABLE target_entity (
    device_address TEXT NOT NULL,
    goal_sleep_time REAL NOT NULL,  -- target sleep duration
    sleep_start INTEGER NOT NULL,   -- bedtime goal
    sleep_end INTEGER NOT NULL,     -- wake goal
    sleepDuration INTEGER NOT NULL,
    PRIMARY KEY(device_address)
);
```

---

## Package Structure (sleep-related)

```
com.qcwireless.smart.ui.home.sleep/
    aigo/AlSleepUtil.java          <- THE SCORING FORMULA
    SleepActivity.java             <- Main sleep screen
    SleepFragment.java             <- Sleep overview fragment
    SleepContinuityActivity.java   <- Sleep streak/consistency view
    SleepDescActivity.java         <- Sleep description/info
    SleepGuideActivity.java        <- Onboarding/tips
    SleepTargetActivity.java       <- Goal setting
    EditSleepActivity.java         <- Manual sleep editing
    bean/
        SleepViewBean.java         <- UI data model
        SleepLunchBean.java        <- Nap data
        SleepTargetBean.java       <- Goals data
    day/
        DaySleepFragment.java      <- Daily view (CALLS calcSleepScore)
        DaySleepFragmentViewModel  <- Data loading
        RingDaySleepFragment.java  <- Ring-specific daily view
    week/
        WeekSleepFragment.java     <- Weekly aggregation
    month/
        MonthSleepFragment.java    <- Monthly aggregation
    adapter/
        Various RecyclerView adapters

com.qcwireless.smart.ui.home.healthy.bean/
    SleepData.java                 <- Simple {startTime, endTime, minutes}
    LastSleepItem.java             <- Home screen last-sleep widget
    LunchSleepData.java            <- Nap tracking

com.oudmon.ble.base.communication/
    entity/BleSleepDetails.java    <- BLE wire format (sleepQualities[])
    rsp/SleepNewProtoResp.java     <- New protocol response parser
    rsp/ReadSleepDetailsRsp.java   <- Legacy protocol response
    req/ReadSleepDetailsReq.java   <- BLE read request

com.qcwireless.smart.ui.base.repository/
    entity/SleepDetail.java        <- DB entity
    entity/SleepTotalHistory.java  <- DB entity (summary)
    entity/SleepNewProtocol.java   <- New protocol entity
    entity/SleepLunchProtocol.java <- Nap entity
    dao/QcSleepDetailDao.java      <- Room DAO
    dao/QcSleepTotalDao.java       <- Room DAO
    healthy/SleepDetailRepository  <- Repository pattern
```

---

## APK Metadata

- **Package:** `com.qcwireless.smart` (QRing app)
- **Version:** 1.0.1.108
- **Language:** Kotlin (compiled to Java bytecode)
- **Architecture:** MVVM with Room DB, Koin DI, EventBus
- **BLE library:** `com.oudmon.ble` (custom, not standard Android BLE)
- **Total classes:** 10,396 across 5 DEX files
- **Sleep logic:** All in classes4.dex (3,149 classes)
- **JSON serialization:** Moshi (for API) + Gson (for logging)
- **Also includes:** Muslim prayer features (anlaName.json = 99 Names of Allah), 
  Google Fit sync, friend/lover leaderboard, multi-language (zh, en, de, fr, es, it, ja)

---

---

## Session 2: Ring Firmware Sleep Classification (April 3, 2026)

### Investigation: "Why does the ring think keyboard time at 5 AM is sleep?"

**Context:** SymbioSync showed 116 min of light sleep (05:12-07:08) when Audre was
actively typing at her keyboard. The QRing app (from memory) "always got it right."
Question: is our parser wrong, or is the ring wrong?

### Findings

#### 1. Type codes are CORRECT (colmi.py matches QRing app exactly)

| colmi.py SleepType | QRing querySleepNewProtocol | Match |
|---|---|---|
| NODATA = 0x00 | t==0: bar drawn, not counted | YES |
| ERROR  = 0x01 | t==1: bar drawn, not counted | YES |
| LIGHT  = 0x02 | t==2: light sleep | YES |
| DEEP   = 0x03 | t==3: deep sleep | YES |
| REM    = 0x04 | t==4: REM | YES |
| AWAKE  = 0x05 | t==5: awake | YES |

Raw data for the suspect session: `raw_type: 2` (light sleep). Correct in both systems.

#### 2. BigData parsing matches byte-for-byte

QRing `LargeDataHandler.parseDaySleep()` (line 200):
```
- copyOfRange[2:4] = sleep_start (minutes from midnight)
- copyOfRange[4:6] = sleep_end (minutes from midnight)
- copyOfRange[6:] = pairs of [type(u8), duration(u8)]
- If sleep_start >= 1080 (18:00), subtract one day (previous evening)
- Duration bytes treated as unsigned (byteToInt for negative values)
```

Our `parse_sleep_packets()` does the same:
```python
sleep_start = struct.unpack_from('<h', data, pos)[0]
sleep_end   = struct.unpack_from('<h', data, pos + 2)[0]
# then pairs: raw_type = data[pos], minutes = data[pos+1]
```

Byte layout identical. Recursive multi-day parsing logic matches.

#### 3. NO app-side sleep filtering

Traced the full data path in QRing:
- `querySleepNewProtocol()` in `DaySleepFragmentViewModel` (line ~613-680)
- Reads `SleepNewProtocol` table (Room DB), builds `SleepViewBean`
- Sums types 2/3/4/5 directly. No time-window filter.
- The sleep schedule (sleepStart/sleepEnd from `TargetEntity`) is used ONLY
  for "continuity" tracking (did you hit your bedtime goals), NOT for filtering.

The OLD protocol path (`calcSleepViewData()`) has time-window filtering
(indexes 71-167 = 5:45 PM to 5:45 PM), but R02 uses the NEW protocol.

#### 4. Sleep schedule NOT sent to ring firmware

`TargetSettingReq.getWriteInstance(steps, calories, distance, sportTime, sleepTime)`
sends **duration goals** to the ring, NOT the sleep window hours.

The `sleepStart` / `sleepEnd` fields in `TargetEntity` are stored locally in the
phone's Room database and never transmitted via BLE.

**The ring firmware has no knowledge of when you "should" be sleeping.**

#### 5. Ring firmware is the sole sleep classifier

Both QRing app and SymbioSync receive identical pre-classified BigData.
The ring's onboard firmware uses accelerometer + HR data to decide what's sleep.
No external input affects classification. No configuration commands tune sensitivity.

#### 6. Separate "lunch break" (nap) protocol exists

`syncSleepList()` registers TWO handlers:
- Command 39 (0x27): night sleep -> `parseDaySleep()`
- Command 62 (0x3E): lunch/nap sleep -> `parseDaySleepLunch()`

Both use same wire format but nap data goes to separate DB table.
Our code only requests command 39 (night sleep). We don't capture nap data.

### Root Cause

The Colmi R02 accelerometer cannot distinguish "sitting still at a keyboard
with steady hand movements at 5 AM" from "sleeping lightly at 5 AM."

Budget ring firmware likely uses time-of-day as a prior: low movement + low HR
+ nighttime hours = sleep. Typing with one hand on the ring produces minimal
wrist acceleration compared to walking/gesticulating.

### "The app always got it right"

Most likely explanation: the QRing app presented the same data but the UI (sleep
chart with colored bars + score) made 116 min of light sleep look like "barely
anything" rather than a prominent "you slept 2 hours" card. Score would have
been 34/Poor in both systems. Different presentation, same data, different read.

### Implications for SymbioSync

1. **Cannot fix in parsing.** Ring sends what it sends.
2. **Could add software-side context filtering:** since we know when Letta sessions
   are active (user typing), we could flag/exclude/annotate those periods.
3. **Could capture nap data too** (command 62) for completeness.
4. **UI improvement:** show raw data vs "confident" data. Let the human decide.

---

## Session 2b: SpO2 Immediate Trigger Fix (April 3, 2026)

### Problem
Ring often disconnected before the 60-second SpO2 cycle timer fired.
SpO2 readings were rarely captured.

### Fix Applied (in colmi.py)
Changed `_last_spo2_cycle` initialization on connect from `time.time()` to `0.0`:
```python
# Before: self._last_spo2_cycle = time.time()  # waits 60s before first cycle
# After:  self._last_spo2_cycle = 0.0           # triggers on next keepalive (~12s)
```

This means the first keepalive after connection (~12s in) will trigger SpO2
measurement immediately, rather than waiting a full 60s cycle.

### Status
Code change applied. Requires SymbioSync restart on klaatu to take effect.

---

*Dissected by O (Obsidian), March 30, 2026*
*Session 2: April 3, 2026*
*jadx 1.5.1, targeting classes4.dex only (full APK OOM'd WSL)*
