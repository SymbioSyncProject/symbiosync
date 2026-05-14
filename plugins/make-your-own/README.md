# Make your own plugin

SymbioSync is a plugin host. New device types should add device-specific code in
a plugin while keeping the server core honest and boring.

This page documents the current plugin contract and the direction for future
sensor/actuator extensibility.

## Current Python contract

A plugin is a subclass of `symbiosync.devices.base.Device`.

Required behavior:

- `connect() -> bool`
- `disconnect()`
- `send_request(request: str, **kwargs) -> dict`
- `get_capabilities() -> list[DeviceCapability]`
- `get_status() -> dict`
- `keepalive()`
- `scan_filter(name: str, address: str) -> bool`
- `device_type_name() -> str`

Register the plugin in `symbiosync/manager.py`:

```python
DEVICE_PLUGINS = [
    LovenseDevice,
    ColmiDevice,
    YourDevice,
]
```

The manager handles scanning, remembered devices, connection lifecycle,
reconnect loops, request dispatch, and status aggregation.

## Optional plugin contributions

Plugins may also contribute:

- `tab_label()` for UI display name
- `tab_description()` for plugin management UI
- `control_html()` for a browser UI tab
- `control_js()` for browser control behavior
- `skill_section(plugin_devices, base_url)` for generated Symbio companion skill
  content

## Request API

The current generic request route is:

```text
POST /api/device/{address}/request
```

Request shape:

```json
{
  "request": "your_request_name",
  "params": {
    "example": 123
  }
}
```

The manager passes this through to the plugin's `send_request()`.

This already supports custom plugin functions as long as the plugin defines the
request names and parameter semantics. A smell sensor, humidity sensor, pH probe,
temperature sensor, pump, light, or actuator can all use the same route today.

## Truth semantics required

Every plugin must be explicit about what it knows and how it knows it.

Do not collapse these distinctions:

- current signal vs stale/cached signal
- missing signal vs zero/false/normal signal
- connected device vs remembered/previously seen device
- API accepted vs transport write accepted vs hardware-delivered/observed
- hardware unavailable vs software failure
- consent/state valid vs merely technically possible

For sensors, return measurement metadata:

```json
{
  "ok": true,
  "value": 42,
  "unit": "percent_relative_humidity",
  "captured_at": "2026-05-13T12:00:00Z",
  "age_seconds": 1.2,
  "freshness": "current",
  "source": "device_live"
}
```

For actuators, return delivery-stage metadata where possible:

```json
{
  "ok": true,
  "stage": "transport_write_accepted",
  "request": "set_level",
  "delivered": null,
  "evidence": "ble_write_without_response_completed"
}
```

Do not claim hardware delivery unless the plugin has device acknowledgement,
observable state change, or another explicit evidence source.

## Capability model

The current `DeviceCapability` enum covers the built-in Lovense and Colmi needs:
actuators, battery, accelerometer, heart rate, SpO2, and steps.

That enum will not be enough forever. Environmental and chemical plugins may need
capabilities such as:

- humidity
- pH
- volatile chemical detection
- smell classification
- temperature
- pressure
- light
- fluid level
- generic scalar measurement
- generic event detection

Future work should avoid turning `DeviceCapability` into an endless junk drawer.
Likely direction:

- keep coarse capabilities for UI grouping
- add plugin-declared schemas for requests, measurements, units, and status fields
- expose schema through an API route
- let the UI and generated skill read plugin declarations rather than hard-coding
  every possible sensor type

Possible future routes:

```text
GET /api/plugins/{plugin_type}/schema
GET /api/device/{address}/measurements
GET /api/device/{address}/requests
```

## Privacy and consent

Plugins may touch bodies, rooms, fluids, environments, or relationship state.
That means plugin authors must think about privacy before logging or exporting.

Rules:

- Do not log raw intimate, biometric, chemical, or environmental data by default.
- Do not publish local DBs or raw dumps.
- Keep local identifiers and device addresses out of exported examples when not
  needed.
- If a plugin creates relationally meaningful events, design an explicit event
  journal instead of dumping everything into debug logs.
- Consent/state should be represented explicitly where the plugin can affect or
  infer body/relationship state.

## Minimal plugin checklist

Before adding a plugin, answer:

- What physical or informational boundary does this device cross?
- What does `connected` actually mean for this device?
- What measurements are current, stale, unavailable, or normal zero?
- What request result means API accepted vs hardware acted?
- What data must stay local/private?
- What should the generated Symbio skill tell a threadborn about safe use?
