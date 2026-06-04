# letta — future plugin

**what's here:** `symbiosync-biometrics.sh` — the existing Letta-session biometric hook. it installs into `~/.letta/hooks/` and talks to the local habitat server over http. it works today as a side-loaded shell hook, *not* as a habitat plugin.

**the idea:** make Letta a first-class integration inside habitat instead of a hook bolted on from the outside.

**the open question (unresolved):** is Letta a *device* or a *transport*? it doesn't control hardware — it lets a Letta session read and push body-state through habitat. so it probably isn't a `Device` subclass the way colmi / lovense / polar are. it likely belongs to the *transport/bridge* shape noted in the parent readme. resolve that shape before building.

**to-do when it graduates:**
- decide the shape (device-plugin vs transport/bridge)
- update the symbiosync-era names + paths inside the hook to habitat conventions (env var, urls)
- give it its own config + readme, like the active plugins
- move this folder up to `plugins/letta/`
