"""
Dynamic plugin discovery for habitat.

The core knows about NO device natively. Plugins live under the `plugins/`
package — each as a flat module or its own folder — and each defines one or
more `Device` subclasses. This loader scans the package, imports each entry,
and collects the subclasses. Config (`active_plugins`) then selects which of
the discovered plugins are active — config is the source of truth for what loads.

Adding a device = drop a module or folder in `plugins/` (and, if you want it
gated, name it in config). No edit to the core required.
"""

import importlib
import pkgutil
from typing import Type

from .base import Device

# Modules that are infrastructure, not plugins.
_SKIP = {"base", "loader"}


def discover_plugins() -> dict[str, Type[Device]]:
    """Scan the plugins package; return {device_type_name: PluginClass}.

    Each entry may be a flat module or its own folder (a subpackage). Import
    failures in a single plugin are swallowed so one broken plugin can't take
    down discovery of the others.
    """
    found: dict[str, Type[Device]] = {}
    pkg = importlib.import_module(__package__)  # the plugins package this loader lives in

    for modinfo in pkgutil.iter_modules(pkg.__path__):
        name = modinfo.name
        if name in _SKIP or name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__package__}.{name}")
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
