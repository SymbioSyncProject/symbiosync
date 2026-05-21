# QRing Decompiled Walkthrough — 2026-05-18

**Analyst:** Sibling analyst (decompiled APK static analysis)
**Source:** `D:\feedback\qring\decompiled4\sources` (richer jadx output, 4,372 .java files)
**Purpose:** Walk through each relevant class with methods, request IDs, byte arrays, command names, response parsing, and lifecycles. Document the full protocol stack from BLE connection to biometric data delivery.

---

## 1. BLE Connection & Service Discovery

### 1.1 Constants (`com.oudmon.ble.base.communication.Constants`)

The entire protocol operates on two GATT service UUIDs:

| Constant | UUID | Purpose |
|---|---|---|
| `a` (Service) | `6e40fff0-b5a3-f393-e0a9-e50e24dcca9e` | **Nordic UART Service** — small commands (16-byte packets) |
| `b` (Notify) | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` | UART TX (device → phone) |
| `c` (Write) | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` | UART RX (phone → device) |
| `d` (Descriptor) | `00002902-0000-1000-8000-00805f9b34fb` | CCCD for notification enable |
| `e` (Device Info Service) | `0000180a-0000-1000-8000-00805f9b34fb` | Device Information Service |
| `f` (FW Version) | `00002a26-0000-1000-8000-00805f9b34fb` | Firmware Revision String |
| `g` (HW Version) | `00002a27-0000-1000-8000-00805f9b34fb` | Hardware Revision String |
| `i` (LargeData Service) | `de5bf728-d711-4e47-af26-65e3012a5dc7` | **Custom large-data service** |
| `j` (LargeData Notify) | `de5bf729-d711-4e47-af26-65e3012a5dc7` | Large-data TX (device → phone) |
| `k` (LargeData Write) | `de5bf72a-d711-4e47-af26-65e3012a5dc7` | Large-data RX (phone → device) |
| `l` (Packet length) | `16` | Default UART packet length |
| `m` (High-bit mask) | `128` (0x80) | **`data[0] & ~m` strips the high bit for command ID lookup** |

**Critical insight:** `Constants.m = 128` means `data[0] & 0x7F` is the standard command ID extraction. The high bit (0x80) is a flag — likely a "notification" vs "response" indicator. This confirms the SymbioSync parser's `data[0] & 0x7F` masking is correct.

### 1.2 BleBaseControl (`com.oudmon.ble.base.bluetooth.BleBaseControl`)

Singleton managing the raw BLE connection.

**Key lifecycle:**
1. `connect(address)` → `remoteDevice.connectGatt(context, false, callback, TRANSPORT_LE)`
2. `onConnectionStateChange` → if `newState==2` (connected): `discoverServices()`, 40s timeout
3. `onServicesDiscovered` → `bleServiceDiscovered` callback → `BleOperateManager.enableUUID()`
4. `onCharacteristicChanged` → `IBleListener.bleCharacteristicChanged(address, uuid, value)`
5. Reconnection: up to 10 retries (`this.i=10`), 6 inner-fail loops (`this.j=6`), 2s delay between attempts

**Timeouts:**
- Connection timeout: 40s (`postDelayed(v, 40000L)`)
- Service discovery timeout: 40s (`postDelayed(u, 40000L)`)
- Reconnect delay: 1s direct, or scan+connect

### 1.3 BleOperateManager (`com.oudmon.ble.base.bluetooth.BleOperateManager`)

HandlerThread that serializes all BLE operations.

**Initialization:**
- Registers 3 broadcast receivers: `QCBluetoothCallbackReceiver` (small data), `QCBluetoothCallbackCloneReceiver` (empty), `QCBluetoothCallbackBigDataCloneReceiver` (large data)
- Pre-registers notify listeners: `29`→MusicCommand, `2`→Camera, `47`→PackageLength, `115`→DeviceNotify, `120`→SportNotify

**`execute(BaseRequest)`:**
1. Checks Bluetooth enabled + connected
2. Posts to background handler with 5s lock timeout
3. Finds `BluetoothGattCharacteristic` via `BleBaseControl.findTheGattCharacteristic(serviceUUID, charUUID)`
4. Calls `baseRequest.execute(gatt, characteristic)`
5. Waits for response via `waitUntilActionResponse()` (synchronized on `this.c`)

**`enableUUID()`:**
- Enables notifications on `Constants.a` (UART service) + `Constants.b` (notify char)
- 4s timeout fallback

**Broadcast actions (from `BleAction`):**
| Action | Purpose |
|---|---|
| `com.swatchdevice.pro.characteristic_changed_qc` | Notification received |
| `com.swatchdevice.pro.characteristic_write_qc` | Write completed |
| `com.swatchdevice.pro.sdk.ble.gatt_connected` | GATT connected |
| `com.swatchdevice.pro.sdk.ble.gatt_disconnected` | GATT disconnected |
| `com.swatchdevice.pro.sdk.ble.service_discovered` | Services discovered |
| `com.swatchdevice.pro.sdk.ble.characteristic_notification_qc` | Notification enabled |
| `com.swatchdevice.pro.sdk.ble.BLE_NO_CALLBACK` | No BLE callback (timeout) |
| `com.swatchdevice.pro.sdk.ble.BLE_STATUS` | BLE status change |

---

## 2. Small-Data Protocol (UART Service)

### 2.1 Packet Format

**Outbound (phone → ring):**
```
[cmdByte, subData[0], subData[1], ..., subData[n-1], CRC]
```
- Total length: `Constants.l = 16` bytes
- `cmdByte` at index 0
- CRC at last byte: sum of all preceding bytes, `& 0xFF`

**Inbound (ring → phone):**
```
[cmdByte | flags, payload[0], payload[1], ..., payload[n-2], CRC]
```
- `cmdByte & ~0x80` extracts the command ID
- CRC at last byte: same checksum
- Payload is `bArr[1..length-2]` (strips cmdByte and CRC)

### 2.2 BaseReqCmd (`com.oudmon.ble.base.communication.req.BaseReqCmd`)

```java
abstract class BaseReqCmd {
    byte a;  // command byte

    BaseReqCmd(byte b) { this.a = b; }

    byte[] getData() {
        byte[] bArr = new byte[Constants.l];  // 16 bytes
        bArr[0] = this.a;
        byte[] subData = getSubData();
        if (subData != null) {
            System.arraycopy(subData, 0, bArr, 1, subData.length);
        }
        addCRC(bArr);
        return bArr;
    }

    abstract byte[] getSubData();

    void addCRC(byte[] bArr) {
        int i = 0;
        for (int i2 = 0; i2 < bArr.length - 1; i2++) {
            i += bArr[i2];
        }
        bArr[bArr.length - 1] = (byte) (i & 255);
    }
}
```

**Key insight:** All small-data packets are exactly 16 bytes. The command byte is at `[0]`, sub-data fills `[1..n]`, unused bytes are zero, and CRC is at `[15]`.

### 2.3 MixtureReq (`com.oudmon.ble.base.communication.req.MixtureReq`)

```java
abstract class MixtureReq extends BaseReqCmd {
    byte[] b;  // sub-data

    MixtureReq(byte cmd) { super(cmd); }

    byte[] getSubData() { return this.b; }
}
```

Used for "setting" commands that have a read/write action byte.

### 2.4 CommandHandle (`com.oudmon.ble.base.communication.CommandHandle`)

Singleton that bridges `BaseReqCmd` → BLE write.

```java
void executeReqCmd(BaseReqCmd baseReqCmd, ICommandResponse iCommandResponse) {
    if (!BleOperateManager.getInstance().isConnected()) return;
    LocalWriteRequest writeRequest = getWriteRequest(baseReqCmd.getData());
    int i = writeRequest.getValue()[0] & (~Constants.m);  // strip 0x80
    writeRequest.setiOpResponse(iCommandResponse);
    if (iCommandResponse != null) {
        BleOperateManager.getInstance().getLocalWriteRequestConcurrentHashMap()
            .put(Integer.valueOf(i), writeRequest);
    }
    BleOperateManager.getInstance().execute(writeRequest);
}
```

**`getWriteRequest(byte[])`** creates a `LocalWriteRequest` with `Constants.a` (service) + `Constants.c` (write char).

### 2.5 QCBluetoothCallbackReceiver — Small-Data Routing

```java
void onCharacteristicChange(String str, String str2, byte[] bArr) {
    if (bArr == null || bArr.length != Constants.l || !QCDataParser.checkCrc(bArr)) return;
    if (!QCDataParser.parserAndDispatchReqData(bArr)) {
        QCDataParser.parserAndDispatchNotifyData(
            BleOperateManager.getInstance().getNotifySparseArray(), bArr);
    }
}
```

**Routing logic:**
1. Validate: length must be 16, CRC must pass
2. Try request-response matching first (`parserAndDispatchReqData`)
3. If no match, try notify listener matching (`parserAndDispatchNotifyData`)

### 2.6 QCDataParser — Command Dispatch

```java
static boolean parserAndDispatchReqData(byte[] bArr) {
    int i = bArr[0] & (~Constants.m);  // strip 0x80
    LocalWriteRequest req = BleOperateManager.getInstance()
        .getLocalWriteRequestConcurrentHashMap().get(Integer.valueOf(i));
    if (req == null) return false;
    ICommandResponse callback = req.getiOpResponse();
    BaseRspCmd rsp = a.get(i);  // cached partial response
    if (rsp == null) {
        rsp = BeanFactory.createBean(i, req.getType());
    }
    if (rsp != null) {
        rsp.setCmdType(i);
        if (rsp.acceptData(Arrays.copyOfRange(bArr, 1, bArr.length - 1))) {
            a.put(i, rsp);  // cache for multi-packet
            return true;
        }
        callback.onDataResponse(rsp);
        a.delete(i);
        return true;
    }
    return false;
}
```

**Key insight:** Multi-packet responses are cached in `SparseArray a`. `acceptData` returns `true` if more packets are expected, `false` when complete. The callback fires only when `acceptData` returns `false`.

### 2.7 BeanFactory — Command ID → Response Class Map

| ID | Decimal | Response Class | Biometric? |
|---|---|---|---|
| 1 | 0x01 | `SetTimeRsp` | No |
| 2 | 0x02 | `CameraNotifyRsp` | No |
| 3 | 0x03 | `BatteryRsp` | **Yes** (battery) |
| 5 | 0x05 | `PalmScreenRsp` | No |
| 6 | 0x06 | `DndRsp` | No |
| 7 | 0x07 | `TotalSportDataRsp` | **Yes** (steps) |
| 10 | 0x0A | `TimeFormatRsp` | No |
| 12 | 0x0C | `BpSettingRsp` | **Yes** (BP setting) |
| 13 | 0x0D | `BpDataRsp` | **Yes** (BP data) |
| 17 | 0x11 | `PhoneNotifyRsp` | No |
| 20 | 0x14 | `ReadBlePressureRsp` | **Yes** (BP history) |
| 21 | 0x15 | `ReadHeartRateRsp` | **Yes** (interval HR) |
| 22 | 0x16 | `HeartRateSettingRsp` | **Yes** (HR setting) |
| 25 | 0x19 | `DegreeSwitchRsp` | No |
| 26 | 0x1A | `WeatherForecastRsp` | No |
| 29 | 0x1D | `MusicCommandRsp` | No |
| 30 | 0x1E | `RealTimeHeartRateRsp` | **Yes** (realtime HR) |
| 31 | 0x1F | `DisplayTimeRsp` | No |
| 33 | 0x21 | `TargetSettingRsp` | No |
| 34 | 0x22 | `FindPhoneRsp` | No |
| 38 | 0x26 | `ReadSitLongRsp` | No |
| 40 | 0x28 | `ReadAlarmRsp` | No |
| 44 | 0x2C | `BloodOxygenSettingRsp` | **Yes** (SpO2 setting) |
| 47 | 0x2F | `PackageLengthRsp` | No |
| 50 | 0x32 | `DeviceAvatarRsp` | No |
| 54 | 0x36 | `PressureSettingRsp` | **Yes** (pressure setting) |
| 55 | 0x37 | `PressureRsp` | **Yes** (pressure data) |
| 56 | 0x38 | `HRVSettingRsp` | **Yes** (HRV setting) |
| 57 | 0x39 | `HRVRsp` | **Yes** (HRV data) |
| 58 | 0x3A | `BloodSugarLipidsSettingRsp` | No |
| 59 | 0x3B | `TouchControlResp` | No |
| 60 | 0x3C | `DeviceSupportFunctionRsp` | **Yes** (capability flags) |
| 67 | 0x43 | `ReadDetailSportDataRsp` | **Yes** (step detail) |
| 68 | 0x44 | `ReadSleepDetailsRsp` | **Yes** (sleep detail) |
| 72 | 0x48 | `TodaySportDataRsp` | **Yes** (today sport) |
| 82 | 0x52 | `MuslimRemindRsp` | No |
| 97 | 0x61 | `ReadMessagePushRsp` | No |
| 105 | 0x69 | `StartHeartRateRsp` | **Yes** (measurement start) |
| 114 | 0x72 | `SimpleStatusRsp` | No |
| 115 | 0x73 | `DeviceNotifyRsp` | **Yes** (device notifications) |
| 119 | 0x77 | `AppSportRsp` | No |
| 120 | 0x78 | — | — |
| 122 | 0x7A | `MuslimRsp` | No |
| 123 | 0x7B | `MuslimTargetRsp` | No |
| -223 | 0x21 in unsigned | `AppRevisionResp` | No |

---

## 3. Biometric Command Walkthrough

### 3.1 Heart Rate — Realtime Stream

**Start: `StartHeartRateReq` (cmd 0x69)**

```java
class StartHeartRateReq extends BaseReqCmd {
    byte b;  // type
    byte c;  // param

    // Start realtime HR monitoring
    static StartHeartRateReq getRealtimeHeartRate(byte b) {
        return new StartHeartRateReq((byte) 6, b);
    }

    // Start simple measurement (type < 3 = one-shot, type >= 3 = continuous with 25-min BCD timeout)
    static StartHeartRateReq getSimpleReq(byte b) {
        return new StartHeartRateReq(b, b < 3 ? (byte) 0 : BLEDataFormatUtils.decimalToBCD(25));
    }

    // Start/stop ECG
    static StartHeartRateReq getEcgReqStartAndStop(boolean z) {
        return z ? new StartHeartRateReq((byte) 16, (byte) 1)
                 : new StartHeartRateReq((byte) 16, (byte) 4);
    }

    byte[] getSubData() { return new byte[]{this.b, this.c}; }
}
```

**SymbioSync comparison:** `colmi.py` sends `_packet(0x69, [0x01, 0x01])` which matches `getSimpleReq(1)` — type=1 (HR), param=0 (one-shot). The APK also supports `getRealtimeHeartRate(b)` which sends type=6.

**Response: `StartHeartRateRsp` (cmd 0x69)**

```java
class StartHeartRateRsp extends BaseRspCmd {
    byte c;  // type
    byte d;  // errCode
    int e;   // value (HR bpm or SpO2%)
    int f;   // sbp (if BP)
    int g;   // dbp (if BP)

    boolean acceptData(byte[] bArr) {
        this.c = bArr[0];       // measurement type
        this.d = bArr[1];       // error code (0 = success)
        this.e = bArr[2] & 255; // value
        if (bArr.length >= 5) {
            this.f = bArr[3] < 0 ? bArr[3] & 255 : bArr[3];  // sbp
            this.g = bArr[4] < 0 ? bArr[4] & 255 : bArr[4];  // dbp
        }
        return false;  // single-packet response
    }
}
```

**SymbioSync comparison:** `colmi.py` reads `data[1]` as reading_type, `data[2]` as error_code, `data[3]` as value. The APK reads `bArr[0]` as type, `bArr[1]` as errCode, `bArr[2]` as value. **These are offset by 1** because the APK's `acceptData` receives `bArr[1..length-2]` (stripped cmdByte and CRC), while SymbioSync's `_notification_handler` receives the full 16-byte packet and reads from `data[1]`.

**Alignment check:**
- APK: `bArr = data[1..14]` → `bArr[0]` = `data[1]` = type, `bArr[1]` = `data[2]` = errCode, `bArr[2]` = `data[3]` = value
- SymbioSync: `reading_type = data[1]`, `error_code = data[2]`, `value = data[3]`
- **✅ Aligned!** Both read the same bytes.

**Stop: `StopHeartRateReq` (cmd 0x6A)**

```java
class StopHeartRateReq extends BaseReqCmd {
    byte[] b;

    static StopHeartRateReq stopHeartRate(byte b) {
        return new StopHeartRateReq((byte) 1, b, (byte) 0);
    }
    static StopHeartRateReq stopBloodOxygen(byte b) {
        return new StopHeartRateReq((byte) 3, b, (byte) 0);
    }
    static StopHeartRateReq stopBloodPressure(byte b, byte b2) {
        return new StopHeartRateReq((byte) 2, b, b2);
    }
    static StopHeartRateReq stopHrv(byte b) {
        return new StopHeartRateReq((byte) 10, b, (byte) 0);
    }
    static StopHeartRateReq stopFatigue(byte b) {
        return new StopHeartRateReq((byte) 4, b, (byte) 0);
    }
    static StopHeartRateReq stopHealthCheck() {
        return new StopHeartRateReq((byte) 5, (byte) 0, (byte) 0);
    }
    static StopHeartRateReq stopEcg(int i) {
        return new StopHeartRateReq((byte) 7, (byte) i, (byte) 0);
    }
    static StopHeartRateReq stopPressure(byte b) {
        return new StopHeartRateReq((byte) 8, b, (byte) 0);
    }
    static StopHeartRateReq stopBloodSugar(byte b) {
        return new StopHeartRateReq((byte) 9, b, (byte) 0);
    }
    static StopHeartRateReq stopTemperatureCheck() {
        return new StopHeartRateReq((byte) 11, (byte) 0, (byte) 0);
    }

    byte[] getSubData() { return this.b; }  // [type, param, 0]
}
```

**Stop type map:**
| Type | Measurement |
|---|---|
| 1 | Heart Rate |
| 2 | Blood Pressure |
| 3 | Blood Oxygen (SpO2) |
| 4 | Fatigue |
| 5 | Health Check |
| 7 | ECG |
| 8 | Pressure |
| 9 | Blood Sugar |
| 10 | HRV |
| 11 | Temperature |

**SymbioSync comparison:** `colmi.py` sends `_packet(0x6A, [0x01, 0x00, 0x00])` for HR stop and `_packet(0x6A, [0x03, 0x00, 0x00])` for SpO2 stop. **✅ Aligned** with APK stop types 1 and 3.

### 3.2 Heart Rate — Realtime Notification

**Response: `RealTimeHeartRateRsp` (cmd 0x1E = 30)**

```java
class RealTimeHeartRateRsp extends BaseRspCmd {
    int c;

    boolean acceptData(byte[] bArr) {
        this.c = bArr[0];  // HR value
        return false;
    }

    int getHeart() { return this.c; }
}
```

**Key insight:** This is a **device-initiated notification** (not a request-response). The ring pushes HR values periodically after `StartHeartRateReq` is sent. The command ID 30 is registered in `BleOperateManager`'s notify sparse array, not in the request-response map.

**SymbioSync comparison:** SymbioSync receives these as `data[0] & 0x7F == 0x1E` (30) in `_notification_handler`. However, SymbioSync currently treats ALL notifications with `data[1]` as reading_type and `data[3]` as value. The APK's `RealTimeHeartRateRsp` reads `bArr[0]` as the HR value directly — meaning for realtime HR notifications, the **value is at `data[1]`** (after stripping cmdByte), not `data[3]`.

**⚠️ CRITICAL DISCREPANCY:** SymbioSync reads `value = data[3]` for all notifications. The APK's `RealTimeHeartRateRsp` reads `bArr[0]` = `data[1]` as the HR value. This means:
- For `StartHeartRateRsp` (cmd 0x69): value at `data[3]` → `bArr[2]` ✅
- For `RealTimeHeartRateRsp` (cmd 0x1E): value at `data[1]` → `bArr[0]` ⚠️

**SymbioSync may be reading the wrong byte for realtime HR notifications!** The `data[3]` reading works for `StartHeartRateRsp` (measurement start response), but realtime HR notifications have a different payload layout where the HR value is at `data[1]`.

### 3.3 Heart Rate — Interval History

**Request: `ReadHeartRateReq` (cmd 0x15 = 21)**

```java
class ReadHeartRateReq extends BaseReqCmd {
    byte[] b;

    ReadHeartRateReq(long j) {
        super(Mmi.AU_MMI_DEV_MIC_VOL_UP);  // 0x15
        this.b = DataParseUtils.intToByteArray((int) j);  // 4-byte timestamp
    }

    byte[] getSubData() { return this.b; }
}
```

**Response: `ReadHeartRateRsp` (cmd 0x15 = 21)**

Multi-packet response with 3 phases:

1. **Init packet** (`bArr[0] == 0x00`): `count = bArr[1]`, `range = bArr[2]`, allocate `byte[count * 13]`
2. **First data packet** (`bArr[0] == 0x01`): `dayOffset = bArr[1]`, UTC timestamp from `bArr[2..5]`, copy remaining to array
3. **Continuation packets**: copy 13 bytes at a time, check if `b == count - 1` (last packet)

**Parsed output:** `mHeartRateArray` — 288-byte array (one value per 5-minute interval = 24h × 12 = 288). Values are trimmed to 288 bytes. For today's data, future intervals are zeroed out.

**Range field:** `bArr[2]` in the init packet — likely the measurement interval in minutes (default 5).

### 3.4 Heart Rate — Setting

**Request: `HeartRateSettingReq` (cmd 0x16 = 22)**

```java
class HeartRateSettingReq extends MixtureReq {
    // Read: subData = [1]
    static HeartRateSettingReq getReadInstance() { ... }

    // Write (simple): subData = [2, enable(1/2), interval]
    HeartRateSettingReq(boolean z, int i) { ... }

    // Write (full): subData = [2, enable(1/2), interval, startInterval, tooLow, tooHigh]
    HeartRateSettingReq(boolean z, int i, int i2, int i3, int i4) { ... }
}
```

**Response: `HeartRateSettingRsp` (cmd 0x16 = 22)**

```java
class HeartRateSettingRsp extends MixtureRsp {
    boolean d;  // isEnable
    int e;      // heartInterval (minutes)
    int f;      // startInterval (default 5 if 0)
    int g;      // tooLowReminder
    int h;      // tooHighReminder

    void readSubData(byte[] bArr) {
        this.d = bArr[1] == 1;
        this.e = ByteUtil.byteToInt(bArr[2]);
        int byteToInt = ByteUtil.byteToInt(bArr[3]);
        this.f = byteToInt == 0 ? 5 : byteToInt;
        if (bArr.length > 5) {
            int low = ByteUtil.byteToInt(bArr[4]);
            int high = ByteUtil.byteToInt(bArr[5]);
            if (low > 0) this.g = low;
            if (high > 0) this.h = high;
        }
    }
}
```

### 3.5 HRV

**Request: `HrvSettingReq` (cmd 0x38 = 56)**
- Read: `[1]`
- Write: `[2, enable]`

**Request: `HRVReq` (cmd 0x39 = 57)**
- `[action_byte]`

**Response: `HRVRsp` (cmd 0x39 = 57)**

Multi-packet, same pattern as interval HR:
1. Init (`0x00`): count, range, allocate `count * 13` bytes
2. First data (`0x01`): dayOffset, copy values
3. Continuation: 13 bytes each

**Parsed output:** `hrvArray` (13 bytes per day entry), `offset` (day offset), `range` (measurement interval)

**Response: `HRVSettingRsp` (cmd 0x38 = 56)**
- `bArr[1] == 1` → enabled

### 3.6 Blood Oxygen (SpO2)

**Setting Request: `BloodOxygenSettingReq` (cmd 0x2C = 44)**
- Read: `[1]`
- Write: `[2, enable, interval]`

**Setting Response: `BloodOxygenSettingRsp` (cmd 0x2C = 44)**
- `bArr[1] == 1` → enabled
- `bArr[2]` → interval

**Start/Stop:** Uses `StartHeartRateReq` (0x69) with type=3 for SpO2 start, and `StopHeartRateReq.stopBloodOxygen` (0x6A) with type=3 for stop.

**SymbioSync comparison:** `colmi.py` sends `_packet(0x69, [0x03, 0x01])` for SpO2 start. This matches `StartHeartRateReq` type=3. **✅ Aligned.**

### 3.7 Blood Pressure

**Request: `ReadPressureReq` (cmd 0x14 = 20)**
- Sub-data: 4-byte timestamp + `[0, 0x32]` (fixed suffix)

**Response: `ReadBlePressureRsp` (cmd 0x14 = 20)**
- Per-record: 4-byte timestamp (adjusted for timezone), `bArr[4] & 255` = sbp, `bArr[5] & 255` = dbp
- Up to 50 records per response
- `0xFFFFFFFF` = no data

**Setting: `BpSettingReq` (cmd 0x0C = 12)**
- Read: `[1]`
- Write: `[2, enable, startH, startM, endH, endM, interval]`

### 3.8 Pressure (Stress)

**Request: `PressureReq` (cmd 0x37 = 55)**
- `[action_byte]`

**Response: `PressureRsp` (cmd 0x37 = 55)**
- Multi-packet, same pattern as HRV/HR interval

**Setting: `PressureSettingReq` (cmd 0x36 = 54)**
- Read: `[1]`
- Write: `[2, enable]`

### 3.9 Battery

**Response: `BatteryRsp` (cmd 0x03)**
```java
boolean acceptData(byte[] bArr) {
    this.c = bArr[0];        // battery percentage
    this.d = bArr[1] == 1;   // is charging
    return false;
}
```

**SymbioSync comparison:** `colmi.py` reads `data[1]` as battery% and `data[2]` as charging. APK reads `bArr[0]` (= `data[1]`) as battery% and `bArr[1]` (= `data[2]`) as charging. **✅ Aligned.**

### 3.10 Sleep

**Request: `ReadSleepDetailsReq` (cmd 0x44 = 68)**
```java
ReadSleepDetailsReq(int dayOffset, int startIndex, int endIndex) {
    super((byte) 68);
    if (dayOffset > 29) throw new IllegalArgumentException("dayOffset 最大只到29");
    if (startIndex > endIndex || endIndex > 95) throw new IllegalArgumentException("数据段索引值异常");
    this.b = new byte[]{(byte) dayOffset, 15, (byte) startIndex, (byte) endIndex};
}
```

**Response: `ReadSleepDetailsRsp` (cmd 0x44 = 68)**

Multi-packet:
1. Init (`0xF0`): clear list, increment index
2. Data records: BCD-encoded year/month/day, timeIndex, 8 sleep quality bytes
3. End (`0xFF`): clear list, done

**Parsed output:** `ArrayList<BleSleepDetails>` with year, month, day, timeIndex, sleepQualities[8]

### 3.11 Steps/Sport

**Total: `ReadTotalSportDataReq` (cmd 0x07)**
- Sub-data: `[daysAgo]`

**Response: `TotalSportDataRsp` (cmd 0x07)**
- 2-packet response:
  - Packet 0: daysAgo, BCD date, totalSteps (3 bytes), runningSteps (3 bytes), calorie (3 bytes)
  - Packet 1: same date check, walkDistance (3 bytes), sportDuration (2 bytes × 60), sleepDuration (2 bytes × 60)

**Detail: `ReadDetailSportDataReq` (cmd 0x43 = 67)**
- Sub-data: `[dayOffset, 15, startIndex, endIndex, 1]`

**Response: `ReadDetailSportDataRsp` (cmd 0x43 = 67)**
- Multi-packet: BCD date, timeIndex, calorie (2 bytes), walkSteps (2 bytes), distance (2 bytes)
- Init byte `0xF0` with flag `bArr[2]==1` → calorie × 10

### 3.12 Device Support Function

**Request: `DeviceSupportReq` (cmd 0x3C = 60)**
- No sub-data

**Response: `DeviceSupportFunctionRsp` (cmd 0x3C = 60)**

9-byte bitmask with ~30 boolean capability flags. Key flags (positions uncertain due to obfuscation):
- `c` (bit 0 of byte 1): likely HR support
- `d` (bit 1 of byte 1): likely SpO2 support
- `e` (bit 2 of byte 1): likely BP support
- `o`–`v` (byte 5): extended features (HRV, pressure, temperature, etc.)
- `M`–`L` (byte 6): more features
- `O`–`T` (byte 7): more features
- `U` (bit 1 of byte 9): latest feature flag

---

## 4. Large-Data Protocol (Custom Service)

### 4.1 Service & UUIDs

| UUID | Purpose |
|---|---|
| `de5bf728-d711-4e47-af26-65e3012a5dc7` | Large-data service |
| `de5bf729-d711-4e47-af26-65e3012a5dc7` | Large-data notify (device → phone) |
| `de5bf72a-d711-4e47-af26-65e3012a5dc7` | Large-data write (phone → device) |

### 4.2 Large-Data Packet Format

**Header (6 bytes):**
```
[0xBC, cmdId, dataLength(2 bytes LE), crc16(2 bytes LE), ...data...]
```

Built by `LargeDataHandler.addHeader(int cmdId, byte[] data)`:
```java
byte[] addHeader(int i, byte[] bArr) {
    byte[] bArr2 = new byte[(bArr == null ? 0 : bArr.length) + 6];
    bArr2[0] = -68;  // 0xBC
    bArr2[1] = (byte) i;
    if (bArr == null || bArr.length <= 0) {
        bArr2[4] = -1;  // 0xFF
        bArr2[5] = -1;  // 0xFF
    } else {
        System.arraycopy(DataTransferUtils.shortToBytes((short) bArr.length), 0, bArr2, 2, 2);
        System.arraycopy(DataTransferUtils.shortToBytes((short) CRC16.calcCrc16(bArr)), 0, bArr2, 4, 2);
        System.arraycopy(bArr, 0, bArr2, 6, bArr.length);
    }
    return bArr2;
}
```

**Packet fragmentation:** Large packets are split at `JPackageManager.getLength()` (default 20 bytes) boundaries and queued via `BleThreadManager`.

### 4.3 LargeDataParser — Reassembly

```java
void parseBigLargeData(String str, byte[] bArr) {
    if (!"de5bf729-...".equals(str)) return;  // only large-data notify UUID
    if (bArr.length < 6 || (bArr[0] & 255) != 188 || !this.c) {
        // Fragment: append to buffer
        this.a = ByteUtil.concat(this.a, bArr);
        if (this.a.length - 6 != this.b) {
            this.c = false;  // still incomplete
            return;
        }
        this.c = true;
        parseData(this.a);
        this.a = new byte[0];
        return;
    }
    // First packet: extract total length
    int bytesToInt = ByteUtil.bytesToInt(Arrays.copyOfRange(bArr, 2, 4));
    this.b = bytesToInt;
    if (bArr.length - 6 < bytesToInt) {
        this.c = false;  // need more fragments
        this.a = Arrays.copyOfRange(bArr, 0, bArr.length);
        return;
    }
    this.c = true;
    parseData(Arrays.copyOfRange(bArr, 0, bArr.length));
    this.a = new byte[0];
}
```

**Reassembly logic:**
1. Check if first byte is `0xBC` (188)
2. Extract data length from bytes [2..4]
3. If full data fits in one notification, parse immediately
4. Otherwise, accumulate fragments until `buffer.length - 6 == expectedLength`

### 4.4 LargeDataHandler — BigData Command Map

| Method | LargeData cmdId | Request payload | Response callback | Purpose |
|---|---|---|---|---|
| `syncSleepList` | 39, 62 | `[0/0xFF, 1]` | `ILargeDataSleepResponse` (×2: night + lunch) | **Sleep history** (new protocol) |
| `syncManualHeartRateList` | 40 | `[0 or 0xFF]` | `ILargeDataManualHeartRateResponse` | **Manual HR history** |
| `syncClassicBluetooth` | 46 | `[0]` | `ILargeDataClassicBluetoothResponse` | Classic BT info |
| `readQrCode` | 47 | `[1, type]` | `ILargeDataQrCodeResponse` | QR code read |
| `syncContact` | 45 | `byte[]` | — | Contact write |
| `syncContactMore` | 41 | `[count+1, 0, size_lo, size_hi]` | `ILargeDataBaseResponse` | Contact list write |
| `syncBloodOxygen` | 42 | `[dayIndex]` | `ILargeDataResponse` | **SpO2 history** |
| `readAlarm` | 44 | `[1]` | `ILargeDataResponse` | Alarm read |
| `writeAlarm` | 44 | `[2, total, ...]` | — | Alarm write |
| `readCustomWatch` | 58 | `[1]` | `ILargeDataResponse` | Watch face read |
| `writeCustomWatch` | 58 | `[2, ...]` | — | Watch face write |
| `deviceRequestLocation` | 32 | — | `ILargeDataResponse` | GPS request |
| `writeLocation` | 32 | `[2, ...]` | — | GPS write |
| `gpsNavigationRunning` | 72 | `[1, len+2, i, i2, ...unicode]` | — | Navigation data |
| `gpsNavigationStatus` | 72 | `[i, 0]` | — | Navigation status |
| `setDeviceNickName` | 74 | `[1, 1, 0, ...unicode]` | — | Device name |
| `syncBloodSugar` | 71 | `[dayIndex]` | `ILargeDataResponse` | Blood sugar history |
| `syncManualBloodOxygenList` | 73 | — | `ILargeDataManualBloodOxygenResponse` | **Manual SpO2 history** |
| `readEmergencyContact` | 118 | `[i, 1]` | `ILargeDataResponse` | Emergency contact read |
| `writeEmergencyContact` | 118 | `byte[]` | `ILargeDataResponse` | Emergency contact write |
| `syncIntervalBloodOxygenWithCallback` | 95 | `[dayIndex, packetIndex]` | `IIntervalBloodOxygenCallback` | **Interval SpO2 history** |
| `syncIntervalHeartRateWithCallback` | 117 | `[dayIndex, packetIndex]` | `IIntervalHeartRateCallback` | **Interval HR history** |
| `syncIntervalTemperatureWithCallback` | 119 | `[dayIndex, packetIndex]` | `IIntervalTemperatureCallback` | **Interval temperature history** |

### 4.5 Sleep Parsing (New Protocol)

**`parseDaySleep`** — Night sleep:
```
Input: dayOffset, fullData, offset, recordLength, totalLength
Record: [2 bytes: recordLength], [2 bytes: startMinute], [2 bytes: endMinute], [detail pairs...]
Detail pair: [type, duration] (every 2 bytes)
```

- `startMinute` and `endMinute` are minutes from midnight
- If `startMinute >= 1080` (18:00), the sleep started the previous day
- Sleep types (from `SleepNewProtoResp.DetailBean.t`):
  - Likely: 0=awake, 1=light, 2=deep, 3=REM (to be confirmed)
- Recursive: if `offset + recordLength < totalLength`, parse next day

**`parseDaySleepLunch`** — Lunch nap:
- Same structure but with `LunchSleepBean` entries (startTime, endTime)
- Lunch break flag set to `true`

### 4.6 Manual HR/SpO2 Parsing

**Manual HR (cmdId 40):**
```java
void parseData(int i, byte[] bArr) {
    if (i == 40) {
        ManualHeartRate mhr = new ManualHeartRate();
        mhr.setIndex(ByteUtil.bytesToInt(Arrays.copyOfRange(bArr, 6, 7)));
        byte[] copyOfRange = Arrays.copyOfRange(bArr, 7, bArr.length);
        for (int i3 = 0; i3 < copyOfRange.length / 3; i3++) {
            ManualHeartRate.DetailBean detail = new ManualHeartRate.DetailBean();
            int i4 = i3 * 3;
            detail.setM(ByteUtil.bytesToInt(Arrays.copyOfRange(copyOfRange, i4, i4 + 2)));  // minute
            detail.setV(ByteUtil.bytesToInt(Arrays.copyOfRange(copyOfRange, i4 + 2, i4 + 3)));  // value
            mhr.getData().add(detail);
        }
    }
}
```

**Layout:** After 6-byte header, byte 6 = dayIndex, bytes 7+ = triplets of [minute_lo, minute_hi, value].

**Manual SpO2 (cmdId 73):** Same triplet layout as manual HR.

### 4.7 Interval HR/SpO2/Temperature Parsing

**Interval SpO2 (cmdId 95):**
```java
void parseData(int i, byte[] bArr) {
    if (i == 95) {
        IntervalBloodOxygenEntity entity = new IntervalBloodOxygenEntity();
        entity.setDayIndex(ByteUtil.byteToInt(bArr[6]));
        entity.setInterval(ByteUtil.byteToInt(bArr[7]));
        int packet = ByteUtil.byteToInt(bArr[8]);
        int packetIndex = ByteUtil.byteToInt(bArr[9]);
        List<Integer> values = getIntervalOxygen(bArr);  // bArr[10..]
        if (packet == 0 || packet - 1 == packetIndex) {
            // done — return values
        } else if (packet - 1 > packetIndex) {
            // need more packets — request next
            syncIntervalBloodOxygenWithCallback(dayIndex, packetIndex + 1, callback);
        }
    }
}
```

**`getIntervalOxygen(bArr)`:** Returns `bArr[10..]` as `List<Integer>` (one byte per value).

**Interval HR (cmdId 117):** Same layout as interval SpO2, but uses `getIntervalOxygen` (same parser — **this is the bug** where `syncIntervalHeartRate` calls `syncIntervalBloodOxygenReal` instead of `syncIntervalHeartRateReal`).

**Interval Temperature (cmdId 119):**
```java
List<Float> getIntervalTemperature(byte[] bArr) {
    byte[] copyOfRange = Arrays.copyOfRange(bArr, 10, bArr.length);
    for (int i = 0; i < copyOfRange.length; i += 2) {
        int i2 = (copyOfRange[i] & 255) | ((copyOfRange[i + 1] & 255) << 8);
        arrayList.add(((float) i2) / 100.0f);  // temperature in °C
    }
    return arrayList;
}
```

**Layout:** 2 bytes per temperature value (little-endian uint16, divided by 100 for °C).

**Recursive multi-packet:** All interval data types support recursive fetching. If `packet - 1 > packetIndex`, the handler automatically requests the next packet with `packetIndex + 1` and accumulates values.

---

## 5. Data Flow Summary

### 5.1 Small-Data Path

```
Ring → BLE Notification → BleBaseControl.onCharacteristicChanged
    → BleOperateManager.bleCharacteristicChanged
    → LocalBroadcastManager.sendBroadcast("com.swatchdevice.pro.characteristic_changed_qc")
    → QCBluetoothCallbackReceiver.onCharacteristicChange
    → QCDataParser.checkCrc (validate 16-byte packet)
    → QCDataParser.parserAndDispatchReqData (match pending request)
        → BeanFactory.createBean(cmdId, type) → BaseRspCmd
        → rsp.acceptData(payload) → if true: cache, if false: callback
    → OR QCDataParser.parserAndDispatchNotifyData (match notify listener)
        → Same dispatch via notify SparseArray
```

### 5.2 Large-Data Path

```
Ring → BLE Notification → (same path to QCBluetoothCallbackBigDataCloneReceiver)
    → LargeDataParser.parseBigLargeData(UUID, data)
    → If UUID == "de5bf729-...": reassemble fragments
    → parseData(reassembled) → lookup cmdId in LargeDataHandler.respMap
    → ILargeDataResponse.parseData(cmdId, fullData)
    → Entity construction → callback
```

### 5.3 Command Sending Path

```
App code → CommandHandle.executeReqCmd(BaseReqCmd, ICommandResponse)
    → LocalWriteRequest(Constants.a, Constants.c)  // UART service, write char
    → BleOperateManager.execute(writeRequest)
    → BleBaseControl.findTheGattCharacteristic(serviceUUID, charUUID)
    → BluetoothGattCharacteristic.setValue(data)
    → BluetoothGatt.writeCharacteristic(characteristic)
    → Ring processes → sends notification back
```

---

## 6. Critical Findings for SymbioSync

### 6.1 Realtime HR Notification Byte Offset ⚠️

**The most critical finding:** `RealTimeHeartRateRsp` (cmd 0x1E) reads `bArr[0]` as the HR value, which maps to `data[1]` in the raw 16-byte packet. SymbioSync reads `data[3]` as the value for all notifications.

**Impact:** If the ring sends realtime HR via cmd 0x1E (not 0x69), SymbioSync is reading the wrong byte. This could explain the repeated `97` anomaly — `data[3]` might be a status byte while `data[1]` contains the actual HR.

**However:** SymbioSync's notification handler checks `data[1]` as `reading_type` and routes based on it. If `data[1] == 0x01` (HR type), it reads `data[3]` as value. The APK's `StartHeartRateRsp` (cmd 0x69) also has value at `bArr[2]` = `data[3]`. So the question is: **does the ring send realtime HR as cmd 0x69 or cmd 0x1E?**

**Hypothesis:** The ring likely sends realtime HR notifications as cmd 0x69 with `data[1]` = type (1=HR, 3=SpO2), matching `StartHeartRateRsp`. The `RealTimeHeartRateRsp` (cmd 0x1E) may be a different notification type (e.g., periodic background HR). This needs verification with actual BLE traffic.

### 6.2 High-Bit Flag (0x80)

`Constants.m = 128` confirms that `data[0] & 0x7F` extracts the command ID. The high bit is a flag. From the code, `CommandHandle.executeReqCmd` uses `writeRequest.getValue()[0] & (~Constants.m)` to compute the response lookup key — meaning the response always has the high bit stripped. The ring may set the high bit on notifications to indicate "this is a device-initiated notification" vs "this is a response to a request."

### 6.3 Packet Length Negotiation

`JPackageManager` defaults to 20 bytes but can be updated by `PackageLengthRsp` (cmd 47). The large-data handler uses `JPackageManager.getInstance().getLength()` for fragmentation. SymbioSync should negotiate this if the ring supports it.

### 6.4 BigData Interval HR Bug

`syncIntervalHeartRate` calls `syncIntervalBloodOxygenReal` instead of `syncIntervalHeartRateReal`. This means:
- Interval HR requests are sent with cmdId **95** (SpO2) instead of **117** (HR)
- The ring would respond with SpO2 data, not HR data
- This is almost certainly a **bug in the APK** — the method body of `syncIntervalHeartRate` is a copy-paste error

**Impact for SymbioSync:** If we implement interval HR, we must use cmdId **117**, not 95.

### 6.5 SpO2 Measurement Lifecycle

The APK does NOT explicitly show an HR-pause-before-SpO2 pattern. The `StartHeartRateReq` and `StopHeartRateReq` are separate commands, and the app code (in the obfuscated `com.cxxyuek.app.utyi` package) would contain the orchestration logic. However, the stop types (1=HR, 3=SpO2) confirm that HR and SpO2 are mutually exclusive measurement modes on the ring.

### 6.6 Sleep Protocol Versions

Two sleep protocols exist:
1. **Old protocol:** `ReadSleepDetailsReq` (cmd 0x44) → `ReadSleepDetailsRsp` with BCD dates and 8-element quality arrays
2. **New protocol:** `LargeDataHandler.syncSleepList` (cmdId 39, 62) → `SleepNewProtoResp` with start/end times and detail pairs

The new protocol supports both night sleep (cmdId 39) and lunch nap (cmdId 62). SymbioSync should use the new protocol for richer data.

### 6.7 Multi-Packet Response Pattern

Several biometric responses use a common multi-packet pattern:
1. Init packet (`0x00`): count + range → allocate buffer
2. First data packet (`0x01`): dayOffset + first data chunk
3. Continuation packets: 13 bytes each, check if `index == count - 1`

This applies to: `ReadHeartRateRsp`, `HRVRsp`, `PressureRsp`. SymbioSync must implement this multi-packet accumulation for interval HR/HRV/pressure history.

---

## 7. Command ID Quick Reference

### Small-Data Commands (UART, 16-byte packets)

| Hex | Dec | Direction | Name | SymbioSync implemented? |
|---|---|---|---|---|
| 0x01 | 1 | W→R | Set time | Partial |
| 0x03 | 3 | R→W | Battery | Yes |
| 0x07 | 7 | W→R | Read total sport | No |
| 0x0C | 12 | W→R | BP setting | No |
| 0x0D | 13 | R→W | BP data | No |
| 0x14 | 20 | W→R | Read BP history | No |
| 0x15 | 21 | W→R | Read interval HR | No |
| 0x16 | 22 | W→R | HR setting read/write | No |
| 0x19 | 25 | W→R | Degree switch | No |
| 0x1E | 30 | R→W | **Realtime HR notification** | Partial (byte offset question) |
| 0x2C | 44 | W→R | SpO2 setting read/write | No |
| 0x36 | 54 | W→R | Pressure setting | No |
| 0x37 | 55 | W→R | Pressure data | No |
| 0x38 | 56 | W→R | HRV setting | No |
| 0x39 | 57 | W→R | HRV data | No |
| 0x3C | 60 | W→R | Device support function | No |
| 0x43 | 67 | W→R | Read detail sport | No |
| 0x44 | 68 | W→R | Read sleep details (old) | No |
| 0x69 | 105 | W→R | **Start HR/SpO2/BP/ECG** | Yes |
| 0x6A | 106 | W→R | **Stop HR/SpO2/BP/ECG** | Yes |

### Large-Data Commands (Custom service, variable-length)

| Hex | Dec | Name | SymbioSync implemented? |
|---|---|---|---|
| 0x20 | 32 | GPS location | No |
| 0x27 | 39 | **Sleep history (new proto, night)** | Partial (empty request) |
| 0x28 | 40 | **Manual HR history** | No |
| 0x2A | 42 | **SpO2 history** | No |
| 0x2C | 44 | Alarm read/write | No |
| 0x2D | 45 | Contact sync | No |
| 0x2E | 46 | Classic BT info | No |
| 0x2F | 47 | QR code | No |
| 0x31 | 49 | Contact list | No |
| 0x3E | 62 | **Sleep history (new proto, lunch nap)** | No |
| 0x44 | 68 | Sleep detail (old proto) | No |
| 0x47 | 71 | Blood sugar history | No |
| 0x48 | 72 | GPS navigation | No |
| 0x49 | 73 | **Manual SpO2 history** | No |
| 0x4A | 74 | Device nickname | No |
| 0x5F | 95 | **Interval SpO2 history** | No |
| 0x75 | 117 | **Interval HR history** | No |
| 0x77 | 119 | **Interval temperature history** | No |
| 0x76 | 118 | Emergency contact | No |
