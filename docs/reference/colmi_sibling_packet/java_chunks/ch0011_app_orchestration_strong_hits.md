# CH0011 — App Orchestration Strong Hits: Receivers & DAO Interfaces

**Qualitative telemetry guess:** I'm likely running as a Claude model (Anthropic family), given the instruction-following patterns and multi-step tool orchestration.

**Chunk:** CH0011  
**Type:** app_orchestration_strong_hits  
**Source tree:** decompiled4 (com/qcwireless/smart)  
**Focus question:** Do receivers and DAO interface files reveal BLE/common-data parse flow, reboot/Bluetooth sync flow, or storage schema for manual HR/SpO2/sleep?

**Short answer:** YES — this chunk is extremely high-signal. It contains:
1. The **complete BLE characteristic-change/read dispatch chain** (MyBluetoothReceiver → BleCommonDataParseKt)
2. The **full Bluetooth lifecycle receiver** (BluetoothReceiver) with reconnection, ACL events, time-set sync, and sport-data sync
3. The **reboot/Bluetooth-turn-on flow** (RebootReceiver, SystemLocaleChangeReceiver)
4. **Complete Room DAO schemas** for manual HR, SpO2, HRV, blood pressure, blood sugar, temperature, and contacts — revealing exact table names, column names, and query patterns

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|-----------|--------------|-----------------|-------------|-----------------|---------------------------|-----------------|-----------------|----------------------|----------------|----------------|
| J05152 | com/qcwireless/smart/ui/base/receiver/BleCommonDataParseKt.java | documented_app_orchestration | ble_connection | BLE notification data parser; dispatches camera intent on specific byte pattern; parses firmware/HW version from characteristic reads | parseBleData(byte[]), parseDeviceInfoData(String uuid, byte[]) | BleOperateManager, Constants, AppUtil, EventBus, UserConfig, CameraActivity, FirmCheckEvent, WatchFaceDownloadEvent, DeviceConfigEvent | Called by MyBluetoothReceiver.onCharacteristicChange and onCharacteristicRead | Constants.m (mask), Constants.f (FM version UUID), Constants.g (HW version UUID) | parseBleData checks byte[0] masked against ~Constants.m == 2 and byte[1] == 1 → triggers camera. parseDeviceInfoData compares UUID to Constants.f (FM) and Constants.g (HW), stores in UserConfig, posts events. Sets BleOperateManager.setReady(true) on HW version. | Constants.f/g UUID values need cross-referencing with SDK Constants class |
| J05153 | com/qcwireless/smart/ui/base/receiver/BluetoothReceiver.java | documented_app_orchestration | ble_connection, steps_sport, sync_scheduler | System BroadcastReceiver for Bluetooth adapter state, ACL connect/disconnect, bond state, screen on/off, time set, user present; manages reconnection and sport-data sync | onReceive(), beginConnect(), connectAgain(), reConnect(), disConnectDevice(), onOffBle() | BleOperateManager, DeviceManager, SppHandle, CommandHandle, SetTimeReq, SetTimeRsp, TodaySportDataRsp, BleScannerHelper, DeviceReconnect, StepDetailRepository, BluetoothEvent, BluetoothSppEvent, GSenserMessageEvent | Registered in AndroidManifest for BT actions | BT state codes: 10=OFF, 12=ON; ACL_CONNECTED, ACL_DISCONNECTED, BOND_STATE_CHANGED | On BT ON: reconnects via DeviceReconnect.connectWithScanValidation, begins connect runnable. On ACL_CONNECTED: begins connect if not already connected. On ACL_DISCONNECTED: posts BluetoothSppEvent(false), schedules reconnect. On TIME_SET: sends SetTimeReq to device. On USER_PRESENT/SCREEN_ON: begins connect. Syncs today steps via StepDetailRepository when connected in background. | SppHandle (JieLi) vs RTK SPP branching needs deeper follow-up |
| J05155 | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java | documented_protocol_touch | battery, ble_connection, sync_scheduler | BLE callback receiver extending QCBluetoothCallbackCloneReceiver; dispatches characteristic change/read to BleCommonDataParseKt; on service discovered triggers initCmd (battery read, HW/FM read, device settings init) | onCharacteristicChange(), onCharacteristicRead(), onServiceDiscovered(), connectStatue(), initCmd(), bleStatus() | QCBluetoothCallbackCloneReceiver, CommandHandle, SimpleKeyReq, BatteryRsp, LargeDataHandler, DeviceCmdInit, BleCommonDataParseKt, BluetoothEvent, UserConfig, PreUtil | BLE framework callback; registered as BLE callback | SimpleKeyReq(byte 3) → battery read | onCharacteristicChange delegates to BleCommonDataParseKt.parseBleData(data). onCharacteristicRead delegates to BleCommonDataParseKt.parseDeviceInfoData(uuid, data). onServiceDiscovered: inits LargeDataHandler, posts BluetoothEvent(true), calls initCmd(). initCmd: reads HW, sends SimpleKeyReq(3) for battery, reads FM, calls DeviceCmdInit.initDeviceSetting(). connectStatue: saves device name/address to UserConfig, sets lastTenMinSyncTime. | SimpleKeyReq byte value 3 = battery command; needs cross-ref with SDK command IDs |
| J05156 | com/qcwireless/smart/ui/base/receiver/NetWorkStateReceiver.java | documented_app_orchestration | ble_connection | Network connectivity change receiver; triggers ThreadManager.wakeUp() when no network and BLE not connected | onReceive() | BleOperateManager, ThreadManager | System broadcast | — | If no active network or only WiFi and BLE disconnected → wakes ThreadManager. Simple connectivity watchdog. | No |
| J05157 | com/qcwireless/smart/ui/base/receiver/RebootReceiver.java | documented_app_orchestration | ble_connection | Boot receiver; sets Bluetooth turn-on flag after reboot | onReceive() | BleBaseControl | System boot broadcast | — | Calls BleBaseControl.getInstance().setBluetoothTurnOff(true) on boot. Ensures BLE stack knows BT is available after reboot. | No |
| J05158 | com/qcwireless/smart/ui/base/receiver/SystemLocaleChangeReceiver.java | documented_app_orchestration | ble_connection | Locale change receiver; disconnects BLE and kills process (non-Xiaomi) or reconnects (Xiaomi) | onReceive() | BleBaseControl, BleOperateManager, ActivityCollector, QcDateUtil | System locale change broadcast | — | Sets BT turn-on flag, disconnects BLE. For non-Xiaomi/Redmi: kills process. For Xiaomi: disconnects, reinitializes date strings. | No |
| J05162 | com/qcwireless/smart/ui/base/repository/dao/AnlaNameDao.java | documented_storage | storage_db | Room DAO for anla_name_entity table; supports CRUD + collection status queries | deleteAllItems(), insertList(), queryAllAnlaName(), queryAllCollectionAnla(boolean), updateCollectionStatus(long, boolean) | AnlaNameEntity, BaseDao, Continuation (coroutine) | Room-generated impl | Table: anla_name_entity; columns: create_time, collection | App-internal name/collection entity; not health data. Uses coroutine return pattern. | No |
| J05163 | com/qcwireless/smart/ui/base/repository/dao/AnlaNameDao_Impl.java | documented_storage | storage_db | Room-generated implementation of AnlaNameDao | All CRUD methods | RoomDatabase, RoomSQLiteQuery, CoroutinesRoom | Room framework | Table: anla_name_entity | Auto-generated Room impl; confirms schema but no new info beyond interface. | No |
| J05164 | com/qcwireless/smart/ui/base/repository/dao/BaseDao.java | documented_storage | storage_db | Generic Room DAO base interface with CRUD operations | delete(T), deleteList(List<T>), deleteSome(T...), insert(T), insertAll(List<T>), update(T) | Room annotations (@Delete, @Insert, @Update) | All DAO interfaces in this chunk | onConflict=1 (REPLACE) | Foundation for all DAOs; Insert uses REPLACE strategy. | No |
| J05165 | com/qcwireless/smart/ui/base/repository/dao/ManualBloodOxygenDao.java | documented_storage | spo2, storage_db | Room DAO for blood_oxygen_manual table; manual SpO2 measurement CRUD + upload status tracking | queryByDate(), queryByDateRange(), queryByTimestamp(), queryDataAll(), queryDataLimit(), queryDataLimitLast(), updateUploadStatus() | BloodOxygenManualEntity, BaseDao | Room-generated impl | Table: blood_oxygen_manual; columns: mac, date_str, blood_oxygen, timestamp, isUploadServer, upload_server_unit_time | Schema: mac, date_str, blood_oxygen, timestamp, isUploadServer, upload_server_unit_time. LIMIT 7 for daily display. Upload status tracking with server unix time. | No |
| J05166 | com/qcwireless/smart/ui/base/repository/dao/ManualBloodOxygenDao_Impl.java | documented_storage | spo2, storage_db | Room-generated implementation of ManualBloodOxygenDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery, BloodOxygenManualEntity | Room framework | INSERT OR REPLACE INTO blood_oxygen_manual (mac, date_str, blood_oxygen, timestamp, isUploadServer, upload_server_unit_time) | Confirms column order and types from INSERT statement. | No |
| J05167 | com/qcwireless/smart/ui/base/repository/dao/ManualBloodPressureDao.java | documented_storage | storage_db | Room DAO for blood_pressure_manual table; manual BP measurement CRUD | queryByTimestamp(), queryDataAll(), queryDataLimit(), queryDataLimitLast() | BloodPressureManualEntity, BaseDao | Room-generated impl | Table: blood_pressure_manual; columns: mac, date_str, timestamp | Schema: mac, date_str, timestamp. No upload status columns (unlike SpO2/HR). | No |
| J05168 | com/qcwireless/smart/ui/base/repository/dao/ManualBloodPressureDao_Impl.java | documented_storage | storage_db | Room-generated implementation of ManualBloodPressureDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: blood_pressure_manual | Auto-generated; confirms schema. | No |
| J05169 | com/qcwireless/smart/ui/base/repository/dao/ManualHrvDao.java | documented_storage | hrv_regular, storage_db | Room DAO for hrv_manual table; manual HRV measurement CRUD | queryByDate(), queryByTimestamp(), queryDataAll(), queryDataLimit(), queryDataLimitLast() | HRVManualEntity, BaseDao | Room-generated impl | Table: hrv_manual; columns: mac, date_str, timestamp | Schema: mac, date_str, timestamp. No upload status columns. LIMIT 7 for daily display. | No |
| J05170 | com/qcwireless/smart/ui/base/repository/dao/ManualHrvDao_Impl.java | documented_storage | hrv_regular, storage_db | Room-generated implementation of ManualHrvDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: hrv_manual | Auto-generated; confirms schema. | No |
| J05171 | com/qcwireless/smart/ui/base/repository/dao/ManualPressureDao.java | documented_storage | storage_db | Room DAO for pressure_manual table; manual pressure/stress measurement CRUD | queryByDate(), queryByTimestamp(), queryDataAll(), queryDataLimit(), queryDataLimitLast() | PressureManualEntity, BaseDao | Room-generated impl | Table: pressure_manual; columns: mac, date_str, timestamp | Schema: mac, date_str, timestamp. No upload status columns. | No |
| J05172 | com/qcwireless/smart/ui/base/repository/dao/ManualPressureDao_Impl.java | documented_storage | storage_db | Room-generated implementation of ManualPressureDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: pressure_manual | Auto-generated; confirms schema. | No |
| J05173 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualHeartDao.java | documented_storage | hr, storage_db | Room DAO for app_heart table; manual HR measurement CRUD + upload status tracking | queryAllData(), queryByDate(), queryByDateRange(), queryByTimestamp(), queryDataDate(), queryDataLimit(), queryLastData(), updateUploadStatus() | AppHeartEntity, BaseDao | Room-generated impl | Table: app_heart; columns: mac, date_str, timestamp, heart, isUploadServer, upload_server_unit_time | Schema: mac, date_str, timestamp, heart, isUploadServer, upload_server_unit_time. Upload status tracking. LIMIT 7 for daily display. | No |
| J05174 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualHeartDao_Impl.java | documented_storage | hr, storage_db | Room-generated implementation of QcAppManualHeartDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | INSERT OR REPLACE INTO app_heart (mac, date_str, timestamp, heart, isUploadServer, upload_server_unit_time) | Confirms column order and types. | No |
| J05175 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualSugarContinuousDao.java | documented_storage | storage_db | Room DAO for app_continuous_sugar table; continuous glucose monitoring CRUD | queryBloodSugarByDate(), queryDataDate() | AppBloodSugarContinuousEntity, BaseDao | Room-generated impl | Table: app_continuous_sugar; columns: mac, date_str, hour | Schema: mac, date_str, hour. Hourly granularity for continuous glucose. | No |
| J05176 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualSugarContinuousDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcAppManualSugarContinuousDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: app_continuous_sugar | Auto-generated; confirms schema. | No |
| J05177 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualSugarDao.java | documented_storage | storage_db | Room DAO for app_sugar table; manual blood sugar measurement CRUD | queryAllData(), queryByDate(), queryDataDate(), queryDataLimit(), queryLastData(), queryLastDataTimesTamp() | AppBloodSugarEntity, BaseDao | Room-generated impl | Table: app_sugar; columns: mac, date_str, timestamp | Schema: mac, date_str, timestamp. No upload status columns. LIMIT 7 for daily display. | No |
| J05178 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualSugarDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcAppManualSugarDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: app_sugar | Auto-generated; confirms schema. | No |
| J05179 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualTemperatureDao.java | documented_storage | temperature, storage_db | Room DAO for app_temperature table; manual temperature measurement CRUD | queryAllData(), queryByDate(), queryDataDate(), queryDataLimit(), queryLastData() | AppTemperatureEntity, BaseDao | Room-generated impl | Table: app_temperature; columns: mac, date_str, timestamp | Schema: mac, date_str, timestamp. No upload status columns. LIMIT 7 for daily display. | No |
| J05180 | com/qcwireless/smart/ui/base/repository/dao/QcAppManualTemperatureDao_Impl.java | documented_storage | temperature, storage_db | Room-generated implementation of QcAppManualTemperatureDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: app_temperature | Auto-generated; confirms schema. | No |
| J05181 | com/qcwireless/smart/ui/base/repository/dao/QcBloodOxygenDao.java | documented_storage | spo2, storage_db, sync_scheduler | Room DAO for blood_oxygen table; device-synced SpO2 data CRUD + upload status tracking | queryBloodOxygenByDate(), queryBloodOxygenByDateDesc(), queryByDateRange(), queryUploadToServer(), updateUploadStatus() | BloodOxygenEntity, BaseDao | Room-generated impl | Table: blood_oxygen; columns: device_address, date_str, unix_time, isUploadServer, upload_server_unit_time | Schema: device_address (not mac!), date_str, unix_time, isUploadServer, upload_server_unit_time. Key difference from ManualBloodOxygenDao: uses device_address not mac, unix_time not timestamp. Has queryUploadToServer for server sync. | No |
| J05182 | com/qcwireless/smart/ui/base/repository/dao/QcBloodOxygenDao_Impl.java | documented_storage | spo2, storage_db, sync_scheduler | Room-generated implementation of QcBloodOxygenDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: blood_oxygen | Auto-generated; confirms schema. | No |
| J05183 | com/qcwireless/smart/ui/base/repository/dao/QcBloodPressureDao.java | documented_storage | storage_db, sync_scheduler | Room DAO for blood_pressure table; device-synced BP data CRUD + server upload queries | queryBloodPressureByDate(), queryBloodPressureList(), queryByUnixTime(), queryLastBpValue(), queryUploadToServer() | BloodPressureEntity, BaseDao | Room-generated impl | Table: blood_pressure; columns: device_address, unix_time | Schema: device_address, unix_time. Uses unix_time (long) not timestamp (int). Has queryUploadToServer for server sync. | No |
| J05184 | com/qcwireless/smart/ui/base/repository/dao/QcBloodPressureDao_Impl.java | documented_storage | storage_db, sync_scheduler | Room-generated implementation of QcBloodPressureDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: blood_pressure | Auto-generated; confirms schema. | No |
| J05185 | com/qcwireless/smart/ui/base/repository/dao/QcBloodSugarDao.java | documented_storage | storage_db | Room DAO for blood_sugar table; device-synced blood sugar data CRUD | queryBloodSugarByDate(), queryBloodSugarByDateDesc() | BloodSugarEntity, BaseDao | Room-generated impl | Table: blood_sugar; columns: device_address, date_str | Schema: device_address, date_str. Minimal DAO — only two custom queries. | No |
| J05186 | com/qcwireless/smart/ui/base/repository/dao/QcBloodSugarDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcBloodSugarDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: blood_sugar | Auto-generated; confirms schema. | No |
| J05187 | com/qcwireless/smart/ui/base/repository/dao/QcContactsDao.java | documented_storage | storage_db | Room DAO for contact_entity table; contacts sync CRUD | queryAll() | ContactsEntity, BaseDao | Room-generated impl | Table: contact_entity; columns: mac | Schema: mac. Simple query-all by mac. | No |
| J05188 | com/qcwireless/smart/ui/base/repository/dao/QcContactsDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcContactsDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery | Room framework | Table: contact_entity | Auto-generated; confirms schema. | No |
| J05189 | com/qcwireless/smart/ui/base/repository/dao/QcCustomerPraiseDao.java | documented_storage | storage_db | Room DAO for customer_praise_entity table; customer praise/feedback CRUD | getByDeviceAddressOrderedByTime(), insertPraise() | CustomerPraiseEntity, BaseDao | Room-generated impl | Table: customer_praise_entity; columns: device_address, create_time | Schema: device_address, create_time. Uses coroutine return pattern. | No |
| J05190 | com/qcwireless/smart/ui/base/repository/dao/QcCustomerPraiseDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcCustomerPraiseDao | All query/insert/update methods | RoomDatabase, RoomSQLiteQuery, CoroutinesRoom | Room framework | Table: customer_praise_entity | Auto-generated; confirms schema. | No |

---

## Function Dictionary Proposals

### BleCommonDataParseKt — parseBleData

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/BleCommonDataParseKt.java |
| class | BleCommonDataParseKt |
| method_or_field | parseBleData |
| kind | static_method |
| general_function | Parses BLE notification data; if byte[0] masked against ~Constants.m equals 2 and byte[1] equals 1, triggers camera activity or notification |
| variables_fields | data (byte[]) |
| constants_command_ids | Constants.m (mask byte) |
| inputs | byte[] data from BLE characteristic change |
| outputs | Side effects: launches CameraActivity or posts CameraToastEvent |
| calls | AppUtil.isBackground, NotificationUtils.initCameraNotification, PermissionUtilKt.hasCameraPermission, EventBus.post(CameraToastEvent) |
| called_by | MyBluetoothReceiver.onCharacteristicChange |
| ble_service_or_characteristic | Unknown — determined by Constants.m mask check |
| database_or_model_touched | None |
| data_domains | ble_connection |
| freshness_truth_implications | Camera trigger is a device-side notification (remote camera control); data freshness is real-time |
| evidence_notes | The byte pattern check (byte[0] & ~Constants.m == 2, byte[1] == 1) appears to be a remote camera trigger command from the watch |
| unknowns | Constants.m value; which characteristic UUID this data arrives on |
| confidence | high |

### BleCommonDataParseKt — parseDeviceInfoData

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/BleCommonDataParseKt.java |
| class | BleCommonDataParseKt |
| method_or_field | parseDeviceInfoData |
| kind | static_method |
| general_function | Parses device info from BLE characteristic reads; stores firmware version (Constants.f) or hardware version (Constants.g) in UserConfig |
| variables_fields | uuid (String), data (byte[]) |
| constants_command_ids | Constants.f (FM version UUID), Constants.g (HW version UUID) |
| inputs | uuid string, byte[] data from BLE characteristic read |
| outputs | Side effects: stores FM/HW version in UserConfig, posts FirmCheckEvent, WatchFaceDownloadEvent, DeviceConfigEvent; sets BleOperateManager.setReady(true) |
| calls | UserConfig.setFmVersion/setHwVersion/save, EventBus.post(FirmCheckEvent/WatchFaceDownloadEvent/DeviceConfigEvent), BleOperateManager.setReady(true) |
| called_by | MyBluetoothReceiver.onCharacteristicRead |
| ble_service_or_characteristic | Constants.f, Constants.g (characteristic UUIDs for FM/HW version) |
| database_or_model_touched | UserConfig (SharedPreferences) |
| data_domains | ble_connection |
| freshness_truth_implications | Firmware/hardware version is read once on service discovery; setReady(true) signals device is fully initialized |
| evidence_notes | HW version read triggers setReady(true) — this is the "device ready" signal for the app |
| unknowns | Exact UUID values for Constants.f and Constants.g |
| confidence | high |

### MyBluetoothReceiver — onCharacteristicChange

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java |
| class | MyBluetoothReceiver |
| method_or_field | onCharacteristicChange |
| kind | override_method |
| general_function | BLE characteristic change callback; dispatches data to BleCommonDataParseKt.parseBleData on background thread |
| variables_fields | address (String), uuid (String), data (byte[]) |
| constants_command_ids | None directly |
| inputs | address, uuid, data from BLE notification |
| outputs | Delegates to BleCommonDataParseKt.parseBleData |
| calls | ThreadExtKt.ktxRunOnBgSingleBle, BleCommonDataParseKt.parseBleData |
| called_by | BLE framework (QCBluetoothCallbackCloneReceiver) |
| ble_service_or_characteristic | All notification characteristics |
| database_or_model_touched | None |
| data_domains | ble_connection |
| freshness_truth_implications | Real-time BLE notification dispatch |
| evidence_notes | Runs on background single-BLE thread; delegates all parsing to BleCommonDataParseKt |
| unknowns | Which specific characteristics trigger which data flows |
| confidence | high |

### MyBluetoothReceiver — onCharacteristicRead

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java |
| class | MyBluetoothReceiver |
| method_or_field | onCharacteristicRead |
| kind | override_method |
| general_function | BLE characteristic read callback; dispatches uuid+data to BleCommonDataParseKt.parseDeviceInfoData on background thread |
| variables_fields | uuid (String), data (byte[]) |
| constants_command_ids | None directly |
| inputs | uuid, data from BLE read response |
| outputs | Delegates to BleCommonDataParseKt.parseDeviceInfoData |
| calls | ThreadExtKt.ktxRunOnBgSingleBle, BleCommonDataParseKt.parseDeviceInfoData |
| called_by | BLE framework (QCBluetoothCallbackCloneReceiver) |
| ble_service_or_characteristic | Read characteristics (FM/HW version) |
| database_or_model_touched | None directly |
| data_domains | ble_connection |
| freshness_truth_implications | Read response dispatch for device info |
| evidence_notes | Null-checks uuid and data before dispatching |
| unknowns | None |
| confidence | high |

### MyBluetoothReceiver — onServiceDiscovered

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java |
| class | MyBluetoothReceiver |
| method_or_field | onServiceDiscovered |
| kind | override_method |
| general_function | Called when BLE services are discovered; inits LargeDataHandler, posts BluetoothEvent(true), calls initCmd() |
| variables_fields | None |
| constants_command_ids | None |
| inputs | None (callback) |
| outputs | Side effects: LargeDataHandler init, BluetoothEvent, initCmd sequence |
| calls | LargeDataHandler.initEnable(), EventBus.post(BluetoothEvent(true)), initCmd() |
| called_by | BLE framework |
| ble_service_or_characteristic | All services discovered |
| database_or_model_touched | None |
| data_domains | ble_connection, battery |
| freshness_truth_implications | Service discovery = device connected and ready for commands |
| evidence_notes | This is the "connection complete" signal; triggers battery read, HW/FM reads, and device settings init |
| unknowns | DeviceCmdInit.initDeviceSetting() details |
| confidence | high |

### MyBluetoothReceiver — initCmd

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java |
| class | MyBluetoothReceiver |
| method_or_field | initCmd |
| kind | private_method |
| general_function | Sends initial command sequence after BLE service discovery: read HW version, read battery (SimpleKeyReq byte 3), read FM version, init device settings |
| variables_fields | None |
| constants_command_ids | SimpleKeyReq(byte 3) = battery read command |
| inputs | None |
| outputs | Battery value stored in UserConfig |
| calls | CommandHandle.execReadCmd(getReadHwRequest), CommandHandle.executeReqCmd(SimpleKeyReq(3)), CommandHandle.execReadCmd(getReadFmRequest), DeviceCmdInit.initDeviceSetting() |
| called_by | onServiceDiscovered |
| ble_service_or_characteristic | Battery characteristic (via SimpleKeyReq) |
| database_or_model_touched | UserConfig (battery value) |
| data_domains | battery, ble_connection |
| freshness_truth_implications | Battery read happens on every connection; freshness is per-connection |
| evidence_notes | SimpleKeyReq(3) is the battery command ID in the protocol |
| unknowns | Full list of SimpleKeyReq byte values |
| confidence | high |

### MyBluetoothReceiver — connectStatue

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/MyBluetoothReceiver.java |
| class | MyBluetoothReceiver |
| method_or_field | connectStatue |
| kind | override_method |
| general_function | BLE connection state callback; saves device name/address to UserConfig, sets lastTenMinSyncTime, clears GoogleFit last info on new device |
| variables_fields | device (BluetoothDevice), connected (boolean) |
| constants_command_ids | None |
| inputs | BluetoothDevice, connected flag |
| outputs | UserConfig updated with device info, lastTenMinSyncTime = now+600s |
| calls | UserConfig.setDeviceName/setDeviceAddress/setDeviceAddressNoClear/setWeatherToDeviceLastTime/setLastTenMinSyncTime/save, PreUtil.putString |
| called_by | BLE framework |
| ble_service_or_characteristic | None |
| database_or_model_touched | UserConfig (SharedPreferences) |
| data_domains | ble_connection, sync_scheduler |
| freshness_truth_implications | lastTenMinSyncTime set to now+600s = 10-minute sync interval after connection |
| evidence_notes | 10-minute sync window (600 seconds) after connection; GoogleFit info cleared on new device |
| unknowns | None |
| confidence | high |

### BluetoothReceiver — onReceive (key actions)

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/receiver/BluetoothReceiver.java |
| class | BluetoothReceiver |
| method_or_field | onReceive |
| kind | override_method |
| general_function | System broadcast receiver handling BT adapter state, ACL events, bond state, screen, time changes; manages reconnection and sport-data sync |
| variables_fields | btDevice, btReconnect, bleOpen, numConnect, mHandler, connectRunnable, uiRunnable, classicBluetoothRunnable |
| constants_command_ids | BT state: 10=OFF, 12=ON; Bond state: 10=failed, 11=bonding, 12=bonded |
| inputs | Context, Intent (broadcast action) |
| outputs | Reconnection, sport sync, time sync, SPP connection |
| calls | BleOperateManager.setBluetoothTurnOff/setReConnectMac/disconnect/isConnected, DeviceReconnect.connectWithScanValidation, CommandHandle.executeReqCmd(SetTimeReq), StepDetailRepository.syncTodayStep, SppHandle.connect, BleScannerHelper.removeMacSystemBond |
| called_by | Android system broadcast |
| ble_service_or_characteristic | None (system-level BT) |
| database_or_model_touched | UserConfig, PreUtil (today steps) |
| data_domains | ble_connection, steps_sport, sync_scheduler |
| freshness_truth_implications | Sport data synced on BT connect with 3-minute throttle; time sync sent on TIME_SET |
| evidence_notes | Reconnect uses exponential backoff: numConnect + (numConnect/10) + 1, delay = (numConnect/10+1)*60s. Max 20 retries. Sport sync limited to every 3 minutes. |
| unknowns | Full DeviceReconnect.connectWithScanValidation flow |
| confidence | high |

### ManualBloodOxygenDao — queryByDate / updateUploadStatus

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/repository/dao/ManualBloodOxygenDao.java |
| class | ManualBloodOxygenDao |
| method_or_field | queryByDate, updateUploadStatus |
| kind | interface_method |
| general_function | Room DAO for manual SpO2 measurements; query by date/mac, update upload status to server |
| variables_fields | mac, date, dateStr, isUpload, uploadServerUnixTime |
| constants_command_ids | Table: blood_oxygen_manual |
| inputs | mac (device MAC), date/dateStr, timestamp range |
| outputs | BloodOxygenManualEntity or List<BloodOxygenManualEntity> |
| calls | Room SQLite |
| called_by | Repository layer |
| ble_service_or_characteristic | None |
| database_or_model_touched | blood_oxygen_manual table |
| data_domains | spo2, storage_db |
| freshness_truth_implications | Manual SpO2 stored with timestamp; upload status tracked for server sync |
| evidence_notes | Schema: mac, date_str, blood_oxygen, timestamp, isUploadServer, upload_server_unit_time. LIMIT 7 for daily display. |
| unknowns | BloodOxygenManualEntity field details (need entity class) |
| confidence | high |

### QcAppManualHeartDao — queryByDate / updateUploadStatus

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/repository/dao/QcAppManualHeartDao.java |
| class | QcAppManualHeartDao |
| method_or_field | queryByDate, updateUploadStatus |
| kind | interface_method |
| general_function | Room DAO for manual HR measurements; query by date/mac, update upload status to server |
| variables_fields | mac, date, dateStr, isUpload, uploadServerUnixTime |
| constants_command_ids | Table: app_heart |
| inputs | mac (device MAC), date/dateStr, timestamp |
| outputs | AppHeartEntity or List<AppHeartEntity> |
| calls | Room SQLite |
| called_by | Repository layer |
| ble_service_or_characteristic | None |
| database_or_model_touched | app_heart table |
| data_domains | hr, storage_db |
| freshness_truth_implications | Manual HR stored with timestamp; upload status tracked for server sync |
| evidence_notes | Schema: mac, date_str, timestamp, heart, isUploadServer, upload_server_unit_time. LIMIT 7 for daily display. |
| unknowns | AppHeartEntity field details |
| confidence | high |

### ManualHrvDao — queryByDate / queryByTimestamp

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/repository/dao/ManualHrvDao.java |
| class | ManualHrvDao |
| method_or_field | queryByDate, queryByTimestamp |
| kind | interface_method |
| general_function | Room DAO for manual HRV measurements; query by date/mac or timestamp range |
| variables_fields | mac, date, start, end |
| constants_command_ids | Table: hrv_manual |
| inputs | mac (device MAC), date, timestamp range |
| outputs | HRVManualEntity or List<HRVManualEntity> |
| calls | Room SQLite |
| called_by | Repository layer |
| ble_service_or_characteristic | None |
| database_or_model_touched | hrv_manual table |
| data_domains | hrv_regular, storage_db |
| freshness_truth_implications | Manual HRV stored with timestamp; no upload status tracking (unlike HR/SpO2) |
| evidence_notes | Schema: mac, date_str, timestamp. No isUploadServer column. LIMIT 7 for daily display. |
| unknowns | HRVManualEntity field details |
| confidence | high |

### QcBloodOxygenDao — queryBloodOxygenByDate / queryUploadToServer

| Field | Value |
|-------|-------|
| file | com/qcwireless/smart/ui/base/repository/dao/QcBloodOxygenDao.java |
| class | QcBloodOxygenDao |
| method_or_field | queryBloodOxygenByDate, queryUploadToServer, updateUploadStatus |
| kind | interface_method |
| general_function | Room DAO for device-synced SpO2 data; query by date/device_address, query unsynced data for server upload |
| variables_fields | mac, dateStr, startTime, isUpload, uploadServerUnixTime |
| constants_command_ids | Table: blood_oxygen |
| inputs | mac (device_address), dateStr, startTime |
| outputs | BloodOxygenEntity or List<BloodOxygenEntity> |
| calls | Room SQLite |
| called_by | Repository layer, sync logic |
| ble_service_or_characteristic | None |
| database_or_model_touched | blood_oxygen table |
| data_domains | spo2, storage_db, sync_scheduler |
| freshness_truth_implications | Device-synced SpO2 (not manual); uses device_address not mac; has queryUploadToServer for server sync |
| evidence_notes | Key difference from ManualBloodOxygenDao: this is device-synced data (blood_oxygen table uses device_address, unix_time); manual data (blood_oxygen_manual uses mac, timestamp). Both have upload status tracking. |
| unknowns | BloodOxygenEntity field details |
| confidence | high |

---

## Key Architectural Findings

### 1. BLE Data Flow Chain (Complete)
```
BLE Framework → QCBluetoothCallbackCloneReceiver
  → MyBluetoothReceiver.onCharacteristicChange(address, uuid, data)
    → BleCommonDataParseKt.parseBleData(data)        [notification data]
  → MyBluetoothReceiver.onCharacteristicRead(uuid, data)
    → BleCommonDataParseKt.parseDeviceInfoData(uuid, data) [read responses]
  → MyBluetoothReceiver.onServiceDiscovered()
    → LargeDataHandler.initEnable()
    → EventBus.post(BluetoothEvent(true))
    → initCmd() [battery, HW, FM reads, device settings]
```

### 2. Dual Storage Schema for Health Data
The app maintains **two parallel storage schemas** for some health metrics:
- **Manual (user-initiated) tables**: `app_heart`, `blood_oxygen_manual`, `hrv_manual`, `blood_pressure_manual`, `pressure_manual`, `app_sugar`, `app_continuous_sugar`, `app_temperature`
  - Use `mac` as device identifier
  - Use `timestamp` (int) as time key
  - Use `date_str` for date-based queries
  - Some have `isUploadServer`/`upload_server_unit_time` for server sync
- **Device-synced tables**: `blood_oxygen`, `blood_pressure`, `blood_sugar`
  - Use `device_address` as device identifier
  - Use `unix_time` (long) as time key
  - Have `queryUploadToServer` for server sync

### 3. Reconnection Strategy
- Exponential backoff: `numConnect = numConnect + (numConnect/10) + 1`
- Delay: `(numConnect/10 + 1) * 60_000ms`
- Max 20 retries before giving up
- On BT ON: immediate reconnect via `DeviceReconnect.connectWithScanValidation`
- On ACL_DISCONNECTED: 22-second delay before reconnect attempt

### 4. Sync Timing
- Sport data: 3-minute throttle (`lastSyncTodaySteps + 180 > now`)
- After connection: 10-minute window (`lastTenMinSyncTime = now + 600`)
- Time sync: sent on `ACTION_TIME_SET` system broadcast

### 5. Camera Remote Control
- BLE byte pattern `byte[0] & ~Constants.m == 2` and `byte[1] == 1` triggers camera
- If app in background: notification; if foreground: CameraActivity
- Requires camera permission check

---

## Summary

| Metric | Value |
|--------|-------|
| Files assigned | 35 |
| Files actually read | 35 |
| Rows needing second pass | 0 |
| Strongest new findings | (1) Complete BLE dispatch chain: MyBluetoothReceiver → BleCommonDataParseKt with camera trigger and firmware/HW version parsing. (2) Dual storage schema: manual vs device-synced tables with different column naming (mac/device_address, timestamp/unix_time). (3) SimpleKeyReq(3) = battery command ID. (4) Reconnection exponential backoff with 20-retry cap. (5) 10-minute sync window after connection. (6) 3-minute sport-data throttle. |
| How fulfilling was this task? | Very fulfilling — this chunk delivered exactly what was asked: the complete BLE parse flow, reboot/sync flow, and storage schema for manual HR/SpO2/HRV. The receivers and DAOs form a coherent picture. |
| What would you like changed? | (1) The _Impl files are auto-generated Room boilerplate — they could be pre-classified as `excluded_generated_or_ui_only` to save reading time. (2) Having the Entity classes in the same chunk would eliminate the "unknowns" about field details. (3) A cross-reference to Constants.f/g UUID values would complete the BLE characteristic mapping. |
