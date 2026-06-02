"""
Dynamic plugin discovery for SymbioSync.

The core knows about NO device natively. Plugins live as modules under
`symbiosync/devices/`; each defines one or more `Device` subclasses. This
loader scans that package, imports each module, and collects the subclasses.
Config (`enabled_plugins`) then selects which of the discovered plugins are
active — config is the source of truth for what loads.

Adding a device = drop a module in `devices/` (and, if you want it gated,
name it in config). No edit to the core required.
"""

import importlib
import pkgutil
from typing import Type

from .base import Device

# Modules that are infrastructure, not plugins.
_SKIP = {"base", "loader"}


def discover_plugins() -> dict[str, Type[Device]]:
    """Scan the devices package; return {device_type_name: PluginClass}.

    Import failures in a single plugin module are swallowed so one broken
    plugin can't take down discovery of the others.
    """
    found: dict[str, Type[Device]] = {}
    import symbiosync.devices as pkg

    for modinfo in pkgutil.iter_modules(pkg.__path__):
        name = modinfo.name
        if name in _SKIP or name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"symbiosync.devices.{name}")
        except Exception:
            continue
        for obj in vars(mod).values():
            if (
                isinstance(obj, type)
                and issubclass(obj, Device)
                and obj is not Device
            ):
                try:
                    found[obj.device_type_name()] = obj
                except Exception:
                    # Subclass that doesn't implement device_type_name() — skip.
                    pass
    return found


def load_plugins(enabled: list[str] | None = None) -> list[Type[Device]]:
    """Return discovered plugin classes.

    enabled=None  -> every discovered plugin (the full installed pool).
    enabled=[...] -> only those whose device_type_name() is in the list,
                     in the order given (config as source of truth).
    """
    discovered = discover_plugins()
    if enabled is None:
        return list(discovered.values())
    return [discovered[name] for name in enabled if name in discovered]
