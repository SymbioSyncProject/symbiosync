# SymbioSync plugins

SymbioSync is a plugin host. The server core handles local API, WebSocket, UI
serving, config, logging, lifecycle, and dispatch. Device-specific behavior
lives in plugins.

Current plugins:

| Plugin | Kind | Maturity | Details |
|--------|------|----------|---------|
| Lovense | Actuator/control | Alpha; Ferri is the primary tested device | [plugins/lovense](lovense/) |
| Colmi | Biometric-adjacent ring/sensor | Active in-progress; useful but still being hardened | [plugins/colmi](colmi/) |

For new plugin work, start with [make-your-own](make-your-own/).

## Plugin truth rules

Every plugin must be explicit about what it actually knows.

Do not flatten these distinctions:

- current signal vs stale/cached signal
- missing signal vs zero/false/normal signal
- connected device vs remembered/previously seen device
- API command accepted vs transport write accepted vs hardware-delivered/observed
- hardware unavailable vs software failure
- consent/state valid vs merely technically possible

A plugin that touches a body, reads a body, or mediates relationship state needs
more than happy-path control. It needs visible uncertainty and honest failure.
