"""Environment configuration for the Chiron MCP server.

Every knob is an environment variable so a deployment can be re-pointed without
code changes.  Defaults are deliberately the conservative end of each choice:
PHI is opt-in, the operator tool group is off, and the single write tool is off.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Chiron's own access-level codes (chiron/models/user_models.py, ChironUser.AccessLevel)
PHI = "phi"
DEID = "deid"
AGG = "agg"

# Ordered least -> most privileged, used for the ceiling comparison.
ACCESS_ORDER = [AGG, DEID, PHI]


def _flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _csv(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _discover_chiron_src() -> str:
    """Find the Chiron source tree without hardcoding anyone's home directory.

    Order: CHIRON_MCP_CHIRON_SRC, then an already-importable `chiron` package, then a
    sibling checkout next to this project. Returns "" if none found; validate() reports it.
    """
    env = os.environ.get("CHIRON_MCP_CHIRON_SRC")
    if env:
        return env

    try:  # already installed (pip install -e /path/to/is4r-chiron)
        import chiron  # noqa: F401

        return str(Path(chiron.__file__).resolve().parent.parent)
    except Exception:  # noqa: BLE001
        pass

    here = Path(__file__).resolve().parent.parent
    for candidate in (
        here / "vendor" / "is4r-chiron",
        here.parent / "is4r-chiron-develop",
        here.parent / "is4r-chiron",
        here / "is4r-chiron-develop",
    ):
        if (candidate / "chiron" / "__init__.py").exists():
            return str(candidate)
    return ""


@dataclass
class Config:
    # --- where Chiron lives -------------------------------------------------
    chiron_src: str = field(default_factory=_discover_chiron_src)
    project_dir: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_PROJECT_DIR", "")
    )
    base_settings: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_BASE_SETTINGS", "project.settings")
    )

    # --- the two databases --------------------------------------------------
    # Empty means "inherit whatever the host project's settings already say", which is
    # the right default for a fresh checkout.
    metadata_db: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_METADATA_DB", "")
    )
    warehouse_url: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_WAREHOUSE_URL", "")
    )

    # --- identity and safety ------------------------------------------------
    username: str = field(default_factory=lambda: os.environ.get("CHIRON_MCP_USERNAME", ""))
    max_access_level: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_MAX_ACCESS_LEVEL", DEID).lower()
    )
    dataset_allowlist: list[str] = field(default_factory=lambda: _csv("CHIRON_MCP_DATASETS"))
    operator: bool = field(default_factory=lambda: _flag("CHIRON_MCP_OPERATOR"))
    # Base URL of the Chiron web UI, used to build hand-off links.
    ui_url: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_UI_URL", "http://localhost:3000").rstrip("/")
    )
    allow_save: bool = field(default_factory=lambda: _flag("CHIRON_MCP_ALLOW_SAVE"))
    max_export_rows: int = field(
        default_factory=lambda: int(os.environ.get("CHIRON_MCP_MAX_EXPORT_ROWS", "50000"))
    )

    def __post_init__(self) -> None:
        if self.chiron_src and not self.project_dir:
            self.project_dir = str(Path(self.chiron_src) / "test_project")

    def validate(self) -> None:
        if not self.chiron_src:
            raise SystemExit(
                "Could not find the Chiron source tree. Set CHIRON_MCP_CHIRON_SRC to the "
                "is4r-chiron checkout (the directory containing the `chiron/` package), or "
                "pip install it into this venv."
            )
        if not Path(self.chiron_src, "chiron", "__init__.py").exists():
            raise SystemExit(
                f"CHIRON_MCP_CHIRON_SRC={self.chiron_src!r} does not contain a `chiron/` package."
            )
        if not Path(self.project_dir, "project", "settings.py").exists():
            raise SystemExit(
                f"No Django project settings at {self.project_dir!r}. Set "
                "CHIRON_MCP_PROJECT_DIR to your Chiron host project (the directory holding "
                "manage.py), and CHIRON_MCP_BASE_SETTINGS if it is not `project.settings`."
            )
        if self.metadata_db and not Path(self.metadata_db).exists():
            raise SystemExit(f"CHIRON_MCP_METADATA_DB={self.metadata_db!r} does not exist.")
        if not self.username:
            raise SystemExit(
                "CHIRON_MCP_USERNAME is required. The server binds to exactly one Django "
                "user and resolves that user's real ChironUser per dataset; there is no "
                "default identity and no autocreate."
            )
        if self.max_access_level not in ACCESS_ORDER:
            raise SystemExit(
                f"CHIRON_MCP_MAX_ACCESS_LEVEL must be one of {ACCESS_ORDER}, "
                f"got {self.max_access_level!r}"
            )


CONFIG = Config()
