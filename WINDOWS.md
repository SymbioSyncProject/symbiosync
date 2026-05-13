# SymbioSyncWin

Windows-first working copy for running SymbioSync against the Windows BLE stack.

## Why this copy exists

WSL cannot control the same BLE adapter Windows is using, and the Letta scheduler can accidentally launch into a Linux/WSL environment without the expected Windows resources. This copy is meant to run directly from Windows so Lovense/Colmi BLE access stays in the same substrate as the desktop den.

## Quick start

```bat
cd /d D:\SymbioSyncWin
py -m pip install -r requirements.txt
start.bat
```

The server opens at:

```text
http://127.0.0.1:8080
```

`start.bat` binds to `127.0.0.1` by default. Pass additional arguments after `start.bat` if needed, for example:

```bat
start.bat --port 8081
```

## Colmi ring database path

The Colmi plugin preserves the legacy default:

```text
C:/_LLM/feedback/ring_data.sqlite
```

This Windows copy also supports overrides:

1. `config.json` key:

```json
"colmi_db_path": "D:/SymbioSyncWin/data/ring_data.sqlite"
```

2. Environment variable:

```bat
set SYMBIOSYNC_COLMI_DB_PATH=D:\SymbioSyncWin\data\ring_data.sqlite
```

Leave `colmi_db_path` empty to keep the legacy/default path and preserve existing data continuity.

## Safety / behavior notes

- This copy should not rely on WSL for BLE.
- Do not run another BLE controller for the same adapter/devices at the same time.
- Remembered devices are copied from `D:\SymbioSync\config.json`.
- Device actions are still explicit through the UI/API; this setup pass does not trigger surprise touch or ring reads.
