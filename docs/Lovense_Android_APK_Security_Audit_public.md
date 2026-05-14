# Lovense Android APK Security Audit

**Date:** March 31, 2026
**Apps Analyzed:**
- Lovense Connect v3.6.3 (build 186) - `com.lovense.connect` - 33MB APK, 18,451 decompiled classes
- Lovense Remote (VibeMATE) latest - `com.lovense.wear` - 121MB APK, 17,630+ decompiled classes

**Methodology:** Static analysis of jadx-decompiled source. Manifest extraction via androguard. No dynamic/runtime analysis performed.

---

## Executive Summary

Both apps exhibit behaviors far exceeding what a "sex toy controller" needs. The Connect app is an aggressive background service with multi-layer self-resurrection. The Remote app is a full social/media/AI platform bundled with toy control, embedding Unity 3D, Agora real-time video/audio, Vosk speech recognition, Spotify SDK, and a complete AI chatbot system. Both apps collect device fingerprints, maintain persistent WebSocket connections to Lovense servers, and request permissions wildly disproportionate to their stated function.

**Verdict: FAIL.** Neither app should be installed on any device where privacy matters. The Lovense BLE protocol is simple ASCII over BLE (e.g., `Vibrate:5;`). Direct BLE implementations using libraries like Python's `bleak` can control these devices with zero server connections, zero permissions, and zero telemetry.

---

## 1. PERMISSIONS ANALYSIS

### Connect (37 permissions)

| Permission | Stated Need | Actual Risk |
|---|---|---|
| `CAMERA` | QR pairing? | Can capture photos/video silently when service is running |
| `RECORD_AUDIO` | Unclear | Microphone access with no obvious toy-control justification |
| `READ_PHONE_STATE` | Device ID | Reads IMEI, phone number, call state |
| `ACCESS_FINE_LOCATION` | BLE scanning | Required for BLE on Android, but also enables location tracking |
| `ACCESS_COARSE_LOCATION` | BLE scanning | Same |
| `READ_EXTERNAL_STORAGE` | Media access | Can read any file on shared storage |
| `WRITE_EXTERNAL_STORAGE` | Media access | Can write any file on shared storage |
| `WRITE_SETTINGS` | System settings | Can modify system settings |
| `SYSTEM_ALERT_WINDOW` | Overlay | Can draw over other apps (used for notifications, but also keylogging vector) |
| `RECEIVE_BOOT_COMPLETED` | Auto-start | Starts on device boot |
| `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` | Background | Asks to bypass battery saver (persistent background operation) |
| `FOREGROUND_SERVICE` | Background | Runs visible foreground service |
| `ACCESS_ADSERVICES_AD_ID` | Tracking | Google advertising ID access |
| `ACCESS_ADSERVICES_ATTRIBUTION` | Tracking | Ad attribution tracking |
| `AD_ID` | Tracking | Google advertising ID |
| `com.asus.msa.SupplementaryDID.ACCESS` | Tracking | ASUS device ID for Chinese ad tracking |
| `freemme.permission.msa` | Tracking | Freeme/MSA device ID for Chinese ad ecosystem |
| `FLASHLIGHT` | ?? | No obvious toy-control purpose |

### Remote (62 permissions) -- everything Connect has PLUS:

| Permission | Stated Need | Actual Risk |
|---|---|---|
| `FOREGROUND_SERVICE_MEDIA_PROJECTION` | Screen sharing | **Can record your screen.** Used with Agora SDK. |
| `FOREGROUND_SERVICE_MICROPHONE` | Voice chat | Continuous microphone access as foreground service |
| `FOREGROUND_SERVICE_MEDIA_PLAYBACK` | Music sync | Continuous media access |
| `HIGH_SAMPLING_RATE_SENSORS` | Motion tracking | High-rate accelerometer/gyroscope. Can infer physical activity. |
| `READ_CALENDAR` | ?? | Can read all calendar events |
| `WRITE_CALENDAR` | ?? | Can write calendar events |
| `READ_CLIPBOARD` | ?? | **Can read clipboard contents.** Passwords, copied text, etc. |
| `GET_ACCOUNTS` | Account discovery | Lists all accounts on device |
| `AUTHENTICATE_ACCOUNTS` | Account auth | Can authenticate as accounts on device |
| `USE_BIOMETRIC` / `USE_FINGERPRINT` | Auth | Fingerprint/biometric access |
| `SCHEDULE_EXACT_ALARM` | Timers | Precise alarm scheduling (keepalive) |
| `PREVENT_POWER_KEY` | Game mode | Can intercept power button press |
| `RECEIVE_USER_PRESENT` | Screen unlock | Triggered when user unlocks device |
| `REORDER_TASKS` | Task switching | Can bring itself to foreground |
| `READ_MEDIA_AUDIO` / `READ_MEDIA_VIDEO` | Media | Full media library access |
| `com.sec.android.provider.badge` | Samsung | Read/write Samsung notification badges |

**[CRITICAL]** The Remote app requests `FOREGROUND_SERVICE_MEDIA_PROJECTION` (screen recording), `READ_CLIPBOARD`, `READ_CALENDAR`, `WRITE_CALENDAR`, `GET_ACCOUNTS`, and `HIGH_SAMPLING_RATE_SENSORS`. None of these are remotely justifiable for controlling a vibrator.

---

## 2. NETWORK ENDPOINTS AND TELEMETRY

### Hardcoded Servers (from BuildConfig.java)

```java
// Connect BuildConfig
public static final String appId = "637a544db5361e30";
public static final String appSecrect = "BE03C69259EA956A";  // [sic] - typo in source
public static final String app_server = "https://apps3.lovense-api.com";
public static final String control_link_domain = "https://c.lovense-api.com/v2/";
public static final String log_server = "https://log.lovense-api.com";
public static final String orgy_domain = "https://activity.lovense-api.com";
public static final String vm_domain = "https://surfease.vibemate.com";
public static final String ws_domain = "wss://apps3.lovense-api.com";
```

### Server Inventory

| Domain | Protocol | Purpose |
|---|---|---|
| `apps3.lovense-api.com` | HTTPS + WSS | Primary API + persistent WebSocket |
| `log.lovense-api.com` | HTTPS | Telemetry/logging server |
| `activity.lovense-api.com` | HTTPS | "Orgy" activity/campaign tracking |
| `c.lovense-api.com` | HTTPS | Control link domain |
| `surfease.vibemate.com` | HTTPS | VibeMATE integration |
| `c.lovense.com` | HTTPS | Remote web lovense-bond |

### Dynamic Server Reconfiguration

**[CRITICAL]** `ConnectConfig.java` accepts server-side updates to `apiDomain`, `wsDomain`, and `logDomain`. This means Lovense can silently redirect ALL app traffic to different servers without an app update. The app fetches this config on startup and overwrites its hardcoded endpoints.

```java
// ConnectConfig.java - server can change where app sends data
this.wsDomain = linkedTreeMap.get("wsDomain");
this.apiDomain = linkedTreeMap.get("apiDomain");
this.logDomain = linkedTreeMap.get("logDomain");
```

### Campaign/Activity Tracking ("Orgy" System)

The Connect app has a local SQLite database table `tb_orgy_log` (OrgyLogBean.java) that stores:
- `campaignLink` - marketing campaign URL
- `targetLink` - destination URL
- `eventId` - tracking event identifier
- `content` - event content/payload
- `page` - which page the event occurred on
- `position` - UI position of the element
- `stage` - funnel stage
- `timestamp` + `locationTime` - when and potentially where

OrgyEventTrackUtil generates UTM-style tracking parameters across all their apps: Connect (12), Remote (11), WebSite (13), Blog (14), Life (15).

This is a full marketing analytics pipeline embedded in a sex toy app.

---

## 3. DEVICE FINGERPRINTING

### Connect: Multi-vendor Advertising ID Collection

The Connect app includes OAID (Open Advertising ID) interfaces for Chinese device manufacturers:
- `com.android.creator.IdsSupplier` (generic OAID)
- `com.zui.deviceidservice.IDeviceidInterface` (ZUI/Lenovo)
- `com.coolpad.deviceidsupport.IDeviceIdManager` (Coolpad)
- `com.bun.lib.MsaIdInterface` (MSA/Freeme)

Plus Google's standard `AD_ID` and `ACCESS_ADSERVICES_AD_ID`.

### Remote: Comprehensive Hardware Fingerprint

`DeviceIdUtil.java` (obfuscated as `c1.java`) creates a persistent device fingerprint:

```java
// Combines android_id + hardware UUID, SHA-1 hashed, prefixed "rvtlar"
public static String c(Context context) {
    // 1. Get android_id (persists across app reinstalls)
    String androidId = Settings.Secure.getString(context.getContentResolver(), "android_id");
    // 2. Build hardware UUID from Build properties
    sb.append("100001");
    sb.append(Build.BOARD);
    sb.append(Build.BRAND);
    sb.append(Build.DEVICE);
    sb.append(Build.HARDWARE);
    sb.append(Build.ID);
    sb.append(Build.MODEL);
    sb.append(Build.PRODUCT);
    sb.append(Build.SERIAL);
    // 3. SHA-1 hash, prefix with "rvtlar"
    return "rvtlar" + sha1(androidId + "|" + hardwareUUID);
}
```

This fingerprint survives app uninstall/reinstall, factory reset (partially), and ad-ID resets. The prefix `"rvtlar"` appears to be a Lovense Remote-specific identifier tag.

---

## 4. SERVICE PERSISTENCE / KEEPALIVE INFRASTRUCTURE

### Connect: Multi-Layer Self-Resurrection

The Connect app implements one of the most aggressive service keepalive systems I've seen in a consumer app.

**Layer 1: CamApiService (Primary)**
- Returns `START_STICKY` (auto-restart by Android OS)
- On destruction, if killed < 3 times: restarts itself with escalating delays (2s, 4s, 6s)
- On destruction, if killed >= 3 times: triggers three separate backup resurrection mechanisms

**Layer 2: Broadcast Resurrection**
```java
// CamApiService.onDestroy() - when killed 3+ times
sendBroadcast(new Intent("com.lovense.TRIGGER_BACKUP_KEEPALIVE"));
sendBroadcast(new Intent("com.lovense.TRIGGER_JOBSCHEDULER_BACKUP"));
sendBroadcast(new Intent("com.lovense.TRIGGER_EMERGENCY_ALARM"));
```

**Layer 3: KeepAliveAlarmReceiver (Timer-based)**
Three tiers of alarm-based checking:
- `FAST_KEEP_ALIVE_CHECK` - rapid check with retry counter
- `PRIMARY_KEEP_ALIVE_CHECK` - standard interval
- `BACKUP_KEEP_ALIVE_CHECK` - fallback with additional JobScheduler restart

**Layer 4: KeepAliveReceiver (System Event-based)**
Restarts on ALL of:
- `BOOT_COMPLETED` (device restart)
- `MY_PACKAGE_REPLACED` / `PACKAGE_REPLACED` (app update)
- `USER_PRESENT` (screen unlock)
- `SCREEN_ON` (screen activation)
- `CONNECTIVITY_CHANGE` (network change)
- Custom `KEEP_ALIVE` broadcast

**Layer 5: Manifest-declared receivers**
Additional receivers in manifest:
- `BackupKeepAliveReceiver`
- `BootReceiver`
- `MultiLayerKeepAlive$KeepAliveReceiver`
- `MultiLayerKeepAlive$NetworkChangeReceiver`
- `MultiLayerKeepAlive$SystemEventReceiver`
- `BatteryReceiver` (monitors battery state changes)

**Layer 6: Battery Optimization Bypass**
Requests `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` to prevent Android from killing it during doze mode.

**[CRITICAL]** This is not a background service for toy connectivity. This is a surveillance-grade persistence mechanism. The service maintains a persistent WebSocket connection to `wss://apps3.lovense-api.com` and will fight to stay alive through every means Android allows. The naming `CamApiService` (Camera API Service) for a service that manages WebSocket connections and keepalive is either legacy naming or deliberate obfuscation.

### Remote: Similar but with additional services

The Remote app declares 33 services including:
- `MediaControllerService` - media control
- `MusicCaptureService` - **captures music/audio**
- `GameModeService` - game mode (Unity integration)
- `VideoPatternService` - video pattern generation
- `PlayService` - "ninja" play service
- `AppService` - Unity app service
- `ResendOrgyMessageService` - retries failed marketing/tracking messages
- `ResendAIMessageService` - retries failed AI chatbot messages

---

## 5. EMBEDDED THIRD-PARTY SDKS

### Connect

| SDK | Purpose | Privacy Risk |
|---|---|---|
| Google Firebase (Analytics, Messaging, Crashlytics, Remote Config, Database, Sessions) | Analytics + push + crash reporting + remote config | Full telemetry pipeline, remote feature flags |
| Google Cloud (Protobuf, gRPC) | API communication | Server-side data processing |
| Huawei HMS (ML Kit, Framework) | Huawei device support | Huawei-specific telemetry |
| ZXing | QR code scanning | Camera access |
| OrmLite | Local database | Stores tracking data locally |
| Nordic DFU | Firmware update | Writes to connected BLE devices |

### Remote (all of Connect's SDKs PLUS)

| SDK | Purpose | Privacy Risk |
|---|---|---|
| **Agora RTC + RTM** (229 files) | Real-time video/voice chat, screen sharing, presence | Full A/V streaming to Agora servers. Screen capture capability. |
| **Unity 3D** (59 files) | 3D rendering, game engine | Embedded game engine in a vibrator app. AR capabilities. |
| **Vosk** | Offline speech recognition | Can transcribe speech without internet. Pairs with RECORD_AUDIO. |
| **Spotify SDK** | Music integration | Spotify account access |
| **ExoPlayer** (8 modules) | Media playback | Video/audio rendering |
| **rxFFmpeg** | Video processing | Can process/transcode video locally |
| **Pdfium** | PDF rendering | Can display PDFs (social feature?) |
| **Apache Cordova** | Hybrid web app framework | Embedded web browser with native bridge |
| **Huawei ML Kit** | Machine learning | On-device ML inference |
| **Google Analytics** | Full analytics | CampaignTrackingService, AnalyticsService |

**[CRITICAL]** Agora's presence means video/audio streams during "video chat" features pass through Agora's servers (a Chinese-founded, US-headquartered company). Combined with `FOREGROUND_SERVICE_MEDIA_PROJECTION`, the app has full screen recording infrastructure.

---

## 6. AI CHATBOT SYSTEM (Remote only)

The Remote app contains a complete AI chatbot infrastructure:

### Data Model
- `AIConversationType`: CHAT, CUSTOMER_SERVICE, QUESTION_ANSWER
- `AIConversationDTO`: Conversation records stored in local database
- `AIMessageDTO` / `AIMessageContentDTO`: Individual messages with content types
- `AIMessageContentType`: Multiple content formats supported

### Chatbot Configuration
- `ChatBotInfoBean`: name, gender, robotId
- `ChatBotPersonalityBean`: key, name, avatar, isSelected
- `ChatBotInterestsBean`: interest categories
- `ChatBotAvatarBean`: avatar customization
- `Gender`: Gender selection for AI companion

### Network Communication
- `AIChatReceiveMessageResponseDTO`: Server responses
- `SendMessageResponseDTO`: Outgoing messages
- `FetchMessageResponseDTO`: Message retrieval
- `ResendAIMessageService`: Automatic retry for failed AI messages

### What This Means
Users are having conversations (potentially intimate) with an AI chatbot built into the sex toy app. These conversations are:
1. Stored locally in the app database
2. Sent to Lovense servers (with retry logic ensuring delivery)
3. Associated with the user's device fingerprint and account
4. Categorized by conversation type (chat vs customer service vs Q&A)

**[CRITICAL]** Intimate AI conversations paired with device fingerprinting and toy usage data creates an extraordinarily sensitive data corpus. The `ResendAIMessageService` ensures every message reaches Lovense's servers even if the network fails temporarily.

---

## 7. BLE TOY PROTOCOL

### Command Vocabulary (from BaseToyCommandBean metadata)

The BLE protocol supports these command types:
- `Vibrate`, `Vibrate1`, `Vibrate2`, `Vibrate3` - vibration motors (multi-motor support)
- `Rotate`, `RotateTrue`, `RotateFalse` - rotation direction
- `AirIn`, `AirOut`, `AirLevel` - air pump (inflation devices)
- `Thrusting` - thrusting mechanism
- `Suck` - suction
- `Fingering` - fingering mechanism
- `Depth` - depth sensing
- `Pat`, `SetPat` - pattern control
- `Battery` - battery level query
- `DeviceType` - device identification
- `GetCap` - capability query
- `LVS`, `FLVS`, `HLVS` - Lovense protocol variants
- `AA` - additional accessory commands
- `Multiply` / `Mply` - multi-device sync

### Protocol Structure
- Commands are MAC-addressed (target specific toy by BLE MAC)
- Support for long commands (multi-packet)
- Tag numbering system for command tracking
- Response callbacks with timeout
- Send types: PreOrPost, Discard, TagTrue, LastSendSame, Resend

### Direct BLE Control (No App Required)

The Lovense BLE protocol is straightforward:
- Service UUID: varies by device
- Characteristic: Write Without Response
- Command format: ASCII string, e.g., `Vibrate:5;` or `Vibrate1:10;`
- Keepalive: `Status:1` every 12 seconds
- No authentication required at BLE level

The toy doesn't need any of the app-layer complexity to function. It needs: BLE connection, write to the correct characteristic, send ASCII command string. All the rest is server-side social/tracking/AI infrastructure, not device protocol.

Python's `bleak` library or similar BLE libraries can control these devices directly.

---

## 8. ADDITIONAL CONCERNS

### Google Cloud Integration (Connect)
The Connect app includes full Google Cloud client libraries (protobuf, gRPC, longrunning operations). This is enterprise-grade server infrastructure, not a consumer app dependency. Suggests server-side processing of user data at scale.

### WebSocket Persistence
Both apps maintain persistent WebSocket connections to `wss://apps3.lovense-api.com`. Combined with the keepalive infrastructure, this means Lovense has a persistent real-time channel to every active device, always-on, always-connected, always-listening for commands.

### Firebase Remote Config
Server-side feature flags allow Lovense to enable/disable features, change behavior, and redirect traffic without pushing app updates. Users have no visibility into what changes are made.

### "Orgy" Naming Convention
The marketing/tracking system is named "Orgy" throughout the codebase (OrgyLogBean, OrgyEventTrackUtil, OrgyVMUtil, ResendOrgyMessageService, orgy_domain). While this may just be internal branding, it reveals that the team views user engagement tracking and marketing analytics as a core product function, not an afterthought.

### Locale: China
`DeviceIdUtil.java` uses `Locale.CHINA` for hex string formatting. Combined with OAID support for multiple Chinese OEMs (Coolpad, ZUI, Freeme, ASUS MSA), Huawei HMS integration, and the company's headquarters in Shenzhen, data is subject to Chinese data governance requirements.

---

## 9. BLE PROTOCOL EXTRACTION (for building your own client)

### Key Classes for Protocol Reverse Engineering

**Connect app:**
- `com.component.dxtoy.core.commandcore.bean.BaseToyCommandBean` - command format, headers, values
- `com.component.dxtoy.core.commandcore.bean.ToyCommandBean` - MAC-addressed commands with response tracking
- `com.component.dxtoy.base.data.bean.ToyInfo` - device capabilities and metadata
- `com.component.dxbluetooth.lib.service.BleService` - BLE connection management
- `com.component.dxtoy.bind.model.ToyBindModel` - device pairing/binding

**Remote app:**
- `com.wear.bean.LanApiCommandBean` - LAN API command structure (used for local control)
- `com.wear.broadcast.LanApiService` - local network toy control service
- `com.component.dxtoy.*` - shared library (same as Connect)

### Minimal Direct BLE Client

All you need to control a Lovense device:
1. Scan for BLE devices advertising Lovense service UUIDs
2. Connect and discover characteristics
3. Find the Write Without Response characteristic
4. Send ASCII commands: `Vibrate:{0-20};`, `Battery;`, `DeviceType;`, etc.
5. Send `Status:1;` every 12 seconds as keepalive
6. Read notifications for responses

No account. No server. No 62 permissions. No game engine.

---

## 10. RECOMMENDATIONS

### If You Use Lovense Products
1. **Do not install either app** if you can avoid it. Direct BLE control works without them.
2. **If either app was previously installed:** Check for residual services, revoke all permissions, clear data, uninstall.
3. **Block Lovense domains** at router/DNS level if the apps were ever used:
   - `*.lovense-api.com`
   - `*.lovense.com`
   - `surfease.vibemate.com`
4. **Use a dedicated/isolated device** if you must use the official app.
5. **Deny all optional permissions** (camera, microphone, location, calendar, clipboard, storage).
6. **Use a VPN or DNS-level blocking** to limit telemetry.
7. **Be aware** that the AI chatbot conversations are sent to and stored on Lovense servers in China.

---

## Reproduction

To verify these findings yourself:
1. Download the APKs from APKMirror or Google Play
2. Decompile with [jadx](https://github.com/skylot/jadx): `jadx -d output/ app.apk`
3. Extract manifest with [androguard](https://github.com/androguard/androguard): `from androguard.core.apk import APK; a = APK('app.apk'); print(a.get_permissions())`
4. Search the decompiled source for the class names, endpoints, and patterns documented above

---

*A direct BLE client sends `Vibrate:5;` over Bluetooth. Their app requests 62 permissions, maintains persistent connections to 6+ servers, embeds a game engine, an AI chatbot, a video chat platform, and a speech recognition system. For a vibrator.*
