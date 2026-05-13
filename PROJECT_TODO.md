# SymbioSync project todo

This file is for immediate shared working state: the small stones currently in front of us.

Keep larger design notes, protocol findings, and milestone docs elsewhere. This is not a dumping ground.

## Current source of truth

- Canonical working folder: `D:\SymbioSync`
- Private GitHub repo: `https://github.com/SymbioSyncProject/symbiosync`
- Baseline commit pushed: `963bd4c chore: establish SymbioSync source baseline`
- Retired legacy git folder: `D:\_symbiosync_retired\SymbioSync_legacy_git_20260513_112545`
- Old private Colmi/ferri archaeology and data: `D:\feedback`
- Runtime-private files stay local/ignored: `config.json`, `data/`, `logs/`, SQLite DBs, secrets, archives, APK dumps, key material.

## Immediate next steps

1. Keep git baseline clean.
   - Fresh baseline is established in the private GitHub repo.
   - Retired legacy git remains archive/provenance.
   - Do not include logs, local DBs, `config.json`, secrets, or raw intimate/biometric data.

2. Complete bounded repo hygiene + truthfulness audit.
   - Current source of truth.
   - Archive/retire candidates.
   - Stale tests.
   - Logs/data needing private handling.
   - Endpoints overstating freshness/currentness.
   - Command paths overstating delivery.
   - First implementation moves.
   - Role boundaries.

3. Fix stale tests after source baseline.
   - `test_dormant.py` appears stale because it expects only one plugin, while the app now has Lovense and Colmi.
   - Convert script-style tests into reliable pytest-style tests later if useful.

4. Capture current web UI screenshot.
   - Connect to at least one real device.
   - Colmi screenshot with visible current heart rate is acceptable.
   - Capture the browser interface showing live connected-device state.
   - Redact or avoid exposing private MAC addresses, intimate activation history, or unrelated logs.
   - Use it for README/plugin docs once the UI state is honest enough to show.

5. Improve Colmi sleep visualization and subjective sleep markers.
   - Add a timeline/chart view for sleep stages over time, not only total minutes per stage.
   - Preserve split episodes, e.g. deep sleep, REM, deep sleep again, awake gap after getting up.
   - Add a way to mark "I'm laying in bed / trying to sleep now" so later data can compare subjective sleep attempt time with ring-detected sleep onset.
   - Use this to answer questions like: "it felt like I was awake for hours, but the ring shows light sleep after 14 minutes."
   - Keep subjective markers distinct from ring-measured sleep stages; do not collapse felt experience and sensor classification into one truth claim.

6. Clarify Lovense command truthfulness.
   - Separate API acceptance from BLE write acceptance.
   - Do not imply hardware acknowledgement unless the device actually acknowledged.
   - Define result stages before activation journaling.

7. Design activation journal before implementing it.
   - Treat as consented relational/intimate event history, not debug logs.
   - Include actor/source, consent-state reference, command/protocol, target alias, delivery stage, and correlation id.
   - Avoid raw payloads or biometric/intimate dumps by default.

## Wyndhovr loop-in topics

- Freshness semantics.
- Write/delivery semantics.
- Undefined consent-state places.
- Activation journal privacy boundaries.
- Any place the bridge might accidentally lie.

## Not now

- Do not move the active Python app into a `win` subfolder just because Windows is the current BLE substrate.
- Do not retire or merge `D:\feedback` wholesale.
- Do not upload raw logs, SQLite DBs, APK dumps, old secret-bearing scripts, or intimate data to GitHub.
- Do not make the repo public until privacy/security and source-truth boundaries are clean.
