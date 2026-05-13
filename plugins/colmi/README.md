# Colmi ring plugin

The Colmi plugin is SymbioSync's active biometric-adjacent ring/sensor plugin.
It targets QRing/Colmi-style smart rings and stores local data in SQLite.

This plugin is useful now, but still in active hardening around BLE reliability,
freshness semantics, historical import, and privacy boundaries.

## Status

Active in-progress.

Current support includes:

- live heart-rate style reads
- opt-in SpO2 attempts
- battery
- activity/sports snapshots
- sleep capture and parsed sleep segments
- local SQLite persistence
- current-read endpoint with freshness metadata

## Current-read semantics

The endpoint `/api/biometrics/current` is stricter than generic `/api/status`.
It returns freshness metadata so stale cached body-state does not look current.

Each metric should be read as a value plus context, not as a naked scalar:

- `ok`: true only when the value is current enough for the endpoint contract
- `value`: the measurement value, or null when unavailable
- `captured_at`: timestamp for the source reading
- `age_seconds`: age at response time
- `freshness`: `current`, `stale`, or `unavailable`
- `source`: current live stream, sports poll, etc.

SpO2 is opt-in because it can interrupt HR streaming and has correlated with BLE
flakiness. A missing or stale SpO2 value is not the same thing as normal oxygen
state.

## Local SQLite data

The plugin stores local ring data in SQLite. Runtime DB files are private and
ignored by git.

High-level stored data includes:

- rings and sessions
- realtime heart-rate samples
- realtime SpO2 samples where available
- battery snapshots
- today/activity/sports snapshots
- sleep raw captures
- parsed sleep segments
- subjective sleep journal entries

Do not publish raw DBs or dumps casually. They are biometric-adjacent and may be
relationship/body-state records.

## BLE reliability notes

Colmi rings are flaky BLE devices. The code carries several practical behaviors
because of that:

- pass the scanned BLEDevice object to BleakClient on Windows when possible
- set ring time on connect
- start/restart HR streaming when needed
- keep SpO2 infrequent because it pauses HR and can destabilize the link
- use BigData service for sleep capture when available
- preserve old data for later merge/import rather than throwing it away

## Sleep data

Sleep capture uses the Colmi BigData path when available. Parsed sleep records
should be treated as ring/firmware classification, not a ground truth claim about
what the human experienced.

The app may compute scores from parsed segments, but those scores are derived
signals. Keep the source and uncertainty visible.

## Historical data import

Older Colmi/ferri archaeology and larger DBs currently live outside the repo.
Those should be treated as private archive/import sources, not source files.

Future work should provide a deliberate import/review flow rather than mixing
old raw data into normal project code.

## Protocol sources

- curated QRing APK references in `../../reference/colmi_inferred_operations/`
- Puxtril Colmi BLE protocol notes
- prior sleep parsing and scoring findings in
  `../../reference/colmi_inferred_operations/prior_findings/`
- local field tests against Colmi/QRing hardware

## Known limitations

- SpO2 can interfere with HR streaming.
- Generic `/api/status` includes cached values with age fields; use
  `/api/biometrics/current` when a current body-state read is required.
- Historical import/merge is not implemented yet.
- BigData and sleep parsing need continued validation against real captures.
- BLE drop/reconnect behavior is still being hardened.
