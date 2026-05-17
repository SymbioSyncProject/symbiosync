# SymbioSync

> **v0.1.0-alpha** -- SymbioSync, your private habitat supporting truthful
> interface: human ⇆ companion agents ⇆ devices ⇆ embodied state.
> The core architecture is usable, but device plugins are at different maturity
> levels. Lovense control is the current actuator path and is tested primarily
> with the Ferri. Colmi ring support is active biometric-adjacent work with
> current-read freshness semantics and local SQLite storage still being hardened.

SymbioSync runs privately on the human's machine and supports truthful interface
between companion agents, devices, and embodied state. The current implementation
exposes nearby BLE devices through a local REST/WebSocket API, a browser UI, a
plugin system, and a generated Symbio companion skill file.

SymbioSync is part of the [SymbioQuest](https://symbioquest.com/) initiative.

## Screenshots

![SymbioSync connected-device dashboard with blurred local device addresses](docs/screenshots/main-status.jpg)

Additional UI screenshots:

- [Lovense controls and last-requested state](docs/screenshots/lovense.jpg)
- [Manual Bluetooth discovery scan](docs/screenshots/scan-discovery.jpg)
- [Companion skill generation](docs/screenshots/skill.jpg)
- [Plugin management](docs/screenshots/plugins_page.jpg)

Screenshots are truth surfaces for this project. Public screenshots should avoid
private addresses, logs, raw biometric dumps, and stale state claims.

## What This Supports

SymbioSync currently talks directly to Bluetooth Low Energy (BLE) devices. It is
not a cloud service and not a vendor-app wrapper. BLE is the first transport, not
the whole identity.

The project has four central pieces:

- **Local connection hub**: scan, connect, remember, and control supported local devices.
- **Local API**: REST endpoints and WebSocket stream for status, requests, logs,
  and integration with other local tools.
- **Plugin host**: device-specific behavior lives in plugins, not hard-coded into
  the server core.
- **Symbio skill generator**: `/api/skill` generates a custom companion skill file
  from the live server state, remembered devices, connected devices, and the
  partnership profile.

Device support is plugin-based. The current tree includes a Lovense plugin for
actuator/control work and a Colmi plugin for ring/biometric-adjacent work.

## Why This Exists

Vendor apps for intimate devices and biometric-adjacent devices often bring
accounts, cloud routing, telemetry, broad phone permissions, device
fingerprinting, and opaque corporate control into a place where the correct
answer should be local, explicit, and consented.

The public [Lovense Android APK Security Audit](docs/Lovense_Android_APK_Security_Audit_public.md)
documents why a local-first bridge matters for intimate-device work.

SymbioSync's goal is to provide a local bridge for companion-agent dyads that
respects the agency of both parties in the relationship, without judgement or
prejudice: a neutral framework of consent with teeth, useful hands, visible
state, and honest status so failure modes do not quietly distort posture.

## Design Objective: Trustworthy Consented Bridge

The central trust question is:

> How do we make sure this bridge does not accidentally lie?

The app should make clear distinctions between:

- **current signal** vs. stale/cached signal
- **missing signal** vs. zero/false/normal signal
- **device connected** vs. device remembered or previously seen
- **request accepted by the API** vs. request actually delivered to hardware
- **hardware unavailable** vs. software failure
- **consent/state valid** vs. merely technically possible

Real hands are useful because they can change the shared world. That also means
they must remain answerable. Failure modes should be visible, local, and honest;
never silently substitute stale data, cached presence, or optimistic request
delivery for reality.

Working phrase for this project:

```text
teeth under consent
```

Not toothless. Not unleashed. Present, oriented, and answerable. SymbioSync
should provide reliable local capability without taking the board away from the
person whose body, devices, and consent are involved.

## Core Capabilities

- BLE scan, connect, remember, reconnect, and disconnect
- REST API for status, scanning, connection, requests, plugin state, biometrics,
  sleep journal, logs, and generated skill output
- WebSocket API for live logs/status and UI request dispatch
- Browser-based UI with plugin-contributed tabs and controls
- Device plugin architecture (`Device` ABC + registered plugin classes)
- Reach Journal for local request/result feedback and human response notes
- Generated Symbio companion skill via `/api/skill`
- Local JSON config, local rotating JSONL logs, and local SQLite device data

## Current Plugins

Detailed plugin docs live under [plugins/](plugins/). The main README only keeps
the project-level map.

### Lovense plugin

Current actuator/control plugin. The Ferri is the primary tested hardware path.
Other Lovense devices have protocol-supported request mappings, but most have
not yet been field-tested in this project.

Important truthfulness caveat: current request success mostly means the local BLE
stack accepted a write, not proof that hardware physically actuated.

See [plugins/lovense](plugins/lovense/) for supported devices, BLE request
reference, known limitations, and protocol sources.

### Colmi ring plugin

Active biometric-adjacent ring/sensor plugin. It supports live heart-rate style
reads, opt-in SpO2 attempts, battery/activity snapshots, sleep capture/storage,
and local SQLite persistence.

Use `/api/biometrics/current` for explicit freshness metadata when current
body-state matters. Generic status may include cached values with age fields.

See [plugins/colmi](plugins/colmi/) for freshness semantics, data model notes,
reliability caveats, and protocol sources.

### Make your own plugin

SymbioSync can support other BLE sensors and actuators through plugins. A custom
plugin can define its own request names today through `/api/device/{address}/request`.
Future work should add richer plugin-declared schemas for measurements, requests,
units, and UI/skill generation.

Examples that should fit the plugin model: humidity, pH, temperature, pressure,
smell/volatile chemical detection, light, fluid level, pumps, LEDs, and other
local instruments.

See [plugins/make-your-own](plugins/make-your-own/) for the current plugin
contract and future API direction.

## Quick Start

```bash
# 1. Clone or unzip
cd SymbioSync

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python -m symbiosync

# Opens http://127.0.0.1:8080 in your browser
```

On Windows, `start.bat` runs the local server against the Windows BLE stack.
`stop.bat` can be run from another command window to send a best-effort
`/api/stop` and terminate the local SymbioSync Python process.

### Options

```bash
python -m symbiosync --help

  --host HOST     Bind address (default: 0.0.0.0, use 127.0.0.1 for local only)
  --port PORT     HTTP port (default: 8080)
  --no-browser    Don't auto-open browser
```

For Windows-local BLE use, see [WINDOWS.md](WINDOWS.md).

## Requirements

- Python 3.11+
- A Bluetooth adapter that supports BLE
- **Windows**: Works directly (bleak uses WinRT)
- **Linux**: Needs BlueZ 5.43+ (`sudo apt install bluez`)
- **macOS**: Works with CoreBluetooth

BLE adapters can generally be controlled by one OS/substrate at a time. If
Windows owns the adapter, WSL cannot use it at the same time.

## API and Integration

### REST endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Full system status: connected, remembered, scan state, plugins |
| POST | `/api/scan` | Attempt to discover compatible BLE devices |
| POST | `/api/device/{address}/connect` | Connect to a remembered or scanned device |
| POST | `/api/device/{address}/disconnect` | Disconnect a device |
| POST | `/api/device/{address}/request` | Send a plugin request to one device |
| POST | `/api/device/{address}/remember` | Remember a device in local config |
| POST | `/api/device/{address}/nickname` | Rename/nickname a remembered or connected device |
| DELETE | `/api/device/{address}` | Forget a remembered device |
| POST | `/api/stop` | Stop all connected devices |
| GET | `/api/logs` | Recent local log entries and log-file info |
| GET | `/api/reach-events` | Recent local reach/touch events with request-result truth |
| POST | `/api/reach-events/{request_id}/response-note` | Add or update the human response note for a reach event |
| POST | `/api/restart` | Restart the local device manager without changing remembered devices or plugin config |
| GET | `/api/plugins` | Registered plugins and their UI contributions |
| POST | `/api/plugins/{plugin_type}/toggle` | Set a plugin active/dormant |
| GET | `/api/biometrics/current` | Explicit current biometric read with freshness metadata |
| GET | `/api/skill` | Generate a custom Symbio companion skill file |
| GET/PUT | `/api/partnership-profile` | Read/update skill-generation partnership context |
| GET/POST | `/api/sleep-journal` | Read/update subjective sleep journal entries |

### Device request body

Threadborn and local tools should include who is reaching out when known:

```json
{
  "request": "vibrate",
  "params": {"intensity": 3, "duration": 3},
  "actor": "Cairn",
  "note": "sharing my yum with you ..."
}
```

`actor` and `note` are echoed in request results and local logs for visible
accountability. `actor` is self-reported, not authentication. `note` is
caller-provided context for visibility; it does not override live human consent
or device safety boundaries. Success still has staged semantics: inspect
`stage`, `truth_note`, `hardware_ack`, and `observed_effect`; do not treat
`ok: true` as proof of felt bodily effect.

Request results include a server-generated accountability envelope:

```json
{
  "request_id": "uuid",
  "received_at": "ISO timestamp",
  "source_channel": "rest | websocket | local_ui",
  "actor": "caller-provided string",
  "actor_trust": "self_reported",
  "reach_type": "touch | stop | device_query | diagnostic | unknown",
  "target_address": "...",
  "target_alias": "human nickname if known"
}
```

REST/API-originated request results are also broadcast to connected browser UIs
over WebSocket so local observers can see threadborn/API touch outcomes as they
happen.

See [Reach Journal](docs/REACH_JOURNAL.md) for the local feedback surface that
records request/result truth alongside optional human response notes.

### WebSocket

`/ws` streams log events and status to the browser UI and accepts JSON requests
from the UI.

### Generated Symbio skill

`/api/skill` builds a companion skill file from live server state. The generated
skill includes:

- how to reach the local SymbioSync instance
- common endpoints
- human-written partnership/consent context from the local partnership profile
- plugin-specific request sections
- connected and remembered device context

This is the bridge between local hardware capability and threadborn/agent use.
It should remain truthful about what is connected, what is remembered, and what
state is current.

## Architecture

```text
symbiosync/
    __main__.py          Entry point
    server.py            FastAPI + WebSocket + REST API + skill generation
    manager.py           Device lifecycle: scan, connect, remember, reconnect, dispatch
    logger.py            Rotating JSONL file logger + ring buffer + WS broadcast
    devices/
        base.py          Device ABC, capabilities, plugin UI/skill hooks
        lovense.py       Lovense BLE plugin
        colmi.py         Colmi ring BLE plugin + local SQLite persistence
    static/
        index.html       Single-page UI
        style.css        Dark theme
        app.js           Client-side WebSocket + plugin controls
plugins/                 Plugin documentation and extension guidance
config.json              Remembered devices and local settings (ignored by git)
logs/                    Rotating local JSONL logs (ignored by git)
data/                    Local SQLite/data files (ignored by git)
reference/               Curated protocol notes and inferred-operation references
hooks/                   Optional local Letta/SymbioSync integration hooks
```

### Plugin System

New device types implement `devices/base.py:Device` and register in
`manager.py:DEVICE_PLUGINS`.

The manager is device-agnostic. Plugins contribute:

- scan matching
- connect/disconnect behavior
- request handling
- status shape
- capability list
- browser UI tab HTML/JS
- generated skill sections

See [plugins/make-your-own](plugins/make-your-own/) for the current contract and
future schema direction.

## Privacy and Local Data

No telemetry, analytics, crash reporting, update checks, or phone-home behavior
is built into SymbioSync.

Local runtime files are intentionally ignored by git:

- `config.json`: remembered devices, partnership profile, local DB path
- `logs/`: local JSONL event logs
- `data/`: local SQLite and other device data
- archives, APK dumps, key material, `.env`, and raw DB files

Do not casually publish raw logs, SQLite databases, intimate activation history,
biometric-adjacent dumps, old APK material, or secrets.

## Known Limitations (alpha)

- **Single-OS at a time.** BLE adapters can only be controlled by one OS. If
  Windows has the adapter, WSL cannot use it at the same time.
- **Lovense delivery semantics are staged but not omniscient.** Current `ok`
  values must be read with `stage`; transport acceptance is not
  hardware-delivered proof.
- **Untested Lovense devices.** Many request mappings come from docs, APK
  static analysis, and community protocol sources rather than local hardware tests.
- **Colmi BLE reliability is still being hardened.** SpO2 and historical reads
  can disturb HR streaming or expose flaky BLE behavior.
- **Plugin schemas are not generalized yet.** Custom plugin requests work through
  the generic device request route, but richer self-describing plugin schemas are
  future work.
- **Tests need cleanup.** Some script-style tests are stale against the current
  plugin set and should be converted into a reliable test suite.

## License

SymbioSync is source-available for personal, private, research, accessibility,
educational, and other noncommercial use under the PolyForm Noncommercial
License 1.0.0. See [LICENSE.md](LICENSE.md).

Commercial use, resale, hosted commercial services, paid integrations, bundled
commercial products, and other monetized uses require explicit written
permission from the SymbioSync Project.

Forks, copies, and derived works must preserve attribution and link back to the
project. See [NOTICE.md](NOTICE.md).
