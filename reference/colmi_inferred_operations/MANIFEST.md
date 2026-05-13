# Curated Colmi / QRing APK static analysis references

Source root: `D:\feedback\qring`
Current project: `D:\SymbioSync`

This folder is not a raw dump. It holds the first curated reference chunk from the old klaatu archaeology so the current Windows-first codebase can carry forward only useful protocol evidence.

Raw Java-derived operation references were moved out of this public-candidate repo to the private reference archive:

- `https://github.com/SymbioSyncProject/symbiosync-inferred-operations-private`

Keep only public-safe summaries, derived notes, and hand-curated protocol conclusions here.

## Notes produced from this reference

- `BIOMETRIC_PROTOCOL.md`
  - Current/manual/interval biometric protocol notes from the curated Java references.
  - Records UART current-measurement evidence, BigData HR/SpO2 ids and parser layouts, and trust-bearing implications for SymbioSync.

## First chunk copied

### Prior findings

- `prior_findings/Obsidian_FINDINGS.md`
  - Keep. High-signal prior sleep scoring analysis.
  - Confirms QRing score is mostly duration: 70 points target 500 minutes, plus 15 free awake-bonus points because APK calls awakeTimes as 0.
- `prior_findings/calc_sleep_score.py`
  - Keep. Python port of the APK score formula.
  - Current `symbiosync/devices/colmi.py` already contains equivalent scoring logic.

### Private inferred-operation references

The private archive preserves raw operation-reference snippets used to infer:

- sleep score formula
- UART UUIDs and BigData UUIDs
- 16-byte command packet layout and checksum
- HR and SpO2 start/stop command ids
- BigData sleep, manual HR, manual blood oxygen, interval oxygen, and interval HR ids
- response command map for battery, sleep details, today sport, start measurement, realtime HR, and read HR

Only the conclusions needed by the current app should be copied into this folder.

## First chunk conclusions

- Current `colmi.py` is aligned with the APK on core UART UUIDs, 16-byte command checksum, set time, battery, today sports, HR start/stop, SpO2 start/stop, and sleep score logic.
- The APK exposes additional historical/BigData surfaces worth mining later:
  - manual HR list: BigData id `40`
  - manual SpO2 list: BigData id `73`
  - interval SpO2: BigData id `95`
  - interval HR: BigData id `117`
  - older UART sleep details command `0x44`
- One APK-derived oddity: `syncIntervalHeartRate()` calls `syncIntervalBloodOxygenReal()` in the static analysis, but `syncIntervalHeartRateReal()` exists and uses id `117`; treat as static-analysis/app weirdness until validated.

## Next candidate chunks

1. Inspect BigData bean/entity classes for manual HR/SpO2 and interval data layouts.
2. Inspect `ReadSleepDetailsRsp.java` and `SleepNewProtoResp.java` to compare old UART sleep protocol with current BigData parser.
3. Inspect current `D:\feedback` root scripts (`sleep_parse_v2.py`, `reparse_sleep.py`, `ring_explore.py`) and decide whether any should be copied forward or archived.
