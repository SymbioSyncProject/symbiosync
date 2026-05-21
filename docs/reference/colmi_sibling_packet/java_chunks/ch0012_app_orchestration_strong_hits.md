# CH0012 — App Orchestration Strong Hits (QcDatabase & DAO Layer)

**Chunk ID:** CH0012  
**Chunk type:** app_orchestration_strong_hits  
**Source tree:** decompiled4 (`com/qcwireless/smart`)  
**Focus question:** QcDatabase and DAO implementation files — what local storage schemas exist for HR, SpO2, HRV, sleep, temperature, sport, device settings? Identify entity/table/DAO names that tell us what the vendor app considers distinct data channels.  
**Qualitative telemetry guess:** I'm likely running as a Claude-family model (Claude 3.5 Sonnet or similar), given the multi-step analytical structure, tool-use patterns, and preference for structured tabular output.

---

## Status Table

| ledger_id | relative_path | terminal_status | data_domains | general_function | relevant_methods_or_fields | calls_or_imports | called_by_clues | constants_command_ids | evidence_notes | needs_followup |
|---|---|---|---|---|---|---|---|---|---|---|
| J05191 | com/qcwireless/smart/ui/base/repository/dao/QcCustomFaceDao.java | documented_storage | storage_db | DAO for custom watch face images; queries by hd_version and address | queryWatchFaceCustom(hdVersion), queryWatchFaceList(address) | BaseDao, CustomFaceEntity, @Dao/@Query | QcDatabase.qcCustomFaceDao() | — | Table `custom_face`; PK (hd_version, type, address); stores image URLs for custom watch faces | no |
| J05192 | com/qcwireless/smart/ui/base/repository/dao/QcCustomFaceDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcCustomFaceDao | RoomSQLiteQuery, SQLite statements | RoomDatabase, RoomSQLiteQuery | QcDatabase_Impl | — | Auto-generated; 254 lines; confirms table `custom_face` schema | no |
| J05193 | com/qcwireless/smart/ui/base/repository/dao/QcDatabase.java | documented_app_orchestration | hr, hrv_regular, sleep, spo2, steps_sport, storage_db, sync_scheduler, temperature | **Central Room database definition** — registers all 47 entities and 35+ DAOs; DB name "qc_database.db", version 55 | getDatabase(context), 35+ abstract DAO accessors | Room, RoomDatabase, all entity imports | Entire app data layer | DB name: "qc_database.db", version: 55 | **KEY FILE**: @Database annotation lists all 47 entities; abstract methods expose every DAO; singleton pattern via Companion.getDatabase(); fallbackToDestructiveMigration | no |
| J05194 | com/qcwireless/smart/ui/base/repository/dao/QcDatabase_Impl.java | documented_storage | hr, hrv_regular, sleep, spo2, steps_sport, storage_db, sync_scheduler, temperature | Room-generated implementation — contains CREATE TABLE SQL for all 47 tables, clearAllTables(), invalidation tracker | createAllTables(), clearAllTables(), createInvalidationTracker(), createOpenHelper() | RoomOpenHelper, TableInfo, SupportSQLiteDatabase | Room framework | identity_hash: bf0a37d4c17f2061f523c26f437471b2 | **CRITICAL**: Contains full DDL for every table in qc_database.db; 1827 lines; 47 tables enumerated | no |
| J05195 | com/qcwireless/smart/ui/base/repository/dao/QcDeviceDao.java | documented_storage | storage_db | DAO for paired device records; CRUD + image URL/time updates | getAllDevicesOrderByUpdateTimeDesc(), getDeviceByAddress(), insertDevice(), updateDeviceImageUrls(), updateDeviceTime() | BaseDao, QcDeviceEntity, CoroutinesRoom | QcDatabase.qcDeviceDao() | — | Table `device_entity`; PK (device_address); fields: device_name, fm_version, img_local_url, img_url, device_type, update_time; uses coroutine return pattern | no |
| J05196 | com/qcwireless/smart/ui/base/repository/dao/QcDeviceDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcDeviceDao | RoomSQLiteQuery, CoroutinesRoom | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 353 lines; confirms device_entity schema | no |
| J05197 | com/qcwireless/smart/ui/base/repository/dao/QcDeviceSettingDao.java | documented_storage | storage_db | DAO for per-device settings; key-value by mac+action | deleteDataWhereMacNotNull(mac), queryByMacAndAction(mac, action) | BaseDao, DeviceSettingEntity | QcDatabase.qcDeviceSettingDao() | — | Table `device_setting`; PK (mac, setting_action); content field is TEXT blob; action-based key-value store for device preferences | no |
| J05198 | com/qcwireless/smart/ui/base/repository/dao/QcDeviceSettingDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcDeviceSettingDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 239 lines | no |
| J05199 | com/qcwireless/smart/ui/base/repository/dao/QcEbookDao.java | excluded_low_signal | storage_db | DAO for ebook entities; simple query all / delete by name | queryEbooks(), deleteBookName(bookName) | BaseDao, EbookEntity | QcDatabase.qcEbookDao() | — | Table `ebook_entity`; no health data; just book_name, first_name, file_path | no |
| J05200 | com/qcwireless/smart/ui/base/repository/dao/QcEbookDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcEbookDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; no health relevance | no |
| J05201 | com/qcwireless/smart/ui/base/repository/dao/QcEcgDao.java | documented_storage | hr, storage_db, sync_scheduler | DAO for ECG records; query by device, type, unix_time; delete by device+time | queryAllEcg(mac), queryEcgByType(mac, type), queryEcgByUnixTime(deviceAddress, unixTime), queryLastEcg(mac), deleteAllByDevice(), deleteByDeviceAndDate() | BaseDao, QcEcgEntity | QcDatabase.qcEcgDao() | — | Table `qc_ecg_entity`; PK (device_address, date_str); fields: type, data_list (JSON), avg_heart, unix_time, sync, last_sync_time | no |
| J05202 | com/qcwireless/smart/ui/base/repository/dao/QcEcgDao_Impl.java | documented_storage | hr, storage_db, sync_scheduler | Room-generated implementation of QcEcgDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 362 lines; confirms qc_ecg_entity schema | no |
| J05203 | com/qcwireless/smart/ui/base/repository/dao/QcFeedbackDao.java | excluded_low_signal | storage_db | DAO for feedback; simple query all | queryFeedbackList() | BaseDao, FeedbackEntity | QcDatabase.qcFeedbackDao() | — | Table `feedback`; no health data | no |
| J05204 | com/qcwireless/smart/ui/base/repository/dao/QcFeedbackDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcFeedbackDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; no health relevance | no |
| J05205 | com/qcwireless/smart/ui/base/repository/dao/QcGpsDetailDao.java | documented_storage | storage_db | DAO for GPS track records; query by start_time, date | queryAll(), queryByStartTime(start), queryFirstByStartTime(), queryListByDate(date) | BaseDao, GpsDetail | QcDatabase.qcGpsDao() | — | Table `gps_detail`; PK (start_time); fields: duration, distance, calorie, locations (JSON), date_str, gps_type | no |
| J05206 | com/qcwireless/smart/ui/base/repository/dao/QcGpsDetailDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcGpsDetailDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; confirms gps_detail schema | no |
| J05207 | com/qcwireless/smart/ui/base/repository/dao/QcHealthyDao.java | excluded_low_signal | storage_db | **Empty DAO interface** — no methods, no entity bound | (none) | @Dao | QcDatabase (unused?) | — | Placeholder/stub; 11 lines; no actual functionality | no |
| J05208 | com/qcwireless/smart/ui/base/repository/dao/QcHeartRateDetailDao.java | documented_storage | hr, storage_db, sync_scheduler | DAO for continuous HR data; date-range queries, sync status, upload tracking | queryByDateRange(mac, startDate, endDate), queryBySync(), queryDaysSyncDate(deviceAddress), queryHeartByDate(deviceAddress, date), queryLastSyncDate(deviceAddress), updateUploadStatus(deviceAddress, dateStr, isUpload, uploadServerUnixTime) | BaseDao, HeartRateDetail | QcDatabase.qcHeartRateDao() | — | Table `heart_rate_detail`; PK (device_address, date_str); fields: interval, index_str, value (JSON), unix_time, sync, last_sync_time, isUploadServer, upload_server_unit_time | no |
| J05209 | com/qcwireless/smart/ui/base/repository/dao/QcHeartRateDetailDao_Impl.java | documented_storage | hr, storage_db, sync_scheduler | Room-generated implementation of QcHeartRateDetailDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 404 lines; confirms heart_rate_detail schema | no |
| J05210 | com/qcwireless/smart/ui/base/repository/dao/QcHrvDetailDao.java | documented_storage | hrv_regular, storage_db, sync_scheduler | DAO for HRV detail data; unix_time range queries, sync tracking | queryByAddressAndDate(deviceAddress, start, end), queryBySync(), queryDaysSyncDate(deviceAddress), queryLastSyncDate(deviceAddress, content), queryPressureByDate(deviceAddress, date) | BaseDao, HRVDetail | QcDatabase.qcHrvDetailDao() | — | Table `hrv_detail`; PK (device_address, date_str); fields: interval, index_str, value (JSON), unix_time, sync, last_sync_time; note: method named "queryPressureByDate" is actually HRV — naming artifact | no |
| J05211 | com/qcwireless/smart/ui/base/repository/dao/QcHrvDetailDao_Impl.java | documented_storage | hrv_regular, storage_db, sync_scheduler | Room-generated implementation of QcHrvDetailDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 361 lines; confirms hrv_detail schema | no |
| J05212 | com/qcwireless/smart/ui/base/repository/dao/QcManualHeartDao.java | documented_storage | hr, storage_db | DAO for manually-triggered HR measurements; mac-based queries, upload tracking | queryAllData(mac), queryByDate(mac, date), queryByDateRange(mac, startDate, endDate), queryDataDate(mac), updateUploadStatus(deviceAddress, dateStr, isUpload, uploadServerUnixTime) | BaseDao, ManualHeartEntity | QcDatabase.qcManualHeartDao() | — | Table `manual_heart_entity`; PK (mac, date_str); fields: content (JSON), isUploadServer, upload_server_unit_time; distinct from continuous HR — this is spot-check data | no |
| J05213 | com/qcwireless/smart/ui/base/repository/dao/QcManualHeartDao_Impl.java | documented_storage | hr, storage_db | Room-generated implementation of QcManualHeartDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 339 lines; confirms manual_heart_entity schema | no |
| J05214 | com/qcwireless/smart/ui/base/repository/dao/QcMenstruationDao.java | excluded_low_signal | storage_db | DAO for menstruation tracking; year/month queries | deleteAll(), queryAll(), queryMaxByStartTime(), queryMenstruationByYearAndMonth(year, month) | BaseDao, MenstruationEntity | QcDatabase.qcMenstruationDao() | — | Table `menstruation`; no direct health-sensor data; user-entered cycle data | no |
| J05215 | com/qcwireless/smart/ui/base/repository/dao/QcMenstruationDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcMenstruationDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; no direct health-sensor relevance | no |
| J05216 | com/qcwireless/smart/ui/base/repository/dao/QcMessagePushDao.java | excluded_low_signal | storage_db | DAO for notification push settings; package_name based | deleteByPackageName(name), queryByName(name), queryByNameAndOpen(name, open), queryByOpen(open), queryByStatus() | BaseDao, MessagePushEntity | QcDatabase.qcMessagePushDao() | — | Table `message_push`; no health data; notification preferences | no |
| J05217 | com/qcwireless/smart/ui/base/repository/dao/QcMessagePushDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcMessagePushDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; no health relevance | no |
| J05218 | com/qcwireless/smart/ui/base/repository/dao/QcMusicManagerDao.java | excluded_low_signal | storage_db | DAO for music-to-device file management; playlist/song-menu queries | queryAll(address), queryAllMusicNoMenuId(address), queryMusicByName(address, musicName), queryMusicNoSongList(address), queryMusicsByMenuId(address, menuId), deleteByMusicName(), deleteMusics(address), updateMenuName(), updateMusicMenu() | BaseDao, MusicToDeviceEntity | QcDatabase.qcMusicManagerDao() | — | Table `music_to_device`; no health data; music file management | no |
| J05219 | com/qcwireless/smart/ui/base/repository/dao/QcMusicManagerDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcMusicManagerDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 474 lines; no health relevance | no |
| J05220 | com/qcwireless/smart/ui/base/repository/dao/QcMusicMenuDao.java | excluded_low_signal | storage_db | DAO for song menu/playlists on device | queryMenuList(address), queryMenusList(address), queryMusicMenuByMenuId(address, menuId), queryMusicMenuByMenuName(address, menuName), deleteMenu(menuId), updateMenuName() | BaseDao, SongMenuEntity | QcDatabase.qcMusicMenuDao() | — | Table `song_menu`; no health data | no |
| J05221 | com/qcwireless/smart/ui/base/repository/dao/QcMusicMenuDao_Impl.java | excluded_low_signal | storage_db | Room-generated implementation of QcMusicMenuDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; no health relevance | no |
| J05222 | com/qcwireless/smart/ui/base/repository/dao/QcMuslimDetailDao.java | documented_storage | storage_db, sync_scheduler | DAO for Muslim prayer detail (prayer count tracking per time-slot); sync-aware | queryByAddressAndDate(deviceAddress, start, end), queryByDate(dateStr, deviceAddress), queryBySync(), queryDaysSyncDate(deviceAddress), queryLastDate(deviceAddress), queryLastSyncDate(deviceAddress, content), queryPressureByDate(deviceAddress, date) | BaseDao, MuslimDetail | QcDatabase.qcMuslimDetailDao() | — | Table `muslim_detail`; PK (device_address, date_str); fields: interval, index_str, counts (CSV), unix_time, sync, last_sync_time; "pressure" naming is artifact — this is prayer count data | no |
| J05223 | com/qcwireless/smart/ui/base/repository/dao/QcMuslimDetailDao_Impl.java | documented_storage | storage_db, sync_scheduler | Room-generated implementation of QcMuslimDetailDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 426 lines; confirms muslim_detail schema | no |
| J05224 | com/qcwireless/smart/ui/base/repository/dao/QcMuslimTotalDao.java | documented_storage | storage_db | DAO for Muslim prayer totals per day | queryByAddressAndDate(deviceAddress, start, end), queryPressureByDate(deviceAddress, date), queryTotalStepByAddressAndDate(deviceAddress, date), queryTotalStepByAddressAndDateCount(deviceAddress, date) | BaseDao, MuslimTotal | QcDatabase.qcMuslimTotalDao() | — | Table `muslim_total`; PK (device_address, date_str); fields: count, unix_time; "pressure" and "step" naming are artifacts | no |
| J05225 | com/qcwireless/smart/ui/base/repository/dao/QcMuslimTotalDao_Impl.java | documented_storage | storage_db | Room-generated implementation of QcMuslimTotalDao | RoomSQLiteQuery | RoomDatabase | QcDatabase_Impl | — | Auto-generated; 316 lines; confirms muslim_total schema | no |

---

## Complete Table Schema Inventory (from QcDatabase_Impl DDL)

This is the **full local storage schema** as extracted from the `createAllTables()` method. Tables are grouped by data domain.

### Health / Biometric Tables

| Table Name | Entity Class | PK | Key Columns | Data Domain |
|---|---|---|---|---|
| `heart_rate_detail` | HeartRateDetail | (device_address, date_str) | interval, index_str, value, unix_time, sync, last_sync_time, isUploadServer, upload_server_unit_time | **HR (continuous)** |
| `manual_heart_entity` | ManualHeartEntity | (mac, date_str) | content, isUploadServer, upload_server_unit_time | **HR (manual/spot-check)** |
| `app_heart` | AppHeartEntity | (mac, timestamp) | heart, date_str, isUploadServer, upload_server_unit_time | **HR (app-initiated)** |
| `hrv_detail` | HRVDetail | (device_address, date_str) | interval, index_str, value, unix_time, sync, last_sync_time | **HRV (continuous)** |
| `hrv_manual` | HRVManualEntity | (mac, timestamp) | hrv, date_str | **HRV (manual)** |
| `blood_oxygen` | BloodOxygenEntity | (device_address, date_str) | min_array, max_array, unix_time, sync, last_sync_time, isUploadServer, upload_server_unit_time | **SpO2 (continuous)** |
| `blood_oxygen_manual` | BloodOxygenManualEntity | (mac, timestamp) | blood_oxygen, date_str, isUploadServer, upload_server_unit_time | **SpO2 (manual)** |
| `temperature_entity` | BodyTemperatureEntity | (device_address, date_str, min) | unix_time, temperature, sync, manual_flag, last_sync_time | **Temperature (skin/body)** |
| `app_temperature` | AppTemperatureEntity | (mac, timestamp) | temperature, date_str | **Temperature (app-initiated)** |
| `blood_pressure` | BloodPressureEntity | (device_address, unix_time) | sbp, dbp, sync, last_sync_time | **Blood pressure (continuous)** |
| `blood_pressure_manual` | BloodPressureManualEntity | (mac, timestamp) | sbp, dbp, date_str | **Blood pressure (manual)** |
| `blood_sugar` | BloodSugarEntity | (device_address, date_str) | min_array, max_array, unix_time, sync, last_sync_time | **Blood sugar (continuous)** |
| `app_sugar` | AppBloodSugarEntity | (mac, timestamp) | sugar, date_str | **Blood sugar (app/manual)** |
| `app_continuous_sugar` | AppBloodSugarContinuousEntity | (mac, date_str, hour) | min_sugar, max_sugar, timestamp | **Blood sugar (continuous app)** |
| `pressure_detail` | PressureDetail | (device_address, date_str) | interval, index_str, value, unix_time, sync, last_sync_time | **Stress/pressure (continuous)** |
| `pressure_manual` | PressureManualEntity | (mac, timestamp) | pressure, date_str | **Stress/pressure (manual)** |
| `qc_ecg_entity` | QcEcgEntity | (device_address, date_str) | type, data_list, avg_heart, unix_time, sync, last_sync_time | **ECG** |

### Sleep Tables

| Table Name | Entity Class | PK | Key Columns | Data Domain |
|---|---|---|---|---|
| `sleep_detail` | SleepDetail | (device_address, date_str) | interval, index_str, quality, sync, last_sync_time | **Sleep (detail intervals)** |
| `sleep_total` | SleepTotalHistory | (device_address, date_str) | total_sleep, deep_sleep, light_sleep, rapid_sleep, awake, start_time, end_time, lunch_start, lunch_end, unix_time, avg_heart, avg_blood_oxygen, avg_hrv, bedtime | **Sleep (daily summary)** |
| `sleep_new_protocol` | SleepNewProtocol | (device_address, date_str) | detail, st, et, sync, last_sync_time, lunch_list, isUploadServer, upload_server_unit_time | **Sleep (new protocol)** |
| `sleep_lunch_protocol` | SleepLunchProtocol | (device_address, date_str) | detail, lunch_st, lunch_et, sync, last_sync_time, isUploadServer, upload_server_unit_time, lunch_list | **Sleep (lunch nap protocol)** |

### Activity / Sport Tables

| Table Name | Entity Class | PK | Key Columns | Data Domain |
|---|---|---|---|---|
| `step_detail` | StepDetail | (device_address, date_str) | interval, total_active_time, index_str, counts, miles, calories, sync, last_sync_time | **Steps (detail)** |
| `step_total` | StepTotal | (device_address, date_str) | step, distance, calorie, unix_time, isUploadServer, upload_server_unit_time | **Steps (daily total)** |
| `sport_plus_detail` | SportPlusDetail | (device_address, start_time, sport_type) | duration, distance, calories, steps, rate_value, avg_rate, sync | **Sport (multi-type)** |
| `gps_detail` | GpsDetail | (start_time) | duration, distance, calorie, locations, date_str, gps_type | **GPS tracks** |
| `target_entity` | TargetEntity | (device_address) | goal_steps, goal_calorie, goal_distance, goal_sport_time, goal_sleep_time, sleep_start, sleep_end, sleepDuration | **Goals/targets** |

### Device / Settings Tables

| Table Name | Entity Class | PK | Key Columns | Data Domain |
|---|---|---|---|---|
| `device_entity` | QcDeviceEntity | (device_address) | device_name, fm_version, img_local_url, img_url, device_type, update_time | **Paired devices** |
| `device_setting` | DeviceSettingEntity | (mac, setting_action) | content | **Per-device settings (KV)** |
| `sync_entity` | SyncDataEntity | (uid, data_action) | last_sync_id | **Sync state tracking** |

### App / UI / Lifestyle Tables

| Table Name | Entity Class | PK | Notes |
|---|---|---|---|
| `user` | UserEntity | (uid) | User profile: email, nick, gender, weight, height, birthday, goals |
| `watch_face` | WatchFace | (name, hardware_version) | Marketplace watch faces |
| `pay_watch_face` | PayWatchFace | (uid, name, hardware_version) | Purchased watch faces |
| `watch_face_index` | WatchFaceIndexEntity | (hardware_version, type_id, position) | Watch face index |
| `custom_face` | CustomFaceEntity | (hd_version, type, address) | Custom watch face images |
| `menstruation` | MenstruationEntity | (mid AUTO) | Menstrual cycle tracking |
| `message_push` | MessagePushEntity | (package_name) | Notification push settings |
| `feedback` | FeedbackEntity | (type_id, feedback_id) | User feedback |
| `contact_entity` | ContactsEntity | (mac, phone_number, contact_name) | Contacts for device |
| `music_to_device` | MusicToDeviceEntity | (music_name) | Music files on device |
| `song_menu` | SongMenuEntity | (menu_id) | Song playlists |
| `ebook_entity` | EbookEntity | (book_name) | Ebooks on device |
| `muslim_total` | MuslimTotal | (device_address, date_str) | Prayer count totals |
| `muslim_detail` | MuslimDetail | (device_address, date_str) | Prayer count details |
| `anla_name_entity` | AnlaNameEntity | (create_time) | Arabic/Chinese/English name dictionary |
| `worship_time_entity` | WorshipTimeEntity | (worship_uuid) | Worship time reminders |
| `quran_entity` | QuranEntity | (content_uuid) | Quran content |
| `customer_praise_entity` | CustomerPraiseEntity | (uuid) | Customer praise records |

---

## Distinct Data Channels Identified

The vendor app (QcWireless/QRing) considers the following **distinct data channels**, each with its own table + DAO + entity:

| # | Data Channel | Tables | Continuous? | Manual? | App-initiated? |
|---|---|---|---|---|---|
| 1 | **Heart Rate** | heart_rate_detail, manual_heart_entity, app_heart | Yes (interval-based) | Yes (spot-check) | Yes (app_heart) |
| 2 | **HRV / Heart Rate Variability** | hrv_detail, hrv_manual | Yes (interval-based) | Yes (hrv_manual) | — |
| 3 | **Blood Oxygen / SpO2** | blood_oxygen, blood_oxygen_manual | Yes (min/max arrays) | Yes (single reading) | — |
| 4 | **Body/Skin Temperature** | temperature_entity, app_temperature | Yes (per-minute) | — | Yes (app_temperature) |
| 5 | **Blood Pressure** | blood_pressure, blood_pressure_manual | Yes (unix_time keyed) | Yes (manual) | — |
| 6 | **Blood Sugar** | blood_sugar, app_sugar, app_continuous_sugar | Yes (min/max arrays) | Yes (app_sugar) | Yes (continuous app) |
| 7 | **Stress / Pressure** | pressure_detail, pressure_manual | Yes (interval-based) | Yes (manual) | — |
| 8 | **ECG** | qc_ecg_entity | Yes (data_list JSON) | — | — |
| 9 | **Sleep** | sleep_detail, sleep_total, sleep_new_protocol, sleep_lunch_protocol | Yes (multi-protocol) | — | — |
| 10 | **Steps** | step_detail, step_total | Yes (interval-based) | — | — |
| 11 | **Sport / Exercise** | sport_plus_detail | Yes (per-session) | — | — |
| 12 | **GPS Tracks** | gps_detail | Yes (per-session) | — | — |
| 13 | **Muslim Prayer** | muslim_detail, muslim_total | Yes (interval-based) | — | — |

**Key architectural insight:** The vendor distinguishes between **three capture modes** for most biometric data:
- **Continuous/device-synced** (interval-based, stored with `index_str` + `value` arrays, `sync` flag)
- **Manual/spot-check** (single reading, stored with `mac` + `timestamp`)
- **App-initiated** (phone-side measurement, stored with `mac` + `timestamp`, `isUploadServer` flag)

The `sync` column (0 = unsynced, appears on device-synced tables) and `isUploadServer` + `upload_server_unit_time` (server upload tracking) form a **two-tier sync model**: device-to-app sync, then app-to-server upload.

---

## Function Dictionary Proposals

### QcDatabase (J05193)

| Field | Value |
|---|---|
| file | QcDatabase.java |
| class | QcDatabase |
| method_or_field | getDatabase(context) |
| kind | method |
| general_function | Singleton factory for Room database instance; creates qc_database.db with fallbackToDestructiveMigration |
| variables_fields | INSTANCE (volatile singleton), Companion |
| constants_command_ids | DB name: "qc_database.db", version: 55 |
| inputs | Context |
| outputs | QcDatabase |
| calls | Room.databaseBuilder() |
| called_by | App initialization |
| ble_service_or_characteristic | — |
| database_or_model_touched | qc_database.db (creates) |
| data_domains | storage_db, hr, hrv_regular, sleep, spo2, steps_sport, temperature, sync_scheduler |
| freshness_truth_implications | fallbackToDestructiveMigration means schema changes wipe all data — no migration path |
| evidence_notes | All 47 entities registered in @Database annotation; 35+ abstract DAO accessors |
| unknowns | Which DAOs are actually used at runtime vs. just registered |
| confidence | high |

### QcHeartRateDetailDao (J05208)

| Field | Value |
|---|---|
| file | QcHeartRateDetailDao.java |
| class | QcHeartRateDetailDao |
| method_or_field | queryByDateRange, queryBySync, queryDaysSyncDate, queryHeartByDate, queryLastSyncDate, updateUploadStatus |
| kind | interface/DAO |
| general_function | Continuous HR data access; date-range queries, sync status tracking, server upload status |
| variables_fields | — |
| constants_command_ids | — |
| inputs | mac/deviceAddress, startDate, endDate, dateStr |
| outputs | List<HeartRateDetail>, HeartRateDetail |
| calls | Room SQLite queries on heart_rate_detail |
| called_by | QcDatabase.qcHeartRateDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | heart_rate_detail table |
| data_domains | hr, storage_db, sync_scheduler |
| freshness_truth_implications | sync=0 means unsynced from device; isUploadServer tracks server upload; queryDaysSyncDate LIMIT 7 suggests weekly view |
| evidence_notes | Table: device_address, date_str, interval, index_str, value (JSON), unix_time, sync, last_sync_time, isUploadServer, upload_server_unit_time |
| unknowns | Structure of `value` and `index_str` JSON fields |
| confidence | high |

### QcHrvDetailDao (J05210)

| Field | Value |
|---|---|
| file | QcHrvDetailDao.java |
| class | QcHrvDetailDao |
| method_or_field | queryByAddressAndDate, queryBySync, queryDaysSyncDate, queryLastSyncDate, queryPressureByDate |
| kind | interface/DAO |
| general_function | Continuous HRV data access; unix_time range queries, sync tracking |
| variables_fields | — |
| constants_command_ids | — |
| inputs | deviceAddress, start, end, date, content |
| outputs | List<HRVDetail>, HRVDetail |
| calls | Room SQLite queries on hrv_detail |
| called_by | QcDatabase.qcHrvDetailDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | hrv_detail table |
| data_domains | hrv_regular, storage_db, sync_scheduler |
| freshness_truth_implications | Same sync pattern as HR; queryPressureByDate is misnamed — actually queries HRV by date |
| evidence_notes | Table: device_address, date_str, interval, index_str, value, unix_time, sync, last_sync_time |
| unknowns | Why method is named "queryPressureByDate" — likely copy-paste from pressure DAO |
| confidence | high |

### QcManualHeartDao (J05212)

| Field | Value |
|---|---|
| file | QcManualHeartDao.java |
| class | QcManualHeartDao |
| method_or_field | queryAllData, queryByDate, queryByDateRange, queryDataDate, updateUploadStatus |
| kind | interface/DAO |
| general_function | Manual/spot-check HR measurement storage; mac-based queries, server upload tracking |
| variables_fields | — |
| constants_command_ids | — |
| inputs | mac, date, startDate, endDate |
| outputs | List<ManualHeartEntity>, ManualHeartEntity |
| calls | Room SQLite queries on manual_heart_entity |
| called_by | QcDatabase.qcManualHeartDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | manual_heart_entity table |
| data_domains | hr, storage_db |
| freshness_truth_implications | content field stores JSON array of HR readings; separate from continuous HR — this is user-triggered spot measurement |
| evidence_notes | Table: mac, date_str, content (JSON), isUploadServer, upload_server_unit_time |
| unknowns | Structure of `content` JSON |
| confidence | high |

### QcEcgDao (J05201)

| Field | Value |
|---|---|
| file | QcEcgDao.java |
| class | QcEcgDao |
| method_or_field | queryAllEcg, queryEcgByType, queryEcgByUnixTime, queryLastEcg, deleteAllByDevice, deleteByDeviceAndDate |
| kind | interface/DAO |
| general_function | ECG recording storage; query by device, type, unix_time; supports deletion by device+time |
| variables_fields | — |
| constants_command_ids | — |
| inputs | mac/deviceAddress, type, unixTime |
| outputs | List<QcEcgEntity>, QcEcgEntity |
| calls | Room SQLite queries on qc_ecg_entity |
| called_by | QcDatabase.qcEcgDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | qc_ecg_entity table |
| data_domains | hr, storage_db, sync_scheduler |
| freshness_truth_implications | type field distinguishes ECG recording modes; data_list is JSON array of ECG samples; avg_heart is computed average |
| evidence_notes | Table: device_address, date_str, type, data_list (JSON), avg_heart, unix_time, sync, last_sync_time |
| unknowns | What `type` values mean (likely ECG lead types or measurement modes) |
| confidence | high |

### QcDeviceDao (J05195)

| Field | Value |
|---|---|
| file | QcDeviceDao.java |
| class | QcDeviceDao |
| method_or_field | getAllDevicesOrderByUpdateTimeDesc, getDeviceByAddress, insertDevice, updateDeviceImageUrls, updateDeviceTime |
| kind | interface/DAO |
| general_function | Paired device registry; CRUD + image URL and time updates; coroutine-based |
| variables_fields | — |
| constants_command_ids | — |
| inputs | deviceAddress, localUrl, remoteUrl, newTime |
| outputs | List<QcDeviceEntity>, QcDeviceEntity, Long, Integer, Unit |
| calls | Room SQLite queries on device_entity; CoroutinesRoom |
| called_by | QcDatabase.qcDeviceDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | device_entity table |
| data_domains | storage_db, ble_connection |
| freshness_truth_implications | update_time tracks last interaction; device_type distinguishes device categories; img_url/img_local_url for device icons |
| evidence_notes | Table: device_address, device_name, fm_version, img_local_url, img_url, device_type, update_time |
| unknowns | What device_type values map to |
| confidence | high |

### QcDeviceSettingDao (J05197)

| Field | Value |
|---|---|
| file | QcDeviceSettingDao.java |
| class | QcDeviceSettingDao |
| method_or_field | deleteDataWhereMacNotNull, queryByMacAndAction |
| kind | interface/DAO |
| general_function | Per-device settings key-value store; mac+action composite key; content is TEXT blob |
| variables_fields | — |
| constants_command_ids | — |
| inputs | mac, action |
| outputs | DeviceSettingEntity |
| calls | Room SQLite queries on device_setting |
| called_by | QcDatabase.qcDeviceSettingDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | device_setting table |
| data_domains | storage_db, device_settings |
| freshness_truth_implications | setting_action is a string key — likely maps to specific BLE command IDs or device feature flags |
| evidence_notes | Table: mac, setting_action, content; PK (mac, setting_action); content is arbitrary TEXT |
| unknowns | What setting_action values exist; whether content is JSON or serialized proto |
| confidence | high |

### QcGpsDetailDao (J05205)

| Field | Value |
|---|---|
| file | QcGpsDetailDao.java |
| class | QcGpsDetailDao |
| method_or_field | queryAll, queryByStartTime, queryFirstByStartTime, queryListByDate |
| kind | interface/DAO |
| general_function | GPS track storage; query by start_time, date; locations stored as JSON |
| variables_fields | — |
| constants_command_ids | — |
| inputs | start, date |
| outputs | List<GpsDetail>, GpsDetail |
| calls | Room SQLite queries on gps_detail |
| called_by | QcDatabase.qcGpsDao() |
| ble_service_or_characteristic | — |
| database_or_model_touched | gps_detail table |
| data_domains | storage_db, steps_sport |
| freshness_truth_implications | locations is JSON array of lat/lng points; gps_type distinguishes activity types |
| evidence_notes | Table: start_time, duration, distance, calorie, locations (JSON), date_str, gps_type |
| unknowns | Format of locations JSON; what gps_type values mean |
| confidence | high |

---

## Summary

- **Files assigned count:** 35
- **Files actually read count:** 35 (all 17 DAO interfaces + 1 QcDatabase + 1 QcDatabase_Impl read in full; 16 _Impl files confirmed as auto-generated Room implementations with no additional domain logic beyond what their DAO interfaces define)
- **Rows needing second pass:** 0
- **Strongest new findings:**
  1. **Complete schema map**: 47 tables in qc_database.db v55, with full DDL extracted from QcDatabase_Impl
  2. **Three capture modes**: The vendor app distinguishes continuous/device-synced, manual/spot-check, and app-initiated data for HR, SpO2, HRV, blood pressure, blood sugar, temperature, and stress — each mode gets its own table
  3. **Two-tier sync model**: `sync` flag tracks device-to-app sync; `isUploadServer` + `upload_server_unit_time` track app-to-server upload
  4. **Sleep has 4 tables**: sleep_detail (interval), sleep_total (daily summary with avg_heart, avg_blood_oxygen, avg_hrv), sleep_new_protocol, sleep_lunch_protocol — indicating protocol evolution and lunch-nap support
  5. **Muslim prayer tracking** is a first-class data channel with interval-based detail and daily totals, using the same sync pattern as health data
  6. **QcHealthyDao is a stub** — empty interface, no methods, no entity — possibly a placeholder for future unified health queries
  7. **Naming artifacts**: Several DAOs have "pressure" in method names (queryPressureByDate) that actually query HRV or Muslim prayer data — evidence of copy-paste development
  8. **device_setting is a KV store**: mac + setting_action composite key with arbitrary TEXT content — likely serializes BLE command parameters
- **How fulfilling was this task?** Very fulfilling. This chunk is the **single most important chunk** for understanding the vendor app's data model. The QcDatabase + QcDatabase_Impl pair provides the complete schema, and the DAO interfaces reveal the query patterns and sync semantics. The three-capture-mode pattern (continuous/manual/app) is a major architectural insight for SymbioSync's own data model design.
- **What would I like changed if asked to do something like this again?** The _Impl files are auto-generated and add no domain insight beyond the DAO interfaces — they could be excluded from chunk assignments to save time. Also, having the entity classes in the same chunk would let us confirm field types and annotations directly rather than inferring from DDL.
