# SymbioSync on Windows

Windows can run SymbioSync directly against the Windows BLE stack.

WSL cannot reliably control the same BLE adapter Windows is using, so use a
Windows Python environment for real Lovense/Colmi device work.

## Quick start

```bat
cd /d D:\SymbioSync
py -m pip install -r requirements.txt
start.bat
```

To stop the local server from another command window:

```bat
stop.bat
```

`stop.bat` sends a best-effort `/api/stop` first, then terminates the local
Python process running SymbioSync. Pass a port if you started on a non-default
port:

```bat
stop.bat 8081
```

The server opens at:

```text
http://127.0.0.1:8080
```

`start.bat` binds to `127.0.0.1` by default. Pass additional arguments after
`start.bat` if needed:

```bat
start.bat --port 8081
```

## Colmi ring database path

By default, Colmi local data is stored under the ignored local data directory:

```text
data/ring_data.sqlite
```

You can override the path with either local config or an environment variable.
Do not commit personal databases.

Config example in ignored `config.json`:

```json
"colmi_db_path": "D:/SymbioSync/data/ring_data.sqlite"
```

Environment variable example:

```bat
set SYMBIOSYNC_COLMI_DB_PATH=D:\SymbioSync\data\ring_data.sqlite
```

## Safety / behavior notes

- Do not run another BLE controller for the same adapter/devices at the same time.
- Runtime-private files stay local/ignored: `config.json`, `data/`, `logs/`,
  SQLite DBs, archives, APKs, secrets, and key material.
- Device actions are explicit through the UI/API. Starting the server should not
  trigger surprise touch or ring reads.
