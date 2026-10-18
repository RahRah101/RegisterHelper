import importlib
import logging
import pkgutil
from functools import cache
from importlib.metadata import entry_points

log = logging.getLogger(__name__)

PLUGIN_GROUP = "registerhelper.adapters"


@cache  # once per process
def load_plugins() -> None:
    """Import every built-in adapter module (everything under this package) and every
    installed plugin (entry point group "registerhelper.adapters"), so their
    @register_platform runs. A broken plugin is logged and skipped; a broken built-in raises."""
    for module in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        _ = importlib.import_module(module.name)
    for ep in entry_points(group=PLUGIN_GROUP):
        try:
            _ = importlib.import_module(ep.module)
        except Exception:
            log.exception("plugin %s (%s) failed to load, skipping", ep.name, ep.value)
