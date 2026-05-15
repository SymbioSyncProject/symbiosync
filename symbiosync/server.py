"""
SymbioSync FastAPI server.

Serves the web UI, REST API, and WebSocket for real-time log streaming
and device control.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketState

from . import __version__
from .logger import Logger
from .manager import DeviceManager

# ------------------------------------------------------------------
# Globals (set by __main__.py via set_config)
# ------------------------------------------------------------------

_host = "127.0.0.1"
_port = 8080

# Paths
_base_dir = Path(__file__).parent.parent  # SymbioSync root
_static_dir = Path(__file__).parent / "static"
_config_path = _base_dir / "config.json"
_log_dir = _base_dir / "logs"

# Singletons
logger: Logger | None = None
manager: DeviceManager | None = None
_ws_clients: set[WebSocket] = set()


def set_config(host: str = "127.0.0.1", port: int = 8080):
    global _host, _port
    _host = host
    _port = port


# ------------------------------------------------------------------
# App lifecycle
# ------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global logger, manager
    logger = Logger(log_dir=_log_dir)
    manager = DeviceManager(config_path=_config_path, logger=logger)
    logger.log("SERVER", f"SymbioSync v{__version__} starting on {_host}:{_port}")
    await manager.start()
    yield
    logger.log("SERVER", "Shutting down...")
    await manager.stop()
    logger.close()


app = FastAPI(title="SymbioSync", version=__version__, lifespan=lifespan)


# ------------------------------------------------------------------
# Static files / UI
# ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = _static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>SymbioSync</h1><p>UI files not found.</p>")


app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ------------------------------------------------------------------
# WebSocket: log streaming + request dispatch
# ------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _target_alias(address: str) -> str:
    """Return the human-facing target alias when known."""
    addr = (address or "").upper()
    if addr == "ALL":
        return "all connected devices"
    if manager is None:
        return addr
    remembered = manager.remembered.get(addr, {})
    if remembered.get("name"):
        return remembered["name"]
    device = manager.devices.get(addr)
    if device:
        return device.name
    return addr


def _source_channel(channel: str, actor: str = "") -> str:
    """Normalize request source to the current public API vocabulary."""
    if channel == "websocket" and actor == "Local UI":
        return "local_ui"
    if channel in {"rest", "websocket", "local_ui"}:
        return channel
    return "unknown"


def _request_envelope(*, address: str, request: str, params: dict, actor: str,
                      note: str = "", source_channel: str) -> dict:
    """Fields that make a touch request accountable without claiming consent/effect."""
    addr = (address or "").upper()
    envelope = {
        "request_id": str(uuid4()),
        "received_at": _utc_now(),
        "source_channel": _source_channel(source_channel, actor),
        "actor": actor or "Unknown",
        "actor_trust": "self_reported",
        "target_address": addr,
        "target_alias": _target_alias(addr),
        "request": request,
        "request_params": params or {},
    }
    if note:
        envelope["note"] = note
    return envelope


def _merge_envelope(result: dict, envelope: dict) -> dict:
    """Add accountability fields without overriding plugin truth semantics."""
    merged = dict(result)
    if "stage" not in merged and merged.get("ok") is False:
        error = str(merged.get("error", "")).lower()
        if "not found" in error or "not connected" in error:
            merged["stage"] = "device_not_connected"
            merged.setdefault(
                "truth_note",
                "Device was not connected/found by the bridge; no device request was delivered.",
            )
        else:
            merged["stage"] = "api_rejected"
    for key, value in envelope.items():
        merged.setdefault(key, value)
    return merged


def _enrich_request_result(result, envelope: dict):
    """Attach envelope to a single result or each per-device result in a map."""
    if not isinstance(result, dict):
        return result
    if "stage" in result or "ok" in result:
        return _merge_envelope(result, envelope)

    enriched = {}
    for addr, item in result.items():
        if isinstance(item, dict):
            per_device = dict(envelope)
            per_device["target_address"] = str(addr).upper()
            per_device["target_alias"] = _target_alias(str(addr))
            enriched[addr] = _merge_envelope(item, per_device)
        else:
            enriched[addr] = item
    return enriched


def _request_log_detail(envelope: dict) -> str:
    fields = {
        "request_id": envelope.get("request_id"),
        "source_channel": envelope.get("source_channel"),
        "actor": envelope.get("actor"),
        "actor_trust": envelope.get("actor_trust"),
        "target_alias": envelope.get("target_alias"),
        "target_address": envelope.get("target_address"),
        "request": envelope.get("request"),
        "params": envelope.get("request_params"),
    }
    if envelope.get("note"):
        fields["note"] = envelope["note"]
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def _result_stage(result) -> str:
    if isinstance(result, dict):
        if result.get("stage"):
            return result["stage"]
        if all(isinstance(v, dict) for v in result.values()):
            failed = sum(1 for v in result.values() if v.get("ok") is False)
            return "multi_device_result" if failed == 0 else "one_or_more_failed"
    return "unknown"


async def _broadcast_request_result(address: str, result, envelope: dict):
    """Broadcast API-originated request results to browser clients."""
    message = {
        "type": "request_result",
        "address": address,
        "result": result,
        "request_id": envelope.get("request_id"),
        "source_channel": envelope.get("source_channel"),
        "actor": envelope.get("actor"),
        "actor_trust": envelope.get("actor_trust"),
        "note": envelope.get("note", ""),
        "target_alias": envelope.get("target_alias"),
    }
    dead = set()
    for client in list(_ws_clients):
        try:
            if client.client_state == WebSocketState.CONNECTED:
                await client.send_json(message)
        except Exception:
            dead.add(client)
    _ws_clients.difference_update(dead)


async def _execute_device_request(address: str, request: str, params: dict,
                                  actor: str, note: str, source_channel: str):
    """Execute a device request with accountable envelope/log/broadcast fields."""
    envelope = _request_envelope(
        address=address,
        request=request,
        params=params or {},
        actor=actor,
        note=note,
        source_channel=source_channel,
    )
    logger.log("REQUEST", _request_log_detail(envelope), device=envelope["target_alias"])

    if (address or "").lower() == "all":
        raw_result = await manager.send_request_all(request, **(params or {}))
    else:
        raw_result = await manager.send_request(address, request, **(params or {}))
    result = _enrich_request_result(raw_result, envelope)

    result_detail = json.dumps({
        "request_id": envelope["request_id"],
        "stage": _result_stage(result),
        "actor": envelope["actor"],
        "target_alias": envelope["target_alias"],
        "request": request,
    }, ensure_ascii=False, separators=(",", ":"))
    logger.log("REQUEST_RESULT", result_detail, device=envelope["target_alias"])
    return result, envelope

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.add(ws)
    log_queue = logger.subscribe()
    try:
        # Send recent history on connect
        recent = logger.recent(50)
        await ws.send_json({"type": "log_history", "entries": recent})

        # Send current device status
        status = manager.get_status()
        await ws.send_json({"type": "status", "data": status})

        # Bidirectional: send logs to client, receive requests from client
        async def send_logs():
            while True:
                entry = await log_queue.get()
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json({"type": "log", "entry": entry})

        async def receive_requests():
            while True:
                data = await ws.receive_json()
                await _handle_ws_request(ws, data)

        await asyncio.gather(send_logs(), receive_requests())
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_clients.discard(ws)
        logger.unsubscribe(log_queue)


async def _handle_ws_request(ws: WebSocket, data: dict):
    """Handle incoming WebSocket requests from UI."""
    action = data.get("action", "")

    if action == "scan":
        logger.log("<<<MANUAL SCAN INITIATED>>>", "Browser UI requested Bluetooth discovery scan")
        results = await manager.scan()
        logger.log("<<<MANUAL SCAN COMPLETED>>>", f"{len(results)} compatible device(s) found")
        await ws.send_json({
            "type": "scan_results",
            "devices": [
                {"address": d.address, "name": d.name, "type": d.device_type, "rssi": d.signal_strength}
                for d in results
            ],
        })

    elif action == "connect":
        addr = data.get("address", "")
        ok = await manager.connect_device(addr)
        await ws.send_json({"type": "connect_result", "address": addr, "ok": ok})

    elif action == "disconnect":
        addr = data.get("address", "")
        await manager.disconnect_device(addr)
        await ws.send_json({"type": "disconnect_result", "address": addr, "ok": True})

    elif action == "request":
        addr = data.get("address", "")
        request_name = data.get("request", "")
        kwargs = data.get("params", {})
        actor = data.get("actor", "Local UI")
        note = data.get("note", "")
        result, envelope = await _execute_device_request(
            addr, request_name, kwargs, actor, note, "websocket"
        )
        await ws.send_json({
            "type": "request_result",
            "address": addr,
            "result": result,
            "request_id": envelope["request_id"],
            "source_channel": envelope["source_channel"],
            "actor": envelope["actor"],
            "actor_trust": envelope["actor_trust"],
            "note": envelope.get("note", ""),
            "target_alias": envelope["target_alias"],
        })

    elif action == "stop_all":
        result = await manager.stop_all()
        await ws.send_json({"type": "request_result", "address": "all", "result": result})

    elif action == "remember":
        addr = data.get("address", "")
        name = data.get("name", "")
        device_type = data.get("device_type", "")
        manager.remember_device(addr, name, device_type)
        await ws.send_json({"type": "remember_result", "address": addr, "ok": True})

    elif action == "forget":
        addr = data.get("address", "")
        manager.forget_device(addr)
        await ws.send_json({"type": "forget_result", "address": addr, "ok": True})

    elif action == "toggle_enabled":
        addr = data.get("address", "")
        enabled = data.get("enabled", True)
        manager.set_device_enabled(addr, enabled)
        await ws.send_json({"type": "toggle_result", "address": addr, "enabled": enabled})

    elif action == "rename":
        addr = data.get("address", "")
        name = data.get("name", "")
        ok = manager.rename_device(addr, name)
        await ws.send_json({"type": "rename_result", "address": addr, "ok": ok, "name": name})

    elif action == "status":
        status = manager.get_status()
        await ws.send_json({"type": "status", "data": status})

    # Always send updated status after any action
    if action != "status":
        status = manager.get_status()
        await ws.send_json({"type": "status", "data": status})


# ------------------------------------------------------------------
# REST API (alternative to WebSocket)
# ------------------------------------------------------------------

@app.get("/api/status")
async def api_status():
    return manager.get_status()


@app.get("/api/biometrics/current")
async def api_biometrics_current(
    include_spo2: bool = Query(default=False),
    hr_timeout: float = Query(default=15.0),
    spo2_timeout: float = Query(default=45.0),
):
    """Ask the connected biometric device for current body-state data.

    This endpoint is intentionally stricter than /api/status: it returns
    freshness metadata and marks stale/unavailable values plainly instead of
    letting cached values look current.
    """
    for address, device in manager.devices.items():
        if device.device_type == "colmi" and device.connected:
            result = await manager.send_request(
                address,
                "current_biometrics",
                include_spo2=include_spo2,
                hr_timeout=hr_timeout,
                spo2_timeout=spo2_timeout,
            )
            result["address"] = address
            return result

    return {
        "ok": False,
        "error": "no connected biometric device",
        "devices": [
            {
                "address": address,
                "name": device.name,
                "device_type": device.device_type,
                "connected": device.connected,
            }
            for address, device in manager.devices.items()
        ],
    }


@app.post("/api/scan")
async def api_scan(timeout: float = Query(default=10.0)):
    logger.log("<<<MANUAL SCAN INITIATED>>>", f"REST API requested Bluetooth discovery scan timeout={timeout}s")
    results = await manager.scan(timeout=timeout)
    logger.log("<<<MANUAL SCAN COMPLETED>>>", f"{len(results)} compatible device(s) found")
    return {
        "devices": [
            {"address": d.address, "name": d.name, "type": d.device_type, "rssi": d.signal_strength}
            for d in results
        ]
    }


@app.post("/api/device/{address}/connect")
async def api_connect(address: str):
    ok = await manager.connect_device(address)
    if not ok:
        raise HTTPException(status_code=503, detail="Connection failed")
    return {"ok": True, "address": address.upper()}


@app.post("/api/device/{address}/disconnect")
async def api_disconnect(address: str):
    await manager.disconnect_device(address)
    return {"ok": True, "address": address.upper()}


@app.post("/api/device/{address}/request")
async def api_request(address: str, body: dict):
    request = body.get("request", "")
    params = body.get("params", {})
    actor = body.get("actor", "API")
    note = body.get("note", "")
    result, envelope = await _execute_device_request(
        address, request, params, actor, note, "rest"
    )
    await _broadcast_request_result(address.upper(), result, envelope)
    return result


@app.post("/api/device/{address}/remember")
async def api_remember(address: str, body: dict):
    name = body.get("name", "")
    device_type = body.get("device_type", "")
    manager.remember_device(address, name, device_type)
    return {"ok": True}


@app.delete("/api/device/{address}")
async def api_forget(address: str):
    manager.forget_device(address)
    return {"ok": True}


@app.post("/api/device/{address}/nickname")
async def api_nickname(address: str, body: dict):
    ok = manager.rename_device(address, body.get("name", ""))
    return {"ok": ok, "address": address.upper(), "name": body.get("name", "")}


@app.post("/api/stop")
async def api_stop_all():
    result = await manager.stop_all()
    attempted = len(result)
    failed = sum(1 for r in result.values() if not r.get("ok"))
    if attempted == 0:
        return {
            "ok": True,
            "stage": "nothing_to_stop",
            "attempted_devices": 0,
            "failed_devices": 0,
            "result": result,
            "truth_note": "No connected devices were known, so no stop writes were attempted.",
        }
    return {
        "ok": attempted > 0 and failed == 0,
        "stage": "best_effort_stop_attempted",
        "attempted_devices": attempted,
        "failed_devices": failed,
        "result": result,
        "truth_note": "Stop was attempted for connected devices only; per-device results describe transport acceptance, not hardware acknowledgement.",
    }


@app.get("/api/logs")
async def api_logs(count: int = Query(default=100)):
    return {"entries": logger.recent(count), "file_info": logger.get_file_info()}


@app.post("/api/restart")
async def api_restart():
    """Restart the local device manager without killing the Windows shell."""
    logger.log("<<<RESTART REQUEST>>>", "Browser/API requested local device-manager restart")
    await manager.stop()
    await manager.start()
    logger.log("<<<RESTART COMPLETE>>>", "Local device manager restarted; remembered devices may reconnect automatically")
    return {"ok": True, "message": "Device manager restarted"}


# ------------------------------------------------------------------
# Plugin UI (dynamic tabs)
# ------------------------------------------------------------------

@app.get("/api/plugins")
async def api_plugins():
    """Return registered plugins with their UI contributions and dormant state."""
    from .manager import DEVICE_PLUGINS
    plugins = []
    for plugin_cls in DEVICE_PLUGINS:
        ptype = plugin_cls.device_type_name()
        dormant = manager.is_plugin_dormant(ptype)
        plugins.append({
            "type": ptype,
            "label": plugin_cls.tab_label(),
            "description": plugin_cls.tab_description(),
            "html": plugin_cls.control_html(),
            "js": plugin_cls.control_js(),
            "dormant": dormant,
        })
    return {"plugins": plugins}


@app.post("/api/plugins/{plugin_type}/toggle")
async def api_toggle_plugin(plugin_type: str):
    """Toggle a plugin between active and dormant."""
    from .manager import DEVICE_PLUGINS
    valid_types = [p.device_type_name() for p in DEVICE_PLUGINS]
    if plugin_type not in valid_types:
        raise HTTPException(status_code=404, detail=f"Unknown plugin: {plugin_type}")

    is_dormant = manager.is_plugin_dormant(plugin_type)
    await manager.set_plugin_dormant(plugin_type, not is_dormant)
    new_state = "dormant" if not is_dormant else "active"
    return {"ok": True, "plugin": plugin_type, "state": new_state}


# ------------------------------------------------------------------
# Companion skill generation
# ------------------------------------------------------------------

@app.get("/api/partnership-profile")
async def api_get_partnership_profile():
    """Get the current partnership profile text."""
    return {"profile": manager.partnership_profile}


@app.put("/api/partnership-profile")
async def api_set_partnership_profile(body: dict):
    """Set the partnership profile text. This is human-editable relational context
    that gets prepended to the generated companion skill file."""
    profile = body.get("profile", "")
    manager.partnership_profile = str(profile)
    manager._save_config()
    return {"ok": True, "length": len(manager.partnership_profile)}


@app.post("/api/sleep-journal")
async def api_sleep_journal_write(body: dict):
    """Record a subjective sleep rating for a given night.
    Body: { "date": "YYYY-MM-DD", "rating": 1-5, "note": "optional text" }
    Rating scale: 1=terrible, 2=poor, 3=ok, 4=good, 5=excellent
    Upserts — posting twice for the same date updates the entry.
    """
    from .devices.colmi import _db_sleep_journal_upsert, DB_PATH
    date = body.get("date")
    rating = body.get("rating")
    note = body.get("note", None)
    if not date:
        return JSONResponse({"ok": False, "error": "date required (YYYY-MM-DD)"}, status_code=400)
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return JSONResponse({"ok": False, "error": "rating must be integer 1–5"}, status_code=400)
    entry = _db_sleep_journal_upsert(DB_PATH, date, rating, note)
    return {"ok": True, "entry": entry}


@app.get("/api/sleep-journal")
async def api_sleep_journal_read(date: str = Query(default=""), limit: int = Query(default=30)):
    """Get subjective sleep journal entries.
    Optional ?date=YYYY-MM-DD for a specific night, otherwise returns recent entries.
    """
    from .devices.colmi import _db_sleep_journal_get, DB_PATH
    entries = _db_sleep_journal_get(DB_PATH, date or None, limit)
    return {"entries": entries}


@app.get("/api/skill")
async def api_generate_skill(host_override: str = Query(default="")):
    """Generate a skill.md file from current server state."""
    status = manager.get_status()
    skill_md = _build_skill_md(status, host_override)
    return {"skill": skill_md}


def _partnership_section() -> str:
    """Build the partnership profile section for the skill file."""
    profile = manager.partnership_profile.strip()
    if not profile:
        return ""
    return f"""## Partnership Profile

> This section was written by the human partner. It describes the relational
> context, consent model, and preferences specific to this partnership.

{profile}

"""


def _build_skill_md(status: dict, host_override: str = "") -> str:
    """Build the companion skill markdown from live server state.

    The server writes the generic skeleton (what SymbioSync is, how to reach it,
    common endpoints). Each device plugin contributes its own section via
    skill_section() -- requests, etiquette, intensity semantics, everything
    specific to that device type.
    """
    if host_override:
        base_url = host_override.rstrip("/")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
    else:
        base_url = f"http://{_host}:{_port}"
        if _host == "0.0.0.0":
            base_url = f"http://127.0.0.1:{_port}"
    generated_at = datetime.now(timezone.utc).isoformat()

    # Group connected devices by plugin type
    connected = {addr: d for addr, d in status.get("devices", {}).items() if d.get("connected")}
    by_type: dict[str, list[dict]] = {}
    for addr, d in connected.items():
        dtype = d.get("device_type", "unknown")
        by_type.setdefault(dtype, []).append(d)

    # Collect plugin skill sections
    from .manager import DEVICE_PLUGINS
    plugin_sections = ""
    for plugin_cls in DEVICE_PLUGINS:
        ptype = plugin_cls.device_type_name()
        plugin_devices = by_type.get(ptype, [])
        # Generate section even if no devices connected (shows requests available)
        section = plugin_cls.skill_section(plugin_devices, base_url)
        if section:
            plugin_sections += section + "\n"

    # Remembered but not connected
    remembered_section = ""
    remembered = status.get("remembered", {})
    not_connected = {a: r for a, r in remembered.items() if a not in connected}
    if not_connected:
        remembered_section = "## Remembered Devices (not currently connected)\n\n"
        for addr, info in not_connected.items():
            remembered_section += f"- **{info.get('name', addr)}** (`{addr}`) - {info.get('type', 'unknown')}\n"
        remembered_section += "\n"

    skill = f"""# SymbioSync Companion Skill

> Auto-generated from a live SymbioSync instance.
> Generated at: `{generated_at}`
> Server: `{base_url}`

This skill is a snapshot. Connected/remembered device state may have changed
after generation. Check `/api/status` before acting, and inspect request result
`stage` / `truth_note` after acting. `ok: true` is not proof of hardware
acknowledgement or bodily effect. Partnership profile text is durable context,
not live consent.

## What This Is

SymbioSync is a privacy-first BLE device controller running on the human's
local machine. It talks directly to configured Bluetooth devices (health rings,
heart rate sensors, Lovense devices, etc.) with zero cloud connectivity.
Device configuration is via plugin, so any Bluetooth device can be included.
You can reach it through REST API calls.

No data leaves the local network. No accounts. No telemetry.

## How to Reach

Base URL: `{base_url}`

All endpoints accept and return JSON. Use POST for requests, GET for status.

When making a touch request, include who is reaching out when known:

```json
{{"request":"vibrate","params":{{"intensity":3,"duration":3}},"actor":"YourName","note":"optional short message"}}
```

`actor` and `note` are caller-provided and echoed in request results for visible
accountability. `actor` is self-reported, not authentication. `note` is context
for visibility; it does not override live human consent or device safety
boundaries.

### Common Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | Full device status JSON |
| POST | `/api/scan` | Attempt to discover nearby compatible Bluetooth devices |
| POST | `/api/stop` | Emergency stop all devices |
| POST | `/api/device/{{address}}/request` | Send a device request with optional `actor` and `note` |
| POST | `/api/device/{{address}}/nickname` | Rename/nickname a remembered or connected device |
| POST | `/api/restart` | Restart local device sessions and reconnect tasks without changing remembered devices or plugin config |

{_partnership_section()}{plugin_sections}{remembered_section}## Error Handling

- If a device is not connected, requests return `{{"ok": false, "error": "not connected"}}`
- If the server is unreachable, BLE may have dropped. Check `/api/status` first.
- The `stop` request is best-effort. Inspect per-device results; transport acceptance is not hardware acknowledgement.

## Notes

- This server runs locally. It is only reachable from the same machine or LAN.
- BLE range is roughly 10 meters / 30 feet. Body occlusion reduces this.
- The server auto-reconnects dropped devices when they come back in range.
- Device request envelopes and outcomes are logged locally with `request_id`,
  `source_channel`, self-reported `actor`, target alias, request, and stage.
  REST/API-originated request results are also broadcast to connected browser
  UIs so local observers can see threadborn/API touch outcomes as they happen.
"""
    return skill
