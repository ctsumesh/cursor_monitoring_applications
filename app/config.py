"""Application configuration. Secrets come from the environment or a local config file."""

from __future__ import annotations

import json
import os
from pathlib import Path

# Repo root (parent of app/)
_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CONFIG = _ROOT / "config.json"
_EXAMPLE_CONFIG = _ROOT / "config.example.json"


def _config_path() -> Path:
    override = os.environ.get("MONITOR_CONFIG")
    if override:
        return Path(override)
    if _DEFAULT_CONFIG.is_file():
        return _DEFAULT_CONFIG
    return _EXAMPLE_CONFIG


def load_file_config() -> dict:
    """Load admin credentials (and optional secret_key) from JSON config."""
    path = _config_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Config file not found: {path}. Copy config.example.json to config.json."
        )
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Config file must be a JSON object")
    return data


class Config:
    """Default config for the localhost demo. DEBUG is off unless explicitly enabled."""

    _file = load_file_config()

    # Prefer env; optional secret_key in local config.json (gitignored). Never commit real secrets.
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or _file.get("secret_key")
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")

    ADMIN_USERNAME = _file.get("admin_username", "admin")
    ADMIN_PASSWORD_HASH = _file.get("admin_password_hash", "")

    # Flask-WTF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None


class TestConfig(Config):
    """Isolated config for unit tests (set ADMIN_* / SECRET_KEY in fixtures as needed)."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key-not-for-production"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD_HASH = ""  # filled by tests / conftest
