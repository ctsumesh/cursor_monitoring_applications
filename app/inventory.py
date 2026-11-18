"""Local JSON inventory for Linux servers (CRUD). Secrets stay in gitignored data file."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.?$|^(\d{1,3}\.){3}\d{1,3}$|^localhost$"
)
_lock = threading.Lock()


def default_inventory_path() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / "data" / "servers.json"


class InventoryError(ValueError):
    """Validation or persistence error for inventory operations."""


def _safe_log_server(server: dict[str, Any]) -> dict[str, Any]:
    """Return a copy safe for logs (never include password or key material)."""
    return {
        "id": server.get("id"),
        "name": server.get("name"),
        "host": server.get("host"),
        "port": server.get("port"),
        "username": server.get("username"),
        "auth_type": server.get("auth_type"),
        "key_path": server.get("key_path") or None,
    }


def validate_server_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    """Validate and normalize server fields. Raises InventoryError on bad input."""
    out: dict[str, Any] = {}

    def require(key: str) -> Any:
        if key not in data or data[key] is None or str(data[key]).strip() == "":
            if partial and key not in data:
                return None
            raise InventoryError(f"Missing or empty field: {key}")
        return data[key]

    name = require("name")
    if name is not None:
        name = str(name).strip()
        if len(name) > 120:
            raise InventoryError("Name too long (max 120)")
        out["name"] = name

    host = require("host")
    if host is not None:
        host = str(host).strip()
        if not _HOST_RE.match(host):
            raise InventoryError("Invalid host (use hostname, localhost, or IPv4)")
        out["host"] = host

    if "port" in data or not partial:
        raw_port = data.get("port", 22)
        try:
            port = int(raw_port)
        except (TypeError, ValueError) as exc:
            raise InventoryError("SSH port must be an integer") from exc
        if port < 1 or port > 65535:
            raise InventoryError("SSH port must be between 1 and 65535")
        out["port"] = port

    username = require("username")
    if username is not None:
        username = str(username).strip()
        if len(username) > 64 or any(c in username for c in " \t\n\r"):
            raise InventoryError("Invalid SSH username")
        out["username"] = username

    auth_type = data.get("auth_type", "password" if not partial else None)
    if auth_type is not None:
        auth_type = str(auth_type).strip().lower()
        if auth_type not in ("password", "key"):
            raise InventoryError("auth_type must be 'password' or 'key'")
        out["auth_type"] = auth_type

    # Secrets: accept but never log
    if "password" in data:
        out["password"] = "" if data.get("password") is None else str(data.get("password"))
    if "key_path" in data:
        key_path = "" if data.get("key_path") is None else str(data.get("key_path")).strip()
        if key_path:
            p = Path(key_path).expanduser()
            if ".." in Path(key_path).parts or ".." in p.parts:
                raise InventoryError("Invalid key_path")
            if not (key_path.startswith("/") or key_path.startswith("~/")):
                raise InventoryError("key_path must be absolute or start with ~/")
        out["key_path"] = key_path

    if not partial:
        auth = out.get("auth_type", "password")
        if auth == "password" and not out.get("password"):
            raise InventoryError("Password required when auth_type is password")
        if auth == "key" and not out.get("key_path"):
            raise InventoryError("key_path required when auth_type is key")

    return out


class ServerInventory:
    """Thread-safe JSON-backed server inventory."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else default_inventory_path()

    def _read(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise InventoryError("Inventory file must be a JSON list")
        return data

    def _write(self, servers: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(servers, fh, indent=2)
            fh.write("\n")
        tmp.replace(self.path)

    def list_servers(self) -> list[dict[str, Any]]:
        with _lock:
            return deepcopy(self._read())

    def get(self, server_id: str) -> dict[str, Any] | None:
        with _lock:
            for item in self._read():
                if item.get("id") == server_id:
                    return deepcopy(item)
        return None

    def add(self, payload: dict[str, Any]) -> dict[str, Any]:
        fields = validate_server_payload(payload, partial=False)
        server = {
            "id": str(uuid.uuid4()),
            "name": fields["name"],
            "host": fields["host"],
            "port": fields["port"],
            "username": fields["username"],
            "auth_type": fields["auth_type"],
            "password": fields.get("password", ""),
            "key_path": fields.get("key_path", ""),
            "last_metrics": None,
            "last_error": None,
            "last_refreshed_at": None,
        }
        with _lock:
            servers = self._read()
            servers.append(server)
            self._write(servers)
        logger.info("Added server %s", _safe_log_server(server))
        return deepcopy(server)

    def update(self, server_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        fields = validate_server_payload(payload, partial=True)
        with _lock:
            servers = self._read()
            for idx, item in enumerate(servers):
                if item.get("id") != server_id:
                    continue
                updated = deepcopy(item)
                for key, value in fields.items():
                    if key == "password" and value == "":
                        # Keep existing password when form left blank
                        continue
                    updated[key] = value
                # Re-validate auth completeness on merged record
                validate_server_payload(
                    {
                        "name": updated["name"],
                        "host": updated["host"],
                        "port": updated["port"],
                        "username": updated["username"],
                        "auth_type": updated["auth_type"],
                        "password": updated.get("password") or "x"
                        if updated["auth_type"] == "password"
                        else "",
                        "key_path": updated.get("key_path", ""),
                    },
                    partial=False,
                )
                servers[idx] = updated
                self._write(servers)
                logger.info("Updated server %s", _safe_log_server(updated))
                return deepcopy(updated)
        raise InventoryError("Server not found")

    def delete(self, server_id: str) -> None:
        with _lock:
            servers = self._read()
            new_list = [s for s in servers if s.get("id") != server_id]
            if len(new_list) == len(servers):
                raise InventoryError("Server not found")
            self._write(new_list)
        logger.info("Deleted server id=%s", server_id)

    def save_metrics(
        self,
        server_id: str,
        metrics: dict[str, Any] | None,
        error: str | None,
        refreshed_at: str,
    ) -> dict[str, Any]:
        with _lock:
            servers = self._read()
            for idx, item in enumerate(servers):
                if item.get("id") != server_id:
                    continue
                updated = deepcopy(item)
                updated["last_metrics"] = metrics
                updated["last_error"] = error
                updated["last_refreshed_at"] = refreshed_at
                servers[idx] = updated
                self._write(servers)
                return deepcopy(updated)
        raise InventoryError("Server not found")
