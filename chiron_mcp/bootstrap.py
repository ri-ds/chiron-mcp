"""Start Django in-process, exactly once, with stdout kept clean.

stdout is the MCP protocol channel.  Django system checks, warnings and any
stray print() in the processor registry would corrupt it, so everything is
redirected to stderr for the duration of setup.
"""

from __future__ import annotations

import contextlib
import os
import sys

from chiron_mcp.config import CONFIG

_READY = False


def ensure_django() -> None:
    global _READY
    if _READY:
        return

    for path in (CONFIG.project_dir, CONFIG.chiron_src):
        if path not in sys.path:
            sys.path.insert(0, path)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chiron_mcp.django_settings")

    import django

    # Chiron's AppConfig.ready() runs the processor-registry system checks and
    # prints; keep all of it off the protocol channel.
    with contextlib.redirect_stdout(sys.stderr):
        django.setup()
        # The host Chiron may lack two fixes Ask needs (chiron_mcp.chiron_patches); put
        # them in place in this process before anything builds a query.
        from chiron_mcp import chiron_patches

        chiron_patches.apply()

    _READY = True
