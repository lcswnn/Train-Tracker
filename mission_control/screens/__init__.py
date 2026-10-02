"""Screen registry.

Importing this package auto-imports every screen module, so the
@register decorators in screens/base.py run and SCREENS is fully
populated no matter who imports first (main.py, control.py, tests...).
Helper modules (base, icons) are skipped. Adding a new screen = drop
in a new module, nothing else to touch.
"""
import importlib
import pkgutil

_SKIP = {"base", "icons"}

for _info in pkgutil.iter_modules(__path__):
    if _info.name not in _SKIP:
        importlib.import_module(f"{__name__}.{_info.name}")
