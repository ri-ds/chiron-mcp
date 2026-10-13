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

TRANSPORTS = ["stdio", "http"]
HTTP_AUTH_MODES = ["none", "oauth"]
# The address the HTTP endpoint binds unless it is hosted (Config.public_url).
HTTP_HOST = "127.0.0.1"
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


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
    # Set only by the Ask web server, and only when the identity came from a real,
    # validated Chiron login of a superuser acting as themselves. The refusal it relaxes
    # exists to stop a *service* being configured as a superuser; a person who is one
    # already has that access in Chiron's own UI. The access ceiling still applies.
    allow_superuser: bool = field(default_factory=lambda: _flag("CHIRON_MCP_ALLOW_SUPERUSER"))
    # Base URL of the Chiron web UI, used to build hand-off links.
    ui_url: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_UI_URL", "http://localhost:3000").rstrip("/")
    )
    allow_save: bool = field(default_factory=lambda: _flag("CHIRON_MCP_ALLOW_SAVE"))
    max_export_rows: int = field(
        default_factory=lambda: int(os.environ.get("CHIRON_MCP_MAX_EXPORT_ROWS", "50000"))
    )

    # --- transport ----------------------------------------------------------
    # "stdio" (the default: an MCP client launches this server as a subprocess) or
    # "http" (a long-running streamable-HTTP endpoint at /mcp).  Without OAuth the HTTP
    # endpoint has no authentication, so anyone who can reach it acts as
    # CHIRON_MCP_USERNAME; it therefore listens on the loopback interface only.
    transport: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_TRANSPORT", "stdio").strip().lower()
    )
    http_port: int = field(
        default_factory=lambda: int(os.environ.get("CHIRON_MCP_HTTP_PORT", "8765"))
    )
    # Hosted mode: the HTTPS address a web server in front publishes this server under,
    # e.g. https://chiron.example.org/chiron, serving the endpoint at <that>/mcp and the
    # sign-in beside it. Empty (the default) keeps everything on this machine.
    # validate() only allows it with OAuth on and HTTPS (http only for localhost tests).
    public_url: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_PUBLIC_URL", "").strip().rstrip("/")
    )
    # The address to listen on. Anything but loopback needs hosted mode, so the endpoint
    # is never reachable from another machine without a sign-in in front of it; in a
    # container, 0.0.0.0 with only the proxy able to reach the port.
    http_host: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_HTTP_HOST", HTTP_HOST).strip()
    )
    # "none": every caller of the HTTP endpoint acts as CHIRON_MCP_USERNAME.
    # "oauth": a caller must log in as a Chiron user first, and each tool call then acts
    # as that user, with their own access level and permission groups (chiron_mcp.oauth).
    # Ignored on stdio, where the client that launched the process is the only caller.
    http_auth: str = field(
        default_factory=lambda: os.environ.get("CHIRON_MCP_HTTP_AUTH", "none").strip().lower()
    )

    def __post_init__(self) -> None:
        if self.chiron_src and not self.project_dir:
            self.project_dir = str(Path(self.chiron_src) / "test_project")

    @property
    def oauth(self) -> bool:
        """True when callers are identified by an OAuth login rather than by config."""
        return self.transport == "http" and self.http_auth == "oauth"

    @property
    def hosted(self) -> bool:
        """True when the HTTP endpoint is published by a proxy at public_url."""
        return bool(self.public_url)

    def _validate_hosting(self) -> None:
        from urllib.parse import urlsplit

        if self.public_url:
            if not self.oauth:
                raise SystemExit(
                    "CHIRON_MCP_PUBLIC_URL needs CHIRON_MCP_TRANSPORT=http and "
                    "CHIRON_MCP_HTTP_AUTH=oauth: a published endpoint must make callers sign in."
                )
            u = urlsplit(self.public_url)
            local = (u.hostname or "") in LOOPBACK_HOSTS
            if u.scheme != "https" and not (u.scheme == "http" and local):
                raise SystemExit(
                    f"CHIRON_MCP_PUBLIC_URL={self.public_url!r} must be https:// (OAuth tokens "
                    "and passwords cross it); plain http is allowed only for localhost tests."
                )
            if u.query or u.fragment or not u.hostname:
                raise SystemExit(f"CHIRON_MCP_PUBLIC_URL={self.public_url!r} is not a plain URL.")
        if self.http_host not in LOOPBACK_HOSTS and not self.public_url:
            raise SystemExit(
                f"CHIRON_MCP_HTTP_HOST={self.http_host!r} would expose the endpoint beyond this "
                "machine; that needs hosted mode (CHIRON_MCP_PUBLIC_URL, OAuth, HTTPS)."
            )

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
        if (self.metadata_db and "://" not in self.metadata_db
                and not Path(self.metadata_db).exists()):
            raise SystemExit(f"CHIRON_MCP_METADATA_DB={self.metadata_db!r} does not exist.")
        if not self.username and not self.oauth:
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
        if self.transport not in TRANSPORTS:
            raise SystemExit(
                f"CHIRON_MCP_TRANSPORT must be one of {TRANSPORTS}, got {self.transport!r}"
            )
        if self.http_auth not in HTTP_AUTH_MODES:
            raise SystemExit(
                f"CHIRON_MCP_HTTP_AUTH must be one of {HTTP_AUTH_MODES}, got {self.http_auth!r}"
            )
        self._validate_hosting()


CONFIG = Config()
